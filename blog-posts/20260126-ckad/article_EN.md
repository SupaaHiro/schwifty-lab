---
layout: default
title: "CKAD Preparation — Understanding and Managing API Deprecations"
date: 2026-01-26
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260126-ckad/article.webp"
summary: "Learn how to identify, understand, and migrate Kubernetes resources using deprecated API versions. Master essential tools and techniques for maintaining application health across cluster upgrades."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

This article marks the beginning of a new section in our CKAD preparation journey. We're moving from the "Application Deployment" domain to the **"Application Observability and Maintenance"** domain. In this article, we'll cover the requirement:

> Understand API deprecations

We'll explore what API deprecations are, why they occur, and most importantly, how to identify and migrate resources that use deprecated API versions — a critical skill for maintaining applications across Kubernetes cluster upgrades.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (like, Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260126-ckad
```

## Understanding API Deprecations in Kubernetes

Kubernetes is an evolving platform. As new features are added and best practices emerge, certain API versions become outdated and are eventually deprecated and removed. This is a normal part of the software lifecycle, but it requires careful attention from developers and operators.

### Why Do API Deprecations Happen?

API deprecations occur for several reasons:

- **API Improvements**: Newer API versions may offer better functionality, security, or consistency
- **Resource Consolidation**: Multiple similar resources may be consolidated into a single, more powerful API
- **Bug Fixes**: Fundamental design issues in older APIs may necessitate breaking changes
- **Performance**: Newer APIs may be more efficient or scalable

### The Kubernetes API Deprecation Policy

Kubernetes follows a well-defined [deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/):

1. **Announcement**: API versions are announced as deprecated in release notes
2. **Grace Period**: Deprecated APIs continue to work for a specific number of releases (typically 3 releases or 9 months, whichever is longer)
3. **Removal**: After the grace period, the API version is removed and will no longer work

For example, when Kubernetes 1.22 was released, several beta APIs that had been deprecated were removed, including:
- `extensions/v1beta1` and `apps/v1beta1` for Deployments, DaemonSets, ReplicaSets
- `networking.k8s.io/v1beta1` for Ingress
- `policy/v1beta1` for PodSecurityPolicy

## Hands-On Challenge: Identifying and Migrating Deprecated APIs

Let's work through a practical scenario where we need to identify and migrate resources using deprecated APIs. We'll use a Kubernetes 1.24 cluster with deprecated APIs, then upgrade to 1.25 where those APIs are removed, experiencing firsthand how to handle this situation.

For this exercise, we'll use the [KillerCoda Ubuntu Playground](https://killercoda.com/playgrounds/scenario/ubuntu) to set up a fresh environment.

### Step 0: Setting Up the Environment

First, let's install K3s version 1.24.17, which still supports the deprecated `policy/v1beta1` API for PodDisruptionBudget:

```bash
export INSTALL_K3S_VERSION="v1.24.17+k3s1"
curl -sfL https://get.k3s.io | sh -
```

Create an alias for easier kubectl usage:

```bash
alias k='/usr/local/bin/kubectl'
```

Verify the cluster is running:

```bash
kubectl version --short
```

You should see Kubernetes version 1.24.17.

### Step 1: Explore Available API Versions

First, let's understand what API versions are available in our cluster:

```bash
kubectl api-versions
```

This command lists all API versions supported by your cluster. You'll see output like:

```bash
admissionregistration.k8s.io/v1
apps/v1
authentication.k8s.io/v1
authorization.k8s.io/v1
...
policy/v1
storage.k8s.io/v1
...
```

You can also list all available resource types:

```bash
kubectl api-resources
```

This shows the short names, API groups, whether resources are namespaced, and the kind of each resource.

### Step 2: Create Resources with Deprecated APIs

Let's create some manifests that use older (and in some cases deprecated) API versions. In a real scenario, you might inherit these from previous developers or older deployments.

First, let's create a PodDisruptionBudget using an older API version. Create the file `manifests/01-pdb-old.yaml`:

```yaml
# This uses the v1beta1 API which was deprecated in Kubernetes 1.21
# and removed in Kubernetes 1.25
apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb-old
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: nginx
```

Now let's create a Pod to go with it. Create `manifests/02-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    ports:
    - containerPort: 80
    resources:
      limits:
        memory: 256Mi
        cpu: 200m
      requests:
        memory: 64Mi
        cpu: 50m
```

Try to apply the old PodDisruptionBudget:

```bash
kubectl apply -f manifests/01-pdb-old.yaml
```

When you apply manifests with deprecated (but not yet removed) APIs, Kubernetes shows warnings. You should see a warning like:

`Warning: policy/v1beta1 PodDisruptionBudget is deprecated in v1.21+, unavailable in v1.25+; use policy/v1 PodDisruptionBudget`

Apply the Pod manifest:

```bash
kubectl apply -f manifests/02-pod.yaml
```

Verify both resources are created:

```bash
kubectl get pdb,pod
```

### Step 3: Understanding PodDisruptionBudget API Evolution

To better understand the deprecation timeline, here's the state of PodDisruptionBudget API across different Kubernetes versions:

| Kubernetes Version | policy/v1beta1 | policy/v1 |
|--------------------|----------------|----------|
| ≤ 1.20 | ✅ Valid | ❌ Not Available |
| 1.21–1.24 | ⚠️ Deprecated | ✅ Valid |
| ≥ 1.25 | ❌ Removed | ✅ Valid |

Our cluster is currently running version 1.24, which is why we see deprecation warnings but the resource still works. Let's see what happens when we upgrade.

### Step 4: Upgrading the Cluster and Experiencing API Removal

Now let's upgrade our K3s cluster to version 1.25.16, where the `policy/v1beta1` API has been completely removed:

```bash
export INSTALL_K3S_VERSION="v1.25.16+k3s1"
curl -sfL https://get.k3s.io | sh -
```

Wait a few moments for the cluster to restart, then verify the new version:

```bash
kubectl version --short
```

You should now see Kubernetes version 1.25.16.

Let's try to apply the old PodDisruptionBudget manifest again:

```bash
kubectl apply -f manifests/01-pdb-old.yaml
```

This time, you'll see an error:

```bash
Error from server (NotFound): error when creating "manifests/01-pdb-old.yaml": the server could not find the requested resource
```

The API version `policy/v1beta1` no longer exists in Kubernetes 1.25! This is what happens when deprecated APIs are removed. Any existing resources using the old API version are automatically migrated by Kubernetes, but you cannot create new resources or update existing ones using the old API.

### Step 5: Migrating to Current API Versions

Now let's create the correct, up-to-date versions of these resources.

Create `manifests/04-pdb-new.yaml`:

```yaml
# Current API version (stable since Kubernetes 1.21)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: nginx
```

The key change here is simply the API version: `policy/v1beta1` → `policy/v1`. Fortunately, for PodDisruptionBudget, the spec remains the same between these versions, making migration straightforward.

Apply the updated resource:

```bash
kubectl apply -f manifests/03-pdb-new.yaml
```

Verify it was created successfully:

```bash
kubectl get pdb
```

You should now see the new `nginx-pdb` without any warnings.

### Step 6: Reading Kubernetes Changelogs and Deprecation Guides

One of the most important practices for staying ahead of API deprecations is regularly reviewing Kubernetes release notes and deprecation guides. Before any cluster upgrade, you should check:

1. **Changelog - Urgent Upgrade Notes**: Each Kubernetes release includes an "Urgent Upgrade Notes" section that highlights breaking changes and removed APIs. For example, the [Kubernetes 1.25 CHANGELOG](https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.25.md#urgent-upgrade-notes) explicitly states:

   > *"PodDisruptionBudget in the policy/v1beta1 API version is no longer served as of v1.25"*

2. **Deprecation Guide**: The official [Kubernetes Deprecation Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/) provides comprehensive information about deprecated APIs, including:
   - When each API was deprecated
   - When it will be removed
   - What to migrate to
   - Any spec changes required

For our PodDisruptionBudget example, the deprecation guide clearly shows that `policy/v1beta1` was deprecated in 1.21 and removed in 1.25, with migration to `policy/v1`.

### Step 7: Checking for Deprecated APIs in Your Cluster

To identify resources in your cluster using deprecated APIs, you can:

1. **Check specific resource types**:

```bash
kubectl get pdb -A -o json | grep -i apiVersion
```

2. **Use third-party tools** like [Pluto](https://github.com/FairwindsOps/pluto) or [kubent (Kube No Trouble)](https://github.com/doitintl/kube-no-trouble):

```bash
# Example with pluto (if installed)
pluto detect-files -d manifests/

# Example with kubent (if installed)
kubent
```

These tools scan your cluster and manifests for deprecated API versions and provide migration guidance.

### Step 8: Best Practices for Managing API Deprecations

Here are some strategies to stay ahead of API deprecations:

1. **Read CHANGELOGs and Deprecation Guides**: Always review the Kubernetes CHANGELOG (especially "Urgent Upgrade Notes") and the official Deprecation Guide before upgrading. These documents clearly state which APIs are being removed and provide migration paths.
2. **Test Upgrades**: Use staging environments to test cluster upgrades before production. This allows you to identify and fix deprecated API usage without affecting production workloads.
3. **Monitor Warnings**: Pay attention to deprecation warnings in kubectl output. Kubernetes provides warnings well in advance of removing APIs.
4. **Automated Scanning**: Use tools like pluto or kubent in CI/CD pipelines to automatically detect deprecated API usage in your manifests.
5. **Version Your Manifests**: Keep manifests in version control and update them regularly to use the latest stable API versions.
6. **Stay Current**: When creating new resources, always use the latest stable API versions to avoid inheriting deprecated APIs.

## Recap: What We've Covered

In this exercise, we explored API deprecations in Kubernetes and learned essential skills for maintaining application health across cluster upgrades:

- Understanding why API deprecations happen and Kubernetes' deprecation policy
- Setting up a K3s cluster with a specific version to test deprecated APIs
- Using `kubectl api-versions` and `kubectl api-resources` to explore available APIs
- Identifying deprecated API versions in manifests
- Recognizing deprecation warnings during `kubectl apply` on Kubernetes 1.24
- Understanding the PodDisruptionBudget API evolution from v1beta1 to v1
- Experiencing API removal firsthand by upgrading from Kubernetes 1.24 to 1.25
- Migrating PodDisruptionBudget from `policy/v1beta1` to `policy/v1`
- Reading Kubernetes CHANGELOGs and the Deprecation Guide to stay informed
- Best practices for staying ahead of deprecations
- Using third-party tools like pluto and kubent for automated detection

Understanding and managing API deprecations is crucial for CKAD exam success and for maintaining production Kubernetes clusters. By staying current with API versions and following Kubernetes release notes, you ensure your applications remain compatible with cluster upgrades and benefit from the latest features and improvements.

## Final Cleanup

To wrap up, let's clean up everything we created for this exercise:

```bash
kubectl delete pdb nginx-pdb
kubectl delete pod nginx-pod
```
