---
layout: default
title: "CKAD Preparation — Implementing Blue/Green and Canary Deployments Using Kubernetes Primitives"
date: 2025-10-23
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

A running Kubernetes cluster (Minikube, Docker Desktop, or [KillerCoda Playgrounds](https://killercoda.com/playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article’s folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20251121-ckad
```

## Understanding Deployment Strategies in Kubernetes

Modern application delivery often requires updating workloads with **zero downtime**. Kubernetes provides native primitives---Deployments, Services, labels, and rolling updates---that help implement common release strategies without external tools.

In this exercise, we focus on two CKAD-relevant patterns:

-   **Blue/Green deployments** --- keep two versions running side-by-side; switch traffic by updating labels/selectors.
-   **Canary deployments** --- send a small portion of traffic to the new version for validation before rolling out fully.

Both examples use only Kubernetes-native mechanisms.

## Hands-On Challenge: Blue/Green Deployment

A Blue/Green deployment is a release strategy that uses two identical environments — one running the current version of an application (Blue) and one running the new version (Green).

We'll run two Deployments:

-   **blue-app** --- version 1
-   **green-app** --- version 2

Traffic will be routed through a Service that selects which version to expose.

Before we start, we need to create a ConfigMap to hold simple two HTML files representing each version "color".

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

Now we can create the blue deployment manifest:

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

Also, let's create the green deployment manifest as well.

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

Now both versions should be running. Let's check it:

```bash
k get pods -l app=demo
```

You should get two pods running, one for each version.

```bash
NAME                         READY   STATUS    RESTARTS   AGE
blue-app-674544c6cf-vfnc9    1/1     Running   0          8m17s
green-app-76897ccfb6-n29b4   1/1     Running   0          7m50s
```

Next, we create a Service to route traffic initially to the `blue` version.

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

A canary deployment is used to gradually roll out a new version of an application to a subset of users before making it available to everyone. Kubernetes Service does not natively support traffic weighting, but we can simulate a Canary deployment by adjusting the number of replicas.

In this lab we'll create two Deployments:
-   **stable-app** --- the stable version
-   **canary-app** --- the new version, with fewer replicas

Notice that both deployments will be selected by the same Service, allowing traffic to be split based on the number of replicas.

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

Let's apply it:

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

Finally, create a Service that selects both deployments:

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

Run multiple curl commands to test traffic distribution:

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

You've completed a manual canary promotion using Kubernetes primitives only.

## Wrapping Up: What We’ve Covered

In this exercise, we practiced how to implement Blue/Green and Canary deployments using only Kubernetes-native constructs.

Here's a recap of what we did in this lab:
- A Blue/Green deployment implemented entirely through label switching and Service routing.
- A Canary rollout created by proportioning traffic via Pod replica ratios.

While these approaches are fully valid for CKAD and work well in controlled scenarios, must be noted that Kubernetes offers only basic primitives for deployment strategies. Traffic routing is binary (a Pod matches a selector or it doesn't), and there’s no native way to shift precise percentages, use custom metrics, or automate progressive analysis.

In real-world environments, these limitations are often addressed by:
- Advanced CNIs that provide richer traffic control capabilities.
- Service mesh layers such as Istio, which enable features like weighted traffic splitting, automated rollback, per-request routing, and shadow deployments.

📝 In later modules, we’ll explore these ecosystem components and see how they enable more advanced deployment patterns beyond what’s available with native Kubernetes alone.

## Final cleanup

When done, remove all resources:

```bash
k delete -f manifests/
```
