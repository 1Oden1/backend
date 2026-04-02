# ENT Salé — Helm Chart Kubernetes

Déploiement complet de l'Espace Numérique de Travail (ENT) de l'EST Salé  
sur Kubernetes via un seul chart Helm.

---

## Architecture déployée

```
Cluster Kubernetes  /  Namespace: ent-sale
│
├── Ingress (nginx)          ← point d'entrée unique
│     └── ent.est-sale.ma
│           ├── /             → frontend (Nginx)
│           ├── /auth         → Keycloak :8080
│           ├── /api/v1/auth  → ms-auth  :8001
│           ├── /api/v1/upload    → ms-upload    :8002
│           ├── /api/v1/download  → ms-download  :8003
│           ├── /api/v1/calendar  → ms-calendar  :8004
│           ├── /api/v1/notes     → ms-notes     :8005
│           ├── /api/v1/admin     → ms-admin     :8006
│           ├── /api/v1/messaging → ms-messaging :8007
│           └── /api/v1/ia        → ms-ia        :8008
│
├── Microservices FastAPI (Deployments)
│     HPA activé sur chaque service (CPU + Mémoire)
│
├── Infrastructure (Bitnami sub-charts)
│     ├── MySQL 8.0         (bases: keycloak, ent_calendar, ent_notes)
│     ├── Cassandra 4.1     (keyspaces: ent_files, ent_messaging)
│     ├── RabbitMQ 3.13     (exchange: ent.events)
│     └── MinIO             (bucket: ent-courses)
│
├── Keycloak 25.0           (identity provider, realm ent-sale)
└── Ollama + Llama 3        (IA conversationnelle)
```

---

## Prérequis

| Outil | Version minimale |
|---|---|
| kubectl | 1.27+ |
| helm | 3.12+ |
| Docker | 24+ |
| metrics-server | installé dans le cluster |
| nginx-ingress-controller | installé dans le cluster |

### Installer metrics-server (pour le HPA)
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Installer nginx-ingress-controller
```bash
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace
```

---

## Déploiement en une seule commande

```bash
# Rendre le script exécutable
chmod +x ent-chart/deploy.sh

# Déploiement complet (build images + helm install)
./ent-chart/deploy.sh install
```

Le script effectue automatiquement :
1. Vérification des prérequis (kubectl, helm, metrics-server, ingress)
2. Ajout des repos Bitnami
3. Build des dépendances Helm
4. Build des images Docker de chaque microservice
5. Import du realm Keycloak
6. `helm install` avec attente de disponibilité des pods
7. Affichage du résumé (pods, HPA, Ingress, URL)

---

## Commandes disponibles

```bash
./deploy.sh install      # Premier déploiement complet
./deploy.sh upgrade      # Mise à jour d'un déploiement existant
./deploy.sh status       # État des pods, HPAs, Ingress
./deploy.sh logs ms-ia   # Logs d'un microservice (streaming)
./deploy.sh uninstall    # Suppression de la release
./deploy.sh build-only   # Builder les images sans déployer
./deploy.sh deps         # Mettre à jour les dépendances Helm
```

---

## Scaling automatique (HPA)

Le HPA est configuré sur chaque microservice :

| Service | Min | Max | Seuil CPU | Seuil Mémoire |
|---|---|---|---|---|
| ms-auth | 2 | 6 | 70% | 80% |
| ms-upload | 2 | 6 | 70% | 80% |
| ms-download | 2 | 10 | 70% | 80% |
| ms-calendar | 2 | 8 | 70% | 80% |
| ms-notes | 2 | 8 | 70% | 80% |
| ms-admin | 1 | 3 | 70% | — |
| ms-messaging | 2 | 8 | 70% | 80% |
| ms-ia | 1 | 4 | **80%** | 85% |
| frontend | 2 | 6 | 60% | — |

```bash
# Surveiller le scaling en temps réel
watch kubectl get hpa -n ent-sale
```

---

## Déploiement production

```bash
# Éditer d'abord les mots de passe dans values-production.yaml !
nano ent-chart/values-production.yaml

VALUES_OVERRIDE=./ent-chart/values-production.yaml \
  ENT_DOMAIN=ent.est-sale.ma \
  ./ent-chart/deploy.sh install
```

---

## Structure du chart

```
ent-chart/
├── Chart.yaml                  # Métadonnées + dépendances Bitnami
├── values.yaml                 # Valeurs par défaut
├── values-production.yaml      # Override production
├── deploy.sh                   # Script de déploiement tout-en-un
└── templates/
    ├── _helpers.tpl             # Macros Helm
    ├── NOTES.txt                # Message post-install
    ├── namespace.yaml           # Namespace ent-sale
    ├── secrets.yaml             # Credentials (Secret Kubernetes)
    ├── configmap.yaml           # Config non-sensible + init SQL
    ├── keycloak.yaml            # StatefulSet Keycloak
    ├── ollama.yaml              # StatefulSet Ollama + pull llama3
    ├── microservices.yaml       # 8 Deployments FastAPI + Services
    ├── frontend.yaml            # Deployment Nginx frontend
    ├── hpa.yaml                 # HPA pour chaque service
    ├── ingress.yaml             # Ingress centralisé
    ├── pdb.yaml                 # PodDisruptionBudgets
    ├── networkpolicy.yaml       # Isolation réseau inter-services
    └── serviceaccount.yaml      # RBAC minimal
```

---

## Dépannage

### Pods en état Pending
```bash
kubectl describe pod <pod-name> -n ent-sale
# Souvent : ressources insuffisantes ou PVC non bound
```

### HPA bloqué à "unknown"
```bash
kubectl top pods -n ent-sale
# Si erreur → metrics-server non installé ou pas encore prêt
```

### Keycloak ne démarre pas
```bash
kubectl logs -n ent-sale -l app.kubernetes.io/name=keycloak
# Vérifier que MySQL est healthy avant Keycloak
```

### Ollama lent au premier démarrage
```bash
kubectl logs -n ent-sale -l app.kubernetes.io/name=ollama -c pull-model
# Le pull de llama3:latest (~4.7 Go) prend plusieurs minutes
```
