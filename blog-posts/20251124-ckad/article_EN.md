---
layout: default
title: "CKAD Preparation — Understanding Deployments and Rolling Updates in Kubernetes"
date: 2025-11-24
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251124-ckad/article.webp"
summary: "Learn how to update Kubernetes Deployments and perform rolling updates using native primitives — an essential CKAD skill for managing application rollout strategies with zero downtime."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

In this post, we’ll cover the requirements within the “Application Deployment” domain:

> Understand Deployments and how to perform rolling updates

We'll cover how to update an existing application deployment with zero downtime and how to go back if something goes wrong.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (like, Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article’s folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20251124-ckad
```

## Hands-On Challenge: Performing and Controlling a Rolling Update

Rolling updates allow you to update applications running in Kubernetes without downtime, replacing Pods gradually and ensuring that the workload remains available throughout the update process. This is the default update strategy used by Deployments, and it is an essential concept for the CKAD exam.

Kubernetes manages rolling updates by creating new ReplicaSet revisions and transitioning traffic from the old Pods to the new ones in a controlled way. Key parameters such as maxUnavailable and maxSurge govern how many Pods can be added or removed during the update process.

In this exercise, we’ll explore how to configure rolling updates, monitor rollout status, perform rollbacks, and intentionally break a deployment to test recovery.

Create this Deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rolling-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: rolling-demo
  template:
    metadata:
      labels:
        app: rolling-demo
        version: v1
    spec:
      containers:
        - name: app
          image: nginx:1.27.3
```

Apply it:

```bash
k apply -f manifests/01-rolling.yaml
```

Verify that all Pods are running:

```bash
k get pods -l app=rolling-demo
```

We should get three pods running, all with version v1.

```bash
NAME                           READY   STATUS    RESTARTS   AGE
rolling-app-69985cf498-bvfmf   1/1     Running   0          12s
rolling-app-69985cf498-mqdkr   1/1     Running   0          12s
rolling-app-69985cf498-tx65k   1/1     Running   0          12s
```

## Triggering a Rolling Update

Trigger a Rolling Update by changing the image version in the Deployment manifest to nginx:1.29.3-perl:

```bash
k set image deploy/rolling-app app=nginx:1.29.3-perl
```

Kubernetes immediately begins a rolling update using the strategy parameters you set earlier.

Check rollout status:

```bash
k rollout status deploy/rolling-app
```

You should see output indicating that the rollout is in progress and eventually completes successfully:

```bash
controlplane:~$ k rollout status deploy/rolling-app
Waiting for deployment "rolling-app" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "rolling-app" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "rolling-app" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "rolling-app" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "rolling-app" rollout to finish: 1 old replicas are pending termination...
deployment "rolling-app" successfully rolled out
```

Check the Pods again:

```bash
k get pods -l app=rolling-demo
```

You should see that the Pods are now running the new image version.

```bash
k get pods -l app=rolling-demo -o=jsonpath="{range .items[*]}{.metadata.name}:{.spec.containers[0].image}{'\n'}{end}"
```

Expected output:

```bash
rolling-app-69577f58f4-cz8mq:nginx:1.29.3-perl
rolling-app-69577f58f4-m5rk7:nginx:1.29.3-perl
rolling-app-69577f58f4-qwd22:nginx:1.29.3-perl
```

### Explore Update Strategy Controls

Now, we'll see how to control the rolling update process using the maxSurge and maxUnavailable parameters.

Duplicate the existing manifest and change the update strategy to the following:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 0
    maxUnavailable: 1
```

Apply the new manifest:

```bash
kubectl apply -f manifests/02-update-strategy.yaml
```

To trigger a new rolling update let's change again the image:

```bash
k set image deploy/rolling-app app=nginx:1.28
```

This time the rollout will proceed more cautiously, ensuring that at least two Pods are always available during the update.

### Introduce a Failing Update

Now simulate a real-world failure scenario by deploying an invalid image:

```bash
k set image deploy/rolling-app app=nginx:not-a-real-tag
```

Check rollout status:

```bash
k rollout status deploy/rolling-app
```

You should see the Deployment hang in a degraded state.

Inspect events:

```bash
k describe deploy/rolling-app
```

Inspect the pods:
```bash
k get pods -l app=rolling-demo
```

You should see events indicating that the new pod is failing to start due to the invalid image:

```bash
rolling-app-69985cf498-9rbvz   1/1     Running        0          93s
rolling-app-69985cf498-f8hdr   1/1     Running        0          91s
rolling-app-6d584f9d5d-lwgql   0/1     ErrImagePull   0          47s
```

Notice how Kubernetes avoids taking down the remaining healthy Pods, maintaining application availability despite the failed update.

### Roll Back to a Working Version

To restore service quickly, roll back to the previous revision:

```bash
k rollout undo deploy/rolling-app
```

Verify that Pods are restored to the last known good version:

```bash
k get pods -l app=rolling-demo
```

You can also inspect revision history:

```bash
k rollout history deploy/rolling-app
```

## Wrapping Up: What We’ve Covered

In this exercise, we explored how Kubernetes Deployments perform rolling updates and how to control their behavior.

You practiced how to:

- Trigger rolling updates using image changes.
- Modify update strategies through maxSurge and maxUnavailable.
- Observe real-time rollout behavior.
- Simulate a failed rollout using an invalid image.
- Perform rollbacks using k rollout undo.

Rolling updates are central to Kubernetes workload management and form an essential part of CKAD exam tasks. Mastering Deployment strategies ensures you can update applications safely, diagnose failed rollouts, and maintain availability during changes.

## Final cleanup

When you’re done, remove all resources:

```bash
k delete -f manifests/
```
