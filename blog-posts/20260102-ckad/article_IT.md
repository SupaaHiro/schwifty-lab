---
layout: default
title: "CKAD Preparation — Use the Helm package manager to deploy existing packages"
date: 2026-01-02
categories: [ckad, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260102-ckad/article.webp"
summary: "Scopri come utilizzare Helm, il package manager di Kubernetes, per semplificare l'installazione e la gestione delle applicazioni. Impara a creare, installare e gestire chart Helm attraverso un esercizio pratico con Nginx."
---

## Introduzione

Questo articolo fa parte di una serie continua progettata per aiutarti a prepararti per l'esame [*Certified Kubernetes Application Developer (CKAD)*](https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad/) attraverso laboratori brevi e mirati.

In questo articolo, tratteremo i requisiti del dominio "Application Deployment":

> Use the Helm package manager to deploy existing packages

Vedremo cos'è Helm, come installarlo e come usarlo per distribuire applicazioni in un cluster Kubernetes.

Puoi iniziare dall'inizio della serie qui: [*CKAD Preparation — What is Kubernetes*](https://supaahiro.github.io/schwifty-lab/blog-posts/20251019-ckad/article_EN.html).

## Prerequisiti

Un cluster Kubernetes in esecuzione (Minikube, Docker Desktop o https://killercoda.com/playgrounds/course/kubernetes-playgrounds) e una familiarità di base con i Pod e i manifesti YAML.

## Ottenere le Risorse

Clona il repository del laboratorio e naviga nella cartella di questo articolo:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-posts/20260102-ckad
```

## Esercizio Pratico: Utilizziamo Helm per Distribuire un'Applicazione

Prima di iniziare a sporcarci le mani con questo esercizio pratico, è bene capire cos'è Helm e perché è utile. In pratica, Helm fa per Kubernetes quello che apt, yum o Homebrew fanno per i sistemi operativi: semplifica l'installazione, l'aggiornamento e la gestione di applicazioni complesse.

Quando distribuiamo un'applicazione su Kubernetes, spesso dobbiamo creare e gestire molte risorse diverse (Pod, Servizi, ConfigMap, Secret, ecc.). Kubernetes sa come gestire queste risorse, ma non ha visibilità su come esse lavorino insieme per formare un'applicazione completa. Qui entra in gioco Helm. Helm utilizza i "chart", che sono pacchetti preconfigurati di risorse Kubernetes. Questi chart possono essere facilmente installati, aggiornati o rimossi con semplici comandi Helm, semplificando notevolmente la gestione delle applicazioni su Kubernetes.

Esistono diversi repository di chart Helm pubblici, come [Artifact Hub](https://artifacthub.io/), che ospita migliaia di chart per varie applicazioni.

Iniziamo installando Helm, seguendo le istruzioni ufficiali riportate nella [documentazione ufficiale](https://helm.sh/docs/intro/install/).

Su un sistema basato su Debian/Ubuntu, puoi installare Helm con i seguenti comandi:

```bash
$ curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
$ chmod 700 get_helm.sh
$ ./get_helm.sh
```

Per capire come funziona Helm, creeremo un semplice chart Helm per distribuire una piccola applicazione web basata su Nginx. Un modo rapido per creare un chart di esempio è utilizzare il comando `helm create`, che genera una struttura di directory di base per un chart Helm.

```bash
helm create my-nginx-app
```

Questo comando dovrebbe creare una directory chiamata `my-nginx-app` con la seguente struttura:

```bash
my-nginx-app/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    _helpers.tpl
    .. altri file ..
```

Dato che l'esempio generato potrebbe essere più complesso di quanto necessario per questo esercizio, semplifichiamo il chart rimuovendo i file non necessari e modificando i manifesti per adattarli alla nostra semplice applicazione Nginx.

Puoi utilizzare direttamente l'esempio presente nella cartella `charts/my-nginx-app` come riferimento per i file modificati oppure seguire le istruzioni qui sotto per apportare le modifiche necessarie.

Se hai scelto di modificare i file manualmente, procedi come segue:

- Rimuovi tutti i file nella directory `templates/`, lasciando solo `deployment.yaml`, `service.yaml`, `_helpers.tpl` e `NOTES.txt`.

- Sostituisci il contenuto di `templates/deployment.yaml` con il seguente:

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

> I file presenti nella cartella templates/ non sono semplici manifesti YAML statici. Helm utilizza infatti Go Templating, un sistema di template che permette di inserire espressioni dinamiche all’interno dei file YAML.

- Sostituisci il contenuto di `templates/service.yaml` con il seguente:

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

- Sostituisci il contenuto di `NOTES.txt` con il seguente:

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

- Per finire, sostituisci il contenuto di `values.yaml` con il seguente:

```yaml
replicaCount: 1

image:
  repository: nginx
  tag: "1.27"
  pullPolicy: IfNotPresent
```

Per finire facciamo un check per verificare che tutto sia a posto:

```bash
helm lint my-nginx-app
```

Dovresti vedere un messaggio che indica che il chart è valido:

```bash
==> Linting my-nginx-app
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Per i chart forniti da terze parti, può essere utile esaminare i valori di configurazione predefiniti e la documentazione del chart prima di procedere con l'installazione.

Puoi farlo usando i comandi `helm show values`, `helm show readme` e `helm show crds`:

```bash
helm show values my-nginx-app
helm show readme my-nginx-app
helm show crds my-nginx-app
```

Ovviamente il nostro chart è molto semplice e non include CRD, ma in scenari reali questi comandi sono molto utili per comprendere come configurare correttamente un chart prima dell'installazione.

Prima di installare il chart, possiamo anche generare i manifesti Kubernetes che Helm creerà per noi usando il comando `helm template`. Questo ci permette di vedere esattamente quali risorse verranno create nel cluster:

```bash
helm template my-nginx-app > ../manifests/nginx-manifests.yaml
```

Se vuoi modificare qualche parametro, puoi farlo direttamente nel file `values.yaml` o passare i valori personalizzati tramite la linea di comando usando l'opzione `--set`.

```bash
helm template my-nginx-app --set replicaCount=2 > ../manifests/nginx-manifests.yaml
```

Ora siamo pronti per installare il nostro chart Helm nel cluster Kubernetes. Usiamo il comando `helm install` per distribuire l'applicazione:

```bash
helm install my-nginx-release my-nginx-app -n nginx --create-namespace
```

Il comando sopra installerà il chart `my-nginx-app` con il nome di rilascio `my-nginx-release` nel namespace `nginx`, creando il namespace se non esiste già.

Puoi verificare che il deployment e il servizio siano stati creati correttamente con il seguente comando:

```bash
k get deploy,svc,po -n nginx
```

Con il comando `helm list` o `helm ls`, puoi vedere tutti i rilasci Helm installati nel cluster:

```bash
helm list -n nginx
```

Con il comando `helm status`, puoi ottenere informazioni dettagliate sullo stato del rilascio:

```bash
helm status my-nginx-release -n nginx
```

Il comando `helm upgrade` ti permette di aggiornare un rilascio esistente con nuove configurazioni o versioni del chart. Ad esempio, per aggiornare l'immagine del container Nginx alla versione 1.29:

```bash
helm upgrade my-nginx-release my-nginx-app --set image.tag="1.29" -n nginx
```

Helm mantiene una cronologia delle versioni per ogni rilascio:

```bash
helm history my-nginx-release -n nginx
```

Ecco un esempio di output:

```bash
REVISION        UPDATED                         STATUS          CHART                   APP VERSION     DESCRIPTION
1               Tue Dec 30 18:32:22 2025        superseded      my-nginx-app-0.1.0      1.16.0          Install complete
2               Tue Dec 30 18:36:43 2025        deployed        my-nginx-app-0.1.0      1.16.0          Upgrade complete
```

Questa cronoligia viene salvata su dei secret gestiti da Helm all'interno del namespace in cui è stato installato il rilascio:

```bash
k get secrets -n nginx
```

Il comando `helm rollback` ti consente di tornare a una versione precedente del rilascio se qualcosa va storto durante un aggiornamento. Ad esempio, per tornare alla revisione 1:

```bash
helm rollback my-nginx-release 1 -n nginx
```

Tieni presente che lo stesso rollback genera un nuovo rilascio, quindi la cronologia mostrerà tutte le versioni, inclusi i rollback:

```bash
REVISION        UPDATED                         STATUS          CHART                   APP VERSION     DESCRIPTION
1               Tue Dec 30 18:32:22 2025        superseded      my-nginx-app-0.1.0      1.16.0          Install complete
2               Tue Dec 30 18:36:43 2025        superseded      my-nginx-app-0.1.0      1.16.0          Upgrade complete
3               Tue Dec 30 18:41:15 2025        deployed        my-nginx-app-0.1.0      1.16.0          Rollback to 1
```

Infine, quando non hai più bisogno dell'applicazione, puoi rimuoverla con il comando `helm uninstall`:

```bash
helm uninstall my-nginx-release -n nginx
```

Per finire la nostra panoramica su Helm, vediamo come aggiungere un repository di chart Helm esterno. Ad esempio, possiamo cercare un applicazione WordPress su [Artifact Hub](https://artifacthub.io/) e aggiungere il [repository](https://artifacthub.io/packages/search?ts_query_web=wordpress&sort=relevance&page=1) ufficiale di Bitnami, che ospita un chart per WordPress.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

Ora possiamo cercare il chart di WordPress nel repository di Bitnami:

```bash
helm search repo bitnami/wordpress --versions
```

L'opzione `--versions` mostra tutte le versioni disponibili del chart.

Possiamo installare WordPress utilizzando il chart di Bitnami con il seguente comando:

```bash
helm install my-wordpress bitnami/wordpress -n wordpress --create-namespace --version 28.0.4 --set wordpressUsername=admin,wordpressPassword=pass123
```

In questo modo, Helm scaricherà il chart di WordPress dal repository di Bitnami e lo installerà nel namespace `wordpress`, creando il namespace se non esiste già. Abbiamo anche specificato alcune configurazioni personalizzate, come il nome utente e la password di WordPress e la password di root di MariaDB.

Se vogliamo aggiornare la versione di WordPress in futuro, possiamo usare il comando `helm upgrade`:

```bash
helm upgrade my-wordpress bitnami/wordpress -n wordpress --version 28.1.0
```

Se guardiamo l'history del rilascio di WordPress, vedremo le diverse versioni installate:

```bash
helm history my-wordpress -n wordpress
```

Ecco un esempio di output:

```bash
REVISION        UPDATED                         STATUS          CHART                   APP VERSION     DESCRIPTION
1               Wed Dec 31 09:56:53 2025        superseded      wordpress-28.0.4        6.9.0           Install complete
2               Wed Dec 31 09:59:28 2025        deployed        wordpress-28.1.0        6.9.0           Upgrade complete
```

## Ricapitolando: Cosa Abbiamo Visto

In questo esercizio abbiamo esplorato Helm, il package manager di Kubernetes, e come possa semplificare notevolmente la gestione delle applicazioni.

Abbiamo imparato a:

- Installare Helm sul nostro sistema seguendo la documentazione ufficiale.
- Creare un chart Helm di base usando il comando `helm create`.
- Personalizzare i template Kubernetes all'interno di un chart per adattarli alle nostre esigenze.
- Validare un chart con `helm lint` per assicurarci che sia configurato correttamente.
- Visualizzare i valori di configurazione, la documentazione e le CRD di un chart con i comandi `helm show`.
- Generare i manifesti Kubernetes senza installarli usando `helm template`.
- Installare un chart nel cluster con `helm install` e verificarne lo stato.
- Gestire i rilasci con `helm list`, `helm upgrade`, `helm rollback` e `helm history`.
- Rimuovere completamente un'applicazione con `helm uninstall`.
- Aggiungere repository di chart esterni e installare applicazioni da essi.

Helm è uno strumento fondamentale nell'ecosistema Kubernetes e rappresenta una competenza essenziale per l'esame CKAD. La capacità di utilizzare chart Helm esistenti, comprenderli e personalizzarli ti permetterà di distribuire applicazioni complesse in modo rapido ed efficiente, mantenendo al contempo la riproducibilità e la gestibilità nel tempo.

Nella pratica quotidiana, Helm ti farà risparmiare tempo prezioso e ridurrà gli errori di configurazione, permettendoti di concentrarti sugli aspetti più importanti dello sviluppo delle tue applicazioni.

# Pulizia finale

Per concludere, rimuoviamo il namespace creato per questo esercizio:

```bash
k delete ns nginx
```
