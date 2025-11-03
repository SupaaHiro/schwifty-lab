# Talos VMs on VMware ESXi

This repository provides an Ansible playbook to provision VMs on a VMware ESXi host for use with SideroLabs Omni and Talos.

## Prerequisites

- A running VMware ESXi hypervisor and credentials
- Python 3.8+ and pip
- Ansible (ansible and ansible-core)
- ovftool (VMware OVF Tool) for OVF/OVA conversion
- Access to the SideroLabs Omni portal to generate/download a Talos ISO

## Install prerequisites

Install Ansible and related tooling:

```bash
pip install ansible==12.1.0 ansible-core==2.19.3 ansible-lint==25.9.2 pyvmomi==9 requests=2.32.5
```

Install required Ansible collections:

```bash
ansible-galaxy collection install -r requirements.yml
```

## Prepare an OVA template

OVF/OVA are virtual appliance formats. Use OVF Tool to convert if needed.

1. On the ESXi host create a minimal VM to act as the template and export it as an OVF (or OVA).
2. If you exported an OVF, convert it locally to OVA:

```bash
ovftool talos-vm0.ovf talos-vm0.ova
```

3. Place the OVA where the playbook host can access it and update the `ova_file` variable in your inventory or `group_vars` (for example, `group_vars/all.yaml`) to point to that path.

## Create an Ansible Vault for secrets

Use Ansible Vault to store ESXi credentials and other secrets. Do not commit the vault file or its password.

Create the vault:

```bash
ansible-vault create vault/vault-keyring.yaml
```

Example contents (inside the vault):

```yaml
ova_deployment_hostname: "esxi.example.com"
ova_deployment_username: "root"
ova_deployment_password: "your-esxi-password"
```

You can edit the vault with `ansible-vault edit` or supply a vault ID / file with `--vault-id` when running playbooks.

## Configure host_vars

For each VM to create, add `host_vars/<hostname>.yaml` with at least the MAC address and NIC name. Example `host_vars/talos-vm0.yaml`:

```yaml
mac_address: "00:50:56:aa:bb:cc"
nic_name: "vmnic0"
```

Adjust additional host-specific variables as required.

## Fix permissions on WSL (if needed)

On WSL, overly permissive permissions on the playbook directory can break Ansible inventory loading. Restrict permissions:

```bash
chmod -R 755 talos-vms/
```

## Generate Talos ISO

Generate or download a Talos ISO from the SideroLabs Omni portal and place it where the playbook host can access it. Update `talos_iso_path` in your inventory or `group_vars/all.yaml` to point to the ISO.

## Deploy

Run the deployment playbook:

```bash
ansible-playbook -i hosts.yaml playbooks/deploy.yaml --ask-vault-pass
```

If you want, you can also perform a syntax check on the playbook before running it:

```bash
ansible-lint
```

Enter the vault password when prompted (or use `--vault-id`).

## Common variables

- `ova_file`: path to the OVA template (local or remote)
- `talos_iso_path`: path to the Talos ISO to attach to new VMs
- `ova_deployment_hostname`: ESXi host FQDN or IP
- `ova_deployment_username`: ESXi user
- `ova_deployment_password`: ESXi password

Place these in `group_vars/all.yaml` or the appropriate vars file for your inventory.

## Troubleshooting

- ovftool not found: install OVF Tool and ensure it is on PATH.
- Permission issues on WSL: enforce restrictive permissions (see section above).
- Inventory not found: verify `hosts.yaml` or `inventory/hosts` path and permissions.
- Vault errors: verify the vault password or vault-id being used.

## Security

- Never commit `vault/vault-keyring.yaml` or any plaintext credentials.
- Protect the vault password and use secure methods in CI/CD (vault IDs, environment variables, or restricted vault password files).

## License and Support

Refer to the repository LICENSE file for licensing. For issues, open a GitHub issue in this repository.
