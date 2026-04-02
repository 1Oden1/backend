#!/usr/bin/env bash
# ================================================================
#  ENT Salé — Script de déploiement Kubernetes (Helm)
#  Usage : ./deploy.sh [install|upgrade|uninstall|status|logs]
#
#  Prérequis :
#    - kubectl configuré et connecté au cluster
#    - helm 3.x installé
#    - metrics-server déployé (pour HPA)
#    - nginx-ingress-controller déployé
# ================================================================
set -euo pipefail

# ── Configuration ───────────────────────────────────────────
RELEASE_NAME="ent"
CHART_DIR="./ent-chart"
NAMESPACE="ent-sale"
DOMAIN="${ENT_DOMAIN:-ent.est-sale.ma}"
VALUES_FILE="./ent-chart/values.yaml"
VALUES_OVERRIDE="${VALUES_OVERRIDE:-}"   # chemin vers un fichier values custom optionnel

# Couleurs terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Fonctions utilitaires ────────────────────────────────────
log()     { echo -e "${BLUE}[ENT]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }
header()  { echo -e "\n${CYAN}══════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════════${NC}\n"; }

# ── Vérifications préalables ─────────────────────────────────
check_prerequisites() {
  header "Vérification des prérequis"

  command -v kubectl >/dev/null 2>&1 || error "kubectl non trouvé. Installez kubectl."
  command -v helm    >/dev/null 2>&1 || error "helm non trouvé. Installez helm 3.x."

  # Vérifier la connexion au cluster
  kubectl cluster-info >/dev/null 2>&1 || error "Impossible de contacter le cluster Kubernetes."
  success "Cluster Kubernetes accessible"

  # Vérifier metrics-server pour HPA
  if ! kubectl get deployment metrics-server -n kube-system >/dev/null 2>&1; then
    warn "metrics-server non détecté — le HPA ne fonctionnera pas."
    warn "Installation : kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
  else
    success "metrics-server détecté"
  fi

  # Vérifier ingress-nginx
  if ! kubectl get ingressclass nginx >/dev/null 2>&1; then
    warn "IngressClass 'nginx' non trouvée."
    warn "Installation : helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace"
  else
    success "nginx-ingress-controller détecté"
  fi
}

# ── Ajout des repos Helm Bitnami ─────────────────────────────
add_helm_repos() {
  header "Ajout des dépôts Helm"
  helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
  helm repo update
  success "Dépôts Helm à jour"
}

# ── Build des dépendances ─────────────────────────────────────
build_dependencies() {
  header "Résolution des dépendances Helm (MySQL, Cassandra, RabbitMQ, MinIO)"
  helm dependency build "$CHART_DIR"
  success "Dépendances résolues"
}

# ── Import realm Keycloak ─────────────────────────────────────
import_keycloak_realm() {
  local realm_file="./ms-auth/keycloak/realm-export.json"
  if [ -f "$realm_file" ]; then
    log "Import du realm Keycloak..."
    kubectl create configmap keycloak-realm-config \
      --from-file=realm-export.json="$realm_file" \
      -n "$NAMESPACE" \
      --dry-run=client -o yaml | kubectl apply -f -
    success "Realm Keycloak importé"
  else
    warn "Fichier realm-export.json non trouvé — Keycloak démarrera sans realm pré-configuré."
    warn "Chemin attendu : $realm_file"
  fi
}

# ── Build des images Docker locales ──────────────────────────
build_images() {
  header "Build des images Docker des microservices"

  declare -A SERVICES=(
    ["ms-auth"]="ent/ms-auth:latest"
    ["ms-upload"]="ent/ms-upload:latest"
    ["ms-download"]="ent/ms-download:latest"
    ["ms-calendar"]="ent/ms-calendar:latest"
    ["ms-notes"]="ent/ms-notes:latest"
    ["ms-admin"]="ent/ms-admin:latest"
    ["ms-messaging"]="ent/ms-messaging:latest"
    ["ms-ia"]="ent/ms-ia:latest"
    ["frontend"]="ent/frontend:latest"
  )

  for svc in "${!SERVICES[@]}"; do
    local img="${SERVICES[$svc]}"
    local ctx="./$svc"

    if [ "$svc" = "frontend" ]; then
      ctx="./frontend"
    fi

    if [ -d "$ctx" ] && [ -f "$ctx/Dockerfile" ]; then
      log "Build $img..."
      docker build -t "$img" "$ctx"
      success "$img construit"
    else
      warn "Dockerfile introuvable pour $svc ($ctx) — image skippée"
    fi
  done
}

# ── Commande helm install/upgrade ────────────────────────────
helm_deploy() {
  local action="$1"   # install | upgrade

  local helm_args=(
    "$action"
    "$RELEASE_NAME"
    "$CHART_DIR"
    --namespace "$NAMESPACE"
    --create-namespace
    --set "global.domain=$DOMAIN"
    --timeout 10m
    --wait
    --atomic
  )

  if [ -n "$VALUES_OVERRIDE" ] && [ -f "$VALUES_OVERRIDE" ]; then
    helm_args+=(-f "$VALUES_OVERRIDE")
    log "Values override : $VALUES_OVERRIDE"
  fi

  if [ "$action" = "upgrade" ]; then
    helm_args+=(--install)   # upgrade --install = upsert
  fi

  log "Lancement : helm ${helm_args[*]}"
  helm "${helm_args[@]}"
}

# ── Attendre que tous les pods soient Ready ───────────────────
wait_for_pods() {
  header "Attente de la disponibilité des pods"
  log "Timeout : 10 minutes"

  kubectl wait pods \
    --all \
    --for=condition=Ready \
    --namespace="$NAMESPACE" \
    --timeout=600s

  success "Tous les pods sont Ready"
}

# ── Afficher le résumé post-déploiement ──────────────────────
show_status() {
  header "État du déploiement ENT Salé"

  echo ""
  log "Pods :"
  kubectl get pods -n "$NAMESPACE" -o wide
  echo ""
  log "Services :"
  kubectl get svc -n "$NAMESPACE"
  echo ""
  log "HPA (Horizontal Pod Autoscalers) :"
  kubectl get hpa -n "$NAMESPACE"
  echo ""
  log "Ingress :"
  kubectl get ingress -n "$NAMESPACE"
  echo ""

  INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "N/A")

  success "Déploiement terminé !"
  echo ""
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "  🌐  ENT :            http://${DOMAIN}"
  echo -e "  🔑  Keycloak Admin : http://${DOMAIN}/auth/admin/"
  echo -e "  📡  Ingress IP :     ${INGRESS_IP}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "  Pour surveiller le scaling :"
  echo -e "  ${YELLOW}watch kubectl get hpa -n $NAMESPACE${NC}"
  echo ""
}

# ── Désinstallation complète ──────────────────────────────────
uninstall() {
  header "Désinstallation de l'ENT"
  warn "Cette action supprime tous les pods et services (pas les PVCs)."
  read -rp "Confirmer la désinstallation ? [oui/NON] " confirm
  if [ "$confirm" = "oui" ]; then
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || true
    success "Release Helm supprimée"

    read -rp "Supprimer aussi le namespace $NAMESPACE ? [oui/NON] " confirm2
    if [ "$confirm2" = "oui" ]; then
      kubectl delete namespace "$NAMESPACE" --ignore-not-found
      success "Namespace supprimé"
    fi
  else
    log "Annulé."
  fi
}

# ── Afficher les logs d'un service ───────────────────────────
show_logs() {
  local svc="${1:-ms-auth}"
  log "Logs de $svc (Ctrl+C pour quitter) :"
  kubectl logs -n "$NAMESPACE" -l "app.kubernetes.io/name=$svc" --tail=100 -f
}

# ── MAIN ─────────────────────────────────────────────────────
ACTION="${1:-install}"

case "$ACTION" in

  install)
    header "🚀 Installation ENT Salé sur Kubernetes"
    check_prerequisites
    add_helm_repos
    build_dependencies
    build_images
    import_keycloak_realm
    helm_deploy install
    wait_for_pods
    show_status
    ;;

  upgrade)
    header "🔄 Mise à jour ENT Salé"
    check_prerequisites
    build_dependencies
    build_images
    import_keycloak_realm
    helm_deploy upgrade
    wait_for_pods
    show_status
    ;;

  uninstall|delete)
    uninstall
    ;;

  status)
    show_status
    ;;

  logs)
    show_logs "${2:-ms-auth}"
    ;;

  build-only)
    header "🔨 Build des images uniquement"
    build_images
    ;;

  deps)
    add_helm_repos
    build_dependencies
    ;;

  *)
    echo ""
    echo "Usage : $0 [commande]"
    echo ""
    echo "Commandes disponibles :"
    echo "  install     — Premier déploiement complet (défaut)"
    echo "  upgrade     — Mise à jour d'un déploiement existant"
    echo "  uninstall   — Suppression de la release Helm"
    echo "  status      — Afficher l'état des pods, HPAs, Ingress"
    echo "  logs [svc]  — Afficher les logs d'un microservice"
    echo "  build-only  — Builder les images Docker sans déployer"
    echo "  deps        — Mettre à jour les dépendances Helm"
    echo ""
    echo "Variables d'environnement :"
    echo "  ENT_DOMAIN=ent.est-sale.ma    # domaine de déploiement"
    echo "  VALUES_OVERRIDE=./my.yaml     # fichier values personnalisé"
    echo ""
    ;;
esac
