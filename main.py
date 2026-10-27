#!/usr/bin/env python3
"""
API-VPS: Secure API Gateway for Self-Hosted VPS

Ce fichier est un exemple de code pour l'API Gateway utilisant FastAPI.
Il inclut :
- Authentification JWT
- Validation des requêtes (whitelist)
- Endpoints pour lire les variables .env, fichiers, et requêtes DB
- Endpoint /health pour le monitoring
- Endpoint /metrics pour Prometheus

Pour l'utiliser :
1. Copiez ce fichier dans /home/ubuntu/API-VPS/main.py
2. Installez les dépendances : pip install -r requirements.txt
3. Démarrez avec : uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import re
import yaml
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(".env")

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "vps-gateway-secret-2026-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 15))
DB_URL = os.getenv("DB_URL", "postgresql://n8n:n8n@n8n_db:5432/n8n_db")

# Charger la whitelist
try:
    with open("whitelist.yaml", "r") as f:
        WHITELIST = yaml.safe_load(f)
except FileNotFoundError:
    WHITELIST = {
        "users": {
            "pi-agent": {
                "scope": ["read:system", "read:db"],
                "allowed_env_keys": ["N8N_DB_PASSWORD"],
                "allowed_file_paths": ["/home/ubuntu/.env"],
                "allowed_db_tables": ["n8n_db.public.workflow_history"],
                "masked_env_keys": ["N8N_DB_PASSWORD"],
                "forbidden_columns": ["password", "api_key", "token", "secret"]
            }
        },
        "tailscale": {
            "allowed_ips": ["100.75.226.13", "100.118.76.30", "fd7a:115c:a1e0::/64"]
        },
        "naming_conventions": {
            "db": {
                "schema_pattern": "^[a-z0-9_]+$",
                "table_pattern": "^[a-z0-9_]+$",
                "column_pattern": "^[a-z0-9_]+$"
            }
        }
    }

# Modèles Pydantic
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ErrorResponse(BaseModel):
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None

class EnvResponse(BaseModel):
    key: str
    value: Optional[str] = None
    masked: bool

class FileResponse(BaseModel):
    file_path: str
    encoding: str
    content: Optional[str] = None
    truncated: bool

class DBQueryResponse(BaseModel):
    table: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    count: int

# Initialisation FastAPI
app = FastAPI(
    title="API-VPS",
    description="Passerelle API sécurisée pour VPS auto-hébergé",
    version="1.0.0"
)

# Sécurité JWT
security = HTTPBearer()

# Fonctions utilitaires
def verify_jwt(token: str) -> Dict[str, Any]:
    """Vérifie et décode un JWT."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Token expired", "code": "TOKEN_EXPIRED"}
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": f"Invalid token: {str(e)}", "code": "INVALID_TOKEN"}
        )

def is_key_allowed(user: str, key: str) -> bool:
    """Vérifie si une clé .env est autorisée pour l'utilisateur."""
    if user not in WHITELIST["users"]:
        return False
    return key in WHITELIST["users"][user]["allowed_env_keys"]

def is_path_allowed(user: str, path: str) -> bool:
    """Vérifie si un chemin de fichier est autorisé pour l'utilisateur."""
    if user not in WHITELIST["users"]:
        return False
    return path in WHITELIST["users"][user]["allowed_file_paths"]

def is_table_allowed(user: str, schema: str, table: str) -> bool:
    """Vérifie si une table DB est autorisée pour l'utilisateur."""
    if user not in WHITELIST["users"]:
        return False
    full_table = f"{schema}.{table}"
    return full_table in WHITELIST["users"][user]["allowed_db_tables"]

def is_column_allowed(user: str, schema: str, table: str, column: str) -> bool:
    """Vérifie si une colonne DB est autorisée pour l'utilisateur."""
    if column in WHITELIST["users"][user]["forbidden_columns"]:
        return False
    return True

def mask_value(user: str, key: str, value: str) -> Optional[str]:
    """Masque les valeurs sensibles."""
    if user in WHITELIST["users"] and key in WHITELIST["users"][user]["masked_env_keys"]:
        return "***MASKED***"
    return value

def get_db_connection():
    """Retourne une connexion PostgreSQL."""
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": f"Database unavailable: {str(e)}", "code": "DB_UNAVAILABLE"}
        )

# Endpoints
@app.post("/v1/auth/token", response_model=Token)
async def generate_token():
    """Génère un JWT pour les tests (à désactiver en production)."""
    payload = {
        "sub": "pi-agent",
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "scope": WHITELIST["users"]["pi-agent"]["scope"]
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/v1/system/read_env", response_model=EnvResponse)
async def read_env(
    key: str = Query(..., pattern="^[a-zA-Z_][a-zA-Z0-9_]*$", max_length=64),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Lire une variable d'environnement."""
    payload = verify_jwt(credentials.credentials)
    user = payload["sub"]
    
    if not is_key_allowed(user, key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Key '{key}' not allowed for user '{user}'", "code": "FORBIDDEN_KEY"}
        )
    
    value = os.getenv(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Key '{key}' not found", "code": "KEY_NOT_FOUND"}
        )
    
    return EnvResponse(
        key=key,
        value=mask_value(user, key, value),
        masked=key in WHITELIST["users"][user]["masked_env_keys"]
    )

@app.get("/v1/system/read_file", response_model=FileResponse)
async def read_file(
    file_path: str = Query(..., max_length=256),
    encoding: str = Query("utf-8", enum=["utf-8", "base64", "hex"]),
    max_lines: int = Query(100, ge=1, le=1000),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Lire un fichier local."""
    payload = verify_jwt(credentials.credentials)
    user = payload["sub"]
    
    if not is_path_allowed(user, file_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Path '{file_path}' not allowed for user '{user}'", "code": "FORBIDDEN_PATH"}
        )
    
    try:
        with open(file_path, "r", encoding=encoding) as f:
            lines = f.readlines()
            content = "".join(lines[:max_lines])
            truncated = len(lines) > max_lines
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"File '{file_path}' not found", "code": "FILE_NOT_FOUND"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"File read error: {str(e)}", "code": "FILE_READ_ERROR"}
        )
    
    return FileResponse(
        file_path=file_path,
        encoding=encoding,
        content=content,
        truncated=truncated
    )

@app.get("/v1/system/query_db", response_model=DBQueryResponse)
async def query_db(
    table: str = Query(..., max_length=128),
    columns: str = Query("*", max_length=256),
    condition: str = Query("", max_length=256),
    limit: int = Query(10, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Exécuter une requête DB en lecture seule."""
    payload = verify_jwt(credentials.credentials)
    user = payload["sub"]
    
    # Parser schema.table
    if "." not in table:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Table must be in format 'schema.table'", "code": "INVALID_TABLE_FORMAT"}
        )
    schema, table_name = table.split(".", 1)
    
    if not is_table_allowed(user, schema, table_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Table '{schema}.{table_name}' not allowed for user '{user}'", "code": "FORBIDDEN_TABLE"}
        )
    
    # Valider les colonnes
    requested_columns = [col.strip() for col in columns.split(",") if col.strip()]
    for col in requested_columns:
        if col != "*" and not is_column_allowed(user, schema, table_name, col):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"Column '{col}' not allowed", "code": "FORBIDDEN_COLUMN"}
            )
    
    # Valider la condition (si fournie)
    if condition:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[a-zA-Z0-9_\-\.]+$", condition):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": f"Condition format not allowed: {condition}", "code": "INVALID_CONDITION"}
            )
        condition_col = condition.split()[0]
        if not is_column_allowed(user, schema, table_name, condition_col):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"Column '{condition_col}' in condition not allowed", "code": "FORBIDDEN_COLUMN_IN_CONDITION"}
            )
    
    # Construire la requête SQL
    try:
        if columns == "*":
            select_columns = sql.SQL("*")
        else:
            select_columns = sql.SQL(",").join(sql.Identifier(col) for col in requested_columns)
        
        where_clause = sql.SQL("")
        if condition:
            where_clause = sql.SQL(" WHERE {condition}").format(condition=sql.SQL(condition))
        
        query = sql.SQL("SELECT {select_columns} FROM {schema}.{table}{where_clause} LIMIT {limit}").format(
            select_columns=select_columns,
            schema=sql.Identifier(schema),
            table=sql.Identifier(table_name),
            where_clause=where_clause,
            limit=sql.Literal(limit)
        )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return DBQueryResponse(
            table=f"{schema}.{table_name}",
            columns=requested_columns if columns != "*" else [],
            rows=rows,
            count=len(rows)
        )
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": f"Database error: {str(e)}", "code": "DB_ERROR"}
        )

@app.get("/v1/health")
async def health_check():
    """Vérifie l'état des services critiques."""
    services = {}
    
    # Vérifier PostgreSQL (n8n_db)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        services["PostgreSQL (n8n_db)"] = {"status": "healthy", "details": "Connection successful"}
    except Exception as e:
        services["PostgreSQL (n8n_db)"] = {"status": "unhealthy", "details": str(e)}
    
    # Vérifier n8n (si accessible)
    try:
        import requests
        response = requests.get("http://n8n:5678/api/v1/health", timeout=5)
        if response.status_code == 200:
            services["n8n"] = {"status": "healthy", "details": "API accessible"}
        else:
            services["n8n"] = {"status": "unhealthy", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        services["n8n"] = {"status": "unhealthy", "details": str(e)}
    
    # Vérifier Caddy (si accessible)
    try:
        response = requests.get("http://localhost:80", timeout=5)
        if response.status_code == 200:
            services["Caddy"] = {"status": "healthy", "details": "HTTP 200 OK"}
        else:
            services["Caddy"] = {"status": "unhealthy", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        services["Caddy"] = {"status": "unhealthy", "details": str(e)}
    
    unhealthy_services = [name for name, status in services.items() if status["status"] != "healthy"]
    
    if unhealthy_services:
        return {
            "status": "unhealthy",
            "services": services,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "healthy",
            "services": services,
            "timestamp": datetime.utcnow().isoformat()
        }

# Pour démarrer l'API en local (développement)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
