"""
Unit tests for Public & Private Key Cryptography concepts described in README.md.

Covers:
  - RSA encryption / decryption
  - RSA data integrity check (encrypt → decrypt → match)
  - SHA-256 checksum (determinism, collision-resistance, one-way property)
  - RSA digital signature (sign with private key, verify with public key)
  - Ed25519 digital signature (sign with private key, verify with public key)

Dependencies (stdlib only — no third-party packages required except cryptography):
  pip install cryptography

Run tests:
    python -m unittest test_cryptography.py
"""

import hashlib
import unittest

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_rsa_key_pair(key_size: int = 2048) -> tuple[RSAPrivateKey, RSAPublicKey]:
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size)
    return private_key, private_key.public_key()


def sha256_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------

class TestRSAEncryptionDecryption(unittest.TestCase):
    """Secrecy guarantee: public key encrypts, private key decrypts."""

    def setUp(self):
        self.private_key, self.public_key = generate_rsa_key_pair()
        self._padding = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )

    def _encrypt(self, plaintext: bytes) -> bytes:
        return self.public_key.encrypt(plaintext, self._padding)

    def _decrypt(self, ciphertext: bytes) -> bytes:
        return self.private_key.decrypt(ciphertext, self._padding)

    # -- basic round-trip ------------------------------------------------

    def test_encrypt_produces_ciphertext(self):
        """Ciphertext must differ from the original plaintext."""
        plaintext = b"Transfer 1000 EUR to Alice"
        ciphertext = self._encrypt(plaintext)
        self.assertNotEqual(plaintext, ciphertext)

    def test_decrypt_restores_original_message(self):
        """Decrypting the ciphertext must reproduce the exact plaintext."""
        plaintext = b"Transfer 1000 EUR to Alice"
        ciphertext = self._encrypt(plaintext)
        recovered = self._decrypt(ciphertext)
        self.assertEqual(plaintext, recovered)

    def test_data_integrity_match(self):
        """The decrypted message must be byte-for-byte identical to the original."""
        original = b"Secret payload: \x00\x01\x02\xff"
        self.assertEqual(original, self._decrypt(self._encrypt(original)))

    # -- wrong key -------------------------------------------------------

    def test_wrong_private_key_cannot_decrypt(self):
        """A different private key must not be able to decrypt the message."""
        from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
        import cryptography.exceptions

        plaintext = b"Only Bob can read this"
        ciphertext = self._encrypt(plaintext)

        other_private, _ = generate_rsa_key_pair()

        with self.assertRaises(Exception):
            other_private.decrypt(ciphertext, self._padding)

    # -- OAEP is probabilistic -------------------------------------------

    def test_same_plaintext_gives_different_ciphertexts(self):
        """OAEP padding is randomised: two encryptions of the same message differ."""
        plaintext = b"Determinism test"
        ct1 = self._encrypt(plaintext)
        ct2 = self._encrypt(plaintext)
        self.assertNotEqual(ct1, ct2)


class TestSHA256Checksum(unittest.TestCase):
    """Hash-function properties: determinism, sensitivity, one-way."""

    def test_same_input_same_hash(self):
        """SHA-256 is deterministic: identical inputs produce identical hashes."""
        data = b"Transfer 1000 EUR to Alice"
        self.assertEqual(sha256_checksum(data), sha256_checksum(data))

    def test_different_input_different_hash(self):
        """A single-byte change produces a completely different hash."""
        h1 = sha256_checksum(b"Transfer 1000 EUR to Alice")
        h2 = sha256_checksum(b"Transfer 9000 EUR to Alice")
        self.assertNotEqual(h1, h2)

    def test_hash_length_is_256_bits(self):
        """SHA-256 always outputs exactly 64 hex characters (256 bits)."""
        for msg in (b"", b"hello", b"x" * 10_000):
            self.assertEqual(len(sha256_checksum(msg)), 64)

    def test_empty_string_has_known_hash(self):
        """Verify the well-known SHA-256 of an empty byte string."""
        known = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertEqual(sha256_checksum(b""), known)

    def test_hash_is_hex_string(self):
        """The checksum must be a lowercase hexadecimal string."""
        result = sha256_checksum(b"test")
        self.assertRegex(result, r"^[0-9a-f]{64}$")


class TestRSADigitalSignature(unittest.TestCase):
    """Authenticity guarantee: private key signs, public key verifies (RSA-PSS)."""

    def setUp(self):
        self.private_key, self.public_key = generate_rsa_key_pair()
        self._padding = padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        )
        self._hash_algo = hashes.SHA256()

    def _sign(self, message: bytes) -> bytes:
        return self.private_key.sign(message, self._padding, self._hash_algo)

    def _verify(self, signature: bytes, message: bytes):
        self.public_key.verify(
            signature, message, self._padding, self._hash_algo)

    # -- happy path ------------------------------------------------------

    def test_valid_signature_verifies(self):
        """A signature produced with the private key must pass public-key verification."""
        message = b"Bob approves this document"
        signature = self._sign(message)
        # verify() raises an exception on failure; no exception means success
        self._verify(signature, message)

    def test_signature_is_not_the_message(self):
        """The signature must differ from the raw message."""
        message = b"Some document"
        self.assertNotEqual(message, self._sign(message))

    # -- tampered message ------------------------------------------------

    def test_tampered_message_fails_verification(self):
        """Modifying even one byte of the message must invalidate the signature."""
        from cryptography.exceptions import InvalidSignature

        message = b"Transfer 1000 EUR to Alice"
        signature = self._sign(message)
        tampered = b"Transfer 9000 EUR to Alice"

        with self.assertRaises(InvalidSignature):
            self._verify(signature, tampered)

    # -- wrong key -------------------------------------------------------

    def test_wrong_public_key_fails_verification(self):
        """A different public key must not verify a signature it did not produce."""
        from cryptography.exceptions import InvalidSignature

        _, other_public = generate_rsa_key_pair()
        message = b"Authentic message"
        signature = self._sign(message)

        with self.assertRaises(InvalidSignature):
            other_public.verify(signature, message,
                                self._padding, self._hash_algo)


class TestEd25519DigitalSignature(unittest.TestCase):
    """Same authenticity guarantee with modern Ed25519 (ECC-based)."""

    def setUp(self):
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    # -- happy path ------------------------------------------------------

    def test_valid_signature_verifies(self):
        """Ed25519 signature must verify against the correct public key."""
        message = b"Ed25519: fast and compact"
        signature = self.private_key.sign(message)
        # No exception → valid
        self.public_key.verify(signature, message)

    def test_signature_size_is_64_bytes(self):
        """Ed25519 signatures are always exactly 64 bytes."""
        sig = self.private_key.sign(b"size check")
        self.assertEqual(len(sig), 64)

    def test_public_key_size_is_32_bytes(self):
        """Ed25519 public keys are always exactly 32 bytes."""
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.assertEqual(len(raw), 32)

    # -- tampered message ------------------------------------------------

    def test_tampered_message_fails_verification(self):
        """Any change to the message must invalidate the Ed25519 signature."""
        from cryptography.exceptions import InvalidSignature

        message = b"Original content"
        signature = self.private_key.sign(message)

        with self.assertRaises(InvalidSignature):
            self.public_key.verify(signature, b"Tampered content")

    # -- wrong key -------------------------------------------------------

    def test_wrong_public_key_fails_verification(self):
        """A different Ed25519 public key must not accept the signature."""
        from cryptography.exceptions import InvalidSignature

        other_private = ed25519.Ed25519PrivateKey.generate()
        other_public = other_private.public_key()

        message = b"Message from original owner"
        signature = self.private_key.sign(message)

        with self.assertRaises(InvalidSignature):
            other_public.verify(signature, message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
