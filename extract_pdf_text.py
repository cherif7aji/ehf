#!/usr/bin/env python3
"""
Script pour extraire le texte des PDFs digitalement nés dans le dossier EHFs
"""

import os
import sys
from pathlib import Path
import PyPDF2
import pdfplumber
from typing import List, Tuple

def extract_text_pypdf2(pdf_path: str) -> str:
    """Extrait le texte d'un PDF avec PyPDF2"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text + "\n"
    except Exception as e:
        print(f"Erreur avec PyPDF2 pour {pdf_path}: {e}")
    return text

def extract_text_pdfplumber(pdf_path: str) -> str:
    """Extrait le texte d'un PDF avec pdfplumber (plus précis)"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text + "\n"
    except Exception as e:
        print(f"Erreur avec pdfplumber pour {pdf_path}: {e}")
    return text

def extract_text_from_pdf(pdf_path: str, method: str = "pdfplumber") -> str:
    """Extrait le texte d'un PDF avec la méthode choisie"""
    if method == "pdfplumber":
        return extract_text_pdfplumber(pdf_path)
    else:
        return extract_text_pypdf2(pdf_path)

def process_ehfs_folder(ehfs_folder: str = "EHFs", output_folder: str = "extracted_texts") -> None:
    """Traite tous les PDFs dans le dossier EHFs"""
    
    # Créer le dossier de sortie s'il n'existe pas
    Path(output_folder).mkdir(exist_ok=True)
    
    # Lister tous les fichiers PDF
    pdf_files = list(Path(ehfs_folder).glob("*.pdf"))
    
    if not pdf_files:
        print(f"Aucun fichier PDF trouvé dans {ehfs_folder}")
        return
    
    print(f"Trouvé {len(pdf_files)} fichiers PDF à traiter...")
    
    results = []
    
    for pdf_file in pdf_files:
        print(f"\nTraitement de {pdf_file.name}...")
        
        # Extraire le texte
        text = extract_text_from_pdf(str(pdf_file))
        
        if text.strip():
            # Sauvegarder le texte extrait
            output_file = Path(output_folder) / f"{pdf_file.stem}_extracted.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Texte extrait de: {pdf_file.name}\n")
                f.write("=" * 50 + "\n")
                f.write(text)
            
            word_count = len(text.split())
            results.append((pdf_file.name, word_count, "Succès"))
            print(f"  ✓ Texte extrait ({word_count} mots) -> {output_file}")
        else:
            results.append((pdf_file.name, 0, "Aucun texte trouvé"))
            print(f"  ✗ Aucun texte extrait")
    
    # Résumé final
    print("\n" + "=" * 60)
    print("RÉSUMÉ DE L'EXTRACTION")
    print("=" * 60)
    
    for filename, word_count, status in results:
        print(f"{filename:<30} | {word_count:>6} mots | {status}")
    
    total_words = sum(count for _, count, _ in results)
    successful = sum(1 for _, _, status in results if status == "Succès")
    
    print(f"\nTotal: {successful}/{len(results)} fichiers traités avec succès")
    print(f"Total de mots extraits: {total_words}")

def main():
    """Fonction principale"""
    print("Script d'extraction de texte des PDFs digitalement nés")
    print("=" * 50)
    
    # Vérifier que le dossier EHFs existe
    if not Path("EHFs").exists():
        print("Erreur: Le dossier 'EHFs' n'existe pas dans le répertoire courant")
        sys.exit(1)
    
    # Traiter tous les PDFs
    process_ehfs_folder()
    
    print("\nExtraction terminée!")

if __name__ == "__main__":
    main()
