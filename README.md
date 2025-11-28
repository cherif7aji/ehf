# EHF Analyzer API

API FastAPI pour analyser les EHF (États Hypothécaires Fonciers).

## 🚀 Démarrage rapide

```bash
python start.py
```

## 📡 API Endpoints

### 1. Propriétaires actuels
```
GET /proprietaires/{ehf_name}
```
Retourne les propriétaires actuels avec leurs biens (commune, adresse, lot, volume).

### 2. Charges actives/expirées  
```
GET /charges/{ehf_name}
```
Retourne les charges actives et expirées avec vérification des dates.

## 💡 Exemples

```bash
curl http://localhost:8000/proprietaires/EHF1
curl http://localhost:8000/charges/EHF1
```

## 📁 Structure

- `api.py` - API FastAPI principale
- `simple_pdf_extract.py` - Extraction des données PDF
- `start.py` - Script de démarrage
- `formalites_json/` - Données extraites des EHF
