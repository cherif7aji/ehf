#!/bin/bash

echo "🧪 Test de la structure Docker..."

# Vérifier les fichiers Docker
echo "📁 Fichiers Docker présents :"
ls -la Dockerfile docker-compose.yml requirements.txt .dockerignore 2>/dev/null || echo "❌ Fichiers manquants"

# Vérifier la syntaxe du Dockerfile
echo "🔍 Vérification Dockerfile :"
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile présent"
    grep -E "FROM|WORKDIR|COPY|RUN|EXPOSE|CMD" Dockerfile
else
    echo "❌ Dockerfile manquant"
fi

# Vérifier docker-compose.yml
echo "🔍 Vérification docker-compose.yml :"
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml présent"
    grep -E "version|services|ports|build" docker-compose.yml
else
    echo "❌ docker-compose.yml manquant"
fi

# Vérifier requirements.txt
echo "🔍 Vérification requirements.txt :"
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt présent"
    cat requirements.txt
else
    echo "❌ requirements.txt manquant"
fi

echo "✅ Structure Docker prête pour le déploiement !"
