---
---
layout: default
title: "CKAD Preparation — Choose and use the right workload resource"
date: 2025-10-21
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-articles/20251021-ckad/article.webp"
summary: ""
---

## Introduction

This article is part of an ongoing series designed to guide you through practical concepts and real-world scenarios for the Certified Kubernetes Application Developer (CKAD) exam.

In this post, we’ll cover CKAD requirements within the “Application Design and Build” domain:

>>> Choose and use the right workload resource (Deployment, DaemonSet, CronJob, StatefulSet, etc.)

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](/blog-articles/20251019-ckad/article_EN.html).

## Prerequisites

A running instance of Kubernetes. You can use Kubernetes for Docker Desktop, Minikube, or a temporary environment on [KillerCoda Playgrounds](https://killercoda.com/playgrounds).

## Getting the Resources

All manifests and examples mentioned in this post are available in the following repository:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-articles/20251021-ckad
```

## Understanding the Resources

Before jumping into pratice, let’s recap the key Kubernetes controllers responsible for managing Pods.

| Resource     | Typical use case                                                            | Scaling                                                 | Lifetime                     | Example                                   |
|--------------|-----------------------------------------------------------------------------|---------------------------------------------------------|------------------------------|-------------------------------------------|
| Deployment   | Stateless apps (frontends, APIs, microservices)                             | ReplicaSets; scale manually or via HPA                  | Continuous                   | Web service, API server                   |
| DaemonSet    | Node-level agents that must run on every (or a subset of) node              | One Pod per targeted node (implicit)                    | Continuous                   | Prometheus Node Exporter, Fluentd         |
| StatefulSet  | Stateful applications requiring stable network IDs and persistent storage   | Replica count with stable identities; scale carefully   | Continuous; stable identity  | Databases (MySQL), Kafka, Redis with PVs  |
| CronJob      | Scheduled or periodic batch tasks                                           | Not applicable for long-running; Jobs spawn on schedule | Short-lived (batch jobs)     | Daily DB backup, periodic cleanup jobs    |

The CKAD exam often tests whether you can identify which resource is appropriate in a given situation — for example, deploying a job that runs periodically (CronJob) versus one that must always have one Pod per node (DaemonSet). In the next sections, we’ll take a closer look at each of these with practical examples.

# Deployment

**Deployments** are the go-to choice for immutable, stateless workloads where each Pod instance can be replaced without concern for identity or local data. This makes them ideal for web services, APIs, or any application that needs to scale horizontally. A Deployment ensures consistency across replicas and provides mechanisms for rolling updates, rollbacks, and automatic recovery when Pods fail.

Let's start with creating a sample YAML manifest so we can customize it:

```bash
k create deploy web --image=nginx:1.29 -o=yaml --dry-run=client > manifests/01-deploy.yaml
```

The flag `-o=yaml` Sets the output format to YAML. Equivalent to -o yaml, while `--dry-run=client` tells the client to validate and construct the request locally but not send it to the server. It shows what would happen without creating/updating the resource. We are using these two to generate a YAML using an imperative command.

Hint: During the CKAD/CKA exams when possible use imperative commands to generate YAML fast, then switch to declarative editing to adjust details if necessary.

This should create something like that:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: web
  name: web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - image: nginx:1.29
        name: nginx
```

Create the manifest:

```bash
k apply -f manifests/01-deploy.yaml
```

The Deployment creates a ReplicaSet that ensures the desired number of Pods are running — in this example it will provision a single Pod.

Verify the Pod reaches the Running state:

```bash
k get pod -o=wide -l=app=web --watch
```

We can scale the number of Pods by increasing the replicas:

```bash
k scale deploy --replicas=2 -l=app=web
```

We can restart the pods:

```bash
k rollout restart deploy -l=app=web
```

Pod vengono riavviati uno alla volta (o in piccoli batch, a seconda della configurazione).

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 25%
    maxSurge: 25%
```

This means:
- A maximum of 25% of Pods can be unavailable during the upgrade.
- Kubernetes can create up to 25% additional Pods temporarily (above the desired number).

Let's change the strategy to Recreate:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: web
  name: web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - image: nginx:1.29
        name: nginx
  strategy:
    type: Recreate
```

Apply the changes:

```bash
k apply -f manifests/01-deploy.yaml
```

If we try a new restart, it should restart all the Pods at one:
```bash
k rollout restart deploy -l=app=web
k get pod -o=wide -l=app=web --watch
```

# DaemonSets

**DaemonSets** serve a different purpose: they ensure that a specific Pod runs on every node (or a subset of nodes) in the cluster. This pattern is essential for workloads that provide node-level functionality, such as log collectors, monitoring agents, or networking tools. Because DaemonSets align Pods with nodes rather than scaling by replica count, they are best suited for cluster-wide background services.

Since we don't have an imperative command `k create ..`, we need to look for a YAML manifest from [the official documentation](https://kubernetes.io/search/?q=daemonset). I took the first YAML I found and simplified it:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-monitor
  labels:
    app: node-monitor
spec:
  selector:
    matchLabels:
      app: node-monitor
  template:
    metadata:
      labels:
        app: node-monitor
    spec:
      containers:
      - name: node-monitor
        image: busybox:1.37
        command: ["sh", "-c", "echo Running on $(hostname); sleep 3600"]
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      - key: node-role.kubernetes.io/master
        operator: Exists
        effect: NoSchedule
```

I kept the tolerations because they allow the daemonset to run Pods on control plane nodes if these have a control-plane or master taints. We'll cover these in detail later, so ignore them for now.

Also, since we are using busybox, we also need to specify a command `["sh", "-c", "echo Running on $(hostname); sleep 3600"]`, otherwise your container will terminate immediately.

This behavior is due to how the busybox image was built. Each Docker image can specify two key fields in its Dockerfile:
- ENTRYPOINT
- CMD

When you run a container (in Kubernetes or Docker), these fields define which process runs at startup. Here's an example with nginx:

```dockerfile
FROM debian
RUN apt-get install -y nginx
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
```

In the example above, Kubernetes doesn’t need a command, because the image already knows what to do — it starts nginx in the foreground.

The busybox image is extremely minimal:
```dockerfile
FROM scratch
ADD busybox /bin/busybox
ENTRYPOINT ["sh"]
```

`sh` if it has neither a command nor an input to process, it considers the work finished and closes the process → the container goes into the Completed state.

Ok, back to the DaemonSet. Let's create it:

```bash
k apply -f manifests/02-daemon-set.yaml
```

Verify the Pod reaches the Running state:

```bash
k get pod -o=wide -l=app=node-monitor --watch
```
The DaemonSet should create a pod on each node:

```text
controlplane:~$ k get pod -o=wide -l=app=node-monitor --watch
NAME                 READY   STATUS    RESTARTS   AGE   IP            NODE           NOMINATED NODE   READINESS GATES
node-monitor-hlr6d   1/1     Running   0          34s   192.168.0.6   controlplane   <none>           <none>
node-monitor-nd7m2   1/1     Running   0          34s   192.168.1.7   node01         <none>           <none>
```

## CronJobs

**CronJobs** are used for scheduled or periodic tasks. They create temporary Job objects at defined times to execute specific operations — for instance, backups, cleanup scripts, or data synchronization tasks. Unlike Deployments or DaemonSets, CronJobs are not designed for continuously running services; they execute once per schedule and terminate upon completion.

```bash
kubectl create cronjob my-job --image=busybox:1.37 --schedule="*/2 * * * *"  -- date > manifests/03-cronjob.yaml
```

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: my-job
spec:
  jobTemplate:
    metadata:
      name: my-job
    spec:
      template:
        spec:
          containers:
          - command:
            - date
            image: busybox:1.37
            name: my-job
          restartPolicy: OnFailure
  schedule: '*/2 * * * *'
```

Let's create it:

```bash
k apply -f manifests/03-cronjob.yaml
```

Within two minutes we should see a new Job which will, in turn, create a pod:

```bash
k get cronjob,job -A
```

If we don't want to wait we can create it manually:

```bash
kubectl create job myjob1 --from=cronjob/my-job
```

The pods should run the command and then go into `Complete` state:

```bash
kubectl get pod -l=job-name=myjob1
```

You should see an output similar to this:

```text
(base) λ k get cronjob,job -A
NAMESPACE   NAME                   SCHEDULE      TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
default     cronjob.batch/my-job   */2 * * * *   <none>     False     0        <none>          43s

NAMESPACE   NAME               STATUS     COMPLETIONS   DURATION   AGE
default     job.batch/myjob1   Complete   1/1           6s         12s
```

Jobs can be suspended by setting the property `suspend` to `true`:

```bash
spec:
  suspend: true
```

## 🏁 Wrapping Up: What We’ve Covered

In this article we reviewed Deployments, DaemonSets, and CronJobs — when to use each, how they behave, and how to create/manage them with kubectl and YAML.

By the end of this article, you’ll be able to:

- Differentiate between the main workload resources and their responsibilities.
- Select the appropriate controller based on functional and operational requirements.
- Apply each resource practically using kubectl and declarative YAML manifests.

We still have to deal with the StatefulSet and stateful workloads. But since they depend on persistent volumes and stable network identities these will be discussed in detail in a dedicated post.

## Final cleanup

When you're done with the experiments, remove all created resources to clean up the environment:

```bash
k delete deploy web
k delete ds node-monitor
```
