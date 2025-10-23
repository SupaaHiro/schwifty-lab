---
layout: default
title: "CKAD Preparation — Introducing Multi-Container Pods"
date: 2025-10-22
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-articles/20251022-ckad/article.webp"
summary: "Deep dive into how Kubernetes runs multi-container Pods — from the controller and scheduler to the runtime chain."
---

## Introduction

This article is part of an ongoing CKAD series that walks through practical Kubernetes patterns and runtime internals. Here we focus on multi-container Pod design patterns — why they exist, common use cases (sidecar, init, adapter), and a small hands-on exercise to practice creating and inspecting a Pod with multiple containers.

In this post, we’ll cover CKAD requirements within the “Application Design and Build” domain:

> Understand multi-container Pod design patterns (e.g. sidecar, init and others)

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-articles/20251019-ckad/article_EN.html).

## Prerequisites

A running instance of Kubernetes with root or equivalent access. You can use Kubernetes for Docker Desktop, Minikube, or a temporary environment on [KillerCoda Playgrounds](https://killercoda.com/playgrounds).

## Getting the Resources

All manifests and examples mentioned in this post are available in the following repository:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-articles/20251022-ckad
```

## Understanding multi-container Pods

In a previous post we introduced the Pod — the smallest deployable unit in Kubernetes that groups one or more containers which share the same network namespace, volumes, and lifecycle.

Most Pods run a single main container, but Kubernetes also supports multi-container Pods for scenarios that need composition of complementary processes. Common container roles inside a Pod include:

- Init containers: run to completion before application containers start to perform setup tasks (e.g., generating config, waiting for dependencies, preloading data).
- Sidecars: companion containers that extend the main container’s behavior (e.g., log forwarding, proxying, metrics collection).
- Adapters and helpers: short-lived or long-running processes that transform data, manage credentials, or perform auxiliary work.

📝 Note: We’ll explore the main architectural patterns for multi-container Pods later in this series.

In production, Pods are rarely created directly; they’re typically managed by controllers such as Deployments. It all starts with creating a resource, which kicks off a chain of events leading to the container's execution. Here's a simplified version of the flow::

1. You submit a Deployment manifest to the API server.
2. The Deployment controller (in kube-controller-manager) notices the desired state and creates or updates a ReplicaSet.
3. The ReplicaSet ensures the correct number of Pod objects exist in etcd.
4. Each new Pod object is scheduled by the scheduler, which picks a node based on resources, labels, affinities, and taints.
5. The kubelet on the chosen node sees the scheduled Pod and calls the container runtime via the Container Runtime Interface (CRI).
6. The runtime creates a Pod sandbox (the pause container) that holds the Pod’s network namespace and IP.
7. The runtime then starts the application containers defined in the Pod spec; the low-level OCI runtime (usually runc) creates and runs each container process.

From the Kubernetes control plane down to the OCI runtime, this chain of components is what turns a manifest in Git or on disk into an active set of processes running together as a single logical unit.

### The pause container

Each Pod has a pause (sandbox) container that holds shared namespaces such as the network namespace. The pause container:

- Holds the Pod IP and network namespace.
- Keeps the Pod's namespaces alive even if application containers exit.
- Acts as the parent for the other containers in the Pod sandbox.

You can often see pause containers listed by CRI tools (`crictl pods` / `ctr`) when inspecting low-level runtime state.

## Troubleshooting and container inspection

A container, once it’s running, is essentially a Linux process executing inside a set of isolated namespaces — network, PID, mount, and others. From Kubernetes’ perspective Pods are a high-level abstraction; underneath, each container remains a process managed by the container runtime.

When a Pod stalls during bootstrap (e.g., ContainerCreating or an Init container hangs), kubectl exec or kubectl logs may not work yet. In those cases drop one level lower and troubleshoot on the node using runtime tools.

1. the CRI client (`crictl`)

`crictl` is the official CLI for runtimes that implement the Container Runtime Interface (CRI), like containerd or CRI-O. Use it when kubectl can’t reach a Pod because it hasn’t fully started.

Common commands:
```bash
crictl ps -a                # List all containers (including stopped)
crictl pods                 # List Pod sandboxes
crictl inspectp <pod-id>    # Inspect a Pod sandbox and its containers
crictl logs <container-id>  # View container logs (if available)
```

2. containerd CLI (`ctr`) — low-level containerd interface

If the node runs containerd, ctr inspects containers at a lower level than the CRI client. It talks directly to containerd internals.

Common commands:
```bash
sudo ctr containers list
sudo ctr tasks list
sudo ctr tasks exec -t <task-id> /bin/sh   # Attach to a container process
sudo ctr tasks kill <task-id>
```

3. Docker-like CLI for containerd (`nerdctl`)

nerdctl offers a Docker-like experience on top of containerd, useful if you prefer familiar Docker commands.

Examples:
```bash
nerdctl ps -a
nerdctl inspect <container-id>
nerdctl logs <container-id>
nerdctl stop <container-id>
nerdctl rm <container-id>
```

> Use runtime tools sparingly and only when kubectl-level debugging isn’t possible; they’re invaluable for investigating bootstrap and sandbox-level problems.

## Hands-On Challenge

Before we wrap it up, let's do a small Hands-On exercise.

Create a multi-container Pod with:
- One main container running Nginx.
- One sidecar container (BusyBox) that tails the Nginx access log and demonstrates shared volumes.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-with-sidecar
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: sidecar
    image: busybox:1.37
    command: ["/bin/sh", "-c", "tail -F /var/log/nginx/access.log"]
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
  restartPolicy: Always
```

Save the manifest as `manifests/01-nginx-with-sidecar.yaml`:

> During the exam, always try to use imperative commands such as `k create <resource> -o yaml --dry-run=client > manifest.yaml` to quickly generate YAML manifest templates that you can then edit and apply with `k apply -f manifest.yaml`.

Apply the Pod:

```bash
k apply -f manifests/01-nginx-with-sidecar.yaml
```

Verify the Pod reaches the Running state:

```bash
k get pod nginx-with-sidecar -o wide --watch
```

Inspect the pod and check the logs:

```bash
k describe pod nginx-with-sidecar
k logs -c sidecar nginx-with-sidecar
```

Kubernetes constantly monitors the state of your Pods to ensure they match the desired configuration declared in the cluster.

To see this in action, let’s simulate a container crash and observe how the kubelet automatically brings it back to life.

First, find the node where your Pod is running:

```bash
k get pod -o wide
```

SSH into that node, then use the container runtime to list containers and identify the process ID (PID) of one of your running containers.

For example, if you’re using containerd:

```bash
sudo crictl ps
sudo crictl inspect <container-id> | grep pid
```

Now, manually kill that process:

```bash
sudo kill -9 <pid>
```

Immediately after the process terminates, you’ll notice that the container disappears from the runtime’s process list — but within a few seconds, kubelet detects the failure. Because the Pod’s desired state (as defined by the controller) still requires the container to be running, kubelet instructs the runtime to recreate it.

You can verify this by watching the Pod status:

```bash
k get pod -o wide --watch
```

You’ll see the container briefly transition through states such as CrashLoopBackOff or ContainerCreating, before returning to Running.

Under the hood, this happens because kubelet continuously polls both the container runtime (via the CRI) and the Kubernetes API to reconcile the Pod’s actual state with its desired state.

If a container process disappears — whether it crashed or was manually killed — kubelet simply recreates it to restore consistency.

## Wrapping Up: What We’ve Covered

In this exercise, we explored how multi-container Pods work in practice and what happens behind the scenes when a Deployment creates and manages them.

We followed the complete lifecycle — from the controller reconciling the desired state, to the scheduler assigning the Pod, to the kubelet interacting with the container runtime. Along the way, we examined the purpose of the pause container, which establishes the Pod’s shared network namespace and serves as the foundation for all other containers.

Through a hands-on example, we deployed an Nginx Pod with a sidecar container that tailed its logs, demonstrating how containers within the same Pod can share data and communicate seamlessly.

Finally, by manually killing the container’s process on the node, we observed how kubelet automatically detected the failure and recreated the container — reinforcing Kubernetes’ self-healing behavior and its focus on maintaining the desired state.

## Final cleanup

When you're done with the exercise remove the Pod and any resources you created:

```bash
kubectl delete -f manifests/nginx-with-sidecar.yaml
```
