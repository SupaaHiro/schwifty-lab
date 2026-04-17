---
layout: default
title: "CKAD Preparation — Debugging in Kubernetes"
date: 2026-04-17
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260417-ckad/article.webp"
summary: "A practical guide to debugging Kubernetes applications: kubectl exec, kubectl debug, ephemeral containers, and diagnosing the most common failure scenarios you'll encounter in the CKAD exam and in production."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

This article **closes the Application Observability and Maintenance domain**. We cover the last remaining requirement:

> Debugging in Kubernetes

In the previous articles we already covered:

- [Use built-in CLI tools to monitor Kubernetes applications](https://supaahiro.github.io/schwifty-lab/blog-posts/20260131-ckad/article_EN.html) — `kubectl get`, `describe`, `events`, `top`
- [Utilize container logs](https://supaahiro.github.io/schwifty-lab/blog-posts/20260304-ckad/article_EN.html) — `kubectl logs`

Those two are the *first* things you reach for. This article adds the next layer: getting inside containers, attaching ephemeral debuggers, and systematically diagnosing the most common failure modes.

After this article, the series continues with the **Application Environment, Configuration and Security** domain.

As usual, you can start from the beginning here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

---

## Prerequisites

A running Kubernetes cluster (Minikube, Docker Desktop, or a [KillerCoda Kubernetes Playground](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and Deployments.

---

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260417-ckad
```

---

## Part 1: kubectl exec

`kubectl exec` lets you run a command inside a running container. It is the equivalent of `docker exec`, but for Pods.

Apply a basic workload:

```bash
k apply -f manifests/01-debug-target.yaml
```

Wait for it to be running:

```bash
k get pods -l app=debug-target -w
```

Run a one-shot command inside the container:

```bash
POD=$(k get pod -l app=debug-target -o jsonpath='{.items[0].metadata.name}')
k exec $POD -- ls /
k exec $POD -- cat /etc/os-release
k exec $POD -- env
```

Open an interactive shell:

```bash
k exec -it $POD -- /bin/sh
```

Once inside you can inspect the filesystem, check environment variables, test network connectivity, or run any binary that exists in the image.

Exit with `exit` or `Ctrl+D`.

**Multi-container pods**: specify the container with `-c`:

```bash
k exec -it $POD -c main -- /bin/sh
```

Without `-c`, exec targets the first container.

---

## Part 2: kubectl debug

`kubectl exec` only works when:

1. The container is *running*
2. The image has a shell (e.g., `busybox`, `debian`, `alpine`)

Many production images are distroless or scratch-based — no shell, no tools, nothing. And if a container is crash-looping, you can never catch it long enough to exec in.

`kubectl debug` solves both problems.

### Ephemeral containers

An ephemeral container is a temporary container injected into a running Pod. It shares the same PID and network namespace as the target container — but uses its own image, which can contain any debugging tools you want.

```bash
k debug -it $POD --image=busybox:1.36 --target=main
```

- `--image`: the image to use for the ephemeral container (can be anything)
- `--target`: the container to share the process namespace with (so you can see its processes)

Inside the ephemeral container you can:

```bash
# See all processes (including from the target container)
ps aux

# Check network connections
netstat -tulnp

# Test DNS resolution
nslookup kubernetes.default

# Test HTTP connectivity
wget -qO- http://some-service
```

Exit with `exit` or `Ctrl+D`. Ephemeral containers cannot be removed — they stay attached until the Pod is deleted.

### Debug a crashed container by copying the Pod

When the container keeps crashing and you can never exec in, use `--copy-to` to create a clone of the Pod with a modified command:

```bash
k debug $POD --copy-to=debug-clone --image=busybox:1.36 -- sleep 1d
```

This creates a new Pod named `debug-clone` with the same spec, but overriding the entrypoint with `sleep 1d`. Now you can exec into it, inspect the filesystem, and figure out why the original is failing.

Clean up:

```bash
k delete pod debug-clone
```

---

## Part 3: kubectl cp

Sometimes the easiest way to inspect something is to pull a file out of the container:

```bash
k cp $POD:/etc/nginx/nginx.conf ./nginx.conf
```

Or push a file in:

```bash
k cp ./my-config.json $POD:/tmp/my-config.json
```

Useful for log files, config files, or application artifacts that don't have a convenient path to inspect them otherwise.

---

## Part 4: Diagnosing Common Failure Scenarios

This is the part that matters most in the CKAD exam. You will be given a broken cluster and asked to find and fix the issue. Here are the most common scenarios and how to diagnose them systematically.

### 4.1 — CrashLoopBackOff

The pod starts, the container exits with a non-zero code, Kubernetes restarts it. After a few restarts, the backoff timer kicks in.

Apply the scenario:

```bash
k apply -f manifests/02-crashloop.yaml
```

Observe:

```bash
k get pods -l app=crashloop -w
```

You'll see the pod cycle through `Error` → `CrashLoopBackOff`.

**Diagnosis steps:**

```bash
# 1. Check events and the exit code
k describe pod -l app=crashloop

# 2. Check current logs
k logs -l app=crashloop

# 3. Check logs from the previous (crashed) instance
k logs -l app=crashloop --previous
```

The exit code in `describe` output (under `Last State`) tells you *how* it failed:
- Exit code `1` — application error
- Exit code `137` — killed by signal (OOM, SIGKILL)
- Exit code `139` — segmentation fault

In this lab the container exits with `1`. The logs tell you exactly what happened.

### 4.2 — OOMKilled

The container uses more memory than its limit allows. The Linux OOM killer terminates it.

Apply the scenario:

```bash
k apply -f manifests/03-oom.yaml
```

Watch it:

```bash
k get pods -l app=oom-demo -w
```

Describe the pod:

```bash
k describe pod -l app=oom-demo
```

Look for:

```
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
```

OOMKilled always means the memory limit is too low for the workload. Solutions:
- Raise the memory limit
- Profile the application and reduce its memory usage
- Use a VPA (Vertical Pod Autoscaler) to tune limits automatically

### 4.3 — ImagePullBackOff

The kubelet cannot pull the container image. This usually means:
- The image tag does not exist
- The image registry requires authentication (missing `imagePullSecret`)
- A typo in the image name

Apply the scenario:

```bash
k apply -f manifests/04-imagepull.yaml
```

Observe:

```bash
k get pods -l app=bad-image -w
```

You'll see `ErrImagePull` first (active retry), then `ImagePullBackOff` (backoff active).

Diagnose:

```bash
k describe pod -l app=bad-image
```

The `Events` section will show the exact pull error. Fix the image name, tag, or add the correct pull secret.

### 4.4 — Pending pod

A pod stays in `Pending` indefinitely — it has been accepted by the API server but no node could be found to schedule it.

Apply the scenario:

```bash
k apply -f manifests/05-pending.yaml
```

Check:

```bash
k get pods -l app=pending-demo
```

Diagnose:

```bash
k describe pod -l app=pending-demo
```

Look at the `Events` section. Common messages:

| Message | Root cause |
|---|---|
| `0/1 nodes are available: 1 Insufficient cpu` | Resource requests exceed available capacity |
| `0/1 nodes are available: 1 node(s) had untolerated taint` | Pod needs a toleration for a taint |
| `0/1 nodes are available: 1 node(s) didn't match Pod's node affinity` | nodeSelector or affinity rules don't match any node |
| `0/1 nodes are available: persistentvolumeclaim "…" not found` | PVC doesn't exist or is not bound |

In this lab the pod requests far more CPU than available. Check the node capacity:

```bash
k describe nodes | grep -A 5 "Allocated resources"
```

Fix by reducing the resource requests in the manifest.

### 4.5 — Service not routing traffic

A pod is `Running` but requests through the Service are not reaching it. Almost always this is a **label selector mismatch**.

Apply the scenario:

```bash
k apply -f manifests/06-service-debug.yaml
```

The service will have no endpoints. Diagnose:

```bash
# Check if the service has any endpoints
k describe svc broken-service

# Look at the Endpoints field — if it's <none>, the selector matches no pods
```

Cross-check the Service selector with the Pod labels:

```bash
k get svc broken-service -o jsonpath='{.spec.selector}'
k get pods -l app=backend --show-labels
```

You'll spot the mismatch. Fix the selector in the Service (or the labels on the pods), and the endpoints will populate automatically.

You can also verify connectivity from inside the cluster:

```bash
k run nettest --image=busybox:1.36 --rm -it --restart=Never -- wget -qO- http://broken-service
```

---

## Part 5: Quick reference — Debugging flowchart

```
Pod not running?
├── Pending     → kubectl describe pod → check Events for scheduling reason
├── CrashLoop   → kubectl logs --previous → check exit code in describe
├── OOMKilled   → kubectl describe pod → look for "OOMKilled" in Last State
└── ImagePull   → kubectl describe pod → check Events for pull error

Pod running but misbehaving?
├── kubectl exec -it <pod> -- /bin/sh       (if image has shell)
├── kubectl debug -it <pod> --image=busybox (if image is minimal/distroless)
└── kubectl logs -f <pod>                  (tail live output)

Service not reachable?
├── kubectl describe svc → check Endpoints
├── kubectl get pods --show-labels → compare with svc selector
└── kubectl run nettest --image=busybox --rm -it -- wget -qO- http://<svc>
```

---

## Wrapping Up

This article closes the **Application Observability and Maintenance** domain. We've now covered all five requirements:

1. Understand API deprecations
2. Implement probes and health checks
3. Use built-in CLI tools to monitor Kubernetes applications
4. Utilize container logs
5. **Debugging in Kubernetes** ← this article

In the next articles we will start the **Application Environment, Configuration and Security** domain, beginning with CRDs and Operators.

---

## Final Cleanup

```bash
k delete -f manifests/
k delete pod nettest --ignore-not-found
k delete pod debug-clone --ignore-not-found
```
