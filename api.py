#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import os
import subprocess
import shutil
from datetime import datetime

app = FastAPI(title="EHF Analyzer API", version="1.0.0")

def charger_donnees_ehf(ehf_name: str):
    """Charge les données d'un EHF"""
    try:
        with open(f"formalites_json/{ehf_name}/{ehf_name}_par_proprietaire.json", 'r') as f:
            proprietaires = json.load(f)
        with open(f"formalites_json/{ehf_name}/{ehf_name}_charges_actives.json", 'r') as f:
            charges_data = json.load(f)
        return proprietaires, charges_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"EHF {ehf_name} non trouvé")

def est_charge_expiree(charge):
    """Vérifie si une charge est expirée"""
    aujourd_hui = datetime.now()
    toutes_dates = []
    
    for sf in charge.get('sous_formalites', []):
        toutes_dates.extend(sf.get('dates_exigibilite', []))
        toutes_dates.extend(sf.get('dates_effet', []))
    
    if not toutes_dates:
        return False
    
    try:
        for date_str in toutes_dates:
            if datetime.strptime(date_str, '%d/%m/%Y') > aujourd_hui:
                return False
        return True
    except:
        return False

@app.get("/", response_class=HTMLResponse)
def root():
    """Interface web principale"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/proprietaires/{ehf_name}")
def get_proprietaires(ehf_name: str):
    """Retourne les propriétaires actuels d'un EHF"""
    proprietaires, _ = charger_donnees_ehf(ehf_name)
    
    result = []
    for proprietaire, data in proprietaires.items():
        biens = []
        for bien in data['biens']:
            biens.append({
                "commune": bien['commune'],
                "adresse": bien['adresse'],
                "lot": bien['lot'],
                "volume": bien['volume']
            })
        result.append({
            "proprietaire": proprietaire,
            "biens": biens
        })
    
    return {"ehf": ehf_name, "proprietaires": result}

@app.get("/charges/{ehf_name}")
def get_charges(ehf_name: str):
    """Retourne les charges actives et expirées d'un EHF"""
    _, charges_data = charger_donnees_ehf(ehf_name)
    
    charges_actives = charges_data.get('charges_actives', [])
    charges_vraiment_actives = []
    charges_expirees = []
    
    for charge in charges_actives:
        charge_info = {
            "titre": charge['titre'],
            "pages": f"{charge['page_debut']}-{charge['page_fin']}"
        }
        
        if est_charge_expiree(charge):
            charges_expirees.append(charge_info)
        else:
            charges_vraiment_actives.append(charge_info)
    
    return {
        "ehf": ehf_name,
        "charges_actives": charges_vraiment_actives,
        "charges_expirees": charges_expirees,
        "resume": {
            "nb_actives": len(charges_vraiment_actives),
            "nb_expirees": len(charges_expirees)
        }
    }

@app.post("/upload")
async def upload_ehf(file: UploadFile = File(...)):
    """Upload et analyse d'un nouveau fichier EHF"""
    
    # Vérifier le type de fichier
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
    
    # Générer un nom unique pour l'EHF
    import time
    timestamp = int(time.time())
    ehf_name = f"EHF_UPLOAD_{timestamp}"
    
    try:
        # Sauvegarder le fichier uploadé
        os.makedirs("EHFs", exist_ok=True)
        file_path = f"EHFs/{ehf_name}.pdf"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Lancer l'analyse avec simple_pdf_extract.py
        result = subprocess.run([
            "python", "simple_pdf_extract.py", file_path
        ], capture_output=True, text=True)
        
        # Supprimer le fichier uploadé après analyse
        try:
            os.remove(file_path)
        except:
            pass  # Ignorer les erreurs de suppression
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {result.stderr}")
        
        return {"message": "Fichier analysé avec succès", "ehf_name": ehf_name}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
