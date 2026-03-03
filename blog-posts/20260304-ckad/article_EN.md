---
layout: default
title: "CKAD Preparation — Application Observability and Maintenance: Utilizing Container Logs"
date: 2026-03-04
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260304-ckad/article.webp"
summary: "A practical and minimal guide to using container logs in Kubernetes for application observability and maintenance."
---

## Introduction

This article continues the **Application Observability and Maintenance** domain of the CKAD path.

This time we focus on one very concrete requirement:

> Utilize container logs

Also, we already covered:

- [Use built-in CLI tools to monitor Kubernetes applications](https://supaahiro.github.io/schwifty-lab/blog-posts/20260131-ckad/article_EN.html)

So we won't repeat `kubectl get`, `describe`, `top`, or events here.

Finally, **Debugging in Kubernetes** will be treated in a dedicated upcoming article. It deserves more depth than a quick section here.

As usual, you can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

Before we start: this month publishing will be lighter than expected due to work commitments and deadlines. The next article will be by the end of March, and then we will return to the regular schedule in April. Thanks for your understanding!

---

## Why Container Logs Matter

In Kubernetes, containers are ephemeral. Pods are replaceable. Nodes come and go.

Your logs are often the *only* narrative of what really happened.

In a production cluster, logs answer questions like:

- Why did this pod restart?
- Is the application failing during startup?
- Is the readiness probe failing because of a real error?
- Is traffic actually reaching the container?

Logs are not observability by themselves — but they are the first and fastest diagnostic layer.

---

## Prerequisites

A running cluster (Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)).

---

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260304-ckad
```

Create a simple failing workload:

```bash
k apply -f manifests/01-failing-app.yaml
```

Watch it:

```bash
k get pods -w
```

You should see `CrashLoopBackOff`. Perfect. Now we have something to inspect.

---

## Basic Log Retrieval

Get the pod name:

```bash
k get pods
```

Then:

```bash
k logs <pod-name>
```

You should see:

```
Starting app...
Simulating failure
```

That's it. That's the root cause. The container exits with code 1.

---

## Logs from a Specific Container

If a pod has multiple containers:

```bash
k logs <pod-name> -c <container-name>
```

Without `-c`, Kubernetes assumes the first container.

In real-world scenarios you can have sidecars, init containers, or multiple app containers. In these situations this flag matters.

---

## Logs from the Previous Crash

When a container restarts, the default logs command shows only the current instance.

`--previous` retrieves the logs from the last terminated container.

```bash
k logs <pod-name> --previous
```

---

## Follow Logs in Real Time

Equivalent of `tail -f`:

```bash
k logs -f <pod-name>
```

Now apply a long-running workload:

```bash
k apply -f manifests/02-streaming-app.yaml
```

Get the pod name and stream its logs:

```bash
POD=$(k get pod -l app=streaming-app -o jsonpath='{.items[0].metadata.name}')
k logs -f $POD
```

This is useful during rollouts, live diagnostics, or verifying traffic patterns.

Press `Ctrl+C` to stop.

---

## Logs from All Pods of a Deployment

Instead of targeting a single pod:

```bash
k logs -l app=failing-app
```

With follow:

```bash
k logs -f -l app=failing-app
```

This aggregates logs from all matching pods.

---

## Limiting Output

Sometimes logs are massive.

Use:

```bash
k logs --tail=50 <pod-name>
```

Or:

```bash
k logs --since=1h <pod-name>
```

These flags reduce noise and make log inspection surgical instead of overwhelming.

---

## Important Concept: Where Logs Actually Live

Kubernetes does not store logs long-term.

By default:

- Containers write to `stdout` and `stderr`
- The container runtime writes logs to node disk
- `kubectl logs` reads from the node

If the pod is deleted, logs are gone (unless you use centralized logging).

This is why production systems typically integrate:

- EFK / ELK stacks
- Loki
- Cloud-native logging services

But that's beyond CKAD scope — and beyond today's minimal article.

---

## Wrapping Up

Today we focused on using `kubectl logs` effectively to understand what’s happening inside your containers. In the next article, we'll properly explore **Debugging in Kubernetes** — including `kubectl exec` and advanced techniques — with the depth it deserves.

---

## Final Cleanup

```bash
k delete -f manifests/
```
