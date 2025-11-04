---
layout: default
title: "Replacing Flannel with Calico on Talos + Omni"
date: 2025-11-04
categories: [talos, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251022-ckad/article.webp"
summary: "Experimenting with replacing Talos’ default Flannel CNI with Calico using SideroLabs Omni — exploring BPF dataplane, kube-proxy management, and declarative cluster configuration."
---

## Introduction

This post is not part of the CKAD series — mostly because between work and developing the new blog platform, I didn’t have time to prepare new exam-related labs.

But, in parallel, I’ve been exploring something that’s been on my list for months: replacing my old high-availability Kubernetes cluster (manually deployed with kubeadm, maintained through a glorious 500-page Word document — yes, I know, that’s not the way 😅) with something more declarative and manageable.

That cluster served me well for years. I built and upgraded everything by hand: control planes, kube-proxy, CNI, certificates, and so on. It was a great learning journey — but now that I know Kubernetes deeply, maintaining it manually has become unnecessary overhead.

So, I started looking for something declarative, self-managed, yet fully under my control.
I already knew about [Talos Linux](https://www.talos.dev/), but never really dug into it. Then, almost by accident, I discovered [SideroLabs Omni](https://www.siderolabs.com/products/omni) — and since then, I’ve been experimenting with it non-stop for three days straight.

Today, I finally managed to replace the default Flannel CNI that comes with Talos with Calico, which I’ve been using for about four years in production environments.

**Spoiler: it works beautifully.**

---

## Why replace Flannel?

Flannel is simple and functional, but Calico offers:
- Advanced BPF dataplane support.
- Built-in network policies and encryption.
- Better observability and BGP-based routing.
- And — importantly — more alignment with production setups I use daily.

The challenge: Talos automatically installs Flannel as the default CNI, so replacing it requires a bit of orchestration.

---

## The key insight — patch before deploying

After reading a lot of documentation across Calico, Talos, and Omni, I found the cleanest approach is simply to apply a custom network configuration before the cluster is deployed.

Here’s the patch that made it work:

```yaml
cluster:
  network:
    cni:
      name: custom
      urls:
        - https://raw.githubusercontent.com/SupaaHiro/schwifty-lab/refs/heads/master/deployment/onprem/manifests/talos-coredns-onprem-config.yaml
        - https://raw.githubusercontent.com/projectcalico/calico/v3.31.0/manifests/operator-crds.yaml
        - https://raw.githubusercontent.com/projectcalico/calico/v3.31.0/manifests/tigera-operator.yaml
        - https://raw.githubusercontent.com/SupaaHiro/schwifty-lab/refs/heads/master/deployment/onprem/manifests/talos-calico-bpf-onprem-config.yaml
```

> ⚠️ Important: This patch must be applied before the cluster bootstrap.
> If you deploy the default cluster first, Flannel will already be initialized and Calico won’t be able to take over cleanly.

---

## Why patch the CoreDNS manifest?

Because of one small (**but critical**) issue:

After the first reboot, CoreDNS couldn’t start because the network wasn’t ready yet — and Calico couldn’t start because the DNS wasn’t working. Classic chicken-and-egg.

To fix that, I introduced an additional manifest `talos-coredns-onprem-config.yaml`, a small patch that ensures DNS resolution is available early during bootstrap — even before Calico is up.

Once the network comes online, Calico takes over seamlessly.

## The journey (a.k.a. “not so easy after all”)

It might sound straightforward now, but getting to this point required quite a few experiments.
Here’s a condensed version of the technical steps I followed.

### 1. Uninstall Flannel

Talos includes Flannel by default. You can remove it manually if you’re testing on an existing cluster

```bash
kubectl delete ds kube-flannel -n kube-system
kubectl -n kube-flannel delete sa flannel
```

### 2. Install Calico via Tigera Operator

Calico’s recommended way to install today is through the Tigera Operator.

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.31.0/manifests/operator-crds.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.31.0/manifests/tigera-operator.yaml
```

Then apply your custom Calico configuration (in my case, configured for the BPF dataplane):

```bash
kubectl create -f custom-resources-talos-bpf.yaml
```

### 3. Monitor the deployment

You can monitor Calico’s progress through the Tigera status resource:

```bash
watch kubectl get tigerastatus
```

Or inspect the node logs for more detail:

```bash
kubectl logs -l k8s-app=calico-node -n calico-system
```

### 4. Disable kube-proxy (Calico BPF mode)

When Calico runs in eBPF mode, it replaces `kube-proxy` entirely. Both try to bind port `10256`, which can lead to conflicts.

To disable kube-proxy on Calico nodes:

```bash
kubectl patch ds kube-proxy -n kube-system --type merge -p '{"spec":{"template":{"spec":{"nodeSelector":{"non-calico":"true"}}}}}'
```

On Windows PowerShell, remember to escape quotes:

```powershell
kubectl patch ds kube-proxy -n kube-system --type merge -p "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"non-calico\":\"true\"}}}}}"
```

### 5. Test pod connectivity

You can quickly launch a test pod and validate network connectivity:

```bash
kubectl run -it --rm test-pod --image=alpine --restart=Never \
  --overrides='{"spec": {"nodeSelector": {"kubernetes.io/hostname": "worker-01"}}}'
```

Then test DNS and network access:

```sh
ping 8.8.8.8
nslookup google.it
apk add --no-cache curl
curl google.it
```

Reboot one node and run these tests again — both Calico and CoreDNS should recover automatically.
Connectivity, DNS resolution, and service discovery should remain stable across node restarts.

> ⚠️ Disclaimer
> In this setup, kube-proxy had already created routing rules before Calico was deployed. While the cluster remains functional, it operates in a mixed and somewhat inconsistent state — effectively with two networking layers coexisting.
> Furthermore, since Talos is an immutable operating system, a full cluster reboot would restore Flannel as the default CNI, reintroducing conflicts between the two network stacks.
>
> This configuration should therefore be considered an experiment, useful for validation and learning purposes.
> The proper, production-grade approach is to patch the cluster manifest before the initial deployment, ensuring Talos boots directly with Calico as the active CNI.

## Learn more

- 🔗 Project Calico Documentation: https://projectcalico.docs.tigera.io/
- 💻 Calico GitHub Repository: https://github.com/projectcalico/calico
- 🧩 SideroLabs Talos: https://www.talos.dev/
- ☁️ SideroLabs Omni: https://docs.siderolabs.com/omni/overview/what-is-omni

## Wrapping up

Moving from a manual kubeadm cluster to Talos + Omni has been refreshing — declarative, clean, and surprisingly stable. Being able to swap the default CNI, patch CoreDNS for bootstrap safety, and declaratively define every configuration piece from Git feels like stepping into the future of cluster management.

This experiment is the first entry in a new series on Talos and Omni — exploring modern, reproducible cluster design beyond traditional tooling. Stay tuned for the next posts!
