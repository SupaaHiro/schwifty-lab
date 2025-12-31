---
layout: default
title: "CKA Preparation — Resource Allocation Based on Node Availability"
date: 2025-12-29
categories: [cka, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251229-cka/article.webp"
summary: "Learn how to properly calculate and allocate CPU and memory resources to Pods in Kubernetes based on node availability — an essential skill for the CKA certification to ensure cluster stability and optimal performance."
---

## Introduction

It's been more than a month since I published an article on the blog! Mainly due to work deadlines, but also because I was preparing to renew my [*CKA*](https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/) certification.

In this article, I would like to share with you an exercise that I came across during my exam preparation, concerning resource allocation based on node availability. This is an exercise that seems easy at first glance, but it hides some traps along the way.

This article is not part of the CKAD series: If you want to start preparing for the CKAD certification, you can begin here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A working Kubernetes cluster (Minikube, Docker Desktop, or https://killercoda.com/playgrounds/course/kubernetes-playgrounds) with *a single worker node* and a basic understanding of Pods and YAML manifests.

Optionally, a metrics server (for example `metrics-server`) can be installed in the cluster to monitor resource usage. You can install it by running the following command:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

In case of TLS issues, modify the `metrics-server` deployment to add the `--kubelet-insecure-tls` argument to the container.

```bash
kubectl -n kube-system edit deployment metrics-server
# In spec.template.spec.containers[].args add:
# - --kubelet-insecure-tls
```

## Getting the Resources

Clone the CKA-PREP-2025-v2 repository and start the exercise like this:

```bash
git clone https://github.com/SupaaHiro/CKA-PREP-2025-v2
cd CKA-PREP-2025-v2
bash ./scripts/run-question.sh 'Question-4 Resource-Allocation'
```

Note: This repo is a fork of the [vj2201/CKA-PREP-2025-v2](https://github.com/vj2201/CKA-PREP-2025-v2) repository with some minor modifications, mainly to keep notes for myself and do experiments.

## Practical Exercise: Resource Allocation Based on Node Availability

After launching the exercise, you should see a prompt similar to this:

```bash
==> Running lab setup for Question-4 Resource-Allocation
deployment.apps/wordpress created

==> Question
# Question
# You are managing a WordPress application running in a Kubernetes cluster
# Your task is to adjust the Pod resource requests and limits to ensure stable operation

# Tasks
# 1. Scale down the wordpress deployment to 0 replicas
# 2. Edit the deployment and divide the node resource evenly across all 3 pods
# 3. Assign fair and equal CPU and memory to each Pod
# 4. Add sufficient overhead to avoid node instability
# Ensure both the init containers and the main containers use exactly the same resource requests and limits
# After making the changes scale the deployment back to 3 replicas

#Video link - https://youtu.be/ZqGDdETii8c

Hints: see Question-4 Resource-Allocation/SolutionNotes.bash
```

The first thing we're asked to do is scale the `wordpress` deployment down to 0 replicas. Let's do this:

```bash
kubectl scale deploy wordpress --replicas 0
```

Before we can resize the deployment, we need to calculate how many resources we can assign to each Pod. To do this, let's check how many resources are available on the node:

```bash
kubectl describe node node01 | grep "Allocatable:" -A5
```

We should see something similar to this:

```bash
Allocatable:
  cpu:                1
  memory:             1846540Ki
  pods:               110
```

For simplicity, let's assume that our cluster has a single worker node available, in this case with 1 CPU and approximately 1.8 GiB of allocatable memory.

These values already take into account the resources used by the system and by kubelet. However, from these values we need to subtract the resources already in use by existing Pods.

```bash
kubectl describe node node01 | grep "Allocated resources:" -A5
```

We should see something similar to this:

```bash
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests     Limits
  --------           --------     ------
  cpu                225m (22%)   0 (0%)
  memory             300Mi (16%)  340Mi (18%)
```

Now we need to do some calculations. We can use up to 1 CPU - 225m = 775m CPU and 1.8 GiB - 300 MiB = approximately 1.5 GiB of memory for our Pods.

We have 3 replicas, so let's divide these resources by 3:
- CPU per Pod: 775m / 3 ≈ 258m
- Memory per Pod: 1.5 GiB / 3 = 512 Mi

To perform the calculations from the terminal, we can use `bc` like this:

```bash
1000 * (1 - 0.225) / 3 -> 258
1846540/1024 *  (1 - 0.16) / 3 -> 504
```

> Note: To exit `bc`, type `quit`.

So, the maximum limits we can assign to each Pod are:
- CPU per Pod: 258m
- Memory per Pod: 504 Mi

Let's round down the limit values:
- CPU Limit per Pod: 250m
- Memory Limit per Pod: 500 Mi

Now that we know the limits, we need to leave some margin to avoid node instability. Let's assign 95% of the limits as requests:

- CPU Request per Pod: 237m (95% of the limit)
- Memory Request per Pod: 475 Mi (95% of the limit)

Now we can modify the `wordpress` deployment to set the resource requests and limits for the main containers and the init containers. Let's open the deployment manifest:

```bash
kubectl edit deploy wordpress
```

Let's add the following `resources` sections under the main containers and the init containers:

```yaml
    spec:
      containers:
      - image: wordpress:6.2-apache
        name: wordpress
        resources:          # edit this section
          limits:
            cpu: 250m
            memory: 500Mi
          requests:
            cpu: 237m
            memory: 475Mi
```

Similarly, let's assign the same resources to the init containers as well.

After saving the changes, let's scale the `wordpress` deployment back to 3 replicas:

```bash
kubectl scale deploy wordpress --replicas 3
```

After a while, the pods should be running.

Let's verify the status of the Pods:

```bash
kubectl get pods -l app=wordpress
```

We should see something similar to this:

```bash
NAME                         READY   STATUS    RESTARTS   AGE
wordpress-5d7f9c6b7b-abcde   1/1     Running   0          30s
wordpress-5d7f9c6b7b-fghij   1/1     Running   0          30s
wordpress-5d7f9c6b7b-klmno   1/1     Running   0          30s
```

Let's double-check the allocated resources on the node to make sure everything is correct:

```bash
kubectl describe node node01 | grep "Allocated resources:" -A5
```

We should see something similar to this:

```bash
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests      Limits
  --------           --------      ------
  cpu                936m (93%)    750m (75%)
  memory             1725Mi (95%)  1840Mi (102%)
```

Perhaps we're slightly overcommitted with the memory limit, but that's okay—the important thing is that the requests are within the node's limits.

There we go! We've completed the resource allocation exercise based on node availability.

## Wrapping Up: What We've Covered

In this article, we've seen how to calculate and allocate resources to Pods in a Kubernetes cluster based on node availability. We've learned to:
- Verify the allocatable and already allocated resources on the node.
- Calculate the available resources for the Pods.
- Modify a deployment to set resource requests and limits.

I hope this article has been helpful in your preparation for the CKA certification. Good luck with your studies, and see you next time!
