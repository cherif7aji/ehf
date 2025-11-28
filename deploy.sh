#!/bin/bash

# Script de déploiement pour EHF Analyzer
echo "🚀 Déploiement EHF Analyzer..."

# Arrêter les conteneurs existants
echo "🛑 Arrêt des conteneurs existants..."
docker-compose down

# Construire et démarrer les nouveaux conteneurs
echo "🔨 Construction et démarrage des conteneurs..."
docker-compose up -d --build

# Vérifier le statut
echo "✅ Vérification du statut..."
docker-compose ps

echo "🌐 Application disponible sur http://localhost:1000"
echo "📊 Logs: docker-compose logs -f"
