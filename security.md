# 🔒 Bonnes Pratiques de Sécurité pour API-VPS
# 🔒 API-VPS Security Best Practices

---

## 🌍 Languages / Langues
- **[Français](#-bonnes-pratiques-de-sécurité-pour-api-vps)**
- **[English](#-api-vps-security-best-practices)**

---

## 🇫🇷 Bonnes Pratiques de Sécurité pour API-VPS

### 📌 Introduction
Ce document décrit les **bonnes pratiques de sécurité** pour déployer et maintenir **API-VPS** de manière sécurisée. L'objectif est de garantir que :
- **L'API n'est accessible que via Tailscale** (pas d'exposition publique).
- **Les secrets sont protégés** (pas de stockage en clair dans le code).
- **Les requêtes sont validées** (whitelist stricte).
- **Les services sont surveillés** (détection des pannes).

---

### 🔐 1. Authentification et Autorisation

#### 🔹 Authentification (JWT)
- **Utilisez des JWT courts** : Durée de vie de **15 minutes** (configurable via `JWT_EXPIRE_MINUTES`).
- **Ne générez pas de JWT manuellement** : Utilisez toujours `/v1/auth/token` (à désactiver en production).
- **Stockez les JWT en sécurité** :
  - Pour Pi Agent : Sauvegardez le JWT dans un fichier **chmod 600** (ex: `pi_agent_jwt.token`).
  - Ne partagez **jamais** le JWT dans des logs ou des messages.

**Exemple de configuration JWT** (dans `.env`) :
```ini
JWT_SECRET=vps-gateway-secret-2026-change-me  # Générez avec `openssl rand -hex 32`
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
```

#### 🔹 Autorisation (Whitelist)
- **Définissez des règles strictes** dans `whitelist.yaml` :
  - **Clés `.env` autorisées** : Seules les clés nécessaires doivent être accessibles.
  - **Chemins de fichiers autorisés** : Restreignez aux fichiers critiques (ex: `/home/ubuntu/.env`).
  - **Tables DB autorisées** : Validez le **schéma**, la **table** et la **colonne**.

**Exemple de `whitelist.yaml`** :
```yaml
users:
  pi-agent:
    scope: ["read:system", "read:db"]
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
    allowed_file_paths: ["/home/ubuntu/.env"]
    allowed_db_tables: ["n8n_db.public.workflow_history"]
    masked_env_keys: ["N8N_DB_PASSWORD"]  # Masquer les valeurs sensibles
    forbidden_columns: ["password", "api_key", "token", "secret"]

tailscale:
  allowed_ips:
    - "100.75.226.13"  # VPS
    - "100.118.76.30"  # PC
    - "fd7a:115c:a1e0::/64"  # Plage IPv6 Tailscale
```

---

### 🌐 2. Accès Réseau

#### 🔹 Tailscale Uniquement
- **Liez les ports uniquement à l'IP Tailscale** (`100.75.226.13`) :
  ```yaml
  # Dans docker-compose.yml
  ports:
    - "100.75.226.13:8000:8000"  # ✅ Correct
    # - "0.0.0.0:8000:8000"    # ❌ À éviter (exposition publique)
    # - "162.19.246.165:8000:8000"  # ❌ À éviter (IP publique)
  ```

- **Vérifiez les ports ouverts** :
  ```bash
  sudo ss -tulnp | grep -E "8000|3000|3001|9090"
  ```
  → **Aucun port** ne doit être lié à `0.0.0.0` ou `162.19.246.165`.

#### 🔹 Pare-feu (UFW)
- **Activez UFW** :
  ```bash
  sudo ufw enable
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP (Caddy)
  sudo ufw allow 443/tcp  # HTTPS (Caddy)
  ```

- **Bloquez les ports inutiles** :
  ```bash
  sudo ufw deny 8000/tcp   # Bloquer l'accès public à l'API Gateway
  sudo ufw deny 3000/tcp   # Bloquer l'accès public à Grafana
  ```

#### 🔹 Cloudflare (Optionnel)
Si vous utilisez Cloudflare pour exposer des services :
- **Activez le proxy Orange** (pour masquer l'IP du VPS).
- **Configurez le WAF** (pare-feu applicatif) pour bloquer les attaques.
- **Utilisez des règles de sécurité** :
  - Bloquer les requêtes SQLi/XSS.
  - Limiter le taux de requêtes (rate limiting).

---

### 🗃 3. Gestion des Secrets

#### 🔹 Ne Stockez Pas de Secrets dans le Code
- **❌ À éviter** :
  ```python
  JWT_SECRET = "mon_secret_en_clair"  # ❌ Danger !
  ```

- **✅ Recommandé** :
  ```python
  JWT_SECRET = os.getenv("JWT_SECRET")  # ✅ Chargé depuis .env
  ```

#### 🔹 Fichier `.env`
- **Ne commitez jamais `.env`** dans Git :
  ```text
  # .gitignore
  .env
  *.env
  ```

- **Restreignez les permissions** :
  ```bash
  chmod 600 .env  # Seuls le propriétaire peut lire/écrire
  chown ubuntu:ubuntu .env
  ```

#### 🔹 Vault (Optionnel pour le Futur)
Pour une gestion centralisée des secrets :
1. **Installez Vault** :
   ```bash
   sudo apt install vault
   ```

2. **Démarrez Vault en mode dev** (pour tester) :
   ```bash
   vault server -dev -dev-listen-address=100.75.226.13:8200
   ```

3. **Stockez les secrets** :
   ```bash
   export VAULT_ADDR='http://100.75.226.13:8200'
   export VAULT_TOKEN='root'
   vault kv put secret/api-gateway JWT_SECRET="votre_secret" DB_URL="postgresql://..."
   ```

4. **Modifiez l'API Gateway** pour utiliser Vault :
   ```python
   import hvac
   client = hvac.Client(url='http://localhost:8200', token=os.getenv('VAULT_TOKEN'))
   JWT_SECRET = client.secrets.kv.v2.read_secret_version(path='api-gateway')['data']['data']['JWT_SECRET']
   ```

---

### 🔍 4. Validation des Requêtes

#### 🔹 Validation des Requêtes DB (3 Niveaux)
L'API Gateway valide **toujours** :
1. **Schéma** : Doit correspondre à une expression regex (ex: `^[a-z0-9_]+$`).
2. **Table** : Doit être dans la whitelist pour l'utilisateur.
3. **Colonne** : Doit être dans la whitelist pour la table.

**Exemple de validation** :
```python
# Dans main.py
def validate_db_column(schema: str, table: str, column: str) -> bool:
    if not re.match(WHITELIST["naming_conventions"]["db"]["column_pattern"], column):
        return False
    if column in WHITELIST["users"][user]["forbidden_columns"]:
        return False
    return column in WHITELIST["users"][user]["allowed_db_tables"][f"{schema}.{table}"]
```

#### 🔹 Validation des Chemins de Fichiers
- **Whitelist des chemins** : Seuls les chemins autorisés sont accessibles.
- **Interdiction des chemins sensibles** :
  ```yaml
  forbidden_patterns:
    - \.ssh/
    - /etc/shadow
    - /etc/passwd
    - \.git/
  ```

---

### 🛡 5. Protection contre les Attaques

#### 🔹 Injections SQL
- **Utilisez des requêtes paramétrées** :
  ```python
  # ✅ Correct (avec psycopg2)
  query = sql.SQL("SELECT {columns} FROM {table} WHERE {condition} LIMIT {limit}").format(
      columns=sql.SQL(",").join(sql.Identifier(col) for col in columns),
      table=sql.Identifier(table),
      condition=sql.SQL(condition),  # Validé avant
      limit=sql.Literal(limit)
  )
  ```

- **❌ À éviter** :
  ```python
  # ❌ Danger (injection SQL possible)
  query = f"SELECT * FROM {table} WHERE {condition}"
  ```

#### 🔹 Injections de Chemin
- **Validez les chemins** :
  ```python
  def is_path_allowed(path: str) -> bool:
      path = os.path.abspath(path)
      for allowed_prefix in WHITELIST["file_paths"]["allowed"]:
          if path.startswith(os.path.abspath(allowed_prefix)):
              return True
      return False
  ```

#### 🔹 Rate Limiting
- **Limitez les requêtes** avec `slowapi` (pour FastAPI) :
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_remote_address)
  
  @app.get("/v1/system/read_env")
  @limiter.limit("10/minute")
  async def read_env(...):
      ...
  ```

---

### 📊 6. Monitoring et Alertes

#### 🔹 Surveillance des Services
- **Endpoint `/v1/health`** : Vérifie l'état des services critiques (PostgreSQL, n8n, Caddy).
- **Endpoint `/v1/metrics`** :Expose les métriques au format Prometheus.

**Exemple de `/v1/health`** :
```json
{
  "status": "healthy",
  "services": {
    "PostgreSQL (n8n_db)": {
      "status": "healthy",
      "details": "localhost:5432 - accepting connections"
    },
    "n8n": {
      "status": "healthy",
      "details": ""
    }
  },
  "timestamp": "2026-10-27T12:00:00Z"
}
```

#### 🔹 Alertes Automatiques
- **Uptime-Kuma** : Configurez un monitor pour `/v1/health` avec un intervalle de **30 secondes**.
- **Notifications** : Envoyez des alertes via **email** ou **webhook** en cas de panne.

**Exemple de configuration Uptime-Kuma** :
- **URL** : `http://100.75.226.13:8000/v1/health`
- **Intervalle** : 30 secondes
- **Seuil de panne** : 1 échec
- **Notification** : Email à `admin@rennesdev.fr`

---

### 🔄 7. Mises à Jour et Maintenance

#### 🔹 Mises à Jour des Conteneurs
- **Mettez à jour régulièrement** les images Docker :
  ```bash
  cd /home/ubuntu/API-VPS
  docker compose pull
  docker compose up -d --build
  ```

- **Vérifiez les vulnérabilités** :
  ```bash
  docker scan vps-api-gateway
  ```

#### 🔹 Sauvegardes
- **Sauvegardez les données** :
  ```bash
  # Sauvegarder les volumes Docker
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /home/ubuntu/backups:/backup \
    alpine:latest \
    sh -c "docker exec vps-api-gateway pg_dump -U n8n n8n_db > /backup/n8n_db_$(date +%Y%m%d).sql"
  ```

- **Automatisez les sauvegardes** avec `cron` :
  ```bash
  0 2 * * * /home/ubuntu/backup_monitoring.sh
  ```

---

### 📝 8. Checklist de Sécurité
| Élément | Vérification | Statut |
|---------|--------------|--------|
| **JWT court** | `JWT_EXPIRE_MINUTES=15` | ⬜ |
| **Pas de secrets dans le code** | `.env` utilisé + `.gitignore` | ⬜ |
| **Ports liés à Tailscale** | `100.75.226.13:8000` | ⬜ |
| **Whitelist des ressources** | `whitelist.yaml` configuré | ⬜ |
| **Validation des requêtes DB** | 3 niveaux (schéma + table + colonne) | ⬜ |
| **Rate Limiting** | `slowapi` configuré | ⬜ |
| **Monitoring activé** | `/v1/health` et `/v1/metrics` | ⬜ |
| **Alertes configurées** | Uptime-Kuma + notifications | ⬜ |
| **Sauvegardes automatiques** | Script cron configuré | ⬜ |

---

---

## 🇬🇧 API-VPS Security Best Practices

### 📌 Introduction
This document outlines **security best practices** for deploying and maintaining **API-VPS** securely. The goal is to ensure that:
- **The API is only accessible via Tailscale** (no public exposure).
- **Secrets are protected** (no hardcoding in files).
- **Requests are validated** (strict whitelisting).
- **Services are monitored** (failure detection).

---

### 🔐 1. Authentication and Authorization

#### 🔹 Authentication (JWT)
- **Use Short-Lived JWTs**: **15-minute** expiry (configurable via `JWT_EXPIRE_MINUTES`).
- **Never Generate JWTs Manually**: Always use `/v1/auth/token` (disable in production).
- **Store JWTs Securely**:
  - For Pi Agent: Save the JWT in a **chmod 600** file (e.g., `pi_agent_jwt.token`).
  - Never share JWTs in logs or messages.

**Example JWT Configuration** (in `.env`):
```ini
JWT_SECRET=vps-gateway-secret-2026-change-me  # Generate with `openssl rand -hex 32`
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
```

#### 🔹 Authorization (Whitelist)
- **Define Strict Rules** in `whitelist.yaml`:
  - **Allowed `.env` Keys**: Only necessary keys should be accessible.
  - **Allowed File Paths**: Restrict to critical files (e.g., `/home/ubuntu/.env`).
  - **Allowed DB Tables**: Validate **schema**, **table**, and **column**.

**Example `whitelist.yaml`**:
```yaml
users:
  pi-agent:
    scope: ["read:system", "read:db"]
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
    allowed_file_paths: ["/home/ubuntu/.env"]
    allowed_db_tables: ["n8n_db.public.workflow_history"]
    masked_env_keys: ["N8N_DB_PASSWORD"]  # Mask sensitive values
    forbidden_columns: ["password", "api_key", "token", "secret"]

tailscale:
  allowed_ips:
    - "100.75.226.13"  # VPS
    - "100.118.76.30"  # PC
    - "fd7a:115c:a1e0::/64"  # Tailscale IPv6 range
```

---

### 🌐 2. Network Access

#### 🔹 Tailscale Only
- **Bind Ports Only to Tailscale IP** (`100.75.226.13`):
  ```yaml
  # In docker-compose.yml
  ports:
    - "100.75.226.13:8000:8000"  # ✅ Correct
    # - "0.0.0.0:8000:8000"    # ❌ Avoid (public exposure)
    # - "162.19.246.165:8000:8000"  # ❌ Avoid (public IP)
  ```

- **Check Open Ports**:
  ```bash
  sudo ss -tulnp | grep -E "8000|3000|3001|9090"
  ```
  → **No ports** should be bound to `0.0.0.0` or `162.19.246.165`.

#### 🔹 Firewall (UFW)
- **Enable UFW**:
  ```bash
  sudo ufw enable
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP (Caddy)
  sudo ufw allow 443/tcp  # HTTPS (Caddy)
  ```

- **Block Unused Ports**:
  ```bash
  sudo ufw deny 8000/tcp   # Block public access to API Gateway
  sudo ufw deny 3000/tcp   # Block public access to Grafana
  ```

#### 🔹 Cloudflare (Optional)
If using Cloudflare to expose services:
- **Enable Orange Proxy** (to hide VPS IP).
- **Configure WAF** (Web Application Firewall) to block attacks.
- **Use Security Rules**:
  - Block SQLi/XSS requests.
  - Rate limiting.

---

### 🗃 3. Secrets Management

#### 🔹 Never Store Secrets in Code
- **❌ Avoid**:
  ```python
  JWT_SECRET = "my_plaintext_secret"  # ❌ Danger!
  ```

- **✅ Recommended**:
  ```python
  JWT_SECRET = os.getenv("JWT_SECRET")  # ✅ Loaded from .env
  ```

#### 🔹 `.env` File
- **Never Commit `.env`** to Git:
  ```text
  # .gitignore
  .env
  *.env
  ```

- **Restrict Permissions**:
  ```bash
  chmod 600 .env  # Only owner can read/write
  chown ubuntu:ubuntu .env
  ```

#### 🔹 Vault (Optional for Future)
For centralized secrets management:
1. **Install Vault**:
   ```bash
   sudo apt install vault
   ```

2. **Start Vault in Dev Mode** (for testing):
   ```bash
   vault server -dev -dev-listen-address=100.75.226.13:8200
   ```

3. **Store Secrets**:
   ```bash
   export VAULT_ADDR='http://100.75.226.13:8200'
   export VAULT_TOKEN='root'
   vault kv put secret/api-gateway JWT_SECRET="your_secret" DB_URL="postgresql://..."
   ```

4. **Modify API Gateway** to Use Vault:
   ```python
   import hvac
   client = hvac.Client(url='http://localhost:8200', token=os.getenv('VAULT_TOKEN'))
   JWT_SECRET = client.secrets.kv.v2.read_secret_version(path='api-gateway')['data']['data']['JWT_SECRET']
   ```

---

### 🔍 4. Request Validation

#### 🔹 DB Query Validation (3 Levels)
The API Gateway **always** validates:
1. **Schema**: Must match a regex pattern (e.g., `^[a-z0-9_]+$`).
2. **Table**: Must be in the whitelist for the user.
3. **Column**: Must be in the whitelist for the table.

**Example Validation**:
```python
# In main.py
def validate_db_column(schema: str, table: str, column: str) -> bool:
    if not re.match(WHITELIST["naming_conventions"]["db"]["column_pattern"], column):
        return False
    if column in WHITELIST["users"][user]["forbidden_columns"]:
        return False
    return column in WHITELIST["users"][user]["allowed_db_tables"][f"{schema}.{table}"]
```

#### 🔹 File Path Validation
- **Whitelist Paths**: Only allowed paths are accessible.
- **Block Sensitive Paths**:
  ```yaml
  forbidden_patterns:
    - \.ssh/
    - /etc/shadow
    - /etc/passwd
    - \.git/
  ```

---

### 🛡 5. Protection Against Attacks

#### 🔹 SQL Injection
- **Use Parameterized Queries**:
  ```python
  # ✅ Correct (with psycopg2)
  query = sql.SQL("SELECT {columns} FROM {table} WHERE {condition} LIMIT {limit}").format(
      columns=sql.SQL(",").join(sql.Identifier(col) for col in columns),
      table=sql.Identifier(table),
      condition=sql.SQL(condition),  # Validated before
      limit=sql.Literal(limit)
  )
  ```

- **❌ Avoid**:
  ```python
  # ❌ Danger (SQL injection possible)
  query = f"SELECT * FROM {table} WHERE {condition}"
  ```

#### 🔹 Path Traversal
- **Validate Paths**:
  ```python
  def is_path_allowed(path: str) -> bool:
      path = os.path.abspath(path)
      for allowed_prefix in WHITELIST["file_paths"]["allowed"]:
          if path.startswith(os.path.abspath(allowed_prefix)):
              return True
      return False
  ```

#### 🔹 Rate Limiting
- **Limit Requests** with `slowapi` (for FastAPI):
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_remote_address)
  
  @app.get("/v1/system/read_env")
  @limiter.limit("10/minute")
  async def read_env(...):
      ...
  ```

---

### 📊 6. Monitoring and Alerts

#### 🔹 Service Monitoring
- **`/v1/health` Endpoint**: Checks the status of critical services (PostgreSQL, n8n, Caddy).
- **`/v1/metrics` Endpoint**: Exposes metrics in Prometheus format.

**Example `/v1/health`**:
```json
{
  "status": "healthy",
  "services": {
    "PostgreSQL (n8n_db)": {
      "status": "healthy",
      "details": "localhost:5432 - accepting connections"
    },
    "n8n": {
      "status": "healthy",
      "details": ""
    }
  },
  "timestamp": "2026-10-27T12:00:00Z"
}
```

#### 🔹 Automatic Alerts
- **Uptime-Kuma**: Configure a monitor for `/v1/health` with a **30-second interval**.
- **Notifications**: Send alerts via **email** or **webhook** in case of failure.

**Example Uptime-Kuma Configuration**:
- **URL**: `http://100.75.226.13:8000/v1/health`
- **Interval**: 30 seconds
- **Failure Threshold**: 1 failure
- **Notification**: Email to `admin@rennesdev.fr`

---

### 🔄 7. Updates and Maintenance

#### 🔹 Container Updates
- **Update Docker Images Regularly**:
  ```bash
  cd /home/ubuntu/API-VPS
  docker compose pull
  docker compose up -d --build
  ```

- **Check for Vulnerabilities**:
  ```bash
  docker scan vps-api-gateway
  ```

#### 🔹 Backups
- **Backup Data**:
  ```bash
  # Backup Docker volumes
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /home/ubuntu/backups:/backup \
    alpine:latest \
    sh -c "docker exec vps-api-gateway pg_dump -U n8n n8n_db > /backup/n8n_db_$(date +%Y%m%d).sql"
  ```

- **Automate Backups** with `cron`:
  ```bash
  0 2 * * * /home/ubuntu/backup_monitoring.sh
  ```

---

### 📝 8. Security Checklist
| Item | Verification | Status |
|------|--------------|--------|
| **Short-Lived JWT** | `JWT_EXPIRE_MINUTES=15` | ⬜ |
| **No Secrets in Code** | `.env` used + `.gitignore` | ⬜ |
| **Ports Bound to Tailscale** | `100.75.226.13:8000` | ⬜ |
| **Resource Whitelist** | `whitelist.yaml` configured | ⬜ |
| **DB Query Validation** | 3 levels (schema + table + column) | ⬜ |
| **Rate Limiting** | `slowapi` configured | ⬜ |
| **Monitoring Enabled** | `/v1/health` and `/v1/metrics` | ⬜ |
| **Alerts Configured** | Uptime-Kuma + notifications | ⬜ |
| **Automated Backups** | Cron script configured | ⬜ |
