# 📤 Pousser vers GitHub

## 1. Créer un dépôt sur GitHub
1. Aller sur https://github.com
2. Cliquer sur "New repository"
3. Nom : `ehf-analyzer`
4. Description : `EHF Analyzer - Analyseur d'États Hypothécaires Fonciers avec interface web`
5. Cocher "Public" ou "Private" selon votre choix
6. **NE PAS** cocher "Initialize with README" (on a déjà nos fichiers)
7. Cliquer "Create repository"

## 2. Ajouter le remote et pousser

```bash
# Remplacer USERNAME par votre nom d'utilisateur GitHub
git remote add origin https://github.com/USERNAME/ehf-analyzer.git

# Pousser le code
git branch -M main
git push -u origin main
```

## 3. Exemple complet

Si votre nom d'utilisateur GitHub est `cherif7aji` :

```bash
cd /home/cherif/Desktop/ocr2
git remote add origin https://github.com/cherif7aji/ehf-analyzer.git
git branch -M main
git push -u origin main
```

## 4. Après le push

Votre projet sera disponible sur :
`https://github.com/USERNAME/ehf-analyzer`

## 5. Déploiement sur VPS

Une fois sur GitHub, sur votre VPS :

```bash
git clone https://github.com/USERNAME/ehf-analyzer.git
cd ehf-analyzer
./deploy.sh
```

L'application sera accessible sur `http://votre-vps-ip:1000`
