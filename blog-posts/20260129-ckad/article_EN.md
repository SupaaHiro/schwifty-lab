---
layout: default
title: "CKAD Preparation — Implementing Probes and Health Checks"
date: 2026-01-29
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260129-ckad/article.webp"
summary: "Master Kubernetes probes and health checks with hands-on examples. Learn liveness, readiness, and startup probes to ensure application reliability and resilience in production environments."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

This article continues our exploration of the **"Application Observability and Maintenance"** domain. We're covering the requirement:

> Implement probes and health checks

Probes and health checks are fundamental to building resilient applications in Kubernetes. They allow the cluster to understand when your application is ready to serve traffic, when it's still alive, and when it needs to be restarted. Mastering probes is essential for the CKAD exam and for building production-grade applications.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (like, Minikube, Docker Desktop, or use one of the [KillerCoda Kubernetes Playgrounds](https://killercoda.com/playgrounds/course/kubernetes-playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260129-ckad
```

## Understanding Kubernetes Probes

Kubernetes provides three types of probes to monitor and manage the health of your applications:

1. **Liveness Probe**: Determines if a container is running properly. If the liveness probe fails, Kubernetes kills the container and restarts it according to the restart policy.

2. **Readiness Probe**: Determines if a container is ready to accept traffic. If the readiness probe fails, the Pod's IP address is removed from the Service endpoints, preventing traffic from reaching it.

3. **Startup Probe**: Determines if the application inside a container has started. While the startup probe is running, liveness and readiness probes are disabled. This is useful for applications that require long startup times.

### Probe Mechanisms

Kubernetes supports several mechanisms for implementing probes:

- **HTTP GET**: Performs an HTTP GET request against a specified path and port. Success is indicated by a response code between 200 and 399.
- **TCP Socket**: Attempts to open a TCP connection to a specified port. Success is indicated by the ability to establish the connection.
- **Exec**: Executes a command inside the container. Success is indicated by an exit code of 0.
- **gRPC**: Performs a gRPC health check (available since Kubernetes 1.24).

### Probe Configuration Parameters

All probes support the following configuration parameters:

- `initialDelaySeconds`: Number of seconds after the container starts before the probe is initiated (default: 0)
- `periodSeconds`: How often (in seconds) to perform the probe (default: 10)
- `timeoutSeconds`: Number of seconds after which the probe times out (default: 1)
- `successThreshold`: Minimum consecutive successes for the probe to be considered successful after having failed (default: 1)
- `failureThreshold`: Number of consecutive failures before the probe is considered failed (default: 3)

## Hands-On Challenge: Implementing Different Types of Probes

Let's explore each probe type with practical examples that demonstrate common scenarios and best practices.

### Step 1: Liveness Probe - Detecting and Recovering from Deadlocks

A liveness probe ensures that your application is running correctly. Let's create a web application that can simulate a deadlock condition, then use a liveness probe to detect and recover from it.

Create the file `manifests/01-liveness-http.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: liveness-http
  labels:
    app: liveness-demo
spec:
  containers:
  - name: web-app
    image: registry.k8s.io/liveness
    ports:
    - containerPort: 8080
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
        httpHeaders:
        - name: Custom-Header
          value: Awesome
      initialDelaySeconds: 3
      periodSeconds: 5
      timeoutSeconds: 1
      failureThreshold: 3
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
k apply -f manifests/01-liveness-http.yaml
```

Watch the Pod status:

```bash
k get pod liveness-http --watch
```

The `registry.k8s.io/liveness` image is designed to fail its liveness probe after 10 seconds. Initially, the HTTP server returns a 200 status code for the first 10 seconds, then it starts returning 500 errors. After 3 consecutive failures (as specified by `failureThreshold`), Kubernetes will restart the container.

You can see the restart count increasing:

```bash
k describe pod liveness-http | grep -A 5 "Containers:"
```

Look for the `Restart Count` field and the events showing the container being killed and restarted.

Let's understand what's happening:
1. Container starts and the liveness probe waits 3 seconds (`initialDelaySeconds`)
2. Every 5 seconds (`periodSeconds`), Kubernetes checks the `/healthz` endpoint
3. After 10 seconds, the application starts failing the health check
4. After 3 consecutive failures (`failureThreshold` × `periodSeconds` = 15 seconds), the container is killed
5. Kubernetes restarts the container, and the cycle repeats

### Step 2: Readiness Probe - Controlling Traffic Flow

A readiness probe determines when a container is ready to accept traffic. This is crucial during application startup, configuration reloading, or when the application is temporarily unable to serve requests.

Let's create an example with both liveness and readiness probes:

Create the file `manifests/02-readiness-probe.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: readiness-demo
  labels:
    app: readiness-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    ports:
    - containerPort: 80
    volumeMounts:
    - name: html
      mountPath: /usr/share/nginx/html
    readinessProbe:
      httpGet:
        path: /ready
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 3
      successThreshold: 1
      failureThreshold: 3
    livenessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 10
      periodSeconds: 5
    resources:
      limits:
        memory: 128Mi
        cpu: 100m
      requests:
        memory: 64Mi
        cpu: 50m
  volumes:
  - name: html
    emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: readiness-svc
spec:
  selector:
    app: readiness-demo
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
```

Apply the manifest:

```bash
k apply -f manifests/02-readiness-probe.yaml
```

Check the Pod status:

```bash
k get pod readiness-demo
```

You'll notice the Pod shows `0/1` in the READY column. This is because the readiness probe is failing (the `/ready` endpoint doesn't exist yet).

Check the Service endpoints:

```bash
k get endpoints readiness-svc
```

The endpoints will be empty because the Pod is not ready. Even though the container is running, Kubernetes won't send traffic to it.

Now let's make the Pod ready by creating the `/ready` file:

```bash
k exec readiness-demo -- sh -c 'echo "ready" > /usr/share/nginx/html/ready'
```

Wait a few seconds and check the Pod again:

```bash
k get pod readiness-demo
```

Now it should show `1/1` READY. Check the endpoints again:

```bash
k get endpoints readiness-svc
```

You should now see the Pod's IP address listed in the endpoints.

Let's simulate the application becoming unready:

```bash
k exec readiness-demo -- rm /usr/share/nginx/html/ready
```

After a few seconds, check the Pod and endpoints:

```bash
k get pod readiness-demo
k get endpoints readiness-svc
```

The Pod will show `0/1` READY again, and the endpoints will be empty. However, notice that the container is NOT restarted - it's still running. This is the key difference between readiness and liveness probes:

- **Liveness probe failure** → Container is killed and restarted
- **Readiness probe failure** → Traffic is stopped, but container keeps running

### Step 3: Startup Probe - Handling Slow-Starting Applications

Some applications require significant time to start up - they might need to load large datasets, establish database connections, or perform complex initialization. A startup probe allows you to give these applications more time to start without interfering with liveness probe settings.

Create the file `manifests/03-startup-probe.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: startup-demo
  labels:
    app: startup-demo
spec:
  containers:
  - name: slow-starter
    image: nginx:1.27
    ports:
    - containerPort: 80
    startupProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 0
      periodSeconds: 5
      failureThreshold: 30  # 30 * 5 = 150 seconds max startup time
    livenessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 5
      failureThreshold: 3  # Only allows 15 seconds of downtime
    readinessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 3
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
k apply -f manifests/03-startup-probe.yaml
```

Watch the Pod:

```bash
k get pod startup-demo --watch
```

In this configuration:
1. The startup probe runs first, checking every 5 seconds for up to 150 seconds (30 × 5)
2. During startup probe execution, liveness and readiness probes are **disabled**
3. Once the startup probe succeeds, it never runs again
4. Liveness and readiness probes then take over

This pattern is essential for legacy applications or microservices with long initialization times. Without a startup probe, you'd need to set a very high `initialDelaySeconds` on the liveness probe, which would delay failure detection during normal operation.

### Step 4: TCP Socket Probe - Checking Port Availability

Not all applications expose HTTP endpoints. For applications that communicate over raw TCP (like databases or message queues), TCP socket probes are appropriate.

Create the file `manifests/04-tcp-probe.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: tcp-probe-demo
  labels:
    app: tcp-demo
spec:
  containers:
  - name: redis
    image: redis:7-alpine
    ports:
    - containerPort: 6379
    livenessProbe:
      tcpSocket:
        port: 6379
      initialDelaySeconds: 15
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      tcpSocket:
        port: 6379
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
    resources:
      limits:
        memory: 256Mi
        cpu: 200m
      requests:
        memory: 128Mi
        cpu: 100m
```

Apply the manifest:

```bash
k apply -f manifests/04-tcp-probe.yaml
```

Verify the Pod is ready:

```bash
k get pod tcp-probe-demo
```

The TCP socket probe simply attempts to establish a connection to the specified port. If the connection succeeds, the probe succeeds.

You can verify Redis is working:

```bash
k exec tcp-probe-demo -- redis-cli ping
```

This should return `PONG`.

### Step 5: Exec Probe - Custom Health Check Commands

For maximum flexibility, exec probes run custom commands inside the container. This is useful when you need complex health check logic that can't be expressed with HTTP or TCP checks.

Create the file `manifests/05-exec-probe.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: exec-probe-demo
  labels:
    app: exec-demo
spec:
  containers:
  - name: postgres
    image: postgres:16-alpine
    env:
    - name: POSTGRES_PASSWORD
      value: mysecretpassword
    - name: POSTGRES_USER
      value: testuser
    - name: POSTGRES_DB
      value: testdb
    ports:
    - containerPort: 5432
    livenessProbe:
      exec:
        command:
        - /bin/sh
        - -c
        - pg_isready -U testuser -d testdb
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      exec:
        command:
        - /bin/sh
        - -c
        - pg_isready -U testuser -d testdb
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
    resources:
      limits:
        memory: 512Mi
        cpu: 500m
      requests:
        memory: 256Mi
        cpu: 250m
```

Apply the manifest:

```bash
k apply -f manifests/05-exec-probe.yaml
```

Wait for the Pod to be ready:

```bash
k get pod exec-probe-demo --watch
```

The `pg_isready` command checks if PostgreSQL is ready to accept connections. The command exits with status 0 if the database is ready, making it perfect for an exec probe.

You can verify PostgreSQL is working:

```bash
k exec exec-probe-demo -- psql -U testuser -d testdb -c "SELECT version();"
```

### Step 6: Understanding Probe Timing and Failure Scenarios

Let's create a comprehensive example that demonstrates the interaction between different probe settings:

Create the file `manifests/06-probe-timing.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: probe-timing
  labels:
    app: probe-timing
spec:
  containers:
  - name: app
    image: nginx:1.27
    ports:
    - containerPort: 80
    startupProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 0
      periodSeconds: 2
      failureThreshold: 15  # 30 seconds max startup time
    livenessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 0  # No delay needed because startup probe handles it
      periodSeconds: 10
      timeoutSeconds: 1
      failureThreshold: 3  # 30 seconds before restart
    readinessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 0
      periodSeconds: 5
      timeoutSeconds: 1
      successThreshold: 1
      failureThreshold: 2  # 10 seconds before marked unready
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
k apply -f manifests/06-probe-timing.yaml
```

Let's trace through what happens:

**Timeline of probe execution:**

```
Time  | Startup Probe | Liveness Probe | Readiness Probe | Status
------|---------------|----------------|-----------------|------------------
0s    | Check #1      | DISABLED       | DISABLED        | Container starting
2s    | Check #2      | DISABLED       | DISABLED        | Startup running
4s    | ✓ SUCCESS     | -              | -               | Startup complete
4s    | DISABLED      | Check #1       | Check #1        | Probes active
9s    | DISABLED      | -              | Check #2        | -
14s   | DISABLED      | Check #2       | Check #3        | -
19s   | DISABLED      | -              | Check #4        | Pod ready
24s   | DISABLED      | Check #3       | Check #5        | Normal operation
```

Key points:
- Startup probe runs every 2 seconds until success (max 30 seconds)
- Once startup succeeds, liveness and readiness probes begin
- Liveness probe runs every 10 seconds
- Readiness probe runs every 5 seconds
- If liveness fails 3 times (30 seconds), container restarts
- If readiness fails 2 times (10 seconds), traffic is stopped

### Step 7: Best Practices and Common Pitfalls

Let's examine some common mistakes and best practices:

**❌ Common Mistake #1: Same endpoint for liveness and readiness**

```yaml
livenessProbe:
  httpGet:
    path: /health  # Same endpoint
readinessProbe:
  httpGet:
    path: /health  # Same endpoint
```

**Why it's bad**: If `/health` depends on external services (database, cache), a temporary external failure will cause the liveness probe to fail and restart the container unnecessarily.

**✓ Better approach**:

```yaml
livenessProbe:
  httpGet:
    path: /alive  # Only checks if process is alive
readinessProbe:
  httpGet:
    path: /ready  # Checks if app can serve traffic (including dependencies)
```

**❌ Common Mistake #2: Aggressive timing on slow applications**

```yaml
livenessProbe:
  periodSeconds: 1
  failureThreshold: 2  # Only 2 seconds before restart!
```

**Why it's bad**: Temporary network hiccups or CPU spikes can trigger unnecessary restarts.

**✓ Better approach**:

```yaml
livenessProbe:
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5  # 30+ seconds before restart
```

**❌ Common Mistake #3: No startup probe for slow applications**

```yaml
livenessProbe:
  initialDelaySeconds: 120  # Overly conservative
  periodSeconds: 10
```

**Why it's bad**: During normal operation, failures won't be detected for up to 120 seconds.

**✓ Better approach**:

```yaml
startupProbe:
  periodSeconds: 5
  failureThreshold: 30  # 150 seconds for startup
livenessProbe:
  periodSeconds: 10
  failureThreshold: 3  # Quick detection during normal operation
```

### Step 8: Debugging Probe Failures

When probes fail, Kubernetes provides events and logs to help diagnose the issue.

Let's create a Pod with a failing probe:

Create the file `manifests/07-failing-probe.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: failing-probe
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    readinessProbe:
      httpGet:
        path: /nonexistent
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 5
    resources:
      limits:
        memory: 128Mi
        cpu: 100m
```

Apply it:

```bash
k apply -f manifests/07-failing-probe.yaml
```

The Pod will never become ready. Check the events:

```bash
k describe pod failing-probe
```

Look for events like:

```
Warning  Unhealthy  readiness probe failed: HTTP probe failed with statuscode: 404
```

You can also check the probe status:

```bash
k get pod failing-probe -o jsonpath='{.status.conditions[?(@.type=="Ready")]}' | jq
```

To debug further, check if the endpoint is accessible:

```bash
k exec failing-probe -- curl -I localhost/nonexistent
```

This shows the 404 error that's causing the probe to fail.

## Wrapping Up: What We've Covered

In this article, we explored Kubernetes probes and health checks as part of the "Application Observability and Maintenance" domain for CKAD preparation. We covered both theoretical concepts and practical implementations:

- **Three types of probes**: Liveness (detect deadlocks), Readiness (control traffic), and Startup (handle slow starts)
- **Four probe mechanisms**: HTTP GET, TCP Socket, Exec commands, and gRPC health checks
- **Probe configuration parameters**: initialDelaySeconds, periodSeconds, timeoutSeconds, successThreshold, and failureThreshold
- **Hands-on implementations**: HTTP probes, TCP socket probes for Redis, exec probes for PostgreSQL, and timing configurations
- **Best practices**: Separate liveness and readiness endpoints, appropriate timing for application behavior, using startup probes for slow applications
- **Common pitfalls**: Same endpoint for different probes, aggressive timing, missing startup probes
- **Debugging techniques**: Using describe, events, and logs to diagnose probe failures

Mastering probes is essential for building resilient Kubernetes applications. They enable self-healing, proper traffic management, and graceful handling of application lifecycle events. These skills are not only crucial for the CKAD exam but also for designing production-grade applications that can withstand failures and maintain high availability.

## Final Cleanup

To clean up all resources created in this lab:

```bash
k delete pod liveness-http readiness-demo startup-demo tcp-probe-demo exec-probe-demo probe-timing failing-probe
k delete svc readiness-svc
```
