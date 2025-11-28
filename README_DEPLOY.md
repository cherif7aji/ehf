# 🚀 Déploiement EHF Analyzer

## 📋 Prérequis VPS

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installer Docker Compose (Plugin)
# Docker Compose v2 est maintenant intégré comme plugin Docker

# Redémarrer la session
logout
```

## 🔧 Déploiement

```bash
# 1. Cloner le projet
git clone <votre-repo> ehf-analyzer
cd ehf-analyzer

# 2. Déployer avec Docker Compose
./deploy.sh

# OU manuellement :
docker compose up -d --build
```

## 🌐 Accès

- **URL** : http://votre-vps-ip:1000
- **Port** : 1000 (mappé vers 8000 dans le conteneur)

## 📊 Gestion

```bash
# Voir les logs
docker compose logs -f

# Redémarrer
docker compose restart

# Arrêter
docker compose down

# Mettre à jour
git pull
docker compose up -d --build
```

## 🔒 Sécurité (Optionnel)

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    
    location / {
        proxy_pass http://localhost:1000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall

```bash
# Ouvrir le port 1000
sudo ufw allow 1000

# OU pour Nginx seulement
sudo ufw allow 80
sudo ufw allow 443
```
