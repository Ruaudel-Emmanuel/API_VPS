# 🚀 API-VPS: Secure API Gateway for Self-Hosted VPS
# 🚀 API-VPS: Passerelle API Sécurisée pour VPS Auto-Hébergé

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)]
[![FastAPI](https://img.shields.io/badge/FastAPI-005571.svg?logo=fastapi)]
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker)]

---

## 🌍 Languages / Langues
- **[Français](#-api-vps-passerelle-api-sécurisée-pour-vps-auto-hébergé)**
- **[English](#-api-vps-secure-api-gateway-for-self-hosted-vps)**

---

## 🇫🇷 API-VPS: Passerelle API Sécurisée pour VPS Auto-Hébergé

### 📌 Description
**API-VPS** est une **passerelle API sécurisée** conçue pour permettre à des agents IA (comme Pi Agent) d'interagir avec un **VPS auto-hébergé** de manière **contrôlée et sécurisée**. Elle agit comme une **couche d'abstraction** entre l'agent IA et les services système (fichiers `.env`, bases de données, logs), en garantissant que :
- **L'IA ne lit jamais directement les fichiers système** (seulement via l'API).
- **Les requêtes sont validées** (whitelist des clés, chemins, tables DB).
- **L'accès est restreint** (uniquement via Tailscale ou réseau interne).

---

### 🔐 Fonctionnalités Clés
| Fonctionnalité | Description |
|----------------|-------------|
| **Authentification JWT** | Accès sécurisé via des tokens JWT (courte durée de vie). |
| **Whitelist des Ressources** | Seules les clés `.env`, chemins et tables DB **préalablement autorisés** sont accessibles. |
| **Validation des Requêtes DB** | Vérification du **schéma**, de la **table** et de la **colonne** avant toute requête. |
| **Masquage des Secrets** | Les valeurs sensibles (mots de passe, tokens) sont **automatiquement masquées**. |
| **Monitoring Intégré** | Endpoint `/v1/health` pour vérifier l'état des services critiques. |
| **Métriques Prometheus** | Endpoint `/v1/metrics` pour le monitoring des performances. |
| **Accès Tailscale** | **Uniquement accessible** via le réseau Tailscale (pas d'exposition publique). |

---

### 🏗 Architecture
```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   💻 Pi Agent (PC)                                                             │
│        │                                                                       │
│        ▼ (Tailscale: 100.118.76.30)                                           │
│   🔒 TAILSCALE (100.75.226.13)                                                 │
│        │                                                                       │
│        ▼                                                                       │
│   🐳 DOCKER (Réseau `apps`)                                                    │
│        │                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌───────────────────────────────────┐  │
│   │  API Gateway │    │    n8n       │    │       PostgreSQL (n8n_db)          │  │
│   │ (FastAPI)    │◄──►│ (Workflow)   │◄──►│       Twenty DB                   │  │
│   └─────────────┘    └─────────────┘    └───────────────────────────────────┘  │
│        │                                                                       │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │  Monitoring                                                               │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │  │
│   │  │ Prometheus   │  │   Grafana    │  │     Uptime-Kuma                  │  │  │
│   │  │ (Port 9090)  │  │ (Port 3000)  │  │     (Port 3001)                  │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────────────┘  │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 📦 Prérequis
- **VPS** : Ubuntu 22.04/24.04 LTS (ou équivalent).
- **Docker** : [Installation Docker](https://docs.docker.com/engine/install/ubuntu/).
- **Docker Compose** : [Installation Docker Compose](https://docs.docker.com/compose/install/).
- **Tailscale** : [Installation Tailscale](https://tailscale.com/download) (pour un accès sécurisé).
- **Python 3.11+** : Pour le développement local (optionnel).

---

### 🚀 Installation Rapide

#### 1. Cloner le dépôt
```bash
git clone https://github.com/VOTRE_NOM/API-VPS.git
cd API-VPS
```

#### 2. Configurer l'environnement
```bash
# Créer un fichier .env (copier depuis .env.example)
cp .env.example .env
nano .env  # Modifier JWT_SECRET, DB_URL, etc.
```

#### 3. Démarrer l'API Gateway
```bash
docker compose up -d
```

#### 4. Tester l'API
```bash
# Récupérer un JWT (pour les tests)
curl -X POST http://localhost:8000/v1/auth/token

# Tester l'endpoint /health
curl http://localhost:8000/v1/health
```

---
### 📡 Endpoints Disponibles
| Méthode | Endpoint | Description | Authentification |
|---------|----------|-------------|------------------|
| POST | `/v1/auth/token` | Génère un JWT (à désactiver en production) | ❌ Aucune |
| GET | `/v1/system/read_env?key={key}` | Lit une variable `.env` | ✅ JWT |
| GET | `/v1/system/read_file?file_path={path}` | Lit un fichier | ✅ JWT |
| GET | `/v1/system/query_db?table={schema.table}` | Requête DB (3 niveaux de validation) | ✅ JWT |
| GET | `/v1/health` | État des services critiques | ❌ Aucune |
| GET | `/v1/metrics` | Métriques Prometheus | ❌ Aucune |

---

### 🔐 Configuration de la Sécurité
#### 1. **Whitelist des Ressources**
Modifiez `whitelist.yaml` pour autoriser :
- Les **clés `.env`** (ex: `N8N_DB_PASSWORD`).
- Les **chemins de fichiers** (ex: `/home/ubuntu/.env`).
- Les **tables DB** (ex: `n8n_db.public.workflow_history`).

Exemple :
```yaml
users:
  pi-agent:
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
    allowed_file_paths: ["/home/ubuntu/.env"]
    allowed_db_tables: ["n8n_db.public.workflow_history"]
    masked_env_keys: ["N8N_DB_PASSWORD"]  # Masquer les valeurs sensibles
```

#### 2. **Authentification JWT**
- **Génération** : `POST /v1/auth/token` (à désactiver en production).
- **Utilisation** : Ajoutez le header `Authorization: Bearer <JWT>` à chaque requête.

#### 3. **Accès Réseau**
- **Tailscale uniquement** : L'API ne répond **que sur l'IP Tailscale** (`100.75.226.13`).
- **Pas d'exposition publique** : Aucun port n'est lié à `0.0.0.0` ou `162.19.246.165`.

---

### 📊 Monitoring
#### 1. **Prometheus + Grafana**
- **Prometheus** : [http://localhost:9090](http://localhost:9090)
- **Grafana** : [http://localhost:3000](http://localhost:3000) (admin / `GRAFANA_ADMIN_PASSWORD`).
- **Configuration** : Voir [docs/deployment.md](docs/deployment.md).

#### 2. **Uptime-Kuma**
- **URL** : [http://localhost:3001](http://localhost:3001)
- **Configuration** : Ajoutez un monitor pour `http://localhost:8000/v1/health`.

---

### 🛠 Développement Local
#### 1. Installer les dépendances
```bash
pip install -r requirements.txt
```

#### 2. Démarrer l'API en local
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Tester avec `curl`
```bash
# Générer un JWT
JWT_TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/token | jq -r '.access_token')

# Lire une variable .env
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/v1/system/read_env?key=N8N_DB_PASSWORD
```

---

### 📚 Documentation Complète
- **[Architecture](docs/architecture.md)** : Schéma détaillé et flux de données.
- **[Déploiement](docs/deployment.md)** : Guide pas à pas pour déployer sur un VPS.
- **[Sécurité](docs/security.md)** : Bonnes pratiques et configuration avancée.

---

### 🤝 Contribuer
Les contributions sont les bienvenues ! Ouvrez une **Pull Request** ou un **Issue** pour :
- Signaler un bug.
- Proposer une amélioration.
- Ajouter une nouvelle fonctionnalité.

---

### 📜 Licence
Ce projet est sous licence **MIT** – voir [LICENSE](LICENSE) pour plus de détails.

---

---

## 🇬🇧 API-VPS: Secure API Gateway for Self-Hosted VPS

### 📌 Description
**API-VPS** is a **secure API gateway** designed to allow AI agents (like Pi Agent) to interact with a **self-hosted VPS** in a **controlled and secure** manner. It acts as an **abstraction layer** between the AI agent and system services (`.env` files, databases, logs), ensuring that:
- **The AI never directly reads system files** (only via the API).
- **Requests are validated** (whitelist of keys, paths, DB tables).
- **Access is restricted** (only via Tailscale or internal network).

---

### 🔐 Key Features
| Feature | Description |
|---------|-------------|
| **JWT Authentication** | Secure access via short-lived JWT tokens. |
| **Resource Whitelisting** | Only pre-approved `.env` keys, file paths, and DB tables are accessible. |
| **DB Query Validation** | Validates **schema**, **table**, and **column** before any query. |
| **Secret Masking** | Sensitive values (passwords, tokens) are **automatically masked**. |
| **Health Check Endpoint** | `/v1/health` to verify critical services status. |
| **Prometheus Metrics** | `/v1/metrics` for performance monitoring. |
| **Tailscale Access** | **Only accessible** via Tailscale network (no public exposure). |

---

### 🏗 Architecture
```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   💻 Pi Agent (PC)                                                             │
│        │                                                                       │
│        ▼ (Tailscale: 100.118.76.30)                                           │
│   🔒 TAILSCALE (100.75.226.13)                                                 │
│        │                                                                       │
│        ▼                                                                       │
│   🐳 DOCKER (Network `apps`)                                                   │
│        │                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌───────────────────────────────────┐  │
│   │  API Gateway │    │    n8n       │    │       PostgreSQL (n8n_db)          │  │
│   │ (FastAPI)    │◄──►│ (Workflow)   │◄──►│       Twenty DB                   │  │
│   └─────────────┘    └─────────────┘    └───────────────────────────────────┘  │
│        │                                                                       │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │  Monitoring                                                               │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │  │
│   │  │ Prometheus   │  │   Grafana    │  │     Uptime-Kuma                  │  │  │
│   │  │ (Port 9090)  │  │ (Port 3000)  │  │     (Port 3001)                  │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────────────┘  │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 📦 Requirements
- **VPS**: Ubuntu 22.04/24.04 LTS (or equivalent).
- **Docker**: [Docker Installation](https://docs.docker.com/engine/install/ubuntu/).
- **Docker Compose**: [Docker Compose Installation](https://docs.docker.com/compose/install/).
- **Tailscale**: [Tailscale Installation](https://tailscale.com/download) (for secure access).
- **Python 3.11+**: For local development (optional).

---

### 🚀 Quick Start

#### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/API-VPS.git
cd API-VPS
```

#### 2. Configure Environment
```bash
# Copy the example .env file
cp .env.example .env
nano .env  # Edit JWT_SECRET, DB_URL, etc.
```

#### 3. Start the API Gateway
```bash
docker compose up -d
```

#### 4. Test the API
```bash
# Get a JWT (for testing)
curl -X POST http://localhost:8000/v1/auth/token

# Test the /health endpoint
curl http://localhost:8000/v1/health
```

---

### 📡 Available Endpoints
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|------------------|
| POST | `/v1/auth/token` | Generate a JWT (disable in production) | ❌ None |
| GET | `/v1/system/read_env?key={key}` | Read an `.env` variable | ✅ JWT |
| GET | `/v1/system/read_file?file_path={path}` | Read a file | ✅ JWT |
| GET | `/v1/system/query_db?table={schema.table}` | DB query (3-level validation) | ✅ JWT |
| GET | `/v1/health` | Critical services status | ❌ None |
| GET | `/v1/metrics` | Prometheus metrics | ❌ None |

---

### 🔐 Security Configuration
#### 1. **Resource Whitelisting**
Edit `whitelist.yaml` to allow:
- **`.env` keys** (e.g., `N8N_DB_PASSWORD`).
- **File paths** (e.g., `/home/ubuntu/.env`).
- **DB tables** (e.g., `n8n_db.public.workflow_history`).

Example:
```yaml
users:
  pi-agent:
    allowed_env_keys: ["N8N_DB_PASSWORD", "BROWSERLESS_TOKEN"]
    allowed_file_paths: ["/home/ubuntu/.env"]
    allowed_db_tables: ["n8n_db.public.workflow_history"]
    masked_env_keys: ["N8N_DB_PASSWORD"]  # Mask sensitive values
```

#### 2. **JWT Authentication**
- **Generation**: `POST /v1/auth/token` (disable in production).
- **Usage**: Add the header `Authorization: Bearer <JWT>` to each request.

#### 3. **Network Access**
- **Tailscale only**: The API only listens on the Tailscale IP (`100.75.226.13`).
- **No public exposure**: No ports are bound to `0.0.0.0` or `162.19.246.165`.

---

### 📊 Monitoring
#### 1. **Prometheus + Grafana**
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3000](http://localhost:3000) (admin / `GRAFANA_ADMIN_PASSWORD`).
- **Setup**: See [docs/deployment.md](docs/deployment.md).

#### 2. **Uptime-Kuma**
- **URL**: [http://localhost:3001](http://localhost:3001)
- **Setup**: Add a monitor for `http://localhost:8000/v1/health`.

---

### 🛠 Local Development
#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Start the API Locally
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Test with `curl`
```bash
# Generate a JWT
JWT_TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/token | jq -r '.access_token')

# Read an .env variable
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/v1/system/read_env?key=N8N_DB_PASSWORD
```

---

### 📚 Full Documentation
- **[Architecture](docs/architecture.md)**: Detailed schema and data flows.
- **[Deployment](docs/deployment.md)**: Step-by-step guide to deploy on a VPS.
- **[Security](docs/security.md)**: Best practices and advanced configuration.

---

### 🤝 Contributing
Contributions are welcome! Open a **Pull Request** or **Issue** to:
- Report a bug.
- Suggest an improvement.
- Add a new feature.

---

### 📜 License
This project is licensed under **MIT** – see [LICENSE](LICENSE) for details.
