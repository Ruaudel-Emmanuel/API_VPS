#!/bin/bash
# Script de sauvegarde pour API-VPS et les services de monitoring
# Ce script sauvegarde :
# - Les volumes Docker de l'API Gateway
# - Les données de Prometheus et Grafana
# - Les données d'Uptime-Kuma
# - Les fichiers de configuration

# Configuration
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7  # Nombre de jours à conserver les sauvegardes

# Créer le dossier de sauvegarde
mkdir -p "$BACKUP_DIR"

# Fonction pour afficher un message
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Sauvegarder l'API Gateway
log "Sauvegarde de l'API Gateway..."
if [ -d "/home/ubuntu/API-VPS" ]; then
    tar -czvf "$BACKUP_DIR/api-gateway_$DATE.tar.gz" \
        /home/ubuntu/API-VPS/.env \
        /home/ubuntu/API-VPS/whitelist.yaml \
        /home/ubuntu/API-VPS/main.py \
        /home/ubuntu/API-VPS/requirements.txt \
        /home/ubuntu/API-VPS/docker-compose.yml
    log "✅ Sauvegarde de l'API Gateway terminée."
else
    log "⚠️  Dossier /home/ubuntu/API-VPS introuvable."
fi

# Sauvegarder Prometheus + Grafana
log "Sauvegarde de Prometheus et Grafana..."
if [ -d "/opt/monitoring" ]; then
    sudo tar -czvf "$BACKUP_DIR/monitoring_$DATE.tar.gz" \
        /opt/monitoring/prometheus/prometheus.yml \
        /opt/monitoring/docker-compose.yml \
        /opt/monitoring/.env
    
    # Sauvegarder les volumes Docker (nécessite docker)
    if command -v docker &> /dev/null; then
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$BACKUP_DIR:/backup" \
            alpine:latest \
            sh -c "docker exec prometheus pg_dump -U postgres postgres > /backup/prometheus_db_$DATE.sql 2>/dev/null || echo 'Prometheus DB non accessible'"
        
        # Sauvegarder les données Grafana
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$BACKUP_DIR:/backup" \
            alpine:latest \
            sh -c "docker cp grafana:/var/lib/grafana /backup/grafana_data_$DATE 2>/dev/null || echo 'Grafana data non accessible'"
    fi
    log "✅ Sauvegarde de Prometheus et Grafana terminée."
else
    log "⚠️  Dossier /opt/monitoring introuvable."
fi

# Sauvegarder Uptime-Kuma
log "Sauvegarde d'Uptime-Kuma..."
if [ -d "/opt/uptime-kuma" ]; then
    sudo tar -czvf "$BACKUP_DIR/uptime-kuma_$DATE.tar.gz" /opt/uptime-kuma
    log "✅ Sauvegarde d'Uptime-Kuma terminée."
else
    log "⚠️  Dossier /opt/uptime-kuma introuvable."
fi

# Sauvegarder les fichiers de configuration système
log "Sauvegarde des fichiers de configuration système..."
tar -czvf "$BACKUP_DIR/system-config_$DATE.tar.gz" \
    /etc/caddy/Caddyfile \
    /home/ubuntu/ORDRES.md \
    /home/ubuntu/ETAT-VPS.md
log "✅ Sauvegarde des fichiers système terminée."

# Nettoyer les anciennes sauvegardes
log "Nettoyage des sauvegardes de plus de $RETENTION_DAYS jours..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete
log "✅ Nettoyage terminé."

# Afficher un résumé
log "=== Résumé des sauvegardes ==="
ls -lh "$BACKUP_DIR" | grep "_$DATE" | awk '{print $9, $5}'
log "=== Sauvegarde terminée ==="
