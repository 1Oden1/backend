# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ENT Salé — Makefile (raccourcis de commandes)                          ║
# ║  Usage : make <cible>                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

.PHONY: help up down build logs ps health clean purge pull-model setup

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m

help: ## Affiche cette aide
	@echo ""
	@echo "$(GREEN)ENT Salé — Commandes disponibles$(NC)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## Premier démarrage : crée .env et lance tout
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)️  Fichier .env créé depuis .env.example$(NC)"; \
		echo "$(YELLOW)   Éditez .env avant de continuer !$(NC)"; \
		exit 1; \
	fi
	@$(MAKE) up

up: ## Lance toute la plateforme
	@echo "$(GREEN) Démarrage de l'ENT Salé...$(NC)"
	docker compose up -d
	@echo "$(GREEN) Plateforme démarrée. Interface : http://localhost:3000$(NC)"

up-infra: ## Lance uniquement l'infrastructure (sans les microservices)
	docker compose up -d mysql cassandra minio rabbitmq keycloak

up-dev: ## Lance en mode développement (avec logs en direct)
	docker compose up

down: ## Arrête tous les services
	@echo "$(YELLOW) Arrêt de l'ENT Salé...$(NC)"
	docker compose down

build: ## Reconstruit toutes les images Docker
	@echo "$(GREEN) Build de toutes les images...$(NC)"
	docker compose build --parallel

build-no-cache: ## Reconstruit toutes les images sans cache
	docker compose build --no-cache --parallel

logs: ## Affiche les logs en temps réel (Ctrl+C pour quitter)
	docker compose logs -f --tail=50

logs-ms: ## Logs d'un microservice spécifique (make logs-ms MS=ms-auth)
	docker compose logs -f --tail=100 $(MS)

ps: ## Affiche l'état de tous les conteneurs
	docker compose ps

health: ## Vérifie la santé de tous les services
	@echo "$(GREEN) Health-check des services...$(NC)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@for port in 8001 8002 8003 8004 8005 8006 8007 8008 3000; do \
		name=$$(case $$port in \
			8001) echo "ms-auth";      ;; 8002) echo "ms-upload";    ;; \
			8003) echo "ms-download";  ;; 8004) echo "ms-calendar";  ;; \
			8005) echo "ms-notes";     ;; 8006) echo "ms-admin";     ;; \
			8007) echo "ms-messaging"; ;; 8008) echo "ms-ia";        ;; \
			3000) echo "frontend";     ;; esac); \
		if curl -sf --max-time 5 http://localhost:$$port/health > /dev/null 2>&1; then \
			printf "  $(GREEN) %-15s$(NC) http://localhost:$$port/health\n" $$name; \
		else \
			printf "  $(RED) %-15s$(NC) http://localhost:$$port/health\n" $$name; \
		fi; \
	done
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

pull-model: ## Télécharge le modèle LLM Ollama (llama3 par défaut)
	@echo "$(GREEN) Téléchargement du modèle Ollama...$(NC)"
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-llama3}

restart: ## Redémarre un service spécifique (make restart SVC=ms-auth)
	docker compose restart $(SVC)

clean: ## Supprime les conteneurs et les images obsolètes
	@echo "$(YELLOW) Nettoyage...$(NC)"
	docker compose down --remove-orphans
	docker image prune -f
	docker network prune -f

purge: ## ️  SUPPRIME TOUT y compris les volumes (données perdues !)
	@echo "$(RED)️  ATTENTION : Cette commande supprime TOUTES les données !$(NC)"
	@read -p "Confirmer (yes/no) : " ans && [ "$$ans" = "yes" ] || exit 1
	docker compose down -v --remove-orphans
	docker volume rm ent_mysql_data ent_cassandra_data ent_minio_data \
	                 ent_rabbitmq_data ent_ollama_data 2>/dev/null || true
	docker image prune -af

migrate: ## Applique les migrations Alembic (ms-calendar & ms-notes)
	docker compose exec ms-calendar alembic upgrade head
	docker compose exec ms-notes     alembic upgrade head

shell: ## Ouvre un shell dans un conteneur (make shell SVC=ms-auth)
	docker compose exec $(SVC) bash || docker compose exec $(SVC) sh

db-shell: ## Ouvre un shell MySQL
	docker compose exec mysql mysql -u$${MYSQL_USER:-ent_user} -p$${MYSQL_PASSWORD:-ent_password}

minio-console: ## Affiche l'URL de la console MinIO
	@echo "$(GREEN)MinIO Console : http://localhost:9001$(NC)"
	@echo "  User : $$(grep MINIO_ACCESS_KEY .env | cut -d= -f2)"
	@echo "  Pass : $$(grep MINIO_SECRET_KEY .env | cut -d= -f2)"

rabbitmq-console: ## Affiche l'URL de la console RabbitMQ
	@echo "$(GREEN)RabbitMQ Console : http://localhost:15672$(NC)"

keycloak-console: ## Affiche l'URL de la console Keycloak
	@echo "$(GREEN)Keycloak Admin : http://localhost:8080/admin$(NC)"

tag: ## Crée un tag git pour déclencher le déploiement (make tag VERSION=v1.2.3)
	@[ -n "$(VERSION)" ] || (echo "$(RED)VERSION requis : make tag VERSION=v1.2.3$(NC)"; exit 1)
	git tag -a $(VERSION) -m "Release $(VERSION)"
	git push origin $(VERSION)
	@echo "$(GREEN) Tag $(VERSION) poussé — déploiement déclenché$(NC)"
