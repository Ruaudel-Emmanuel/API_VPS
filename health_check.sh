#!/bin/bash
# Script de vérification de santé pour API-VPS
# Ce script vérifie que tous les services critiques sont opérationnels.
# Retourne un code de sortie 0 si tout est OK, 1 sinon.

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher un message
log() {
    echo -e "${BLUE}[HEALTH CHECK]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Initialisation
ALL_HEALTHY=true

# 1. Vérifier Docker
log "Vérification de Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé."
    ALL_HEALTHY=false
else
    if ! docker ps &> /dev/null; then
        log_error "Docker n'est pas en cours d'exécution."
        ALL_HEALTHY=false
    else
        log_success "Docker est opérationnel."
    fi
fi

# 2. Vérifier les conteneurs critiques
log "Vérification des conteneurs..."
CONTAINERS=("vps-api-gateway" "grafana" "prometheus" "uptime-kuma" "n8n_db")
for container in "${CONTAINERS[@]}"; do
    if docker ps | grep -q "$container"; then
        log_success "$container est en cours d'exécution."
    else
        log_error "$container n'est pas en cours d'exécution."
        ALL_HEALTHY=false
    fi
done

# 3. Vérifier les ports
log "Vérification des ports..."
PORTS=("8000" "3000" "9090" "3001")
for port in "${PORTS[@]}"; do
    if sudo ss -tulnp | grep -q "100.75.226.13:$port"; then
        log_success "Port $port est ouvert (Tailscale)."
    else
        log_error "Port $port n'est pas ouvert."
        ALL_HEALTHY=false
    fi
done

# 4. Vérifier l'API Gateway
log "Vérification de l'API Gateway..."
if curl -s http://100.75.226.13:8000/v1/health | grep -q '"status": "healthy"'; then
    log_success "API Gateway répond correctement."
else
    log_error "API Gateway ne répond pas correctement."
    ALL_HEALTHY=false
fi

# 5. Vérifier Grafana
log "Vérification de Grafana..."
if curl -s http://100.75.226.13:3000 | grep -q "Grafana"; then
    log_success "Grafana répond correctement."
else
    log_error "Grafana ne répond pas correctement."
    ALL_HEALTHY=false
fi

# 6. Vérifier Prometheus
log "Vérification de Prometheus..."
if curl -s http://100.75.226.13:9090 | grep -q "Prometheus"; then
    log_success "Prometheus répond correctement."
else
    log_error "Prometheus ne répond pas correctement."
    ALL_HEALTHY=false
fi

# 7. Vérifier Uptime-Kuma
log "Vérification d'Uptime-Kuma..."
if curl -s http://100.75.226.13:3001 | grep -q "Uptime Kuma"; then
    log_success "Uptime-Kuma répond correctement."
else
    log_error "Uptime-Kuma ne répond pas correctement."
    ALL_HEALTHY=false
fi

# 8. Vérifier PostgreSQL (n8n_db)
log "Vérification de PostgreSQL (n8n_db)..."
if docker exec n8n_db pg_isready -U n8n -d n8n_db &> /dev/null; then
    log_success "PostgreSQL (n8n_db) est accessible."
else
    log_error "PostgreSQL (n8n_db) n'est pas accessible."
    ALL_HEALTHY=false
fi

# 9. Vérifier la connexion à l'API Gateway depuis le VPS
log "Vérification de la connectivité locale..."
if curl -s http://localhost:8000/v1/health | grep -q '"status": "healthy"'; then
    log_success "API Gateway est accessible localement."
else
    log_warning "API Gateway n'est pas accessible localement (mais peut être OK si lié uniquement à Tailscale)."
fi

# Résumé
log ""
if [ "$ALL_HEALTHY" = true ]; then
    log_success "Tous les services sont en bonne santé !"
    exit 0
else
    log_error "Certains services ne sont pas en bonne santé."
    exit 1
fi
