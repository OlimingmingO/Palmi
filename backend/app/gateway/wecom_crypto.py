"""WeCom message encryption and decryption.

Forked from Hermes Agent gateway/platforms/wecom_crypto.py.
Implements the same wire format as Tencent's official ``WXBizMsgCrypt``
SDK so that WeCom can verify, encrypt, and decrypt callback payloads.

Spec: AES-CBC-256 with PKCS#7 padding (block_size=32).
Signature: SHA1(sort([token, timestamp, nonce, encrypt_msg])).
Encoding key: 43-char Base64 string → 32-byte AES key + 4-byte spare.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import socket
import struct
import time
from typing import Optional
from xml.etree import ElementTree as ET

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WeComCryptoError(Exception):
    pass


class SignatureError(WeComCryptoError):
    pass


class DecryptError(WeComCryptoError):
    pass


class EncryptError(WeComCryptoError):
    pass


# ---------------------------------------------------------------------------
# PKCS#7 padding (block_size=32, per WeCom spec)
# ---------------------------------------------------------------------------

class PKCS7Encoder:
    block_size = 32

    @classmethod
    def encode(cls, text: bytes) -> bytes:
        amount_to_pad = cls.block_size - (len(text) % cls.block_size)
        if amount_to_pad == 0:
            amount_to_pad = cls.block_size
        pad = bytes([amount_to_pad]) * amount_to_pad
        return text + pad

    @classmethod
    def decode(cls, decrypted: bytes) -> bytes:
        if not decrypted:
            raise DecryptError("empty decrypted payload")
        pad = decrypted[-1]
        if pad < 1 or pad > cls.block_size:
            raise DecryptError("invalid PKCS7 padding")
        if decrypted[-pad:] != bytes([pad]) * pad:
            raise DecryptError("malformed PKCS7 padding")
        return decrypted[:-pad]


# ---------------------------------------------------------------------------
# Signature helper
# ---------------------------------------------------------------------------

def _sha1_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    parts = sorted([token, timestamp, nonce, encrypt])
    return hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Core crypto class
# ---------------------------------------------------------------------------

class WXBizMsgCrypt:
    """Minimal WeCom callback crypto helper compatible with BizMsgCrypt semantics."""

    def __init__(self, token: str, encoding_aes_key: str, receive_id: str):
        if not token:
            raise ValueError("token is required")
        if not encoding_aes_key:
            raise ValueError("encoding_aes_key is required")
        if len(encoding_aes_key) != 43:
            raise ValueError("encoding_aes_key must be 43 chars")
        if not receive_id:
            raise ValueError("receive_id is required")

        self.token = token
        self.receive_id = receive_id
        self.key = base64.b64decode(encoding_aes_key + "=")
        self.iv = self.key[:16]

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """Decrypt *echostr* for WeCom URL-verification handshake."""
        plain = self.decrypt(msg_signature, timestamp, nonce, echostr)
        return plain.decode("utf-8")

    def decrypt(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> bytes:
        """Verify signature and decrypt an encrypted payload.

        Returns the inner XML content as raw bytes.
        """
        expected = _sha1_signature(self.token, timestamp, nonce, encrypt)
        if expected != msg_signature:
            raise SignatureError("signature mismatch")
        try:
            cipher_text = base64.b64decode(encrypt)
        except Exception as exc:
            raise DecryptError(f"invalid base64 payload: {exc}") from exc
        try:
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded = decryptor.update(cipher_text) + decryptor.finalize()
            plain = PKCS7Encoder.decode(padded)
            content = plain[16:]  # skip 16-byte random prefix
            xml_length = socket.ntohl(struct.unpack("I", content[:4])[0])
            xml_content = content[4:4 + xml_length]
            receive_id = content[4 + xml_length:].decode("utf-8")
        except WeComCryptoError:
            raise
        except Exception as exc:
            raise DecryptError(f"decrypt failed: {exc}") from exc

        if receive_id != self.receive_id:
            raise DecryptError("receive_id mismatch")
        return xml_content

    def encrypt(self, plaintext: str, nonce: Optional[str] = None, timestamp: Optional[str] = None) -> str:
        """Encrypt *plaintext* and wrap in a signed XML envelope."""
        nonce = nonce or self._random_nonce()
        timestamp = timestamp or str(int(time.time()))
        encrypt = self._encrypt_bytes(plaintext.encode("utf-8"))
        signature = _sha1_signature(self.token, timestamp, nonce, encrypt)
        root = ET.Element("xml")
        ET.SubElement(root, "Encrypt").text = encrypt
        ET.SubElement(root, "MsgSignature").text = signature
        ET.SubElement(root, "TimeStamp").text = timestamp
        ET.SubElement(root, "Nonce").text = nonce
        return ET.tostring(root, encoding="unicode")

    def _encrypt_bytes(self, raw: bytes) -> str:
        try:
            random_prefix = os.urandom(16)
            msg_len = struct.pack("I", socket.htonl(len(raw)))
            payload = random_prefix + msg_len + raw + self.receive_id.encode("utf-8")
            padded = PKCS7Encoder.encode(payload)
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded) + encryptor.finalize()
            return base64.b64encode(encrypted).decode("utf-8")
        except Exception as exc:
            raise EncryptError(f"encrypt failed: {exc}") from exc

    @staticmethod
    def _random_nonce(length: int = 10) -> str:
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# Convenience functions (thin wrappers around WXBizMsgCrypt)
# ---------------------------------------------------------------------------

def verify_signature(
    token: str,
    encoding_aes_key: str,
    receive_id: str,
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str,
) -> str:
    """Decrypt *echostr* for WeCom URL-verification handshake.

    Returns the decrypted plain-text echo string that should be sent
    back to WeCom to complete URL verification.
    """
    crypt = WXBizMsgCrypt(token, encoding_aes_key, receive_id)
    return crypt.verify_url(msg_signature, timestamp, nonce, echostr)


def decrypt_message(
    token: str,
    encoding_aes_key: str,
    receive_id: str,
    encrypted_msg: str,
    msg_signature: str,
    timestamp: str,
    nonce: str,
) -> str:
    """Decrypt an incoming WeCom callback message.

    *encrypted_msg* is the ``<Encrypt>`` element value from the callback
    XML body.  Returns the decrypted inner XML as a string.
    """
    crypt = WXBizMsgCrypt(token, encoding_aes_key, receive_id)
    return crypt.decrypt(msg_signature, timestamp, nonce, encrypted_msg).decode("utf-8")


def encrypt_message(
    token: str,
    encoding_aes_key: str,
    receive_id: str,
    reply_msg: str,
    nonce: Optional[str] = None,
) -> str:
    """Encrypt an outgoing reply message.

    Returns a complete XML envelope string ready to be sent back as an
    HTTP response body (passive reply mode).
    """
    crypt = WXBizMsgCrypt(token, encoding_aes_key, receive_id)
    return crypt.encrypt(reply_msg, nonce=nonce)
