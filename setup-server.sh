#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ENT Salé — Script d'installation initiale (serveur Ubuntu 24.10)       ║
# ║  Usage : sudo bash setup-server.sh                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

INSTALL_DIR="/opt/ent-sale"
GITHUB_REPO="https://github.com/1Oden1/backend/tree/kader.git"   # ← MODIFIER
DEPLOY_USER="ent-deploy"                                    # ← utilisateur dédié

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "️  Installation ENT Salé sur $(hostname)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Mise à jour système ───────────────────────────────────────────────────────
echo " Mise à jour des paquets..."
apt-get update -qq && apt-get upgrade -y -qq

# ── Docker Engine ─────────────────────────────────────────────────────────────
echo " Installation Docker Engine..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | bash
  systemctl enable docker
  systemctl start docker
fi

# Docker Compose plugin
if ! docker compose version &> /dev/null; then
  apt-get install -y docker-compose-plugin
fi

echo "  Docker  : $(docker --version)"
echo "  Compose : $(docker compose version)"

# ── Utilisateur de déploiement ────────────────────────────────────────────────
if ! id "$DEPLOY_USER" &> /dev/null; then
  echo " Création de l'utilisateur $DEPLOY_USER..."
  useradd -m -s /bin/bash "$DEPLOY_USER"
  usermod -aG docker "$DEPLOY_USER"
fi

# ── Répertoire d'installation ─────────────────────────────────────────────────
echo " Préparation du répertoire $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$INSTALL_DIR"

# ── Configuration SSH pour le déploiement ────────────────────────────────────
SSH_DIR="/home/$DEPLOY_USER/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$SSH_DIR/authorized_keys"
chmod 600 "$SSH_DIR/authorized_keys"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$SSH_DIR"

echo ""
echo "️  ÉTAPE MANUELLE REQUISE :"
echo "   Ajoutez la clé publique SSH GitHub Actions dans :"
echo "   $SSH_DIR/authorized_keys"
echo ""
echo "   La clé publique est stockée dans le secret GitHub : PROD_SSH_KEY_PUB"
echo ""

# ── Copier les fichiers de base ───────────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/docker-compose.yml" ]; then
  echo " Clonage du dépôt..."
  git clone "$GITHUB_REPO" /tmp/ent-clone 2>/dev/null || true
  if [ -d /tmp/ent-clone ]; then
    cp /tmp/ent-clone/docker-compose.yml "$INSTALL_DIR/"
    cp /tmp/ent-clone/.env.example        "$INSTALL_DIR/"
    rm -rf /tmp/ent-clone
  fi
fi

# ── Fichier .env ──────────────────────────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
  echo ""
  echo "️  Créez le fichier .env :"
  echo "   cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env"
  echo "   nano $INSTALL_DIR/.env"
  echo ""
fi

# ── Service systemd (optionnel — redémarre automatiquement au boot) ───────────
cat > /etc/systemd/system/ent-sale.service << EOF
[Unit]
Description=ENT Salé — Plateforme numérique de travail
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ent-sale

# ── Firewall (UFW) ────────────────────────────────────────────────────────────
if command -v ufw &> /dev/null; then
  echo " Configuration du firewall..."
  ufw allow ssh
  ufw allow 80/tcp    comment "Frontend HTTP"
  ufw allow 443/tcp   comment "Frontend HTTPS"
  ufw allow 3000/tcp  comment "Frontend direct"
  ufw allow 8080/tcp  comment "Keycloak"
  # Ports internes — accès restreint au réseau local uniquement
  # ufw allow from 10.0.0.0/8 to any port 9000  comment "MinIO"
  # ufw allow from 10.0.0.0/8 to any port 15672 comment "RabbitMQ Console"
  ufw --force enable
  echo "  UFW activé."
fi

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Installation terminée !"
echo ""
echo " PROCHAINES ÉTAPES :"
echo "  1. Éditez  $INSTALL_DIR/.env  avec vos valeurs de production"
echo "  2. Ajoutez la clé SSH dans $SSH_DIR/authorized_keys"
echo "  3. Configurez les secrets GitHub Actions :"
echo "     - PROD_HOST       → $(hostname -I | awk '{print $1}')"
echo "     - PROD_USER       → $DEPLOY_USER"
echo "     - PROD_SSH_KEY    → contenu de votre clé privée SSH"
echo "     - PROD_SSH_PORT   → 22 (ou votre port SSH)"
echo "     - SLACK_WEBHOOK_URL → (optionnel)"
echo "  4. Premier lancement : cd $INSTALL_DIR && docker compose up -d"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
