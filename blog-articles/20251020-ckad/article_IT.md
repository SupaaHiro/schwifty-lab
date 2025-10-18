# Testare le NetworkPolicy di Kubernetes

## Introduzione

Negli ultimi giorni, in vista del rinnovo della CKAD, ho deciso di ripassare alcuni concetti fondamentali di Kubernetes.
Per tenere traccia degli esperimenti, ho iniziato a pubblicare una serie di esercizi pratici su questo tema.
In futuro tutto il materiale confluirà nel mio blog personale — non appena, tempo permettendo, riuscirò a completarne la pubblicazione.

In questo primo esercizio creeremo due Pod per testare una NetworkPolicy di tipo Ingress.

## Prerequisiti

⚠️ Importante:
Verifica che il tuo cluster Kubernetes sia configurato con un plugin CNI che implementi le NetworkPolicy. In assenza di tale supporto, le policy definite verranno semplicemente ignorate. Io ho effettuato alcuni test in locale con Kubernetes su Docker Desktop e con minikube, ma nessuno dei due le supporta nativamente. Alla fine ho optato per un ambiente temporaneo su [KillerCoda Playgrounds](https://killercoda.com/playgrounds)

## Come ottenere le risorse

Puoi trovare tutte le risorse utilizzate in questo articolo clonando il repository:

```yaml
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/blog-articles/20251020-ckad
```

## Creazione del Pod Redis

Per capire come funzionano le NetworkPolicy, dobbiamo creare un paio di pod. Ecco il primo:

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

Questo pod crea un istanza di redis in ascolto sulla porta 6379.

Applichiamo il manifest:
```bash
k create -f manifests/01-redis.yaml
```

Verifichiamo che il Pod raggiunga lo stato Running:

```bash
k get pod -o=wide -l=app=redis --watch
```

## Creazione del Service

Per rendere Redis accessibile agli altri Pod, creiamo un Service di tipo ClusterIP.

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

Applichiamo il manifest:

```bash
k create -f manifests/02-redis-svc.yaml
```

Una volta applicato, controlliamo che l’endpoint sia correttamente popolato con:

```bash
k get svc -l=app=redis -o=wide
k describe svc redis
```

Esempio di output:

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

## Script di test della connettività

Per verificare la connettività verso Redis useremo un semplice script Python.

Lo script tenta di connettersi al servizio Redis e stampa un messaggio di successo o di errore, con un timeout configurabile (default 10 secondi).

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

Per evitare di creare un'immagine Docker dedicata, monteremo lo script come volume tramite una ConfigMap:

```bash
k create cm test-redis-ping --from-file=test-redis-ping.py=./src/test-redis-ping.py
```

## Creazione del Pod Client

Definiamo un Pod chiamato redis-client, basato su python:3.12-alpine.
Il container installerà la libreria redis al volo e poi eseguirà lo script montato dalla ConfigMap.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis-client
  labels:
    app: redis-client
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

Applichiamo il manifest:

```bash
k create -f manifests/03-redis-client.yaml
```

Attendiamo che il Pod sia Running e controlliamo i log:

```bash
k get pod -o=wide -l=app=redis-client --watch
k logs redis-client
```

Se tutto funziona, dovremmo vedere:

```text
✅ Connected to Redis at redis:6379
```

## Definizione delle NetworkPolicy

Creiamo due NetworkPolicy:

- default-deny-ingress — blocca tutto il traffico in ingresso per impostazione predefinita.
- redis-access — consente l’accesso al Pod Redis solo ai Pod che hanno la label access: redis.

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

Applichiamo il manifest:

```bash
k create -f manifests/04-netpol.yaml
```

Dopo l'applicazione, la policy redis-access agirà come un “recinto” attorno ai Pod con label app=redis, permettendo connessioni solo dai Pod etichettati con access=redis.

## Test della connessione bloccata

Attualmente il Pod redis-client non possiede la label access: redis, quindi la connessione dovrebbe fallire.

Rimuoviamo e ricreiamo il Pod, poi controlliamo i log:

```bash
k replace -f manifests/03-redis-client.yaml --force
k logs redis-client
```

Il risultato atteso è un errore di timeout:

```text
❌ Failed to connect to Redis: Timeout connecting to server
```

Nota: l’errore può impiegare qualche secondo a comparire nei log.

## Abilitare l’accesso tramite label

Aggiungiamo la label mancante access: redis al manifest del Pod redis-client e lo ricreiamo:

```bash
yq e '.metadata.labels.access = "redis"' -i manifests/03-redis-client.yaml
k replace -f manifests/03-redis-client.yaml --force
```

Dopo il deploy, la connessione dovrebbe tornare a funzionare correttamente:

```text
✅ Connected to Redis at redis:6379
```

## Pulizia finale

Quando hai terminato gli esperimenti, rimuovi tutte le risorse create (Pod, Service e NetworkPolicy) per ripulire l’ambiente:

```bash
k delete svc redis
k delete netpol default-deny-ingress redis-access
k delete po redis redis-client
```
