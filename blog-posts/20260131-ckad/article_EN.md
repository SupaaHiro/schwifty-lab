---
layout: default
title: "CKAD Preparation — Monitoring Kubernetes Applications with Built-in CLI Tools"
date: 2026-01-31
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260131-ckad/article.webp"
summary: "Master Kubernetes application monitoring using built-in CLI tools. Learn kubectl get, describe, events and top to effectively observe and monitor your applications in real-time."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

This article continues our exploration of the **"Application Observability and Maintenance"** domain. We're covering the requirement:

> Use built-in CLI tools to monitor Kubernetes applications

To keep everything brief and focused, this article focuses specifically on monitoring tools. Container logs and debugging techniques will be covered in separate dedicated articles.

As usual, you can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

Also, a quick personal note: I've been quite busy lately with work deadlines and commitments, so publishing has slowed down.. quite a bit — but I’m planning to get back on track and share new labs very soon!

## Prerequisites

A running Kubernetes cluster (like Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods, Deployments, and Services.

Also, for this lab you'll need the metrics-server installed in your cluster.

If you're using a KillerCoda playground:

```bash
k apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

If you're using Minikube, enable the metrics-server addon:

```bash
minikube addons enable metrics-server
```

For other clusters, follow the [metrics-server installation guide](https://github.com/kubernetes-sigs/metrics-server#installation).

Once the metrics-server is installed, verify it's working:

```bash
k top no
```

If you get `error: Metrics API not available`. Inspect the logs of the metrics-server:

```bash
k logs -n kube-system deployment/metrics-server
```

If you have a TLS certificate validation error like this:

```bash
x509: cannot validate certificate for 172.30.1.2 because it doesn't contain any IP SANs" node="controlplane"
You may need to skip TLS verification depending on the environment:
```

You can patch the metrics-server deployment to add the `--kubelet-insecure-tls` argument:

```bash
k patch deployment metrics-server -n kube-system --type='json' -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

After a few moments, try `k top no` and `k top po` again. You should see resource usage metrics.

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20261231-ckad
```

## Understanding Kubernetes Built-in CLI Monitoring Tools

Kubernetes provides several built-in `kubectl` commands for monitoring and observability:

1. **kubectl get**: List and inspect resources with various output formats
2. **kubectl describe**: Get detailed information about resources and their events
3. **kubectl get events**: Monitor cluster-wide or namespace events
4. **kubectl top**: View resource utilization (CPU/Memory) for nodes and pods
5. **kubectl port-forward**: Access applications locally for monitoring and metrics

Let's explore each tool with hands-on examples that demonstrate real-world monitoring scenarios.

## Hands-On Challenge: Mastering Kubernetes CLI Monitoring Tools

### Step 1: Kubectl Get - Resource Status and Listing

The `kubectl get` command is your primary tool for quickly viewing the status of resources in your cluster. Let's explore its various capabilities.

Create a sample application with multiple resources:

Create the file `manifests/01-sample-app.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
    env: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
        env: production
        version: v1
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            limits:
              memory: 128Mi
              cpu: 100m
            requests:
              memory: 64Mi
              cpu: 50m
---
apiVersion: v1
kind: Service
metadata:
  name: web-app-svc
  labels:
    app: web-app
spec:
  selector:
    app: web-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-app
  labels:
    app: api-app
    env: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-app
  template:
    metadata:
      labels:
        app: api-app
        env: production
        version: v2
    spec:
      containers:
        - name: api
          image: httpd:2.4
          ports:
            - containerPort: 80
          resources:
            limits:
              memory: 128Mi
              cpu: 100m
            requests:
              memory: 64Mi
              cpu: 50m
---
apiVersion: v1
kind: Service
metadata:
  name: api-app-svc
  labels:
    app: api-app
spec:
  selector:
    app: api-app
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 80
  type: ClusterIP
```

Apply the manifest:

```bash
k apply -f manifests/01-sample-app.yaml
```

Wait for the deployments to be ready:

```bash
k rollout status deployment/web-app
k rollout status deployment/api-app
```

**Basic kubectl get commands:**

View all pods:

```bash
k get po
```

View pods with more details:

```bash
k get po -o wide
```

This shows additional columns like IP address, node, nominated node, and readiness gates.

**Filter by labels:**

```bash
k get po -l app=web-app
k get po -l env=production
k get po -l 'app in (web-app,api-app)'
```

**View multiple resource types:**

```bash
k get deployments,services,pods
```

**Watch resources in real-time:**

```bash
k get po --watch
```

Open another terminal and scale a deployment to see changes:

```bash
k scale deployment/web-app --replicas=5
```

Press Ctrl+C to stop watching.

**Custom output formats:**

JSON format (useful for automation):

```bash
k get po -o json | head -n 30
```

YAML format:

```bash
k get po <pod-name> -o yaml
```

Custom columns:

```bash
k get po -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,IP:.status.podIP
```

Extract specific fields with jsonpath:

```bash
k get po -o jsonpath='{.items[*].metadata.name}'
```

Get pod names and their container images:

```bash
k get po -o custom-columns=POD:.metadata.name,CONTAINERS:.spec.containers[*].name,IMAGES:.spec.containers[*].image
```

**Sort output:**

```bash
k get po --sort-by=.metadata.creationTimestamp
k get po --sort-by=.status.startTime
```

**Show labels:**

```bash
k get po --show-labels
k get po -L app,env,version
```

### Step 2: Kubectl Describe - Deep Resource Inspection

The `describe` command provides comprehensive information about resources, including configuration, status, and events.

**Describe a deployment:**

```bash
k describe deploy web-app
```

Look for these important sections:
- **Replicas**: Desired, current, updated, available
- **StrategyType**: Deployment strategy (RollingUpdate, Recreate)
- **Pod Template**: Container specifications
- **Conditions**: Deployment health status
- **Events**: Recent operations

**Describe a pod:**

```bash
POD_NAME=$(k get po -l app=web-app -o jsonpath='{.items[0].metadata.name}')
k describe po $POD_NAME
```

Key sections to examine:
- **Labels and Annotations**: Metadata attached to the pod
- **Status**: Current pod phase (Pending, Running, Succeeded, Failed)
- **IP**: Pod's assigned IP address
- **Controlled By**: Parent resource (ReplicaSet, DaemonSet, etc.)
- **Containers**: State, image, ports, resource limits/requests
- **Conditions**: PodScheduled, Initialized, ContainersReady, Ready
- **Events**: Chronological list of operations

**Describe a service:**

```bash
k describe svc web-app-svc
```

Important information:
- **Type**: ClusterIP, NodePort, LoadBalancer
- **IP**: Cluster IP address
- **Port**: Port mappings
- **Endpoints**: Pod IPs that the service routes to
- **Session Affinity**: Whether client sessions stick to the same pod

Let's create a scenario with issues to see how describe helps troubleshoot:

Create the file `manifests/02-problematic-app.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: problematic-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: problematic-app
  template:
    metadata:
      labels:
        app: problematic-app
    spec:
      containers:
        - name: app
          image: nginx:invalid-tag-9999
          ports:
            - containerPort: 80
          resources:
            limits:
              memory: 128Mi
              cpu: 100m
            requests:
              memory: 64Mi
              cpu: 50m
```

Apply it:

```bash
k apply -f manifests/02-problematic-app.yaml
```

Check the pods:

```bash
k get po -l app=problematic-app
```

You'll see `ImagePullBackOff` or `ErrImagePull` status. Describe a failing pod:

```bash
k describe pod -l app=problematic-app | grep -A 10 Events
```

The events clearly show "Failed to pull image" and the specific error, making troubleshooting straightforward.

Delete the problematic deployment:

```bash
k delete -f manifests/02-problematic-app.yaml
```

### Step 3: Kubectl Get Events - Cluster-Wide Event Monitoring

Events provide a timeline of what's happening in your cluster. They're invaluable for understanding the sequence of operations and identifying issues.

**View all events in the current namespace:**

```bash
k get events
```

**Sort events by timestamp (most recent first):**

```bash
k get events --sort-by='.lastTimestamp'
```

**Filter events by object type:**

```bash
k get events --field-selector involvedObject.kind=Pod
k get events --field-selector involvedObject.kind=Deployment
```

**Filter events by specific object:**

```bash
k get events --field-selector involvedObject.name=web-app
```

**Filter by event type:**

```bash
k get events --field-selector type=Warning
k get events --field-selector type=Normal
```

**Watch events in real-time:**

```bash
k get events --watch
```

In another terminal, perform some operations:

```bash
k scale deployment/web-app --replicas=1
k scale deployment/web-app --replicas=3
```

You'll see events like:
- ScalingReplicaSet
- SuccessfulCreate
- Started

**Combine filters:**

```bash
k get events --field-selector type=Warning,involvedObject.kind=Pod --sort-by='.lastTimestamp'
```

Let's create a scenario that generates various events:

Create the file `manifests/03-resource-constraints.yaml`:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: namespace-quota
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 2Gi
    limits.cpu: "4"
    limits.memory: 4Gi
    pods: "10"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-intensive
spec:
  replicas: 8
  selector:
    matchLabels:
      app: resource-intensive
  template:
    metadata:
      labels:
        app: resource-intensive
    spec:
      containers:
        - name: app
          image: nginx:1.27
          resources:
            requests:
              memory: 512Mi
              cpu: 500m
            limits:
              memory: 1Gi
              cpu: 1000m
```

Apply it:

```bash
k apply -f manifests/03-resource-constraints.yaml
```

Check the events:

```bash
k get events --sort-by='.lastTimestamp' | grep -i quota
```

You'll see events about exceeding resource quotas. Check how many pods were created:

```bash
k get po -l app=resource-intensive
```

Describe the ReplicaSet to see why some pods weren't created:

```bash
k describe rs -l app=resource-intensive
```

Delete the resource-intensive deployment and quota:

```bash
k delete -f manifests/03-resource-constraints.yaml
```

### Step 4: Kubectl Top - Resource Utilization Monitoring

The `top` command shows real-time CPU and memory usage. It requires metrics-server to be installed.

Create pods with varying resource usage patterns:

Create the file `manifests/04-resource-demo.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: idle-pod
  labels:
    app: resource-demo
    load: idle
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "while true; do sleep 30; done"]
      resources:
        limits:
          memory: 64Mi
          cpu: 50m
        requests:
          memory: 32Mi
          cpu: 25m
---
apiVersion: v1
kind: Pod
metadata:
  name: cpu-intensive
  labels:
    app: resource-demo
    load: high-cpu
spec:
  containers:
    - name: app
      image: busybox:1.36
      command:
        - sh
        - -c
        - |
          while true; do
            echo "Computing..." > /dev/null
          done
      resources:
        limits:
          memory: 64Mi
          cpu: 200m
        requests:
          memory: 32Mi
          cpu: 100m
---
apiVersion: v1
kind: Pod
metadata:
  name: memory-intensive
  labels:
    app: resource-demo
    load: high-memory
spec:
  containers:
    - name: app
      image: busybox:1.36
      command:
        - sh
        - -c
        - |
          dd if=/dev/zero of=/tmp/data bs=2M count=50
          while true; do sleep 10; done
      resources:
        limits:
          memory: 128Mi
          cpu: 50m
        requests:
          memory: 64Mi
          cpu: 25m
---
apiVersion: v1
kind: Pod
metadata:
  name: balanced-load
  labels:
    app: resource-demo
    load: balanced
spec:
  containers:
    - name: app
      image: nginx:1.27
      resources:
        limits:
          memory: 128Mi
          cpu: 100m
        requests:
          memory: 64Mi
          cpu: 50m
```

Apply the manifest:

```bash
k apply -f manifests/04-resource-demo.yaml
```

Wait for all pods to be running:

```bash
k get po -l app=resource-demo
```

**View node resource usage:**

```bash
k top no
```

This shows:
- CPU usage (cores and percentage)
- Memory usage (bytes and percentage)

**View pod resource usage:**

```bash
k get po
```

**Filter by labels:**

```bash
k get po -l app=resource-demo
```

**Sort by CPU usage:**

```bash
k get po --sort-by=cpu
```

**Sort by memory usage:**

```bash
k get po --sort-by=memory
```

**Show resource usage for all containers:**

```bash
k get po --containers
```

**Compare actual usage with requests and limits:**

Create a simple script to compare:

```bash
echo "=== Resource Usage vs Requests/Limits ==="

printf "%-30s %-12s %-12s %-15s %-15s %-15s %-15s\n" \
  "POD" "CPU_USED" "MEM_USED" "CPU_REQUEST" "MEM_REQUEST" "CPU_LIMIT" "MEM_LIMIT"

printf "%-30s %-12s %-12s %-15s %-15s %-15s %-15s\n" \
  "----------------------------" "----------" "----------" \
  "------------" "------------" "----------" "----------"

k get po -l app=resource-demo --no-headers | while read pod cpu mem; do

  req_cpu=$(k get po "$pod" -o jsonpath='{.spec.containers[0].resources.requests.cpu}')
  req_mem=$(k get po "$pod" -o jsonpath='{.spec.containers[0].resources.requests.memory}')
  lim_cpu=$(k get po "$pod" -o jsonpath='{.spec.containers[0].resources.limits.cpu}')
  lim_mem=$(k get po "$pod" -o jsonpath='{.spec.containers[0].resources.limits.memory}')

  printf "%-30s %-12s %-12s %-15s %-15s %-15s %-15s\n" \
    "$pod" "$cpu" "$mem" "$req_cpu" "$req_mem" "$lim_cpu" "$lim_mem"

done
```

It will output something like:

```bash
=== Resource Usage vs Requests/Limits ===
POD                            CPU_USED     MEM_USED     CPU_REQUEST     MEM_REQUEST     CPU_LIMIT       MEM_LIMIT
----------------------------   ----------   ----------   ------------    ------------    ----------      ----------
balanced-load                  1/1          Running   0     6m51s 50m             64Mi            100m            128Mi
cpu-intensive                  1/1          Running   0     6m51s 100m            32Mi            200m            64Mi
idle-pod                       1/1          Running   0     6m51s 25m             32Mi            50m             64Mi
memory-intensive               1/1          Running   0     3m17s 25m             64Mi            50m             128Mi
```

This helps identify potential issues, like pods approaching their limits (OOM or throttling) or being over/under-provisioned.

**Monitor over time:**

```bash
watch -n 2 'kubectl get po -l app=resource-demo'
```

Press Ctrl+C to stop watching.

## Wrapping Up: What We've Covered

In this article, we explored Kubernetes built-in CLI monitoring tools as part of the "Application Observability and Maintenance" domain for CKAD preparation.

We focused specifically on monitoring capabilities, covering both theoretical concepts and extensive practical implementations:

- **kubectl get**: Resource listing and status checking with custom output formats, label filtering, and real-time watching
- **kubectl describe**: Deep resource inspection including configuration details, status conditions, and event history
- **kubectl get events**: Cluster-wide event monitoring with filtering by type, object, and timestamp for understanding operational sequences
- **kubectl top**: Real-time resource utilization monitoring for nodes and pods, essential for capacity planning and performance analysis

In the next article, we will dive into container logs analysis and debugging techniques using `kubectl logs`, `kubectl exec`, and `kubectl debug`.

## Final Cleanup

To clean up all resources created in this lab:

```bash
k delete -f manifests/
```

If you enabled metrics-server on Minikube specifically for this lab, you can disable it:

```bash
minikube addons disable metrics-server
```
