#!/usr/bin/env python3
"""
sops-tool — Encrypt/decrypt/view Kubernetes secret manifests with SOPS + age.
Usage: sops-tool <encrypt|decrypt|view> -f <file> [options]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENC_SUFFIX = ".enc.yaml"
PLAIN_SUFFIX = ".yaml"
DEFAULT_AGE_KEYS = Path("~/.config/sops/age/keys.txt").expanduser()


def check_sops():
    if not shutil.which("sops"):
        sys.exit(
            "Error: 'sops' not found in PATH. Please install it before proceeding.")


def find_sops_config(start: Path) -> Path | None:
    """Walks up the directory tree looking for .sops.yaml (same behaviour as sops itself)."""
    for parent in [start, *start.parents]:
        candidate = parent / ".sops.yaml"
        if candidate.exists():
            return candidate
    return None


def run_sops(args_list: list[str], env: dict, verbose: bool) -> subprocess.CompletedProcess:
    if verbose:
        print(f"[sops] {' '.join(args_list)}")
    result = subprocess.run(args_list, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result


def build_env(age_keys: Path) -> dict:
    env = os.environ.copy()
    env["SOPS_AGE_KEY_FILE"] = str(age_keys)
    return env


def cmd_encrypt(file: Path, age_keys: Path, sops_config: Path | None, verbose: bool):
    if file.name.endswith(ENC_SUFFIX):
        sys.exit(f"Error: file is already encrypted (.enc.yaml): {file}")
    if file.suffix != ".yaml":
        sys.exit(
            f"Error: the file to encrypt must have a .yaml extension: {file}")

    out_file = file.with_name(file.stem + ENC_SUFFIX)

    sops_args = ["sops", "--encrypt"]
    if sops_config:
        sops_args += ["--config", str(sops_config)]
    sops_args += ["--input-type", "yaml", "--output-type", "yaml", str(file)]

    result = run_sops(sops_args, build_env(age_keys), verbose)
    out_file.write_text(result.stdout)
    print(f"Encrypted: {file} → {out_file}")


def cmd_decrypt(file: Path, age_keys: Path, sops_config: Path | None, verbose: bool):
    if not file.name.endswith(ENC_SUFFIX):
        sys.exit(
            f"Error: the file to decrypt must have a .enc.yaml extension: {file}")

    stem = file.name[: -len(ENC_SUFFIX)]
    out_file = file.with_name(stem + PLAIN_SUFFIX)

    sops_args = ["sops", "--decrypt"]
    if sops_config:
        sops_args += ["--config", str(sops_config)]
    sops_args += ["--input-type", "yaml", "--output-type", "yaml", str(file)]

    result = run_sops(sops_args, build_env(age_keys), verbose)
    out_file.write_text(result.stdout)
    print(f"Decrypted: {file} → {out_file}")


def cmd_view(file: Path, age_keys: Path, sops_config: Path | None, verbose: bool):
    if not file.name.endswith(ENC_SUFFIX):
        sys.exit(
            f"Error: the file to view must have a .enc.yaml extension: {file}")

    sops_args = ["sops", "--decrypt"]
    if sops_config:
        sops_args += ["--config", str(sops_config)]
    sops_args += ["--input-type", "yaml", "--output-type", "yaml", str(file)]

    result = run_sops(sops_args, build_env(age_keys), verbose)
    print(result.stdout, end="")


def main():
    parser = argparse.ArgumentParser(
        prog="sops-tool",
        description="Manage YAML secrets with SOPS + age (kubectl-style)",
    )
    parser.add_argument(
        "--age-keys",
        type=Path,
        default=DEFAULT_AGE_KEYS,
        metavar="PATH",
        help=f"Path to age keys file (default: {DEFAULT_AGE_KEYS})",
    )
    parser.add_argument(
        "--sops-config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to .sops.yaml (default: auto-detect by walking up the directory tree)",
    )
    parser.add_argument("-v", "--verbose",
                        action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(
        dest="command", required=True, metavar="COMMAND")

    for cmd, help_text in [
        ("encrypt", "Encrypt a .yaml file → .enc.yaml"),
        ("decrypt", "Decrypt a .enc.yaml file → .yaml"),
        ("view", "Display a .enc.yaml file in plaintext (without writing to disk)"),
    ]:
        sub = subparsers.add_parser(cmd, help=help_text)
        sub.add_argument(
            "-f", "--file", type=Path, required=True, metavar="FILE", help="Input file"
        )

    args = parser.parse_args()

    check_sops()

    file = args.file.resolve()
    if not file.exists():
        sys.exit(f"Error: file not found: {file}")

    age_keys = args.age_keys.expanduser()
    if not age_keys.exists():
        sys.exit(f"Error: age keys file not found: {age_keys}")

    sops_config = args.sops_config
    if sops_config is None:
        sops_config = find_sops_config(file.parent)
        if args.verbose:
            if sops_config:
                print(f"[config] .sops.yaml found: {sops_config}")
            else:
                print(
                    "[config] No .sops.yaml found, sops will use its default configuration")

    dispatch = {"encrypt": cmd_encrypt,
                "decrypt": cmd_decrypt, "view": cmd_view}
    dispatch[args.command](file, age_keys, sops_config, args.verbose)


if __name__ == "__main__":
    main()
