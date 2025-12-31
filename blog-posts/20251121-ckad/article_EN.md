---
layout: default
title: "CKAD Preparation — Implementing Blue/Green and Canary Deployments Using Kubernetes Primitives"
date: 2025-11-21
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251121-ckad/article.webp"
summary: "Learn how to implement Blue/Green and Canary deployments using Kubernetes primitives — a key CKAD skill for application design and build."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

In this post, we’ll cover the requirements within the “Application Deployment” domain:

> Implement Blue/Green and Canary deployments using Kubernetes primitives

Here we’ll cover how to **implement Blue/Green and Canary deployments** — a fundamental CKAD topic for managing application rollout strategies and minimizing downtime.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (Minikube, Docker Desktop, or https://killercoda.com/playgrounds/course/kubernetes-playgrounds) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article’s folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20251121-ckad
```

## Understanding Deployment Strategies in Kubernetes

Modern application delivery often requires updating workloads with zero downtime. Kubernetes provides native primitives — Deployments, Services, labels, and rolling updates — that make it possible to implement common release strategies without relying on external tools.

In this exercise, we focus on two CKAD-relevant patterns:

-   **Blue/Green deployments** — keep two versions running side by side and switch traffic by updating labels and selectors.
-   **Canary deployments** — send a small portion of traffic to the new version for validation before rolling it out fully.

Both examples rely only on Kubernetes-native mechanisms.

## Hands-On Challenge: Blue/Green Deployment

A Blue/Green deployment uses two identical environments: one running the current version (Blue) and the other running the new version (Green).

We'll run two Deployments:

-   **blue-app** — version 1
-   **green-app** — version 2

Traffic will be routed through a Service that selects which version to expose.

Before starting, create a ConfigMap containing two simple HTML files representing each version’s “color.”

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-assets
data:
  blue.html: |
    <html>
      <body>
        <div>Hello, it's BLUE !</div>
      </body>
    </html>

  green.html: |
    <html>
      <body>
        <div>Hello, it's GREEN !</div>
      </body>
    </html>
```

Apply it:

```bash
kubectl apply -f manifests/00-web-assets.yaml
```

Alternatively, you can create it directly from files. During the exam, you might prefer this method to save time.

```bash
k create configmap web-assets --from-file=assets/blue.html --from-file=assets/green.html
```

Now we can create the Blue deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blue-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo
      version: blue
  template:
    metadata:
      labels:
        app: demo
        version: blue
    spec:
      volumes:
        - name: web-assets
          configMap:
            name: web-assets
            items:
              - key: blue.html
                path: index.html
      containers:
        - name: app
          image: nginx:1.29.3-perl
          env:
            - name: COLOR
              value: "blue"
          volumeMounts:
            - name: web-assets
              mountPath: "/usr/share/nginx/html"
              readOnly: true
```

Apply it:

```bash
k apply -f manifests/01-blue.yaml
```

Next, create the Green deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: green-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo
      version: green
  template:
    metadata:
      labels:
        app: demo
        version: green
    spec:
      volumes:
        - name: web-assets
          configMap:
            name: web-assets
            items:
              - key: green.html
                path: index.html
      containers:
        - name: app
          image: nginx:1.29.3-perl
          env:
            - name: COLOR
              value: "green"
          volumeMounts:
            - name: web-assets
              mountPath: "/usr/share/nginx/html"
              readOnly: true
```

Apply it:

```bash
k apply -f manifests/02-green.yaml
```

Confirm both versions are running:

```bash
k get pods -l app=demo
```

We should get two pods running, one for each version.

```bash
NAME                         READY   STATUS    RESTARTS   AGE
blue-app-674544c6cf-vfnc9    1/1     Running   0          8m17s
green-app-76897ccfb6-n29b4   1/1     Running   0          7m50s
```

Create a Service that initially routes traffic to the `blue` version:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-svc
spec:
  selector:
    app: demo
    version: blue
  ports:
    - port: 80
      targetPort: 80
```

Apply it:

```bash
k apply -f manifests/03-service.yaml
```

Let's check that the traffic goes to the `blue` deployment:

```bash
k run -it --rm --image=curlimages/curl --restart=Never -- curl demo-svc
```

By patching the Service selector, we can switch traffic to the `green` deployment:

```bash
k patch svc demo-svc -p '{"spec":{"selector":{"app":"demo","version":"green"}}}'
```

If we run the curl command again we should now hit the `green` version:

```bash
k run -it --rm --image=curlimages/curl --restart=Never -- curl demo-svc
```

## Hands-On Challenge: Canary Deployment

A canary deployment gradually introduces a new version to a subset of users before rolling it out completely. Kubernetes Services do not natively support traffic weighting, but we can simulate it by adjusting replica counts.

We’ll create two Deployments:
-   **stable-app** — the stable version
-   **canary-app** — the new version with fewer replicas

Both will be selected by the same Service, allowing traffic distribution to follow replica proportions.

This is the manifest for the stable version:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stable-app
spec:
  replicas: 4
  selector:
    matchLabels:
      app: canary-demo
  template:
    metadata:
      labels:
        app: canary-demo
        version: stable
    spec:
      containers:
        - name: app
          image: nginx:1.29.3-perl
```

Apply it:

```bash
k apply -f manifests/04-stable.yaml
```

This is the manifest for the canary version:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: canary-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: canary-demo
      version: canary
  template:
    metadata:
      labels:
        app: canary-demo
        version: canary
    spec:
      containers:
        - name: app
          image: nginx:1.29.3-perl
          env:
            - name: CANARY
              value: "true"
```

Apply it:

```bash
k apply -f manifests/05-canary.yaml
```

Create a Service that selects both deployments:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: canary-svc
spec:
  selector:
    app: canary-demo
  ports:
    - port: 80
      targetPort: 80
```

Apply it:

```bash
k apply -f manifests/06-service.yaml
```

Now, let's test traffic distribution:

```bash
for i in {1..20}; do
  k run -it --rm --image=curlimages/curl --restart=Never curl canary-svc
done
```

We do expect to see:
-   Most responses hit **stable-app** (4 replicas).
-   Some responses hit **canary-app** (1 replica).

This simulates a real canary rollout: the new version receives a small amount of traffic for validation.

If everything looks good with the canary, we can promote it by scaling up the canary and scaling down the stable:

```bash
k scale deploy/stable-app --replicas=0
```

You’ve completed a manual canary promotion using Kubernetes-native mechanisms only.

## Wrapping Up: What We’ve Covered

In this exercise, we practiced how to implement Blue/Green and Canary deployments using only Kubernetes-native constructs.

Here’s a quick recap:
- **Blue/Green deployment** implemented through label switching and Service routing.
- **Canary rollout** simulated by distributing traffic based on replica counts.

While these approaches are valid for CKAD and effective for controlled scenarios, Kubernetes provides only basic primitives for rollout strategies. Traffic routing is binary — a Pod either matches a selector or it doesn’t — and there’s no native support for precise percentage-based routing, custom metrics, or automated progressive analysis.

In production environments, these limitations are commonly addressed through:
- Advanced CNIs, which offer more granular traffic control.
- Service mesh layers such as Istio, which enable weighted routing, automated rollback, request-level policies, and shadow deployments.

📝 In later modules, we’ll explore these components and see how they unlock more advanced deployment patterns beyond what Kubernetes provides natively.

## Final cleanup

When you’re done, remove all resources:

```bash
k delete -f manifests/
```
