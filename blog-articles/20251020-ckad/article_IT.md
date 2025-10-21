---
layout: default
title: "CKAD Preparation — Build a container image"
date: 2025-10-20
categories: [ckda, kubernetes]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-articles/20251020-ckad/article.webp"
summary: "Step-by-step guide to build a container image for a FastAPI service that exposes /health and /version endpoints. Demonstrates using a metadata.json for versioning, building and running the image, and publishing it to Kubernetes."
---

## Introduzione

In questo articolo vedremo passo dopo passo come creare un container per un semplice servizio API che espone sia lo stato di health sia la versione del software.

La versione viene letta da un file `metadata.json` che, in uno scenario reale, potrebbe essere generato dalla pipeline CI — per esempio usando GitVersion — quando vengono attivati nuovi build su release, merge nel branch `develop`, e così via.

Il nostro progetto avrà la seguente struttura:

```text
src/
├── app/
│   ├── main.py
│   └── metadata.json
├── pyproject.toml
└── Dockerfile
```

## 📘 CKAD Preparation

Questo articolo fa parte di una serie pensata per aiutarti a preparare l’esame **Certified Kubernetes Application Developer (CKAD)**.  

Questo post specifico affronta il seguente requisito:

**Application Design and Build**  
- Define, build and modify container images

Puoi trovare l’articolo introduttivo qui: [*CKAD Preparation — What is Kubernetes*]({{ '/blog-articles/20251019-ckad/article_EN.html' | relative_url }}).

## Prerequisiti

Per questo esercizio ti serviranno Python 3.12 (o più recente) e Docker 28 (o più recente) per costruire l’immagine del container.

Su Windows puoi scaricare e installare Python dalla pagina ufficiale delle release:  
👉 [Download Python for Windows](https://www.python.org/downloads/windows/).

Su Linux, se usi `apt`, esegui:

```bash
sudo apt update
sudo apt install python3
```

Se usi `yum` come package manager, esegui:

```bash
sudo yum update -y
sudo yum install -y yum-utils
sudo yum install -y python3
```

In alternativa, puoi installare Python compilandolo dai sorgenti:

```bash
sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev liblzma-dev
wget https://www.python.org/ftp/python/3.12.11/Python-3.12.11.tgz
tar -zxvf Python-3.12.11.tgz
cd Python-3.12.11/
./configure --enable-optimizations
make -j "$(nproc)"
sudo make altinstall
sudo ln -s /usr/local/bin/python3.12 /usr/local/bin/python

wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
sudo ln -s /usr/local/bin/pip3.12 /usr/local/bin/pip
```

Infine, proveremo a pubblicare l’immagine su un cluster Kubernetes. Puoi usare Kubernetes per Docker Desktop, Minikube, oppure un ambiente temporaneo su [KillerCoda Playgrounds](https://killercoda.com/playgrounds).

## Ottenere le risorse

Tutti i manifest e gli esempi menzionati in questo post sono disponibili nel seguente repository:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-articles/20251020-ckad
```

## Inizializzazione del progetto

Come package manager useremo uv invece di pip.

```bash
pip install uv
uv --version
```

Inizializza il progetto:

```bash
mkdir src && cd src
mkdir app
uv init
uv add fastapi uvicorn
uv lock
```

Dato che non abbiamo ancora una pipeline CI che inserisce metadata reali, creiamo un semplice segnaposto:

```json
{
  "version": "1.0.0",
  "build": "local-dev",
  "commit": "0000000"
}
```

Salvalo come `src/app/metadata.json`.

In uno scenario CI/CD, questo file verrebbe tipicamente sostituito automaticamente — ad esempio da GitVersion o da un job che scrive la corretta metadata della versione nel contesto di build del container.

## Codice sorgente del servizio API

Ecco il codice sorgente del nostro servizio API che eseguiremo all’interno del container:

```python
from fastapi import FastAPI
import json
import uvicorn

app = FastAPI()

def load_metadata():
    try:
        with open("metadata.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": "unknown", "build": "n/a", "commit": "n/a"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/version")
async def version():
    return load_metadata()

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000, reload=True)
```

Salvalo come `src/app/main.py`.

## Testare il servizio API

Attiva l’ambiente virtuale.

Su Linux:
```bash
source .venv/bin/activate
which python
```

Su Windows:
```bash
.venv\Scripts\activate.bat
where python
```

Prova ad avviare l’app manualmente per verificare che funzioni:

```bash
uv run uvicorn app.main:app --reload
```

Dovresti vedere un output simile a:

```bash
INFO:     Will watch for changes in these directories: ['C:\\repos\\github\\schwifty-lab\\blog-articles\\20251020-ckad\\src']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [26020] using StatReload
INFO:     Started server process [11200]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Ora, richiama uno degli endpoint del servizio — per esempio `/health`:

```bash
curl -svk http://127.0.0.1:8000/health
```

Output previsto:

```bash
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
* using HTTP/1.x
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.14.1
> Accept: */*
>
< HTTP/1.1 200 OK
< date: Sun, 19 Oct 2025 18:24:22 GMT
< server: uvicorn
< content-length: 15
< content-type: application/json
<
{"status":"ok"}* Connection #0 to host 127.0.0.1 left intact
```

# Costruire l’immagine del container

Ora creiamo il **Dockerfile** — un file di testo contenente le istruzioni che Docker usa per costruire un’immagine.

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN python -m pip install --no-cache-dir uv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./
RUN python -m uv sync --no-dev

# Copy application
COPY app/ .

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 5000

# Default environment (can be overridden)
ENV UVICORN_PORT=5000

# Start API inside uv virtual environment
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```
> Un **container image** è un pacchetto eseguibile e immutabile che include tutto il necessario per eseguire un’applicazione in modo coerente su ambienti diversi.

Costruisci l’immagine del container:

```bash
docker build -t fastapi:v1 .
```

Poi eseguila per verificare che funzioni:

```bash
docker run -it --rm -p 5000:5000 fastapi:v1
```

Ora prova a chiamare uno degli endpoint, per esempio `/version`:

```bash
curl -svk http://127.0.0.1:5000/version
```

Output previsto:

```bash
*   Trying 127.0.0.1:5000...
* Connected to 127.0.0.1 (127.0.0.1) port 5000
* using HTTP/1.x
> GET /version HTTP/1.1
> Host: 127.0.0.1:5000
> User-Agent: curl/8.14.1
> Accept: */*
>
< HTTP/1.1 200 OK
< date: Sun, 19 Oct 2025 18:43:43 GMT
< server: uvicorn
< content-length: 58
< content-type: application/json
<
{"version":"1.0.0","build":"local-dev","commit":"0000000"}* Connection #0 to host 127.0.0.1 left intact
```

## Pubblicare su Kubernetes

Ora che la nostra immagine è pronta e funzionante, distribuiamola su Kubernetes.  

Per distribuire su un cluster non locale, dobbiamo prima eseguire il push su un **Container Registry** — un repository per immagini container.

Se non ne hai già uno, crea un account su [Docker Hub](https://hub.docker.com) e poi esegui il login:

```bash
docker login
```

Quindi, tagga la tua immagine come `your-account/image-name:tag`:

```bash
docker tag fastapi:v1 <your-docker-account>/fastapi:v1
docker push <your-docker-account>/fastapi:v1
```

Distribuiremo il container come un **Deployment**:

```yaml
# manifests/01-fastapi.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
      - name: fastapi
        image: <your-docker-account>/fastapi:v1
        ports:
        - containerPort: 5000
```

> Un **Deployment** è una risorsa Kubernetes che gestisce il ciclo di vita dei Pod della tua applicazione.  
> Garantisce che il numero desiderato di repliche sia sempre in esecuzione, sostituisce automaticamente i Pod falliti e permette aggiornamenti senza downtime tramite rolling deployments.

Applica il manifest:

```bash
k apply -f manifests/01-fastapi.yaml
```

Il deployment dovrebbe creare due ReplicaSet, che a loro volta creeranno due Pod. Verifica che tutti i Pod siano in stato Running:

```bash
k get deploy,rs -o=wide -l=app=fastapi
k get pod -o=wide -l=app=fastapi --watch
```

Per testare se il nostro servizio API funziona, esponiamo la porta `5000` usando un Service di tipo ClusterIP:

```bash
k expose deploy fastapi
```

Annota l’indirizzo IP del servizio:

```bash
k get svc -o=wide -l=app=fastapi
```

🧠 Nota:  
Quando kube-proxy è configurato per usare iptables, esegue una selezione pseudo-casuale degli endpoint in round-robin. Con due Pod di backend, il Pod che risponde a una singola richiesta è effettivamente casuale — ma su molte richieste la distribuzione dovrebbe essere approssimativamente 50/50.

Ora, apri un Pod temporaneo e prova a raggiungere un endpoint, per esempio `/health`:

```bash
k run -it --rm --image=alpine -- sh
apk add curl
curl <service-ip>:5000/health
exit
```

Output previsto:

```bash
/ # curl 192.168.1.4:5000/health
{"status":"ok"}/ #
Session ended, resume using 'kubectl attach sh -c sh -i -t' command when the pod is running
pod "sh" deleted
```

## Pulizia finale

Quando hai finito di sperimentare, puoi rimuovere l’immagine del container:

```bash
docker image rm fastapi:v1
```
