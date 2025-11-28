#!/usr/bin/env python3
"""
EHF Analyzer - Démarrage simple
Usage: python start.py
"""
import subprocess
import sys
import os

def main():
    print("🚀 Démarrage EHF Analyzer API...")
    
    # Vérifier que les données existent
    if not os.path.exists("formalites_json"):
        print("📋 Génération des données EHF...")
        subprocess.run([sys.executable, "simple_pdf_extract.py"])
    
    print("🌐 Lancement de l'interface web sur http://localhost:8000")
    print("📖 Fonctionnalités:")
    print("   🏠 Interface web interactive")
    print("   👤 Propriétaires actuels par EHF")
    print("   ⚖️  Charges actives/expirées avec vérification des dates")
    print("   📊 Analyse en temps réel")
    print("\n💡 Ouvrez votre navigateur sur:")
    print("   http://localhost:8000")
    print("\n🛑 Ctrl+C pour arrêter")
    
    # Lancer l'API
    subprocess.run([sys.executable, "api.py"])

if __name__ == "__main__":
    main()
