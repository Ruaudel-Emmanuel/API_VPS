# 🚀 Guide de Déploiement d'API-VPS
# 🚀 API-VPS Deployment Guide

---

## 🌍 Languages / Langues
- **[Français](#-guide-de-déploiement-dapi-vps)**
- **[English](#-api-vps-deployment-guide)**

---

## 🇫🇷 Guide de Déploiement d'API-VPS

### 📌 Prérequis
Avant de commencer, assurez-vous que votre VPS répond aux exigences suivantes :

| Exigence | Version | Vérification |
|----------|---------|--------------|
| **Système d'exploitation** | Ubuntu 22.04/24.04 LTS | `lsb_release -a` |
| **Docker** | 24.x | `docker --version` |
| **Docker Compose** | 2.x | `docker compose version` |
| **Tailscale** | Latest | `tailscale version` |
| **Python** | 3.11+ | `python3 --version` |
| **Git** | Latest | `git --version` |

---

### 📥 Étape 1 : Cloner le Dépôt
```bash
# Cloner le dépôt (remplacez par votre URL GitHub)
git clone https://github.com/VOTRE_NOM/API-VPS.git
cd API-VPS
```

---

### 🛠 Étape 2 : Configurer l'Environnement

#### 1. Créer le fichier `.env`
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Modifier le fichier .env avec vos valeurs
nano .env
```

**Exemple de `.env`** :
```ini
# JWT
JWT_SECRET=vps-gateway-secret-2026-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15

# Base de données
DB_URL=postgresql://n8n:n8n@n8n_db:5432/n8n_db

# Réseau
ALLOWED_ORIGINS=http://localhost,https://n8n.rennesdev.fr
TAILSCALE_IP=100.75.226.13

# Grafana
GRAFANA_ADMIN_PASSWORD=GrafanaAdmin2026!
```

#### 2. Configurer la Whitelist
Modifiez `whitelist.yaml` pour autoriser les ressources nécessaires :
```bash
nano whitelist.yaml
```

**Exemple de `whitelist.yaml`** :
```yaml
users:
  pi-agent:
    scope: ["read:system", "read:db"]
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN", "VPS_GATEWAY_KEY"]
    allowed_file_paths: ["/home/ubuntu/.env", "/etc/caddy/Caddyfile"]
    allowed_db_tables: ["n8n_db.public.workflow_history", "n8n_db.public.executions"]
    masked_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]

tailscale:
  allowed_ips:
    - "100.75.226.13"  # VPS
    - "100.118.76.30"  # PC
    - "fd7a:115c:a1e0::/64"  # Plage IPv6 Tailscale

naming_conventions:
  db:
    schema_pattern: "^[a-z0-9_]+$"
    table_pattern: "^[a-z0-9_]+$"
    column_pattern: "^[a-z0-9_]+$"
```

---

### 🐳 Étape 3 : Déployer l'API Gateway

#### 1. Construire et démarrer les conteneurs
```bash
# Depuis le dossier API-VPS
docker compose build
docker compose up -d
```

#### 2. Vérifier que le conteneur est démarré
```bash
docker ps | grep vps-api-gateway
```

#### 3. Tester l'API Gateway
```bash
# Tester l'endpoint /health
curl http://100.75.226.13:8000/v1/health

# Générer un JWT (pour les tests)
curl -X POST http://100.75.226.13:8000/v1/auth/token

# Tester une requête authentifiée (remplacez <JWT> par le token généré)
curl -H "Authorization: Bearer <JWT>" http://100.75.226.13:8000/v1/system/read_env?key=N8N_DB_PASSWORD
```

---

### 📊 Étape 4 : Déployer le Monitoring (Prometheus + Grafana)

#### 1. Créer le dossier pour le monitoring
```bash
sudo mkdir -p /opt/monitoring/{prometheus,grafana/provisioning/dashboards,grafana/provisioning/datasources}
```

#### 2. Configurer Prometheus
Créez le fichier `prometheus.yml` :
```bash
sudo nano /opt/monitoring/prometheus/prometheus.yml
```

**Contenu de `prometheus.yml`** :
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "api-gateway"
    scrape_interval: 15s
    metrics_path: "/v1/metrics"
    static_configs:
      - targets: ["100.75.226.13:8000"]
    scrape_timeout: 5s

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

#### 3. Configurer Grafana
Créez le fichier `.env` pour Grafana :
```bash
sudo nano /opt/monitoring/.env
```

**Contenu de `.env`** :
```ini
GRAFANA_ADMIN_PASSWORD=GrafanaAdmin2026!
```

Créez le fichier `datasources/prometheus.yml` :
```bash
sudo nano /opt/monitoring/grafana/provisioning/datasources/prometheus.yml
```

**Contenu de `prometheus.yml`** :
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

#### 4. Créer le fichier `docker-compose.yml` pour le monitoring
```bash
sudo nano /opt/monitoring/docker-compose.yml
```

**Contenu de `docker-compose.yml`** :
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "100.75.226.13:9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - apps

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "100.75.226.13:3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - apps

volumes:
  prometheus_data:
  grafana_data:

networks:
  apps:
    external: true
```

#### 5. Démarrer Prometheus et Grafana
```bash
cd /opt/monitoring
docker compose up -d
```

#### 6. Vérifier le monitoring
```bash
# Prometheus
curl http://100.75.226.13:9090

# Grafana
curl http://100.75.226.13:3000
```

---

### 🚨 Étape 5 : Déployer Uptime-Kuma

#### 1. Créer le dossier pour Uptime-Kuma
```bash
sudo mkdir -p /opt/uptime-kuma
```

#### 2. Démarrer Uptime-Kuma
```bash
docker run -d \
  --name uptime-kuma \
  --restart=unless-stopped \
  -p 100.75.226.13:3001:3001 \
  -v /opt/uptime-kuma:/app/data \
  --network=apps \
  louislam/uptime-kuma:latest
```

#### 3. Vérifier Uptime-Kuma
```bash
curl http://100.75.226.13:3001
```

---

### 🔐 Étape 6 : Configurer la Sécurité

#### 1. Désactiver `/v1/auth/token` en production
Une fois que vous avez généré un JWT pour Pi Agent, désactivez l'endpoint `/v1/auth/token` :
```bash
# Éditer main.py et commenter la route /v1/auth/token
nano main.py
```

Cherchez la ligne :
```python
@app.post("/v1/auth/token")
```

Et commentez-la :
```python
# @app.post("/v1/auth/token")
```

Puis redémarrez l'API Gateway :
```bash
cd /home/ubuntu/API-VPS
docker compose down && docker compose up -d
```

#### 2. Générer un JWT pour Pi Agent (avant de désactiver `/v1/auth/token`)
```bash
# Générer un JWT valide 1 an
JWT_TOKEN=$(curl -s -X POST http://100.75.226.13:8000/v1/auth/token | jq -r '.access_token')

# Sauvegarder le JWT dans un fichier sécurisé
echo "$JWT_TOKEN" > /home/ubuntu/API-VPS/pi_agent_jwt.token
chmod 600 /home/ubuntu/API-VPS/pi_agent_jwt.token
```

#### 3. Configurer Pi Agent pour utiliser le JWT
Dans la configuration de Pi Agent, ajoutez :
```yaml
api_gateway:
  url: "http://100.75.226.13:8000/v1"
  jwt_token: "$(cat /home/ubuntu/API-VPS/pi_agent_jwt.token)"
```

---

### 🧪 Étape 7 : Tester le Déploiement

#### 1. Tester l'API Gateway
```bash
# /health
curl http://100.75.226.13:8000/v1/health

# /metrics
curl http://100.75.226.13:8000/v1/metrics

# Requête DB (remplacez <JWT> par votre token)
curl -H "Authorization: Bearer <JWT>" "http://100.75.226.13:8000/v1/system/query_db?table=n8n_db.public.workflow_history&limit=1"
```

#### 2. Tester Grafana
Ouvrez [http://100.75.226.13:3000](http://100.75.226.13:3000) dans un navigateur.
- **Identifiant** : `admin`
- **Mot de passe** : `GrafanaAdmin2026!` (ou celui que vous avez défini dans `.env`).

#### 3. Tester Prometheus
Ouvrez [http://100.75.226.13:9090](http://100.75.226.13:9090) dans un navigateur.

#### 4. Tester Uptime-Kuma
Ouvrez [http://100.75.226.13:3001](http://100.75.226.13:3001) dans un navigateur.
- Ajoutez un monitor pour `http://100.75.226.13:8000/v1/health`.

---

### 📝 Étape 8 : Configurer MagicDNS (Optionnel)
Pour utiliser des noms de domaine internes (ex: `vps-rennesdev.rennesdev.local`) :

1. **Activer MagicDNS** dans [Tailscale Admin](https://login.tailscale.com/admin/dns).
2. **Ajouter un domaine personnalisé** (ex: `rennesdev.local`).
3. **Renommer les appareils** :
   - VPS : `vps-rennesdev`
   - PC : `super-pc-vert`

4. **Tester** :
```bash
curl http://vps-rennesdev.rennesdev.local:8000/v1/health
```

---

### 🔧 Dépannage

#### Problème : Les conteneurs ne démarrent pas
1. **Vérifier les logs** :
   ```bash
   docker logs vps-api-gateway
   docker logs grafana
   docker logs prometheus
   docker logs uptime-kuma
   ```

2. **Vérifier les ports** :
   ```bash
   sudo ss -tulnp | grep -E "8000|3000|3001|9090"
   ```

3. **Vérifier les dépendances** :
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

#### Problème : Conflit de port
Si le port `3000` est déjà utilisé (par `browserless` ou `twenty_server`) :
```bash
# Arrêter les conteneurs en conflit
docker stop browserless twenty_server

# Ou changer le port de Grafana dans /opt/monitoring/docker-compose.yml
# ports:
#   - "100.75.226.13:3002:3000"
```

#### Problème : Connexion à PostgreSQL échouée
1. **Vérifier que `n8n_db` est en cours d'exécution** :
   ```bash
   docker ps | grep n8n_db
   ```

2. **Tester la connexion depuis l'API Gateway** :
   ```bash
   docker exec vps-api-gateway pg_isready -h n8n_db -p 5432 -U n8n -d n8n_db
   ```

3. **Vérifier `DB_URL` dans `.env`** :
   ```ini
   DB_URL=postgresql://n8n:n8n@n8n_db:5432/n8n_db
   ```

---

---

## 🇬🇧 API-VPS Deployment Guide

### 📌 Prerequisites
Before starting, ensure your VPS meets the following requirements:

| Requirement | Version | Check |
|-------------|---------|-------|
| **Operating System** | Ubuntu 22.04/24.04 LTS | `lsb_release -a` |
| **Docker** | 24.x | `docker --version` |
| **Docker Compose** | 2.x | `docker compose version` |
| **Tailscale** | Latest | `tailscale version` |
| **Python** | 3.11+ | `python3 --version` |
| **Git** | Latest | `git --version` |

---

### 📥 Step 1: Clone the Repository
```bash
# Clone the repository (replace with your GitHub URL)
git clone https://github.com/YOUR_GITHUB_USERNAME/API-VPS.git
cd API-VPS
```

---

### 🛠 Step 2: Configure the Environment

#### 1. Create the `.env` File
```bash
# Copy the example file
cp .env.example .env

# Edit the .env file with your values
nano .env
```

**Example `.env`**:
```ini
# JWT
JWT_SECRET=vps-gateway-secret-2026-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15

# Database
DB_URL=postgresql://n8n:n8n@n8n_db:5432/n8n_db

# Network
ALLOWED_ORIGINS=http://localhost,https://n8n.rennesdev.fr
TAILSCALE_IP=100.75.226.13

# Grafana
GRAFANA_ADMIN_PASSWORD=GrafanaAdmin2026!
```

#### 2. Configure the Whitelist
Edit `whitelist.yaml` to allow the necessary resources:
```bash
nano whitelist.yaml
```

**Example `whitelist.yaml`**:
```yaml
users:
  pi-agent:
    scope: ["read:system", "read:db"]
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN", "VPS_GATEWAY_KEY"]
    allowed_file_paths: ["/home/ubuntu/.env", "/etc/caddy/Caddyfile"]
    allowed_db_tables: ["n8n_db.public.workflow_history", "n8n_db.public.executions"]
    masked_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]

tailscale:
  allowed_ips:
    - "100.75.226.13"  # VPS
    - "100.118.76.30"  # PC
    - "fd7a:115c:a1e0::/64"  # Tailscale IPv6 range

naming_conventions:
  db:
    schema_pattern: "^[a-z0-9_]+$"
    table_pattern: "^[a-z0-9_]+$"
    column_pattern: "^[a-z0-9_]+$"
```

---

### 🐳 Step 3: Deploy the API Gateway

#### 1. Build and Start the Containers
```bash
# From the API-VPS directory
docker compose build
docker compose up -d
```

#### 2. Verify the Container is Running
```bash
docker ps | grep vps-api-gateway
```

#### 3. Test the API Gateway
```bash
# Test the /health endpoint
curl http://100.75.226.13:8000/v1/health

# Generate a JWT (for testing)
curl -X POST http://100.75.226.13:8000/v1/auth/token

# Test an authenticated request (replace <JWT> with the generated token)
curl -H "Authorization: Bearer <JWT>" http://100.75.226.13:8000/v1/system/read_env?key=N8N_DB_PASSWORD
```

---

### 📊 Step 4: Deploy Monitoring (Prometheus + Grafana)

#### 1. Create the Monitoring Directory
```bash
sudo mkdir -p /opt/monitoring/{prometheus,grafana/provisioning/dashboards,grafana/provisioning/datasources}
```

#### 2. Configure Prometheus
Create the `prometheus.yml` file:
```bash
sudo nano /opt/monitoring/prometheus/prometheus.yml
```

**Content of `prometheus.yml`**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "api-gateway"
    scrape_interval: 15s
    metrics_path: "/v1/metrics"
    static_configs:
      - targets: ["100.75.226.13:8000"]
    scrape_timeout: 5s

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

#### 3. Configure Grafana
Create the `.env` file for Grafana:
```bash
sudo nano /opt/monitoring/.env
```

**Content of `.env`**:
```ini
GRAFANA_ADMIN_PASSWORD=GrafanaAdmin2026!
```

Create the `datasources/prometheus.yml` file:
```bash
sudo nano /opt/monitoring/grafana/provisioning/datasources/prometheus.yml
```

**Content of `prometheus.yml`**:
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

#### 4. Create the `docker-compose.yml` for Monitoring
```bash
sudo nano /opt/monitoring/docker-compose.yml
```

**Content of `docker-compose.yml`**:
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "100.75.226.13:9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - apps

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "100.75.226.13:3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - apps

volumes:
  prometheus_data:
  grafana_data:

networks:
  apps:
    external: true
```

#### 5. Start Prometheus and Grafana
```bash
cd /opt/monitoring
docker compose up -d
```

#### 6. Verify Monitoring
```bash
# Prometheus
curl http://100.75.226.13:9090

# Grafana
curl http://100.75.226.13:3000
```

---

### 🚨 Step 5: Deploy Uptime-Kuma

#### 1. Create the Uptime-Kuma Directory
```bash
sudo mkdir -p /opt/uptime-kuma
```

#### 2. Start Uptime-Kuma
```bash
docker run -d \
  --name uptime-kuma \
  --restart=unless-stopped \
  -p 100.75.226.13:3001:3001 \
  -v /opt/uptime-kuma:/app/data \
  --network=apps \
  louislam/uptime-kuma:latest
```

#### 3. Verify Uptime-Kuma
```bash
curl http://100.75.226.13:3001
```

---

### 🔐 Step 6: Configure Security

#### 1. Disable `/v1/auth/token` in Production
Once you have generated a JWT for Pi Agent, disable the `/v1/auth/token` endpoint:
```bash
# Edit main.py and comment out the /v1/auth/token route
nano main.py
```

Find the line:
```python
@app.post("/v1/auth/token")
```

And comment it out:
```python
# @app.post("/v1/auth/token")
```

Then restart the API Gateway:
```bash
cd /home/ubuntu/API-VPS
docker compose down && docker compose up -d
```

#### 2. Generate a JWT for Pi Agent (Before Disabling `/v1/auth/token`)
```bash
# Generate a JWT valid for 1 year
JWT_TOKEN=$(curl -s -X POST http://100.75.226.13:8000/v1/auth/token | jq -r '.access_token')

# Save the JWT to a secure file
echo "$JWT_TOKEN" > /home/ubuntu/API-VPS/pi_agent_jwt.token
chmod 600 /home/ubuntu/API-VPS/pi_agent_jwt.token
```

#### 3. Configure Pi Agent to Use the JWT
In Pi Agent's configuration, add:
```yaml
api_gateway:
  url: "http://100.75.226.13:8000/v1"
  jwt_token: "$(cat /home/ubuntu/API-VPS/pi_agent_jwt.token)"
```

---

### 🧪 Step 7: Test the Deployment

#### 1. Test the API Gateway
```bash
# /health
curl http://100.75.226.13:8000/v1/health

# /metrics
curl http://100.75.226.13:8000/v1/metrics

# DB Query (replace <JWT> with your token)
curl -H "Authorization: Bearer <JWT>" "http://100.75.226.13:8000/v1/system/query_db?table=n8n_db.public.workflow_history&limit=1"
```

#### 2. Test Grafana
Open [http://100.75.226.13:3000](http://100.75.226.13:3000) in a browser.
- **Username**: `admin`
- **Password**: `GrafanaAdmin2026!` (or the one you set in `.env`).

#### 3. Test Prometheus
Open [http://100.75.226.13:9090](http://100.75.226.13:9090) in a browser.

#### 4. Test Uptime-Kuma
Open [http://100.75.226.13:3001](http://100.75.226.13:3001) in a browser.
- Add a monitor for `http://100.75.226.13:8000/v1/health`.

---

### 📝 Step 8: Configure MagicDNS (Optional)
To use internal domain names (e.g., `vps-rennesdev.rennesdev.local`):

1. **Enable MagicDNS** in [Tailscale Admin](https://login.tailscale.com/admin/dns).
2. **Add a Custom Domain** (e.g., `rennesdev.local`).
3. **Rename Devices**:
   - VPS: `vps-rennesdev`
   - PC: `super-pc-vert`

4. **Test**:
```bash
curl http://vps-rennesdev.rennesdev.local:8000/v1/health
```

---

### 🔧 Troubleshooting

#### Issue: Containers Not Starting
1. **Check Logs**:
   ```bash
   docker logs vps-api-gateway
   docker logs grafana
   docker logs prometheus
   docker logs uptime-kuma
   ```

2. **Check Ports**:
   ```bash
   sudo ss -tulnp | grep -E "8000|3000|3001|9090"
   ```

3. **Rebuild Dependencies**:
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

#### Issue: Port Conflict
If port `3000` is already in use (by `browserless` or `twenty_server`):
```bash
# Stop conflicting containers
docker stop browserless twenty_server

# Or change Grafana's port in /opt/monitoring/docker-compose.yml
# ports:
#   - "100.75.226.13:3002:3000"
```

#### Issue: PostgreSQL Connection Failed
1. **Verify `n8n_db` is Running**:
   ```bash
   docker ps | grep n8n_db
   ```

2. **Test Connection from API Gateway**:
   ```bash
   docker exec vps-api-gateway pg_isready -h n8n_db -p 5432 -U n8n -d n8n_db
   ```

3. **Verify `DB_URL` in `.env`**:
   ```ini
   DB_URL=postgresql://n8n:n8n@n8n_db:5432/n8n_db
   ```
