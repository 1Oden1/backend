#!/usr/bin/env bash
# ================================================================
#  ENT Salé — Setup complet
#  Usage : ./setup.sh
# ================================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()     { echo -e "${CYAN}[ENT]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

# ── 1. Vérifier qu'on est dans le bon dossier ────────────────
[ -f "ent-k8s.yaml" ] || error "Lance ce script depuis le dossier PFE/ où se trouve ent-k8s.yaml"

# ── 2. Demander les mots de passe ────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Configuration des mots de passe ENT     ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

read -rp "MySQL root password     : " MYSQL_ROOT
read -rp "MySQL user password     : " MYSQL_PASS
read -rp "Keycloak admin password : " KC_ADMIN
read -rp "MinIO access key        : " MINIO_KEY
read -rp "MinIO secret key        : " MINIO_SECRET
read -rp "RabbitMQ password       : " RABBIT_PASS
read -rp "Internal token (chaine aleatoire longue) : " INTERNAL_TOKEN

# ── 3. Injecter les mots de passe dans ent-k8s.yaml ─────────
log "Injection des mots de passe..."
cp ent-k8s.yaml ent-k8s-deployed.yaml

sed -i "s|CHANGE_ME_MYSQL_ROOT|${MYSQL_ROOT}|g"         ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_MYSQL_PASS|${MYSQL_PASS}|g"         ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_KC_ADMIN|${KC_ADMIN}|g"             ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_KC_SECRET|changeme|g"               ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_MINIO_KEY|${MINIO_KEY}|g"           ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_MINIO_SECRET|${MINIO_SECRET}|g"     ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_RABBIT_PASS|${RABBIT_PASS}|g"       ent-k8s-deployed.yaml
sed -i "s|CHANGE_ME_INTERNAL_TOKEN|${INTERNAL_TOKEN}|g" ent-k8s-deployed.yaml
success "Mots de passe injectés"

# ── 4. Rebuild des images Docker ─────────────────────────────
echo ""
log "Build des images Docker..."

for svc in ms-auth ms-upload ms-download ms-calendar ms-notes ms-admin ms-messaging ms-ia; do
  if [ -d "./$svc" ] && [ -f "./$svc/Dockerfile" ]; then
    log "Build ent/$svc:latest..."
    docker build -t ent/$svc:latest ./$svc
    success "ent/$svc:latest construit"
  else
    warn "Dockerfile manquant pour $svc — skip"
  fi
done

# Frontend
if [ -d "./frontend" ] && [ -f "./frontend/Dockerfile" ]; then
  log "Build ent/frontend:latest..."
  docker build -t ent/frontend:latest ./frontend
  success "ent/frontend:latest construit"
fi

# ── 5. Import dans k3s ───────────────────────────────────────
echo ""
log "Import des images dans k3s..."

for svc in ms-auth ms-upload ms-download ms-calendar ms-notes ms-admin ms-messaging ms-ia; do
  log "Import ent/$svc..."
  docker save ent/$svc:latest | sudo k3s ctr images import -
done
docker save ent/frontend:latest | sudo k3s ctr images import -
success "Toutes les images importées"

# ── 6. Import realm Keycloak ─────────────────────────────────
REALM_FILE="./ms-auth/keycloak/realm-export.json"
if [ -f "$REALM_FILE" ]; then
  log "Préparation realm Keycloak..."
  # Sera appliqué après kubectl apply
  IMPORT_REALM=true
else
  warn "realm-export.json non trouvé — Keycloak démarrera sans realm"
  IMPORT_REALM=false
fi

# ── 7. Déployer ──────────────────────────────────────────────
echo ""
log "Déploiement Kubernetes..."
kubectl apply -f ent-k8s-deployed.yaml
success "Ressources Kubernetes créées"

# ── 8. Import realm après création du namespace ───────────────
if [ "$IMPORT_REALM" = true ]; then
  log "Import du realm Keycloak..."
  kubectl create configmap keycloak-realm-config \
    --from-file=realm-export.json="$REALM_FILE" \
    -n ent-sale \
    --dry-run=client -o yaml | kubectl apply -f -
  success "Realm Keycloak importé"
fi

# ── 9. Résumé ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Déploiement lancé !                     ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""
echo "  Surveille les pods :"
echo -e "  ${YELLOW}watch kubectl get pods -n ent-sale${NC}"
echo ""

SERVER_IP=$(hostname -I | awk '{print $1}')
echo "  Accès ENT (dans 3-5 min) :"
echo -e "  ${GREEN}http://${SERVER_IP}/login/${NC}"
echo ""
echo "  Keycloak admin :"
echo -e "  ${GREEN}http://${SERVER_IP}:8080/admin/${NC}"
echo ""
