# sops-tool

A small CLI utility to encrypt, decrypt, and view Kubernetes secret manifests using [SOPS](https://github.com/getsops/sops) and [age](https://github.com/FiloSottile/age).

---

## What is age?

[age](https://github.com/FiloSottile/age) is a simple, modern, and secure file encryption tool. It uses small explicit keys, has no config options, and is composable with Unix pipes. An age identity consists of:

- A **private key** (keep this secret) — looks like `AGE-SECRET-KEY-1...`
- A **public key** (safe to share) — looks like `age1...`

age is the recommended encryption backend for SOPS because of its simplicity and strong security defaults.

---

## What is SOPS?

[SOPS](https://github.com/getsops/sops) (Secrets OPerationS) is an editor and CLI tool for encrypting structured files (YAML, JSON, ENV, INI, binary). Unlike full-file encryption, SOPS encrypts only the **values** of the file, leaving keys and structure in plain text. This makes encrypted files diff-friendly and reviewable in version control.

SOPS supports multiple key management backends (age, AWS KMS, GCP KMS, Azure Key Vault, PGP). This tool uses **age**.

A `.sops.yaml` configuration file in your repository tells SOPS which public keys to use when encrypting, and which files to target.

---

## Prerequisites

Install both tools before using `sops-tool`:

```bash
# macOS (Homebrew)
brew install age sops

# Windows (Scoop)
scoop install age sops

# Linux (download binaries from GitHub Releases or use your package manager)
# https://github.com/FiloSottile/age/releases
# https://github.com/getsops/sops/releases
```

---

## Initial Setup

### 1. Generate an age key pair

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
```

This writes both the public and private key to `~/.config/sops/age/keys.txt`. The output also prints your **public key** to stdout — copy it, you will need it in the next step.

Example output:
```
Public key: age1XXX
```

> **Security note:** Keep `keys.txt` private. Never commit it to version control. Back it up securely (e.g. in a password manager).

### 2. Create a `.sops.yaml` configuration

Place a `.sops.yaml` file at the root of your repository (or any parent directory of your secrets). SOPS — and this tool — will auto-detect it by walking up the directory tree.

```yaml
# .sops.yaml
creation_rules:
  - path_regex: .*\.yaml$
    age: >-
      age1XXX
```

To encrypt for multiple recipients (e.g. team members or a CI key), separate public keys with commas:

```yaml
creation_rules:
  - path_regex: .*\.yaml$
    age: >-
      age1XXX,
      age1YYY
```

---

## Usage

```
python sops-tool.py <command> -f <file> [options]
```

### Commands

| Command   | Description                                          |
|-----------|------------------------------------------------------|
| `encrypt` | Encrypts a `.yaml` file → produces a `.enc.yaml`     |
| `decrypt` | Decrypts a `.enc.yaml` file → produces a `.yaml`     |
| `view`    | Decrypts a `.enc.yaml` and prints to stdout (no file written) |

### Global Options

| Option | Default | Description |
|--------|---------|-------------|
| `--age-keys PATH` | `~/.config/sops/age/keys.txt` | Path to the age private key file |
| `--sops-config PATH` | auto-detect | Path to `.sops.yaml` (default: walks up from the input file's directory) |
| `-v`, `--verbose` | off | Print the sops command being executed |

---

## Quick Reference

```bash
# Encrypt a plain secret manifest
python sops-tool.py encrypt -f deploy/infrastructure/controllers/smb-csi/credentials.yaml

# View an encrypted file without writing to disk
python sops-tool.py view -f deploy/infrastructure/controllers/smb-csi/credentials.enc.yaml

# Decrypt an encrypted file back to plain YAML
python sops-tool.py decrypt -f deploy/infrastructure/controllers/smb-csi/credentials.enc.yaml

# Override the age keys path
python sops-tool.py --age-keys /path/custom/keys.txt encrypt -f secret.yaml
```

---

## File Naming Convention

| Operation | Input | Output |
|-----------|-------|--------|
| `encrypt` | `secret.yaml` | `secret.enc.yaml` |
| `decrypt` | `secret.enc.yaml` | `secret.yaml` |
| `view`    | `secret.enc.yaml` | *(stdout only)* |

> **Tip:** Add `*.yaml` (or the specific plain-text names) to `.gitignore` and commit only `*.enc.yaml` files.
