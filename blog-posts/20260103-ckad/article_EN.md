---
layout: default
title: "CKAD Preparation — Using Kustomize to deploy an Nginx Application"
date: 2026-01-03
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260103-ckad/article.webp"
summary: "Discover how to use Kustomize to manage reusable and modular Kubernetes configurations. Learn to create bases, overlays, and customizations for staging and production environments."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through short, focused hands-on labs.

In this article, we'll cover the requirements of the "Application Deployment" domain:

> Kustomize

We'll explore what Kustomize is and how to use it to manage reusable and modular Kubernetes configurations.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (like, Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260103-ckad
```

## Hands-On Exercise: Using Kustomize to Deploy an Nginx Application

Kustomize is a Kubernetes-native tool designed to manage YAML configurations in a modular and reusable way, without having to resort to external templates like Helm. It's built directly into kubectl (you can use it with `kubectl apply -k`) and allows you to create different versions of the same configuration without duplicating files.

When we deploy an application on Kubernetes, we often need to create and manage many different resources (Pods, Services, ConfigMaps, Secrets, etc.). These resources frequently share common configurations, but may also have specific differences depending on the environment (development, staging, production). Kustomize helps us manage these configurations efficiently.

### Creating a Base with Kustomize

To understand how Kustomize works, let's create a simple base with a Deployment and a Service for Nginx, and then we'll create two overlays for staging and production environments.

Let's start by creating the folder structure for Kustomize:

```bash
kustomize/
  base/
    deployment.yaml
    service.yaml
    kustomization.yaml
```

In the `base/` folder, let's create the `deployment.yaml` file with the following content:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
```

And the `service.yaml` file with the following content:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
```

Finally, let's create the `kustomization.yaml` file in the `base/` folder with the following content:

```yaml
resources:
  - deployment.yaml
  - service.yaml

labels:
  - includeSelectors: true
    pairs:
      app: nginx
```

In Kustomize, transformers are tools that allow you to modify resources in a declarative way. For example, we can use a transformer to change the container image or the number of replicas without having to directly modify the original YAML files.

In the example above, we used `commonLabels` as a simple transformer to add a common label to all resources.

### Creating Overlays for Staging and Production

Overlays allow us to adapt the base to different environments by modifying namespaces, replica counts, or deployment names without duplicating manifests.

Structure of our overlays:

```bash
kustomize/
  overlays/
    staging/
      kustomization.yaml
      patch.yaml
    production/
      kustomization.yaml
      patch.yaml
```

In the `overlays/staging/` folder, let's create the `kustomization.yaml` file with the following content:

```yaml
resources:
  - ../../base

namespace: staging
nameSuffix: -staging

patches:
  - path: patch.yaml
```

Let's create the `patch.yaml` file with staging-specific modifications, such as the number of replicas:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 2
```

In the `overlays/production/` folder, let's create the `kustomization.yaml` file with the following content:

```yaml
resources:
  - ../../base

namespace: production
nameSuffix: -prod

patches:
  - path: patch.yaml
```

Let's create the `patch.yaml` file with production-specific modifications, such as the number of replicas:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 5
```

Let's create the necessary namespaces:

```bash
k create ns staging
k create ns production
```

To apply the staging configuration:
```bash
k apply -k overlays/staging/
```

To apply the production configuration:
```bash
k apply -k overlays/production/
```

Let's verify that the resources were created correctly:

```bash
k get deploy, svc, po -n staging
k get deploy, svc, po -n production
```

It's possible to generate the final manifests without applying them:
```bash
kustomize build overlays/staging > ../manifests/nginx-staging.yaml
kustomize build overlays/production > ../manifests/nginx-production.yaml
```

Note that unlike Helm, Kustomize doesn't use Go Templates, but instead relies on patches and declarative transformations, making configuration management simpler without having to learn a templating language. Additionally, it doesn't manage releases or versions like Helm does, but focuses exclusively on configuration management.

## Recap: What We've Learned

In this exercise, we explored Kustomize and how it can simplify the management of Kubernetes manifests across multiple contexts:

- Creating a reusable base with Deployment and Service.

- Applying commonLabels to standardize resources.

- Creating overlays for staging and production with different namespaces, suffixes, and replica counts.

- Modifying configurations without duplicating manifests, using patches and Kustomization.

- Viewing final manifests before applying them to the cluster.

Kustomize is a fundamental tool for keeping Kubernetes configurations clean and modular, making it essential for those preparing for the CKAD exam or managing clusters with multiple environments.

## Final Cleanup

To wrap up, let's clean-up everything we created for this exercise:

```bash
k delete -k overlays/staging/
k delete -k overlays/production/
k delete ns staging production
```
