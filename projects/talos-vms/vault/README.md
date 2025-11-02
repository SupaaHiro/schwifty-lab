# Ansible Vault — vault/vault-keyring.yaml

Create a new encrypted vault (prompts for a password):
```bash
ansible-vault create vault/vault-keyring.yaml
```

Encrypt an existing file:
```bash
ansible-vault encrypt vault/vault-keyring.yaml
```

Edit the encrypted vault (opens editor, saves encrypted):
```bash
ansible-vault edit vault/vault-keyring.yaml
```

View decrypted content (prints to stdout):
```bash
ansible-vault view vault/vault-keyring.yaml
```

Options:
- Use --ask-vault-pass to prompt for the password.
- Use --vault-password-file /path/to/file to read the password from a file.

Example using a password file:
```bash
ansible-vault create --vault-password-file ~/.vault_pass.txt vault/vault-keyring.yaml
```
