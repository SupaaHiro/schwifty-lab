# Talos VMs on VMware ESXi

This repository contains an Ansible playbook to quickly provision a set of VMs on a VMware ESXi host for use with SideroLabs Omni and Talos.

## Prerequisites

- A running VMware ESXi hypervisor with access credentials
- Python 3.8+ and pip
- Ansible (ansible and ansible-core)
- ovftool (VMware OVF Tool) for OVF/OVA conversion
- Access to SideroLabs Omni portal to generate a Talos ISO

## Install prerequisites

Install Python (if needed) and Ansible:

```bash
# Example with pip
pip install --user ansible==11.10.0 ansible-core==2.18.9
```

Install ovftool according to VMware documentation and ensure it is on your PATH.

## Prepare an OVA template

1. On the ESXi host, create a minimal VM that will serve as the template and export it as an OVF (or OVA).
2. If you exported an OVF, convert it to OVA locally:

```bash
ovftool talos-vm0.ovf talos-vm0.ova
```

3. Place the OVA file in a location accessible to your playbook host and note the path.

Update the `ova_file` variable in your inventory or group_vars file (for example, `group_vars/all.yaml`) to point to that OVA path.

## Create a local Ansible Vault for secrets

Create an encrypted vault file to store ESXi credentials and other secrets. Do not commit the vault file or its password to source control.

```bash
ansible-vault create vault/vault-keyring.yaml
```

Example contents (inside the vault file):

```yaml
ova_deployment_hostname: "esxi.example.com"
ova_deployment_username: "root"
ova_deployment_password: "your-esxi-password"
```

You can also use `ansible-vault edit` to change values later. When running playbooks, you will be prompted for the vault password (or use `--vault-id` if you have a vault ID file).

## Configure host_vars

For each host you plan to create, add a `host_vars/<hostname>.yaml` file with at least the MAC address and NIC name that should be attached to the VM. Example `host_vars/talos-vm0.yaml`:

```yaml
mac_address: "00:50:56:aa:bb:cc"
nic_name: "vmnic0"
```

Adjust other host-specific variables as required by your environment.

## Fix permissions on WSL (if needed)

On WSL, having overly permissive permissions on the playbook directory can cause Ansible inventory loading issues. Restrict permissions:

```bash
chmod -R 755 talos-vms/
```

## Generate Talos ISO

Generate or download a Talos ISO from the SideroLabs Omni portal. Place the ISO in a location accessible to the machine that runs the playbook, then update the `talos_iso_path` variable in your inventory or group_vars (example: `group_vars/all.yaml`) to point to the ISO.

## Deploy

Run the deployment playbook:

```bash
ansible-playbook -i hosts.yaml playbooks/deploy.yaml --ask-vault-pass
```

When prompted, enter the vault password to decrypt secrets.

## Common variables

- ova_file: path to the OVA template (local or remote as required)
- talos_iso_path: path to the Talos ISO to be attached to new VMs
- ova_deployment_hostname: ESXi host FQDN or IP
- ova_deployment_username: ESXi user
- ova_deployment_password: ESXi password

Place these in `group_vars/all.yaml` or an appropriate vars file for your inventory.

## Troubleshooting

- ovftool not found: ensure OVF Tool is installed and on PATH.
- Permission issues on WSL: enforce restrictive permissions (see section above).
- Inventory not found: verify `inventory/hosts` path and permissions.
- Vault errors: check you are using the correct vault password or vault-id.

## Security

- Never commit `vault/vault-keyring.yaml` or any file containing plaintext credentials.
- Protect the vault password and use a secure way to supply it in CI/CD (vault IDs, environment variables, or Ansible Vault password files with restricted permissions).

## License and Support

Refer to repository LICENSE file for licensing. For issues, open a GitHub issue in this repository.
