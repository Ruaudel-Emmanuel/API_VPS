# 🏗 Architecture d'API-VPS
# 🏗 API-VPS Architecture

---

## 🌍 Languages / Langues
- **[Français](#-architecture-dapi-vps)**
- **[English](#-api-vps-architecture)**

---

## 🇫🇷 Architecture d'API-VPS

### 📌 Vue d'Ensemble
API-VPS est une **passerelle API sécurisée** qui permet à des agents IA (comme Pi Agent) d'interagir avec un VPS auto-hébergé **sans accès direct aux fichiers système**. Elle agit comme une **couche d'abstraction** entre l'agent IA et les services du VPS, en garantissant que :

1. **L'IA ne lit jamais directement les fichiers** (ex: `.env`, logs).
2. **Les requêtes sont validées** (whitelist des clés, chemins, tables DB).
3. **L'accès est restreint** (uniquement via Tailscale ou réseau interne).

---

### 🔧 Composants Principaux

#### 1. **API Gateway (FastAPI)**
- **Rôle** : Point d'entrée unique pour toutes les requêtes de l'agent IA.
- **Fonctionnalités** :
  - Authentification via **JWT**.
  - Validation des **requêtes DB** (schéma + table + colonne).
  - **Masquage des secrets** (mots de passe, tokens).
  - Endpoints pour lire les **variables `.env`** et les **fichiers**.
- **Port** : `8000` (lié à `100.75.226.13` via Tailscale).

#### 2. **Base de Données (PostgreSQL)**
- **Rôle** : Stocke les données des workflows (n8n, Twenty, etc.).
- **Instances** :
  - `n8n_db` (PostgreSQL 17) : Pour les workflows n8n.
  - `twenty_db` (PostgreSQL 16) : Pour l'application Twenty.
- **Accès** : Uniquement via le réseau Docker `apps`.

#### 3. **Monitoring (Prometheus + Grafana + Uptime-Kuma)**
- **Prometheus** : Collecte les métriques de l'API Gateway (requêtes, latence, erreurs).
- **Grafana** : Tableaux de bord pour visualiser les métriques.
- **Uptime-Kuma** : Surveillance de la disponibilité des services.

#### 4. **Réseau (Tailscale + Docker)**
- **Tailscale** : Réseau VPN pour un accès sécurisé entre le PC et le VPS.
  - IP du VPS : `100.75.226.13`.
  - IP du PC : `100.118.76.30`.
- **Docker** : Réseau `apps` pour la communication entre conteneurs.

---

### 📊 Schéma d'Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   💻 Pi Agent (PC - 100.118.76.30)                                            │
│        │                                                                       │
│        ▼ (Requête : "Lire N8N_DB_PASSWORD")                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │  🔒 TAILSCALE (100.75.226.13)                                           │  │
│   │      │                                                                   │  │
│   │      ▼ (Requête HTTP + JWT)                                             │  │
│   │  ┌───────────────────────────────────────────────────────────────┐    │  │
│   │  │  🐳 DOCKER (Réseau `apps`)                                        │    │  │
│   │  │                                                                  │    │  │
│   │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │    │  │
│   │  │  │  API Gateway │    │    n8n       │    │  PostgreSQL          │  │    │  │
│   │  │  │ (FastAPI)    │    │ (Workflow)   │    │  (n8n_db, twenty_db) │  │    │  │
│   │  │  └─────────────┘    └─────────────┘    └─────────────────────┘  │    │  │
│   │  │        │                                                           │    │  │
│   │  │        ▼ (Valide la requête)                                       │    │  │
│   │  │  ┌───────────────────────────────────────────────────────────┐    │    │  │
│   │  │  │  1. Vérifie le JWT                                             │    │    │  │
│   │  │  │  2. Vérifie la whitelist (clé N8N_DB_PASSWORD autorisée ?)   │    │    │  │
│   │  │  │  3. Lit la variable dans .env                                  │    │    │  │
│   │  │  │  4. Masque la valeur (si sensible)                            │    │    │  │
│   │  │  │  5. Retourne la réponse JSON                                  │    │    │  │
│   │  │  └───────────────────────────────────────────────────────────┘    │    │  │
│   │  │                                                                  │    │  │
│   │  └───────────────────────────────────────────────────────────────┘    │  │
│   │                                                                       │  │
│   │  ┌───────────────────────────────────────────────────────────────┐    │  │
│   │  │  📊 MONITORING                                                     │    │  │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐      │    │  │
│   │  │  │ Prometheus   │  │   Grafana    │  │   Uptime-Kuma        │      │    │  │
│   │  │  │ (Port 9090)  │  │ (Port 3000)  │  │   (Port 3001)        │      │    │  │
│   │  │  └─────────────┘  └─────────────┘  └─────────────────────┘      │    │  │
│   │  └───────────────────────────────────────────────────────────────┘    │  │
│   └───────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔐 Flux de Données

#### 1. **Requête de l'Agent IA**
- **Exemple** : "Quelle est la valeur de `N8N_DB_PASSWORD` ?"
- **Action** : Pi Agent génère une requête HTTP vers `/v1/system/read_env?key=N8N_DB_PASSWORD`.

#### 2. **Vérification par l'API Gateway**
1. **Authentification** : Vérifie le JWT dans le header `Authorization`.
2. **Autorisation** : Vérifie que `N8N_DB_PASSWORD` est dans la whitelist pour l'utilisateur `pi-agent`.
3. **Validation** : Vérifie que la clé respecte les conventions de nommage.

#### 3. **Exécution de la Requête**
- **Lecture de `.env`** : L'API lit la variable `N8N_DB_PASSWORD` depuis le fichier `.env`.
- **Masquage** : Si la clé est dans `masked_env_keys`, la valeur est remplacée par `***MASKED***`.
- **Réponse** : Retourne un JSON avec la clé et la valeur (masquée si nécessaire).

#### 4. **Réponse à l'Agent IA**
- **Exemple de réponse** :
  ```json
  {
    "key": "N8N_DB_PASSWORD",
    "value": "***MASKED***",
    "masked": true
  }
  ```

---

### 🛡 Sécurité

#### 1. **Authentification**
- **JWT** : Tokens signés avec `HS256` et une durée de vie courte (15 min).
- **Génération** : Via `/v1/auth/token` (à désactiver en production).

#### 2. **Autorisation**
- **Whitelist** : Seules les ressources (clés, chemins, tables DB) **préalablement autorisées** sont accessibles.
- **Exemple de `whitelist.yaml`** :
  ```yaml
  users:
    pi-agent:
      allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
      allowed_file_paths: ["/home/ubuntu/.env"]
      allowed_db_tables: ["n8n_db.public.workflow_history"]
      masked_env_keys: ["N8N_DB_PASSWORD"]
  ```

#### 3. **Validation des Requêtes DB**
- **3 niveaux** : Schéma + Table + Colonne.
- **Exemple** :
  - `n8n_db.public.workflow_history` : ✅ Valide.
  - `n8n_db.public.users.password` : ❌ Colonne interdite.

#### 4. **Accès Réseau**
- **Tailscale uniquement** : L'API ne répond **que sur `100.75.226.13`** (IP Tailscale).
- **Pas d'exposition publique** : Aucun port n'est lié à `0.0.0.0` ou `162.19.246.165`.

---

### 📦 Technologies Utilisées
| Technologie | Version | Rôle |
|-------------|---------|------|
| **FastAPI** | 0.109.0 | Framework API (Python). |
| **Uvicorn** | 0.27.0 | Serveur ASGI pour FastAPI. |
| **PostgreSQL** | 17 | Base de données pour n8n. |
| **Docker** | 24.x | Conteneurisation des services. |
| **Tailscale** | Latest | Réseau VPN sécurisé. |
| **Prometheus** | Latest | Collecte des métriques. |
| **Grafana** | Latest | Visualisation des métriques. |
| **Uptime-Kuma** | Latest | Surveillance de la disponibilité. |

---

---

## 🇬🇧 API-VPS Architecture

### 📌 Overview
API-VPS is a **secure API gateway** that allows AI agents (like Pi Agent) to interact with a **self-hosted VPS** **without direct access to system files**. It acts as an **abstraction layer** between the AI agent and VPS services, ensuring that:

1. **The AI never directly reads system files** (e.g., `.env`, logs).
2. **Requests are validated** (whitelist of keys, paths, DB tables).
3. **Access is restricted** (only via Tailscale or internal network).

---

### 🔧 Main Components

#### 1. **API Gateway (FastAPI)**
- **Role**: Single entry point for all AI agent requests.
- **Features**:
  - Authentication via **JWT**. 
  - **DB query validation** (schema + table + column).
  - **Secret masking** (passwords, tokens).
  - Endpoints to read **`.env` variables** and **files**.
- **Port**: `8000` (bound to `100.75.226.13` via Tailscale).

#### 2. **Database (PostgreSQL)**
- **Role**: Stores workflow data (n8n, Twenty, etc.).
- **Instances**:
  - `n8n_db` (PostgreSQL 17): For n8n workflows.
  - `twenty_db` (PostgreSQL 16): For Twenty application.
- **Access**: Only via Docker network `apps`.

#### 3. **Monitoring (Prometheus + Grafana + Uptime-Kuma)**
- **Prometheus**: Collects API Gateway metrics (requests, latency, errors).
- **Grafana**: Dashboards to visualize metrics.
- **Uptime-Kuma**: Monitors service availability.

#### 4. **Network (Tailscale + Docker)**
- **Tailscale**: VPN network for secure access between PC and VPS.
  - VPS IP: `100.75.226.13`.
  - PC IP: `100.118.76.30`.
- **Docker**: Network `apps` for inter-container communication.

---

### 📊 Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   💻 Pi Agent (PC - 100.118.76.30)                                            │
│        │                                                                       │
│        ▼ (Request: "Read N8N_DB_PASSWORD")                                    │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │  🔒 TAILSCALE (100.75.226.13)                                           │  │
│   │      │                                                                   │  │
│   │      ▼ (HTTP Request + JWT)                                             │  │
│   │  ┌───────────────────────────────────────────────────────────────┐    │  │
│   │  │  🐳 DOCKER (Network `apps`)                                        │    │  │
│   │  │                                                                  │    │  │
│   │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │    │  │
│   │  │  │  API Gateway │    │    n8n       │    │  PostgreSQL          │  │    │  │
│   │  │  │ (FastAPI)    │    │ (Workflow)   │    │  (n8n_db, twenty_db) │  │    │  │
│   │  │  └─────────────┘    └─────────────┘    └─────────────────────┘  │    │  │
│   │  │        │                                                           │    │  │
│   │  │        ▼ (Validates Request)                                       │    │  │
│   │  │  ┌───────────────────────────────────────────────────────────┐    │    │  │
│   │  │  │  1. Checks JWT                                                 │    │    │  │
│   │  │  │  2. Checks Whitelist (Is N8N_DB_PASSWORD allowed?)           │    │    │  │
│   │  │  │  3. Reads Variable from .env                                   │    │    │  │
│   │  │  │  4. Masks Value (if sensitive)                                 │    │    │  │
│   │  │  │  5. Returns JSON Response                                       │    │    │  │
│   │  │  └───────────────────────────────────────────────────────────┘    │    │  │
│   │  │                                                                  │    │  │
│   │  └───────────────────────────────────────────────────────────────┘    │  │
│   │                                                                       │  │
│   │  ┌───────────────────────────────────────────────────────────────┐    │  │
│   │  │  📊 MONITORING                                                     │    │  │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐      │    │  │
│   │  │  │ Prometheus   │  │   Grafana    │  │   Uptime-Kuma        │      │    │  │
│   │  │  │ (Port 9090)  │  │ (Port 3000)  │  │   (Port 3001)        │      │    │  │
│   │  │  └─────────────┘  └─────────────┘  └─────────────────────┘      │    │  │
│   │  └───────────────────────────────────────────────────────────────┘    │  │
│   └───────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔐 Data Flow

#### 1. **AI Agent Request**
- **Example**: "What is the value of `N8N_DB_PASSWORD`?"
- **Action**: Pi Agent generates an HTTP request to `/v1/system/read_env?key=N8N_DB_PASSWORD`.

#### 2. **API Gateway Verification**
1. **Authentication**: Checks the JWT in the `Authorization` header.
2. **Authorization**: Checks if `N8N_DB_PASSWORD` is in the whitelist for user `pi-agent`.
3. **Validation**: Checks if the key matches naming conventions.

#### 3. **Request Execution**
- **Read `.env`**: The API reads the `N8N_DB_PASSWORD` variable from the `.env` file.
- **Masking**: If the key is in `masked_env_keys`, the value is replaced with `***MASKED***`.
- **Response**: Returns a JSON with the key and value (masked if necessary).

#### 4. **Response to AI Agent**
- **Example Response**:
  ```json
  {
    "key": "N8N_DB_PASSWORD",
    "value": "***MASKED***",
    "masked": true
  }
  ```

---

### 🛡 Security

#### 1. **Authentication**
- **JWT**: Tokens signed with `HS256` and short-lived (15 min).
- **Generation**: Via `/v1/auth/token` (disable in production).

#### 2. **Authorization**
- **Whitelist**: Only pre-approved resources (keys, paths, DB tables) are accessible.
- **Example `whitelist.yaml`**:
  ```yaml
  users:
    pi-agent:
      allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
      allowed_file_paths: ["/home/ubuntu/.env"]
      allowed_db_tables: ["n8n_db.public.workflow_history"]
      masked_env_keys: ["N8N_DB_PASSWORD"]
  ```

#### 3. **DB Query Validation**
- **3 Levels**: Schema + Table + Column.
- **Example**:
  - `n8n_db.public.workflow_history`: ✅ Valid.
  - `n8n_db.public.users.password`: ❌ Forbidden column.

#### 4. **Network Access**
- **Tailscale Only**: API only listens on `100.75.226.13` (Tailscale IP).
- **No Public Exposure**: No ports are bound to `0.0.0.0` or `162.19.246.165`.

---

### 📦 Technologies Used
| Technology | Version | Role |
|-------------|---------|------|
| **FastAPI** | 0.109.0 | API Framework (Python). |
| **Uvicorn** | 0.27.0 | ASGI Server for FastAPI. |
| **PostgreSQL** | 17 | Database for n8n. |
| **Docker** | 24.x | Containerization of services. |
| **Tailscale** | Latest | Secure VPN network. |
| **Prometheus** | Latest | Metrics collection. |
| **Grafana** | Latest | Metrics visualization. |
| **Uptime-Kuma** | Latest | Availability monitoring. |
