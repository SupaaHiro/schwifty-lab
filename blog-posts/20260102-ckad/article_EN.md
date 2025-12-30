---
layout: default
title: "CKAD Preparation — Use the Helm package manager to deploy existing packages"
date: 2026-01-02
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260102-ckad/article.webp"
summary: "Learn how to use Helm, the Kubernetes package manager, to simplify application installation and management. Master creating, installing, and managing Helm charts through a hands-on exercise with Nginx."
---

## Introduction

This article is part of an ongoing series designed to help you prepare for the [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) exam through small, focused labs.

In this article, we'll cover the requirements within the "Application Deployment" domain:

> Use the Helm package manager to deploy existing packages

We'll explore what Helm is, how to install it, and how to use it to deploy applications in a Kubernetes cluster.

You can start from the beginning of the series here: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisites

A running Kubernetes cluster (Minikube, Docker Desktop, or [KillerCoda Playgrounds](https://killercoda.com/playgrounds)) and basic familiarity with Pods and YAML manifests.

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260102-ckad
```

## Hands-on Exercise: Let's Use Helm to Deploy an Application

Before we dive into this hands-on exercise, it's important to understand what Helm is and why it's useful. In essence, Helm does for Kubernetes what apt, yum, or Homebrew do for operating systems: it simplifies the installation, upgrading, and management of complex applications.

When we deploy an application on Kubernetes, we often need to create and manage many different resources (Pods, Services, ConfigMaps, Secrets, etc.). Kubernetes knows how to handle these resources, but it doesn't have visibility into how they work together to form a complete application. This is where Helm comes in. Helm uses "charts," which are pre-configured packages of Kubernetes resources. These charts can be easily installed, upgraded, or removed with simple Helm commands, significantly simplifying application management on Kubernetes.

There are several public Helm chart repositories, such as [Artifact Hub](https://artifacthub.io/), which hosts thousands of charts for various applications.

Let's start by installing Helm, following the official instructions in the [official documentation](https://helm.sh/docs/intro/install/).

On a Debian/Ubuntu-based system, you can install Helm with the following commands:

```bash
$ curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
$ chmod 700 get_helm.sh
$ ./get_helm.sh
```

To understand how Helm works, we'll create a simple Helm chart to deploy a small Nginx-based web application. A quick way to create a sample chart is to use the `helm create` command, which generates a basic directory structure for a Helm chart.

```bash
helm create my-nginx-app
```

This command should create a directory called `my-nginx-app` with the following structure:

```bash
my-nginx-app/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    _helpers.tpl
    .. other files ..
```

Since the generated example might be more complex than necessary for this exercise, let's simplify the chart by removing unnecessary files and modifying the manifests to fit our simple Nginx application.

You can directly use the example in the `charts/my-nginx-app` folder as a reference for the modified files, or follow the instructions below to make the necessary changes.

If you've chosen to modify the files manually, proceed as follows:

- Remove all files in the `templates/` directory, keeping only `deployment.yaml`, `service.yaml`, `_helpers.tpl`, and `NOTES.txt`.

- Replace the content of `templates/deployment.yaml` with the following:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: { { include "my-nginx-app.fullname" . } }
spec:
  replicas: { { .Values.replicaCount } }
  selector:
    matchLabels:
      app: { { include "my-nginx-app.name" . } }
  template:
    metadata:
      labels:
        app: { { include "my-nginx-app.name" . } }
    spec:
      containers:
        - name: nginx
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: { { .Values.image.pullPolicy } }
          ports:
            - containerPort: 80
```

- Replace the content of `templates/service.yaml` with the following:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: { { include "my-nginx-app.fullname" . } }
spec:
  type: ClusterIP
  selector:
    app: { { include "my-nginx-app.name" . } }
  ports:
    - port: 80
      targetPort: 80
```

- Replace the content of `NOTES.txt` with the following:

```text
Nginx has been successfully installed 🎉

Release: {{ .Release.Name }}
Namespace: {{ .Release.Namespace }}

Replica Count: {{ .Values.replicaCount }}
Image: {{ .Values.image.repository }}:{{ .Values.image.tag }}

To check the status of the pods:
  kubectl get pods -l app={{ include "my-nginx-app.name" . }} -n {{ .Release.Namespace }}

To view the logs of the first pod:
  kubectl logs -l app={{ include "my-nginx-app.name" . }} -n {{ .Release.Namespace }} --tail=100

To remove the release:
  helm uninstall {{ .Release.Name }} -n {{ .Release.Namespace }}

------------------------------------------------------------
Accessing nginx

If you are running inside the cluster:
  curl http://{{ include "my-nginx-app.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local

If the Service type is ClusterIP (default), you can use port-forward:
  kubectl port-forward svc/{{ include "my-nginx-app.fullname" . }} -n {{ .Release.Namespace }} 8080:80
  curl http://localhost:8080

If the Service type is NodePort:
  kubectl get svc {{ include "my-nginx-app.fullname" . }} -n {{ .Release.Namespace }}
  # Then access using:
  http://<NodeIP>:<NodePort>

If the Service is exposed via Ingress:
  kubectl get ingress -n {{ .Release.Namespace }}
  # Then access using the configured host name.
```

- Finally, replace the content of `values.yaml` with the following:

```yaml
replicaCount: 1

image:
  repository: nginx
  tag: "1.27"
  pullPolicy: IfNotPresent
```

Let's finish by running a check to verify everything is in order:

```bash
helm lint my-nginx-app
```

You should see a message indicating that the chart is valid:

```bash
==> Linting my-nginx-app
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

For third-party charts, it can be useful to examine the default configuration values and chart documentation before proceeding with installation.

You can do this using the `helm show values`, `helm show readme`, and `helm show crds` commands:

```bash
helm show values my-nginx-app
helm show readme my-nginx-app
helm show crds my-nginx-app
```

Obviously, our chart is very simple and doesn't include CRDs, but in real-world scenarios these commands are very useful for understanding how to properly configure a chart before installation.

Before installing the chart, we can also generate the Kubernetes manifests that Helm will create for us using the `helm template` command. This allows us to see exactly which resources will be created in the cluster:

```bash
helm template my-nginx-app > ../manifests/nginx-manifests.yaml
```

If you want to modify any parameters, you can do so directly in the `values.yaml` file or pass custom values via the command line using the `--set` option.

```bash
helm template my-nginx-app --set replicaCount=2 > ../manifests/nginx-manifests.yaml
```

Now we're ready to install our Helm chart in the Kubernetes cluster. Let's use the `helm install` command to deploy the application:

```bash
helm install my-nginx-release my-nginx-app -n nginx --create-namespace
```

The above command will install the `my-nginx-app` chart with the release name `my-nginx-release` in the `nginx` namespace, creating the namespace if it doesn't already exist.

You can verify that the deployment and service were created successfully with the following command:

```bash
k get deploy,svc,po -n nginx
```

With the `helm list` or `helm ls` command, you can see all Helm releases installed in the cluster:

```bash
helm list -n nginx
```

With the `helm status` command, you can get detailed information about the release status:

```bash
helm status my-nginx-release -n nginx
```

The `helm upgrade` command allows you to update an existing release with new configurations or chart versions. For example, to upgrade the Nginx container image to version 1.29:

```bash
helm upgrade my-nginx-release my-nginx-app --set image.tag="1.29" -n nginx
```

Helm maintains a version history for each release:

```bash
helm history my-nginx-release -n nginx
```

Here's an example output:

```bash
REVISION        UPDATED                         STATUS          CHART                   APP VERSION     DESCRIPTION
1               Tue Dec 30 18:32:22 2025        superseded      my-nginx-app-0.1.0      1.16.0          Install complete
2               Tue Dec 30 18:36:43 2025        deployed        my-nginx-app-0.1.0      1.16.0          Upgrade complete
```

This history is stored in secrets managed by Helm within the namespace where the release was installed:

```bash
k get secrets -n nginx
```

The `helm rollback` command allows you to revert to a previous version of the release if something goes wrong during an upgrade. For example, to roll back to revision 1:

```bash
helm rollback my-nginx-release 1 -n nginx
```

Keep in mind that the rollback itself generates a new release, so the history will show all versions, including rollbacks:

```bash
REVISION        UPDATED                         STATUS          CHART                   APP VERSION     DESCRIPTION
1               Tue Dec 30 18:32:22 2025        superseded      my-nginx-app-0.1.0      1.16.0          Install complete
2               Tue Dec 30 18:36:43 2025        superseded      my-nginx-app-0.1.0      1.16.0          Upgrade complete
3               Tue Dec 30 18:41:15 2025        deployed        my-nginx-app-0.1.0      1.16.0          Rollback to 1
```

Finally, when you no longer need the application, you can remove it with the `helm uninstall` command:

```bash
helm uninstall my-nginx-release -n nginx
```

## Recap: What We've Covered

In this exercise, we explored Helm, the Kubernetes package manager, and how it can significantly simplify application management.

We learned how to:

- Install Helm on our system following the official documentation.
- Create a basic Helm chart using the `helm create` command.
- Customize Kubernetes templates within a chart to fit our needs.
- Validate a chart with `helm lint` to ensure it's properly configured.
- View configuration values, documentation, and CRDs of a chart with `helm show` commands.
- Generate Kubernetes manifests without installing them using `helm template`.
- Install a chart in the cluster with `helm install` and verify its status.
- Manage releases with `helm list`, `helm upgrade`, `helm rollback`, and `helm history`.
- Completely remove an application with `helm uninstall`.

Helm is a fundamental tool in the Kubernetes ecosystem and represents an essential skill for the CKAD exam. The ability to use existing Helm charts, understand them, and customize them will allow you to deploy complex applications quickly and efficiently, while maintaining reproducibility and manageability over time.

In daily practice, Helm will save you valuable time and reduce configuration errors, allowing you to focus on the most important aspects of your application development.

# Final Cleanup

To conclude, let's remove the namespace created for this exercise:

```bash
k delete ns nginx
```
