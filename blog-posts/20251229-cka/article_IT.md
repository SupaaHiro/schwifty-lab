---
layout: default
title: "CKA Preparation — Assegnazione delle Risorse in Base alla Disponibilità del Nodo"
date: 2025-12-29
categories: [cka, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20251229-cka/article.webp"
summary: "Impara a calcolare e assegnare correttamente le risorse CPU e memoria ai Pod in Kubernetes in base alla disponibilità del nodo — una competenza essenziale per la certificazione CKA per garantire stabilità e prestazioni ottimali del cluster."
---

## Introduzione

E' più di un mese che non pubblico un articolo per il blog! Principalmente a causa deadline lavorative, ma anche perché mi stavo preparando per rinnovare la certificazione [*CKA*](https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/).

In questo articolo, vorrei condividere con voi un esercizio che mi è capitato di fare durante la preparazione per l'esame, riguardante l'assegnazione delle risorse in funzione della disponibilità del nodo. Esercizio che sembra facile, ma che nasconde alcune insidie.

Questo articolo non fa parte della serie CKAD: Se volete iniziare a prepararvi per la certificazione CKAD, potete partire da qui: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisiti

Un cluster Kubernetes funzionante (Minikube, Docker Desktop, o [KillerCoda Playgrounds](https://killercoda.com/playgrounds)) con *un singolo nodo worker* e una conoscenza di base di Pod e manifesti YAML.

Opzionalmente, un server delle metriche (ad esempio `metrics-server`) può essere installato nel cluster per monitorare l'utilizzo delle risorse. Potete installarlo eseguendo il seguente comando:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

In caso di problemi con il TLS, modificate il deployment del `metrics-server` per aggiungere l'argomento `--kubelet-insecure-tls` al container.

```bash
kubectl -n kube-system edit deployment metrics-server
# In spec.template.spec.containers[].args add:
# - --kubelet-insecure-tls
```

## Ottenere le Risorse

Clona il repository CKA-PREP-2025-v2 e avvia l'esercizio così:

```bash
git clone https://github.com/SupaaHiro/CKA-PREP-2025-v2
cd CKA-PREP-2025-v2
bash ./scripts/run-question.sh 'Question-4 Resource-Allocation'
```

Nota: Questo repo è un fork del repository [vj2201/CKA-PREP-2025-v2](https://github.com/vj2201/CKA-PREP-2025-v2) con alcune modifiche minori, pricipalmente per segnarmi delle note e fare esperimenti.

## Esercizio Pratico: Assegnazione delle Risorse in Funzione della Disponibilità del Nodo

Dopo aver lanciato l'esercizio, dovrebbe apparirvi un prompt simile a questo:

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

La prima cosa che ci viene chiesto di fare è scalare il deployment `wordpress` a 0 repliche. Facciamolo così:

```bash
kubectl scale deploy wordpress --replicas 0
```

Prima di poter ridimensionare il deployment, dobbiamo calcolare quante risorse possiamo assegnare a ciascun Pod. Per farlo, verifichiamo quante risorse sono disponibili sul nodo:

```bash
kubectl describe node node01 | grep "Allocatable:" -A5

Dovrremmo vedere qualcosa di simile a questo:

```bash
Allocatable:
  cpu:                1
  memory:             1846540Ki
  pods:               110
```

Per semplicità assimuamo che il nostro cluster abbia un solo nodo worker disponibile, in questa caso con 1 CPU e circa 1.8 GiB di memoria allocabile.

Questi valori tengono già conto delle risorse utilizzate dal sistema e da kubelet, da questi valori però dobbiamo sottrarre le risorse guà in uso dai Pod esistenti.

```bash
kubectl describe node node01 | grep "Allocated resources:" -A5
```

Dovremmo vedere qualcosa di simile a questo:

```bash
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests     Limits
  --------           --------     ------
  cpu                225m (22%)   0 (0%)
  memory             300Mi (16%)  340Mi (18%)
```

Adesso dobbiamo fare un paio di calcoli. Possiamo utilizzare fino a 1 CPU - 225m = 775m CPU e 1.8 GiB - 300 MiB = circa 1.5 GiB di memoria per i nostri Pod.

Abbiamo 3 repliche, quindi dividiamo queste risorse per 3:
- CPU per Pod: 775m / 3 ≈ 258m
- Memoria per Pod: 1.5 GiB / 3 = 512 Mi

Per fare i calcoli da terminale, possiamo usare `bc` così:

```bash
1000 * (1 - 0.225) / 3 -> 258
1846540/1024 *  (1 - 0.16) / 3 -> 504
```

> Nota: Per uscire da `bc`, digitiamo `quit`.

Quindi, i limiti massimi che possiamo assegnare a ciascun Pod sono:
- CPU per Pod: 258m
- Memoria per Pod: 504 Mi

Arrotondiamo i valori dei limiti per difetto:
- Limite CPU per Pod: 250m
- Limite Memoria per Pod: 500 Mi

Adesso che conosciamo i limiti, dobbiamo lasciare un po' di margine per evitare instabilità del nodo. Assegniamo il 95% dei limiti come richieste:

- Richiesta CPU per Pod: 237m (95% del limite)
- Richiesta Memoria per Pod: 475 Mi (95% del limite)

Ora possiamo modificare il deployment `wordpress` per impostare le richieste e i limiti delle risorse per i container principali e gli init container. Apriamo il manifesto del deployment:

```bash
kubectl edit deploy wordpress
```

Aggiungiamo le seguenti sezioni `resources` sotto i container principali e gli init container:

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

Allo stesso modo assegniamo le stesse risorse anche per gli init container.

Dopo aver salvato le modifiche, ridimensioniamo il deployment `wordpress` a 3 repliche:

```bash
kubectl scale deploy wordpress --replicas 3
```

Dopo un po' i pod dovrebbero essere in esecuzione.

Verifichiamo lo stato dei Pod:

```bash
kubectl get pods -l app=wordpress
```

Dovremmo vedere qualcosa di simile a questo:

```bash
NAME                         READY   STATUS    RESTARTS   AGE
wordpress-5d7f9c6b7b-abcde   1/1     Running   0          30s
wordpress-5d7f9c6b7b-fghij   1/1     Running   0          30s
wordpress-5d7f9c6b7b-klmno   1/1     Running   0          30s
```

Ricontrolliamo le risorse allocate sul nodo per assicurarci che tutto sia corretto:

```bash
kubectl describe node node01 | grep "Allocated resources:" -A5
```

Dovremmo vedere qualcosa di simile a questo:

```bash
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests      Limits
  --------           --------      ------
  cpu                936m (93%)    750m (75%)
  memory             1725Mi (95%)  1840Mi (102%)
```

Forse con il limite della memoria siamo un po' overcommitati, ma va bene così, l'importante è che le richieste siano entro i limiti del nodo.

Ecco fatto! Abbiamo completato l'esercizio di assegnazione delle risorse in funzione della disponibilità del nodo.

## Ricapitolando: Cosa Abbiamo Visto

In questo articolo, abbiamo visto come calcolare e assegnare risorse ai Pod in un cluster Kubernetes in base alla disponibilità del nodo. Abbiamo imparato a:
- Verificare le risorse allocabili e già allocate sul nodo.
- Calcolare le risorse disponibili per i Pod.
- Modificare un deployment per impostare richieste e limiti delle risorse.

Spero che questo articolo vi sia stato utile nella vostra preparazione per la certificazione CKA. Buona fortuna con i vostri studi e alla prossima!
