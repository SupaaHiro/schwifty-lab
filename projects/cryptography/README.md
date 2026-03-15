# Public & Private Key Cryptography

> **Internal Knowledge Base** | Security Fundamentals

---

## Overview

Public-key cryptography (also known as **asymmetric cryptography**) is the mathematical foundation
of modern secure communication. Every key pair consists of two mathematically linked keys:

| Key | Visibility | Role |
|-----|------------|------|
| **Public key** | Shared freely with anyone | Encrypt messages, verify signatures |
| **Private key** | Never leaves the owner | Decrypt messages, create signatures |

The two are linked by a one-way mathematical relationship: knowing the public key gives you
essentially zero ability to derive the private key. This asymmetry is what makes the whole
system work.

---

## Two Guarantees

Asymmetric cryptography provides two distinct security properties, each relying on the key
pair in a different — and almost opposite — way.

### 1. Secrecy — via Encryption

**The public key acts like a padlock.**

Anyone can snap it shut. Only the owner of the private key can open it.

```
Alice wants to send a secret message to Bob
  │
  ├─ Alice fetches Bob's PUBLIC key  (freely available)
  ├─ Alice encrypts the message with it  ← anyone can do this
  │
  └─ Only Bob's PRIVATE key can decrypt it  ← Bob is the only one who can read it
```

- The public key **locks** (encrypts).
- The private key **unlocks** (decrypts).
- Even Alice, who encrypted the message, cannot decrypt it afterwards.

---

### 2. Authenticity — via Digital Signature

**The private key acts like a notary stamp.**

Only the owner can apply it. Anyone can verify it is genuine.

```
Bob wants to prove a document really came from him
  │
  ├─ Bob computes a hash of the document  (e.g. SHA-256)
  ├─ Bob signs the hash with his PRIVATE key  ← only Bob can do this
  │
  └─ Anyone with Bob's PUBLIC key can verify the signature  ← open verification
```

- The private key **signs**.
- The public key **verifies**.
- If even a single byte of the document changes, the signature becomes invalid.

> ⚠️ **Important distinction:** in a digital signature, the *entire message is never encrypted*.
> Only a short **hash** (a fixed-size mathematical fingerprint) of the message is signed.
> This makes the process far more efficient and avoids size limitations, while still
> providing the same authenticity guarantee.

---

## The Role of Hash Functions

Before signing, the message is passed through a **cryptographic hash function**, such as those
from the SHA-2 family (SHA-256, SHA-384, SHA-512).

A hash function has three key properties:

1. **Deterministic** — the same input always produces the same output.
2. **One-way** — you cannot reconstruct the original message from the hash.
3. **Collision-resistant** — it is computationally infeasible to find two different inputs
   that produce the same hash.

```
"Transfer €1000 to Alice"  ──SHA-256──▶  e3b0c44298fc1c14...  (32 bytes, always)
"Transfer €9000 to Alice"  ──SHA-256──▶  a87ff679a2f3e71d...  (completely different)
```

Signing this short fingerprint instead of the full document is what makes asymmetric
cryptography practical at scale.

---

## Underlying Algorithms

The security of the key pair rests on mathematical problems that are easy to compute in one
direction, but effectively impossible to reverse.

### RSA — Integer Factorisation

RSA relies on the fact that multiplying two large prime numbers is fast, but factoring the
result back into those primes is computationally infeasible for sufficiently large numbers.

- A 2048-bit or 4096-bit RSA key is standard today.
- Used widely in TLS certificates, SSH, and legacy systems.
- Larger key sizes are required as computing power increases.

### Elliptic Curve Cryptography (ECC) — Ed25519

Modern systems increasingly favour elliptic curves, where the hard problem is the
**discrete logarithm on an elliptic curve**.

**Ed25519** (part of the Edwards-curve Digital Signature Algorithm family) is a popular
modern choice:

- Produces 64-byte signatures with a 32-byte key — dramatically smaller than RSA.
- Faster to sign and verify.
- Resistant to several classes of implementation errors that affect RSA.
- Default key type in modern OpenSSH and recommended for new systems.

| Algorithm | Key size | Security level | Primary use |
|-----------|----------|---------------|-------------|
| RSA-2048  | 2048 bit | ~112-bit equivalent | TLS, legacy SSH |
| RSA-4096  | 4096 bit | ~140-bit equivalent | High-assurance TLS |
| Ed25519   | 256 bit  | ~128-bit equivalent | SSH, signing, modern TLS |

---

## The Bigger Picture

Without public-key cryptography, the internet as we know it would not exist.

- **HTTPS** (TLS/SSL) uses key pairs to establish a shared secret at the start of every
  secure web session — without ever transmitting that secret over the network.
- **SSH** uses key pairs for passwordless, cryptographically strong server authentication.
- **Code signing** ensures the software you download was not tampered with after the
  developer released it.
- **Email signing** (PGP, S/MIME) lets you verify that a message genuinely came from its
  stated author.
- **Cryptocurrencies** use key pairs to prove ownership of funds without a central authority.

Every time you see the padlock icon in your browser, you are benefiting from the mathematics
of prime numbers and elliptic curves working silently in the background.

---

## Quick-Reference Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    KEY PAIR CHEAT SHEET                         │
├──────────────────────┬──────────────────────────────────────────┤
│  Goal                │  Who uses which key?                     │
├──────────────────────┼──────────────────────────────────────────┤
│  Encrypt a message   │  Sender uses recipient's PUBLIC key      │
│  Decrypt a message   │  Recipient uses their own PRIVATE key    │
├──────────────────────┼──────────────────────────────────────────┤
│  Sign a document     │  Author uses their own PRIVATE key       │
│  Verify a signature  │  Verifier uses author's PUBLIC key       │
└──────────────────────┴──────────────────────────────────────────┘
```

---

*Last updated: March 2026*
