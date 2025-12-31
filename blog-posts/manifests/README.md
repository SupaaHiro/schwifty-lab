# Bundle Manifests — Blog Entities

This directory contains the Kubernetes bundle manifests (Kustomize bases and overlays) for the blog-related entities used by this repository (deployments, services, ConfigMaps, Ingress, etc.).

## Prerequisites
- kubectl configured to the target cluster and context
- kustomize (or kubectl with kustomize support)

## Apply
From the directory that contains the `kustomization.yaml` you want to apply:

```bash
k -n <namespace> apply -k .
```

## Delete

```bash
kustomize build ./posts | kubectl -n <namespace> apply -f -
kustomize build ./categories | kubectl -n <namespace> apply -f -
kustomize build ./crds | kubectl -n <namespace> apply -f -
```
