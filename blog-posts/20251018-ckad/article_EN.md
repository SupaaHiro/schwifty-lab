---
layout: default
title: "CKAD Preparation, Testing Kubernetes NetworkPolicy"
date: 2025-10-18
categories: [ckda, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251018-ckad/article.webp"
summary: "Hands-on exercise showing how to test Kubernetes Ingress NetworkPolicy using a Redis Pod and a client Pod, with manifests and a Python connectivity test."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

In this post, we’ll cover the requirements within the "Services and Networking” domain:

> Demonstrate basic understanding of NetworkPolicies

Here we'll demonstrate how to restrict ingress traffic using a Kubernetes NetworkPolicy.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

⚠️ Important:
Verify that your Kubernetes cluster is configured with a CNI plugin that implements NetworkPolicy. Without such support, any defined policies will be silently ignored. I ran some local tests with Kubernetes on Docker Desktop and with minikube, but neither supports them natively. In the end I opted for a temporary environment on [KillerCoda Playgrounds](https://killercoda.com/playgrounds)

## Getting the Resources

All manifests and examples mentioned in this post are available in the following repository:

```yaml
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20251018-ckad
```

## Creating the Redis Pod

To understand how Network Policies work, we need to create a couple of pods.
Here’s the first one:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis
  labels:
    app: redis
spec:
  containers:
    - name: redis
      image: redis:alpine
      ports:
        - containerPort: 6379
```

This pod creates a redis instance listening on port 6379.

Apply the manifest:

```bash
k create -f manifests/01-redis.yaml
```

Verify the Pod reaches the Running state:

```bash
k get pod -o=wide -l=app=redis --watch
```

## Creating the Service

To make Redis accessible to other Pods, create a ClusterIP Service.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  labels:
    app: redis
spec:
  type: ClusterIP
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

Apply the manifest:

```bash
k create -f manifests/02-redis-svc.yaml
```

Once applied, check that the endpoint is correctly populated with:

```bash
k get svc -l=app=redis -o=wide
k describe svc redis
```

Example output:

```text
Name:                     redis
Namespace:                default
Labels:                   app=redis
Annotations:              <none>
Selector:                 app=redis
Type:                     ClusterIP
IP Family Policy:         SingleStack
IP Families:              IPv4
IP:                       10.105.198.164
IPs:                      10.105.198.164
Port:                     <unset>  6379/TCP
TargetPort:               6379/TCP
Endpoints:                10.1.0.174:6379
Session Affinity:         None
Internal Traffic Policy:  Cluster
Events:                   <none>
```

## Connectivity test script

To verify connectivity to Redis we'll use a simple Python script.

The script tries to connect to the Redis service and prints a success or error message, with a configurable timeout (default 10 seconds).

```python
import os
import redis

host = os.getenv("REDIS_HOST", "redis")
port = int(os.getenv("REDIS_PORT", "6379"))
timeout = int(os.getenv("REDIS_TIMEOUT", "10"))

try:
    client = redis.Redis(
        host=host,
        port=port,
        socket_connect_timeout=timeout,
        socket_timeout=timeout
    )
    client.ping()
    print(f"✅ Connected to Redis at {host}:{port} (timeout={timeout}s)")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
```

To avoid creating a dedicated Docker image, we will mount the script as a volume via a ConfigMap:

```bash
k create cm test-redis-ping --from-file=test-redis-ping.py=./src/test-redis-ping.py
```

## Creating the Client Pod

Define a Pod called redis-client, based on python:3.12-alpine.
The container will install the redis library on the fly and then run the script mounted from the ConfigMap.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis-client
  labels:
    app: redis-client
spec:
  containers:
    - name: python-tester
      image: python:3.12-alpine
      command:
      - sh
      - -c
      - >
        pip install --upgrade pip --root-user-action ignore > /dev/null &&
        pip install redis --root-user-action ignore > /dev/null &&
        python /scripts/test-redis-ping.py
      env:
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
      volumeMounts:
        - name: script-volume
          mountPath: /scripts
  volumes:
    - name: script-volume
      configMap:
        name: test-redis-ping
  restartPolicy: Never
```

Apply the manifest:

```bash
k create -f manifests/03-redis-client.yaml
```

Wait for the Pod to be Running and check the logs:

```bash
k get pod -o=wide -l=app=redis-client --watch
k logs redis-client
```

If everything works, we should see:

```text
✅ Connected to Redis at redis:6379
```

## Defining the NetworkPolicy

Create two NetworkPolicy resources:

- default-deny-ingress — blocks all incoming traffic by default.
- redis-access — allows access to the Redis Pod only from Pods that have the label access: redis.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: redis-access
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              access: redis
      ports:
        - protocol: TCP
          port: 6379
```

Apply the manifest:

```bash
k create -f manifests/04-netpol.yaml
```

After applying, the redis-access policy will act like a "fence" around Pods with label app=redis, allowing connections only from Pods labeled with access=redis.

## Testing the blocked connection

Currently the redis-client Pod does not have the label access: redis, so the connection should fail.

Remove and recreate the Pod, then check the logs:

```bash
k replace -f manifests/03-redis-client.yaml --force
k logs redis-client
```

The expected result is a timeout error:

```text
❌ Failed to connect to Redis: Timeout connecting to server
```

Note: the error may take a few seconds to appear in the logs.

## Enable access via label

Add the missing label "access: redis" to the redis-client Pod manifest and recreate it:

```bash
yq e '.metadata.labels.access = "redis"' -i manifests/03-redis-client.yaml
k replace -f manifests/03-redis-client.yaml --force
```

After the deploy, the connection should work again:

```text
✅ Connected to Redis at redis:6379
```

## 🏁 Wrapping Up: What We’ve Covered

In this article we reviewed a practical workflow to test Kubernetes Ingress NetworkPolicy using a Redis server and a client Pod. Key takeaways:

- Ensure your cluster uses a CNI that implements NetworkPolicy; without CNI support, NetworkPolicy objects are ignored.
- Use a "default-deny" Ingress policy to block all incoming traffic by default, then add explicit allow rules to scope access (for example, by pod labels).
- NetworkPolicies are applied to Pods (via podSelector) — label your Pods intentionally to control access and to make policies predictable.
- Test connectivity with a lightweight client Pod and a configurable script (mounted via ConfigMap); check Pod logs for connection timeouts or success messages to validate policy effects.

## Final cleanup

When you're done with the experiments, remove all created resources (Pods, Service and NetworkPolicy) to clean up the environment:

```bash
k delete svc redis
k delete netpol default-deny-ingress redis-access
k delete po redis redis-client
```
