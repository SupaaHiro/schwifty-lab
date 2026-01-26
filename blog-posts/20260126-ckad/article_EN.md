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
k version --short
```

You should see Kubernetes version 1.24.17.

### Step 1: Explore Available API Versions

First, let's understand what API versions are available in our cluster:

```bash
k api-versions
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
k api-resources
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
k apply -f manifests/01-pdb-old.yaml
```

When you apply manifests with deprecated (but not yet removed) APIs, Kubernetes shows warnings. You should see a warning like:

`Warning: policy/v1beta1 PodDisruptionBudget is deprecated in v1.21+, unavailable in v1.25+; use policy/v1 PodDisruptionBudget`

Apply the Pod manifest:

```bash
k apply -f manifests/02-pod.yaml
```

Verify both resources are created:

```bash
k get pdb,pod
```

### Step 3: Understanding PodDisruptionBudget API Evolution

To better understand the deprecation timeline, here's the state of PodDisruptionBudget API across different Kubernetes versions:

| Kubernetes Version | policy/v1beta1 | policy/v1        |
|--------------------|----------------|------------------|
| ≤ 1.20             | ✅ Valid      | ❌ Not Available |
| 1.21–1.24          | ⚠️ Deprecated | ✅ Valid         |
| ≥ 1.25             | ❌ Removed    | ✅ Valid         |

Our cluster is currently running version 1.24, which is why we see deprecation warnings but the resource still works. Let's see what happens when we upgrade.

### Step 4: Upgrading the Cluster and Experiencing API Removal

Now let's upgrade our K3s cluster to version 1.25.16, where the `policy/v1beta1` API has been completely removed:

```bash
export INSTALL_K3S_VERSION="v1.25.16+k3s1"
curl -sfL https://get.k3s.io | sh -
```

Wait a few moments for the cluster to restart, then verify the new version:

```bash
k version --short
```

You should now see Kubernetes version 1.25.16.

Let's try to apply the old PodDisruptionBudget manifest again:

```bash
k apply -f manifests/01-pdb-old.yaml
```

This time, you'll see an error:

```bash
Error from server (NotFound): error when creating "manifests/01-pdb-old.yaml": the server could not find the requested resource
```

The API version `policy/v1beta1` no longer exists in Kubernetes 1.25! This is what happens when deprecated APIs are removed. Any existing resources using the old API version are automatically migrated by Kubernetes, but you cannot create new resources or update existing ones using the old API.

#### Understanding Version Skew and Beta API Lifecycle

To fully grasp why Beta APIs must be supported for at least 3 releases after deprecation, we need to understand Kubernetes' **version skew policy**. This is defined in **Rule #4a** of the [API deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/#deprecating-parts-of-the-api):

- **GA API** versions may be marked as deprecated, but must not be removed within a major version of Kubernetes
- **Beta API** versions are deprecated no more than 9 months or 3 minor releases after introduction (whichever is longer), and are no longer served 9 months or 3 minor releases after deprecation (whichever is longer)
- **Alpha API** versions may be removed in any release without prior deprecation notice

**What is the "2 minor version skew"?**

Kubernetes officially supports a maximum skew of **2 minor versions** between:
- Control plane
- Kubelet
- Client / API consumer (kubectl)

For example, if your control plane is running **1.25**, the supported client/kubelet versions are **1.23–1.25**.

> 👉 **Important**: This means "2 releases" refers to 2 **minor** versions, not major versions.

Let's work through a concrete example to understand this better. Suppose a Beta API is introduced in Kubernetes 1.25:

**1️⃣ Introduction**
- **v1.25** → Beta API becomes available

**2️⃣ Deprecation (after ≥ 3 minor releases)**
- Not before **v1.28**:
  - 1.26 (release 1)
  - 1.27 (release 2)
  - 1.28 (release 3) ← earliest deprecation point

**3️⃣ Removal (after ≥ another 3 minor releases from deprecation)**
- Not before **v1.31**:
  - 1.29 (release 1)
  - 1.30 (release 2)
  - 1.31 (release 3) ← earliest removal point

**Where does the 2-minor version skew come in?**

Imagine this perfectly supported scenario:
- **Control plane**: v1.31
- **Client / workload**: v1.29
- **Difference**: 2 minor versions ✅

Even though the control plane is at v1.31 (where the Beta API is being removed), a client running v1.29 would still be compatible because:
- The Beta API was introduced in v1.25
- It was deprecated in v1.28
- It's only removed in v1.31
- A client at v1.29 (which is v1.31 - 2) would have had time to migrate to the new API version during the deprecation window

This is why the "3 release minimum after deprecation" rule ensures that no supported client loses access to an API unexpectedly during a cluster upgrade within the supported version skew.

> Notice that in case of the `PodDisruptionBudget`, the Beta API has been around for a long time (since Kubernetes 1.5), so it's an example of “stagnant” beta, exactly what Rule #4a wants to avoid in the future.

### Step 5: Migrating to Current API Versions

The existing PodDisruptionBudget resource was automatically migrated by Kubernetes during the upgrade.

You can verify this by checking the resource:

```bash
k get pdb nginx-pdb-old -o yaml
```

The next time we want to create or update a PodDisruptionBudget, we must use the current API version: `policy/v1`. Any existing manifest must be updated accordingly to use the new API version:

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
   get pdb -A -o json | grep -i apiVersion
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

In this article, we covered the fundamentals of API deprecations in Kubernetes as part of CKAD preparation, transitioning to the "Application Observability and Maintenance" domain. We explored both theoretical concepts and practical hands-on skills:

- **Understanding Kubernetes API deprecation policy**: Why deprecations happen, the grace period rules, and the version skew policy that ensures compatibility across cluster upgrades
- **Hands-on experience with deprecated APIs**: Setting up K3s 1.24, creating resources with deprecated `policy/v1beta1` API, upgrading to 1.25, and experiencing API removal firsthand
- **Migration strategies and tools**: Migrating PodDisruptionBudget from v1beta1 to v1, reading CHANGELOGs and deprecation guides, and using tools like Pluto and kubent for automated detection
- **Best practices**: Testing upgrades in staging, monitoring deprecation warnings, scanning manifests in CI/CD pipelines, and staying current with stable API versions

Understanding and managing API deprecations is crucial for CKAD exam success and for maintaining production Kubernetes clusters. By staying current with API versions and following Kubernetes release notes, you ensure your applications remain compatible with cluster upgrades and benefit from the latest features and improvements.

## Final Cleanup

To wrap up, let's clean up everything we created for this exercise:

```bash
k delete pdb nginx-pdb
k delete pod nginx-pod
```
