"""Web push to the StoxSonar app on your own devices, sent from a GitHub Actions run.

There is no server. The app (site/app/) asks the phone or browser for a push
subscription and shows it; you paste it into the Actions secret PUSH_SUBS. Each
run signs a message with the VAPID private key (secret VAPID_PRIVATE_KEY) and
hands it to Apple's, Microsoft's or Google's push service, which delivers it.

Payloads are encrypted for each device (RFC 8291, aes128gcm) and the request is
signed with a VAPID token (RFC 8292), using only the `cryptography` package.

    python -m sonar.push keygen          # once: prints a new key pair
    python -m sonar.push daily --site site
    python -m sonar.push test

A subscription that the push service reports as gone (HTTP 404/410) means the
app was removed or iOS dropped it. The run then posts a Telegram warning so a
dead alert channel never goes unnoticed.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import struct
import sys
import time
from datetime import date
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger("stoxsonar.push")

# Sent to push services as the contact for this sender; a public URL, nothing personal
VAPID_SUBJECT = "https://raghavendar002.github.io/StoxSonar/"
APP_URL = "./"          # opened when the notification is tapped, relative to the app
RECORD_SIZE = 4096
TTL_SECONDS = 20 * 3600  # an evening alert is useless after the next session


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _point(pub: ec.EllipticCurvePublicKey) -> bytes:
    return pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def private_key(raw_b64u: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(unb64u(raw_b64u), "big"), ec.SECP256R1())


def public_key_b64u(raw_b64u: str) -> str:
    return b64u(_point(private_key(raw_b64u).public_key()))


def keygen() -> tuple:
    """(private, public) as base64url: the raw 32-byte scalar and the 65-byte point."""
    k = ec.generate_private_key(ec.SECP256R1())
    return b64u(k.private_numbers().private_value.to_bytes(32, "big")), b64u(_point(k.public_key()))


def _hkdf(salt: bytes, ikm: bytes, info: bytes, n: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=n, salt=salt, info=info).derive(ikm)


def encrypt(payload: bytes, p256dh: str, auth: str, salt: Optional[bytes] = None,
            sender: Optional[ec.EllipticCurvePrivateKey] = None) -> bytes:
    """RFC 8291 message encryption: one aes128gcm record for this device."""
    ua_pub_bytes = unb64u(p256dh)
    ua_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub_bytes)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    as_pub_bytes = _point(sender.public_key())
    salt = salt or os.urandom(16)
    shared = sender.exchange(ec.ECDH(), ua_pub)
    ikm = _hkdf(unb64u(auth), shared, b"WebPush: info\x00" + ua_pub_bytes + as_pub_bytes, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    if len(payload) > RECORD_SIZE - 16 - 1 - 86:
        raise ValueError("push payload too long")
    body = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    header = salt + struct.pack("!L", RECORD_SIZE) + bytes([len(as_pub_bytes)]) + as_pub_bytes
    return header + body


def vapid_header(endpoint: str, raw_private: str, now: Optional[float] = None) -> str:
    """RFC 8292 `Authorization: vapid t=<JWT>, k=<public key>` for this push service."""
    u = urlparse(endpoint)
    claims = {"aud": f"{u.scheme}://{u.netloc}", "exp": int((now or time.time()) + 12 * 3600),
              "sub": VAPID_SUBJECT}
    head = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64u(json.dumps(claims, separators=(",", ":")).encode())
    key = private_key(raw_private)
    r, s = decode_dss_signature(key.sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256())))
    sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={head}.{body}.{sig}, k={b64u(_point(key.public_key()))}"


def parse_subs(text: str) -> list:
    """PUSH_SUBS holds one subscription per line (or a JSON list), as the app's Copy button gives it."""
    text = (text or "").strip()
    if not text:
        return []
    if text.startswith("["):
        items = json.loads(text)
    else:
        items = [json.loads(line) for line in text.splitlines() if line.strip()]
    out = []
    for s in items:
        if s.get("endpoint") and s.get("keys", {}).get("p256dh") and s["keys"].get("auth"):
            out.append(s)
        else:
            log.warning("skipping a subscription without endpoint or keys")
    return out


def _name(sub: dict) -> str:
    """Which device, for the log. Endpoints are bearer URLs, so the public log never shows one."""
    return sub.get("device") or urlparse(sub["endpoint"]).netloc


def send(subs: Iterable[dict], message: dict, raw_private: str, post=None) -> dict:
    """Push one message to every subscription. Returns {"sent": [...], "gone": [...], "failed": [...]}."""
    if post is None:
        import requests
        post = requests.post
    payload = json.dumps(message, separators=(",", ":")).encode()
    res = {"sent": [], "gone": [], "failed": []}
    for sub in subs:
        name = _name(sub)
        try:
            r = post(sub["endpoint"], data=encrypt(payload, sub["keys"]["p256dh"], sub["keys"]["auth"]),
                     headers={"Authorization": vapid_header(sub["endpoint"], raw_private),
                              "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
                              "TTL": str(TTL_SECONDS), "Urgency": "high"}, timeout=30)
        except Exception as exc:          # network trouble: report, never print the endpoint
            log.warning("push to %s failed: %s", name, type(exc).__name__)
            res["failed"].append(name)
            continue
        code = r.status_code
        if code in (200, 201, 202):
            res["sent"].append(name)
        elif code in (404, 410):
            res["gone"].append(name)
        else:
            log.warning("push to %s refused with HTTP %s", name, code)
            res["failed"].append(name)
    log.info("push: %d sent, %d gone, %d failed", len(res["sent"]), len(res["gone"]), len(res["failed"]))
    return res


def _day(as_of: str) -> str:
    d = date.fromisoformat(as_of)
    return f"{d.day} {d.strftime('%b')}"


def daily_message(s: dict) -> dict:
    """The evening alert, built from the same snapshot as the page and the Telegram post."""
    buys = s.get("buys_allowed", True)
    ups = s.get("breakouts") or []
    downs = s.get("breakdowns") or []
    a_ups = [r for r in ups if r["grade"] == "A"]
    if not buys:
        head = f"{s['regime']} market, no new buys."
    elif a_ups:
        head = f"{len(a_ups)} Grade A breakout{'s' if len(a_ups) > 1 else ''}: " + ", ".join(r["symbol"] for r in a_ups) + "."
    elif ups:
        head = f"{len(ups)} Grade B breakout{'s' if len(ups) > 1 else ''} (watchlist): " + ", ".join(r["symbol"] for r in ups[:4]) + "."
    else:
        head = "No new breakouts."
    parts = [head]
    if not buys and ups:
        parts.append(f"{len(ups)} breakout{'s' if len(ups) > 1 else ''} logged only.")
    if downs:
        parts.append(f"{len(downs)} breakdown{'s' if len(downs) > 1 else ''}.")
    closed = s.get("closed_today") or []
    if closed:
        parts.append("Closed: " + ", ".join(f"{r['symbol']} {r['status'].lower()}" for r in closed[:3]) + ".")
    opened = [r for r in s.get("open_signals") or [] if r["direction"] == "up"]
    if opened:
        parts.append(f"{len(opened)} open.")
    return {"title": f"StoxSonar · {_day(s['as_of'])}", "body": " ".join(parts),
            "url": APP_URL, "tag": f"daily-{s['as_of']}"}


def run(message: dict, warn_telegram: bool = True) -> int:
    raw = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    subs = parse_subs(os.environ.get("PUSH_SUBS", ""))
    if not raw or not subs:
        log.info("push not set up (VAPID_PRIVATE_KEY or PUSH_SUBS missing); skipping")
        return 0
    res = send(subs, message, raw)
    if res["gone"] and warn_telegram:
        from sonar import publish
        publish.send_telegram(
            "StoxSonar app alerts stopped on: " + ", ".join(res["gone"]) + ".\n"
            "Open the app from its home-screen icon, go to Settings, tap Turn on alerts, "
            "copy the new code and replace the old line in the PUSH_SUBS secret.")
    return 0 if res["sent"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["daily", "test", "keygen"])
    ap.add_argument("--site", type=Path, default=Path(__file__).resolve().parent.parent / "site")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.what == "keygen":
        priv, pub = keygen()
        print(f"VAPID_PRIVATE_KEY (secret, never commit): {priv}\npublic key (site/app/vapid.json): {pub}")
        return 0
    if a.what == "test":
        msg = {"title": "StoxSonar · test", "body": "Alerts work on this device.", "url": APP_URL, "tag": "test"}
        return run(msg, warn_telegram=True)
    snap = json.loads(re.sub(r"\bNaN\b", "null", (a.site / "data.json").read_text(encoding="utf-8")))
    return run(daily_message(snap))


if __name__ == "__main__":
    sys.exit(main())
