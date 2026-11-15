import json
import os
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from sonar import push


def _device():
    """A fake browser: its key pair and auth secret, as a real subscription would carry them."""
    k = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    sub = {"endpoint": "https://web.push.apple.com/QAbc123", "device": "iPhone",
           "keys": {"p256dh": push.b64u(push._point(k.public_key())), "auth": push.b64u(auth)}}
    return k, auth, sub


def _decrypt(body: bytes, k, auth: bytes) -> bytes:
    """The receiving side of RFC 8291, written out separately from the sender."""
    salt, rs, idlen = body[:16], struct.unpack("!L", body[16:20])[0], body[20]
    as_pub = body[21:21 + idlen]
    assert rs == 4096 and idlen == 65
    shared = k.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    ua_pub = push._point(k.public_key())
    hk = lambda s, i, n, info: HKDF(hashes.SHA256(), n, s, info).derive(i)
    ikm = hk(auth, shared, 32, b"WebPush: info\x00" + ua_pub + as_pub)
    cek = hk(salt, ikm, 16, b"Content-Encoding: aes128gcm\x00")
    nonce = hk(salt, ikm, 12, b"Content-Encoding: nonce\x00")
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert plain.endswith(b"\x02")
    return plain[:-1]


def test_encrypt_round_trip():
    k, auth, sub = _device()
    msg = json.dumps({"title": "StoxSonar · 13 Nov", "body": "Weak market, no new buys."}).encode()
    body = push.encrypt(msg, sub["keys"]["p256dh"], sub["keys"]["auth"])
    assert _decrypt(body, k, auth) == msg


def test_vapid_token_verifies_against_public_key():
    priv, pub = push.keygen()
    assert push.public_key_b64u(priv) == pub
    hdr = push.vapid_header("https://web.push.apple.com/QAbc123", priv, now=1_000_000)
    t, k = hdr[len("vapid t="):].split(", k=")
    assert k == pub
    head, claims, sig = t.split(".")
    c = json.loads(push.unb64u(claims))
    assert c["aud"] == "https://web.push.apple.com" and c["exp"] == 1_000_000 + 12 * 3600
    assert c["sub"].startswith("https://")
    raw = push.unb64u(sig)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    pubkey = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), push.unb64u(pub))
    pubkey.verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))   # raises if wrong


class _Resp:
    def __init__(self, code):
        self.status_code = code


def test_send_sorts_sent_gone_failed_and_never_needs_network():
    priv, _ = push.keygen()
    subs = [_device()[2] for _ in range(3)]
    for s, name in zip(subs, ["iPhone", "Laptop", "Old"]):
        s["device"] = name
    codes = iter([201, 500, 410])
    seen = []

    def post(url, data, headers, timeout):
        seen.append(headers)
        return _Resp(next(codes))

    res = push.send(subs, {"title": "t", "body": "b"}, priv, post=post)
    assert res == {"sent": ["iPhone"], "gone": ["Old"], "failed": ["Laptop"]}
    assert all(h["Content-Encoding"] == "aes128gcm" and h["Authorization"].startswith("vapid t=") for h in seen)


def test_parse_subs_lines_and_list():
    _, _, a = _device()
    _, _, b = _device()
    lines = json.dumps(a) + "\n\n" + json.dumps(b) + "\n"
    assert len(push.parse_subs(lines)) == 2
    assert len(push.parse_subs(json.dumps([a, {"endpoint": "x"}]))) == 1
    assert push.parse_subs("") == []


def test_daily_message_weak_market():
    snap = {"as_of": "2026-11-13", "regime": "Weak", "buys_allowed": False,
            "breakouts": [{"symbol": "AMANTA", "grade": "B", "direction": "up"}], "breakdowns": [],
            "closed_today": [], "open_signals": [{"direction": "up"}, {"direction": "down"}]}
    m = push.daily_message(snap)
    assert m["title"] == "StoxSonar · 13 Nov"
    assert m["body"] == "Weak market, no new buys. 1 breakout logged only. 1 open."


def test_daily_message_grade_a():
    snap = {"as_of": "2026-11-03", "regime": "Healthy", "buys_allowed": True,
            "breakouts": [{"symbol": "X", "grade": "A"}, {"symbol": "Y", "grade": "B"}],
            "breakdowns": [], "closed_today": [{"symbol": "Z", "status": "Confirmed"}], "open_signals": []}
    assert push.daily_message(snap)["body"] == "1 Grade A breakout: X. Closed: Z confirmed."
