# Testing Kubernetes NetworkPolicy

## Introduction

In recent days, ahead of my CKAD renewal, I decided to review some fundamental Kubernetes concepts.
To keep track of the experiments, I started publishing a series of practical exercises on this topic.
In the future all the material will be included in my personal blog — as soon as, time permitting, I manage to finish publishing it.

In this first exercise we will create two Pods to test an Ingress NetworkPolicy.

## Prerequisites

⚠️ Important:
Make sure the cluster uses a CNI that implements NetworkPolicy. Otherwise the policies will be ignored, even if they appear "applied".

I ran some local tests with Kubernetes on Docker Desktop and with minikube, but neither supports them natively.
In the end I opted for a temporary environment on KillerCoda: https://killercoda.com/playgrounds

## Creating the Redis Pod

Define the first Pod, which exposes Redis on port 6379.

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

Apply the manifest and verify the Pod reaches the Running state:

```bash
k create -f manifests/01-redis.yaml
k get pod --watch
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

Once applied, check that the endpoint is correctly populated with:

```bash
k create -f manifests/02-redis-svc.yaml
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

Apply the manifest, wait for the Pod to be Running and check the logs:

```bash
k create -f manifests/03-redis-client.yaml
k get pod --watch
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

After applying, the redis-access policy will act like a "fence" around Pods with label app=redis, allowing connections only from Pods labeled with access=redis.

```bash
k create -f manifests/04-netpol.yaml
```

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

Add the missing label access: redis to the redis-client Pod manifest and recreate it:

```bash
yq e '.metadata.labels.access = "redis"' -i manifests/03-redis-client.yaml
k replace -f manifests/03-redis-client.yaml --force
```

After the deploy, the connection should work again:

```text
✅ Connected to Redis at redis:6379
```

## Final cleanup

When you're done with the experiments, remove all created resources (Pods, Service and NetworkPolicy) to clean up the environment:

```bash
k delete svc redis
k delete netpol default-deny-ingress redis-access
k delete po redis redis-client
```
