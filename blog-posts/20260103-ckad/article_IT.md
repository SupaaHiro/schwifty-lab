---
layout: default
title: "CKAD Preparation — Using Kustomize to deploy an Nginx Application"
date: 2026-01-03
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260103-ckad/article.webp"
summary: "Scopri come utilizzare Kustomize per gestire configurazioni Kubernetes riutilizzabili e modulabili. Impara a creare basi, overlay e personalizzazioni per staging e produzione."
---

## Introduzione

Questo articolo fa parte di una serie continua progettata per aiutarti a prepararti per l'esame [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) attraverso laboratori brevi e mirati.

In questo articolo, tratteremo i requisiti del dominio "Application Deployment":

> Kustomize

Vedremo cos'è Kustomize e come usarlo per gestire configurazioni Kubernetes riutilizzabili e modulabili.

Puoi iniziare dall'inizio della serie qui: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisiti

Un cluster Kubernetes in esecuzione (Minikube, Docker Desktop o https://killercoda.com/playgrounds/course/kubernetes-playgrounds) e una familiarità di base con i Pod e i manifesti YAML.

## Ottenere le Risorse

Clona il repository del laboratorio e naviga nella cartella di questo articolo:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260103-ckad
```

## Esercizio Pratico: Utilizziamo Kustomize per distribuire un'Applicazione Nginx

Kustomize è uno strumento nativo di Kubernetes che serve a gestire configurazioni YAML in maniera modulare e riutilizzabile senza dover ricorrere a template esterni come Helm. Fa parte del kubectl stesso (puoi usarlo direttamente con kubectl apply -k) e permette di creare versioni diverse della stessa configurazione senza duplicare file.

Quando distribuiamo un'applicazione su Kubernetes, spesso dobbiamo creare e gestire molte risorse diverse (Pod, Servizi, ConfigMap, Secret, ecc.). Spesso, queste risorse condividono configurazioni comuni, ma possono anche avere differenze specifiche a seconda dell'ambiente (sviluppo, staging, produzione). Kustyomize ci aiuta a gestire queste configurazioni in modo efficiente.

### Creiamo una Base con Kustomize

Per capire come funziona Kustomize, creiamo una base semplice con un Deployment e un Service per Nginx, e poi creeremo due overlay per ambienti di staging e produzione.

Iniziamo creando la struttura delle cartelle per Kustomize:

```bash
kustomize/
  base/
    deployment.yaml
    service.yaml
    kustomization.yaml
```

Nella cartella `base/`, creiamo il file `deployment.yaml` con il seguente contenuto:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
```

E il file `service.yaml` con il seguente contenuto:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
```

Infine, creiamo il file `kustomization.yaml` nella cartella `base/` con il seguente contenuto:

```yaml
resources:
  - deployment.yaml
  - service.yaml

labels:
  - includeSelectors: true
    pairs:
      app: nginx
```

In Kustomize i transformers sono strumenti che permettono di modificare le risorse in modo dichiarativo. Ad esempio, possiamo usare un transformer per cambiare l'immagine del container o il numero di repliche senza dover modificare direttamente i file YAML originali.

Nel esempio sopra, abbiamo usato `commonLabels` come un semplice transformer per aggiungere un'etichetta comune a tutte le risorse.

### Creiamo gli Overlay per Staging e Produzione

Gli overlay permettono di adattare la base a diversi ambienti, modificando namespace, replica count o nomi dei deployment senza duplicare i manifesti.

Struttura dei nostri overlay:

```bash
kustomize/
  overlays/
    staging/
      kustomization.yaml
      patch.yaml
    production/
      kustomization.yaml
      patch.yaml
```

Nella cartella `overlays/staging/`, creiamo il file `kustomization.yaml` con il seguente contenuto:

```yaml
resources:
  - ../../base

namespace: staging
nameSuffix: -staging

patches:
  - path: patch.yaml
```

Creiamo il file `patch.yaml` con le modifiche specifiche per staging, ad esempio il numero di repliche:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 2
```

Nella cartella `overlays/production/`, creiamo il file `kustomization.yaml` con il seguente contenuto:

```yaml
resources:
  - ../../base

namespace: production
nameSuffix: -prod

patches:
  - path: patch.yaml
```

Creiamo il file `patch.yaml` con le modifiche specifiche per produzione, ad esempio il numero di repliche:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 5
```

Per applicare la configurazione staging:
```bash
k apply -k overlays/staging/
```

Per applicare la configurazione produzione:
```bash
k apply -k overlays/production/
```

Verifichiamo che le risorse siano state create correttamente:

```bash
k get deploy, svc, po -n staging
k get deploy, svc, po -n production
```

È possibile generare i manifesti finali senza applicarli:
```bash
kustomize build overlays/staging > ../manifests/nginx-staging.yaml
kustomize build overlays/production > ../manifests/nginx-production.yaml
```

Notare che a differenze di Helm, Kustomize non utilizza Go Templates, ma si basa su patch e trasformazioni dichiarative, rendendo più semplice la gestione delle configurazioni senza dover imparare un linguaggio di templating. Inoltre non gestisce rilasci o versioni come Helm, ma si concentra esclusivamente sulla gestione delle configurazioni.

## Ricapitolando: Cosa Abbiamo Visto

In questo esercizio abbiamo esplorato Kustomize e come possa semplificare la gestione dei manifesti Kubernetes in contesti multipli:

- Creare una base riutilizzabile con Deployment e Service.

- Applicare commonLabels per uniformare le risorse.

- Creare overlay per staging e produzione con namespace, suffix e replica count differenti.

- Modificare configurazioni senza duplicare i manifesti, usando patch e Kustomization.

- Visualizzare i manifesti finali prima di applicarli al cluster.

Kustomize è uno strumento fondamentale per mantenere pulite e modulabili le configurazioni Kubernetes, rendendolo essenziale per chi prepara l’esame CKAD o gestisce cluster con ambienti multipli.

# Pulizia finale

Per concludere, rimuoviamo il namespace creato per questo esercizio:

```bash
k delete -k overlays/staging/
k delete -k overlays/production/
k delete ns staging production
```
