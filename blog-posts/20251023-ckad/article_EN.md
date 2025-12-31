---
layout: default
title: "CKAD Preparation — Utilize Persistent and Ephemeral Volumes"
date: 2025-10-23
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251023-ckad/article.webp"
summary: "Learn how to persist and share data in Kubernetes using persistent and ephemeral volumes — from emptyDir to PersistentVolumeClaims."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

In this post, we’ll cover the requirements within the “Application Design and Build” domain:

> Utilize persistent and ephemeral volumes

Here we’ll cover how to **utilize persistent and ephemeral volumes** — a fundamental CKAD topic for managing stateful workloads and inter-container data sharing.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (like, Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article’s folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20251023-ckad
```

## Understanding Volumes in Kubernetes

Containers are ephemeral by design: once restarted or rescheduled, their filesystem state is lost. We can overcome this limitation in Kubernetes by using volumes — directories that provide persistent storage accessible to containers within a Pod.

There are two main volume types to know for the CKAD exam:

- Ephemeral volumes — created and destroyed with the Pod. Examples: emptyDir, configMap, secret, downwardAPI, and ephemeral.
- Persistent volumes — survive Pod restarts, backed by cluster-level resources such as PersistentVolume (PV) and PersistentVolumeClaim (PVC).

> Note: Downward API volumes expose Pod metadata and resource information (such as labels or CPU limits) to containers as files. We’ll explore this in a dedicated article.


### Ephemeral Volumes (emptyDir)

An emptyDir volume is created when a Pod is scheduled on a node and deleted when the Pod is removed. It’s ideal for temporary data, caching, or communication between containers.

### Persistent Volumes (PVC)

Persistent volumes are used when data must outlive a Pod’s lifecycle — for example, application databases or user-generated content.
A Pod mounts a PersistentVolumeClaim (PVC), which is a request for storage resources in the cluster. The PVC then binds to a PersistentVolume (PV) provisioned by the cluster or dynamically by a storage class.

## Hands-On Challenge

In this exercise you’ll create:

- A Pod with ephemeral storage shared between two containers.
- A Deployment using a PersistentVolumeClaim for long-lived storage.

### 🧩 Step 1 — Ephemeral Volume with emptyDir

Create a Pod with:

- A busybox writer container that writes a timestamp every 3 seconds to a shared file.
- A busybox reader container that continuously prints that same file.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ephemeral-volume-demo
spec:
  containers:
  - name: writer
    image: busybox:1.37
    command: ["/bin/sh", "-c", "while true; do date >> /data/time.log; sleep 3; done"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  - name: reader
    image: busybox:1.37
    command: ["/bin/sh", "-c", "tail -f /data/time.log"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  volumes:
  - name: shared-data
    emptyDir: {}
  restartPolicy: Always
```

Save it as manifests/01-ephemeral-pod.yaml and apply:

```bash
k apply -f manifests/01-ephemeral-pod.yaml
k get pod ephemeral-volume-demo --watch
```

Once running, check logs from the reader container:

```bash
k logs -f ephemeral-volume-demo -c reader
```

You should see timestamps being continuously appended — proof that both containers share the same emptyDir.

### 💾 Step 2 — Persistent Volume Claim (PVC)

Now let’s create a PersistentVolumeClaim and mount it into a Deployment.

First, create a PVC manifest (manifests/02-pvc.yaml):

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 100Mi
```

Apply it:

```bash
k apply -f manifests/02-pvc.yaml
k get pvc demo-pvc
```

Then create a Deployment that mounts this PVC into an Nginx container.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-pvc
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-pvc
  template:
    metadata:
      labels:
        app: nginx-pvc
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        volumeMounts:
        - name: persistent-storage
          mountPath: /usr/share/nginx/html
      volumes:
      - name: persistent-storage
        persistentVolumeClaim:
          claimName: demo-pvc
```

Apply it:

```bash
k apply -f manifests/03-nginx-pvc.yaml
```

Create a test file inside the Pod and verify persistence:

```bash
k exec -it deploy/nginx-pvc -- /bin/sh
echo "Hello from PVC" > /usr/share/nginx/html/index.html
exit
```

Now delete the Pod and let the Deployment recreate it:

```bash
k delete pod -l app=nginx-pvc
k exec -it deploy/nginx-pvc -- cat /usr/share/nginx/html/index.html
```

✅ You’ll see the same “Hello from PVC” content — confirming that the data persisted even after Pod recreation.

## Wrapping Up: What We’ve Covered

In this exercise, we practiced how to use both ephemeral and persistent storage in Kubernetes.
We built:

- A multi-container Pod that shared temporary data using an emptyDir volume.
- A Deployment using a PersistentVolumeClaim to retain data across Pod restarts.

Understanding when to use ephemeral vs persistent volumes is essential for designing robust, CKAD-ready applications.
Ephemeral volumes are perfect for transient data (logs, caches, scratch space), while persistent volumes ensure state durability across restarts and rescheduling events.

📝 In later modules, we’ll explore StatefulSets and dynamic provisioning for stateful workloads like databases.

## Final cleanup

When done, remove all resources:

```bash
k delete -f manifests/
```
