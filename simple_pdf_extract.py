#!/usr/bin/env python3
import os, pdfplumber, re, json
from typing import List, Dict

def get_formalites_pages(pdf_path: str) -> List[int]:
    patterns = [r"Relevé\s+des\s+formalités\s*-\s*(Publication|Volumétrie|Copropriété|Lotissement|Charge|Formalités en attente|rejet définitif)"]
    formalites_pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                if page_text := page.extract_text():
                    if any(re.search(p, re.sub(r'\s+', ' ', page_text), re.IGNORECASE) for p in patterns):
                        formalites_pages.append(page_num + 1)
    except: pass
    return formalites_pages

def extraire_immeubles_flux(pdf_path: str, nb_pages_max: int = 5) -> List[Dict]:
    immeubles_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(min(nb_pages_max, len(pdf.pages))):
                if (page_text := pdf.pages[page_num].extract_text()) and "Immeubles issus de la demande - formalités du flux" in page_text:
                    for j, table in enumerate(pdf.pages[page_num].extract_tables() or []):
                        immeubles_data.append({'page': page_num + 1, 'table_numero': j + 1, 'donnees': table, 'nb_lignes': len(table), 'nb_colonnes': len(table[0]) if table else 0, 'type': 'immeubles_flux'})
    except: pass
    return immeubles_data


def get_formalites_completes(pdf_path: str, formalites_pages: List[int]) -> List[Dict]:
    if not formalites_pages: return []
    formalites, used_pages = [], set()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for start_page in formalites_pages:
                if start_page in used_pages: continue
                if not (page_text := pdf.pages[start_page - 1].extract_text()): continue
                
                categorie = (re.search(r"Relevé\s+des\s+formalités\s*-\s*([^\n\r]+?)(?:\s+PAGE|\n|\r|$)", page_text, re.IGNORECASE) or type('', (), {'group': lambda x: "Non classée"})).group(1).strip()
                end_page = start_page
                for pattern in [r"PAGE\s+(\d+)\s+[ÀAà]\s+PAGE\s+(\d+)"]:
                    if match := re.search(pattern, page_text, re.IGNORECASE):
                        if int(match.group(1)) == start_page: end_page = int(match.group(2)); break
                
                texte_complet, tables_formalite = "", []
                for page_num in range(start_page, end_page + 1):
                    if page_num <= len(pdf.pages):
                        page = pdf.pages[page_num - 1]
                        if page_content := page.extract_text(): texte_complet += f"\n=== Page {page_num} ===\n{page_content}\n"
                        for j, table in enumerate(page.extract_tables() or []): tables_formalite.append({'page': page_num, 'table_numero': j + 1, 'donnees': table, 'nb_lignes': len(table), 'nb_colonnes': len(table[0]) if table else 0})
                
                formalite = {'page_debut': start_page, 'page_fin': end_page, 'categorie': categorie, 'texte': texte_complet.strip(), 'tables': tables_formalite, 'nb_tables': len(tables_formalite)}
                if categorie.lower() == 'publication': formalite['proprietaires'] = extraire_proprietaires_publication(formalite)
                formalites.append(formalite)
                used_pages.update(range(start_page, end_page + 1))
    except: pass
    return formalites

def extraire_proprietaires_publication(formalite: Dict) -> Dict:
    if formalite['categorie'].lower() != 'publication': return {}
    
    result = {'disposants': [], 'beneficiaires': [], 'immeubles': [], 'dates': [], 'prix': None}
    
    for table in formalite['tables']:
        donnees = table['donnees']
        if not donnees: continue
        
        # Extraire toutes les dates (peut y en avoir plusieurs)
        for row in donnees:
            for cell in row:
                if cell:
                    cell_str = str(cell).lower()
                    if 'date de l\'acte' in cell_str:
                        if match := re.search(r'date de l\'acte\s*:\s*(\d{2}/\d{2}/\d{4})', cell_str):
                            if match.group(1) not in [d.get('date_acte') for d in result['dates']]:
                                result['dates'].append({'date_acte': match.group(1)})
                    if 'date de dépôt' in cell_str:
                        if match := re.search(r'date de dépôt\s*:\s*(\d{2}/\d{2}/\d{4})', cell_str):
                            for date_entry in result['dates']:
                                if 'date_depot' not in date_entry:
                                    date_entry['date_depot'] = match.group(1)
                                    break
                            else:
                                result['dates'].append({'date_depot': match.group(1)})
        
        # Extraire Disposants (peut y en avoir plusieurs)
        if any('disposant' in str(cell).lower() or 'donateur' in str(cell).lower() for row in donnees for cell in row if cell):
            for row in donnees[1:]:
                if len(row) >= 2 and row[1] and str(row[1]).strip():
                    nom = str(row[1]).strip()
                    if not any(x in nom.lower() for x in ['disposant', 'donateur', 'numéro', 'bénéficiaire']):
                        numero_id = str(row[2]).strip() if len(row) > 2 and row[2] and str(row[2]).strip() != '-' else None
                        if not any(d['nom'] == nom for d in result['disposants']):
                            result['disposants'].append({'nom': nom, 'numero_id': numero_id})
        
        # Extraire Bénéficiaires (seulement dans les tables avec en-tête exact "Bénéficiaire, Donataire")
        # Vérifier que c'est bien une table de bénéficiaires et pas une table d'immeubles
        is_beneficiaire_table = False
        for row in donnees:
            if any(cell and 'bénéficiaire, donataire' in str(cell).lower() for cell in row):
                is_beneficiaire_table = True
                break
        
        if is_beneficiaire_table:
            for row in donnees[1:]:
                if len(row) >= 2 and row[1] and str(row[1]).strip():
                    nom = str(row[1]).strip()
                    # Filtrer les faux positifs
                    if (not any(x in nom.lower() for x in ['bénéficiaire', 'donataire', 'date', 'disposant', 'paris', 'transfert', 'page', 'numéro']) 
                        and len(nom) > 2 and not re.match(r'^[A-Z]{2,3}\s+\d+$', nom)):  # Éviter "BD 10", etc.
                        date_naissance = str(row[2]).strip() if len(row) > 2 and row[2] and str(row[2]).strip() != '-' else None
                        # Vérifier que la date de naissance est valide
                        if date_naissance and not re.match(r'\d{2}/\d{2}/\d{4}', date_naissance):
                            date_naissance = None
                        
                        # Extraire le numéro d'identité (colonne 3 ou suivante)
                        numero_identite = None
                        for col_idx in range(3, len(row)):
                            if row[col_idx] and str(row[col_idx]).strip() and str(row[col_idx]).strip() != '-':
                                cell_value = str(row[col_idx]).strip()
                                # Vérifier si c'est un numéro d'identité (format numérique)
                                if re.match(r'^\d{3}\s*\d{3}\s*\d{3}$|^\d{9,}$', cell_value.replace(' ', '')):
                                    numero_identite = cell_value
                                    break
                        
                        if not any(b['nom'] == nom for b in result['beneficiaires']):
                            result['beneficiaires'].append({'nom': nom, 'date_naissance': date_naissance, 'numero_identite': numero_identite})
        
        # Extraire Immeubles (gérer les tableaux fragmentés entre pages)
        if any('immeuble' in str(cell).lower() for row in donnees for cell in row if cell):
            # Trouver les positions des colonnes Volume et Lot dans l'en-tête
            volume_col, lot_col = None, None
            for i, row in enumerate(donnees):
                for j, cell in enumerate(row):
                    if cell and str(cell).strip().lower() == 'volume':
                        volume_col = j
                    elif cell and str(cell).strip().lower() == 'lot':
                        lot_col = j
                if volume_col is not None and lot_col is not None:
                    break
            
            for row in donnees:
                if len(row) >= 1 and row[0]:
                    cell0 = str(row[0]).strip()
                    
                    # Ligne avec bénéficiaire et immeubles
                    if 'bénéficiaire' in cell0.lower() and (':' in cell0):
                        # Extraire le type de droit (toute propriété, usufruit, etc.)
                        type_droit = cell0.split('-', 1)[1].strip() if '-' in cell0 else "Non spécifié"
                        beneficiaire_num = re.search(r'bénéficiaire\s*:\s*(\d+)', cell0.lower())
                        beneficiaire_ref = beneficiaire_num.group(1) if beneficiaire_num else "1"
                        
                        # Extraire volume et lots selon les colonnes identifiées
                        volume = str(row[volume_col]).strip() if volume_col and len(row) > volume_col and row[volume_col] else None
                        lots = str(row[lot_col]).strip() if lot_col and len(row) > lot_col and row[lot_col] else None
                        
                        # Concaténer toutes les colonnes non-nulles entre la colonne 1 et la colonne Volume pour former l'adresse
                        adresse_parts = []
                        start_col = 1  # Commencer après la colonne bénéficiaire
                        end_col = volume_col if volume_col else len(row)
                        
                        for i in range(start_col, end_col):
                            if i < len(row) and row[i] and str(row[i]).strip():
                                adresse_parts.append(str(row[i]).strip())
                        
                        # Approche universelle : premier élément = commune, reste = adresse
                        commune, adresse = None, None
                        if adresse_parts:
                            if len(adresse_parts) >= 2:
                                commune = adresse_parts[0]
                                adresse = ' '.join(adresse_parts[1:])
                            elif len(adresse_parts) == 1:
                                commune = adresse_parts[0]
                                adresse = None
                        
                        immeuble = {
                            'beneficiaire_ref': beneficiaire_ref,
                            'type_droit': type_droit,
                            'commune': commune,
                            'adresse': adresse,
                            'volume': volume,
                            'lots': lots,
                            'page': table.get('page')
                        }
                        result['immeubles'].append(immeuble)
                    
                    # Ligne avec prix
                    elif 'prix' in cell0.lower() and 'eur' in cell0.lower():
                        if match := re.search(r'prix[^:]*:\s*([\d\s,\.]+)\s*eur', cell0.lower()):
                            result['prix'] = match.group(1).strip()
    
    return result

def determiner_proprietaires_actuels(formalites: List[Dict]) -> Dict:
    """
    Détermine le propriétaire actuel de chaque lot/volume basé sur la date d'acte la plus récente
    """
    from datetime import datetime
    
    # Dictionnaire pour stocker les propriétaires par immeuble
    proprietaires_actuels = {}
    
    # Parcourir toutes les formalités de type Publication
    for formalite in formalites:
        if formalite.get('categorie', '').lower() != 'publication' or 'proprietaires' not in formalite:
            continue
            
        proprietaires = formalite['proprietaires']
        
        # Vérifier qu'il y a bien des changements de propriété (disposant requis)
        if not proprietaires.get('disposants'):
            continue
            
        # Si pas de bénéficiaires extraits automatiquement, essayer de les extraire manuellement
        beneficiaires = proprietaires.get('beneficiaires', [])
        if not beneficiaires:
            # Chercher dans les tables pour extraire les bénéficiaires manuellement
            for table in formalite.get('tables', []):
                donnees = table.get('donnees', [])
                # Chercher une table avec "Bénéficiaires, Donataires"
                for i, row in enumerate(donnees):
                    if any(cell and 'bénéficiaires, donataires' in str(cell).lower() for cell in row):
                        # Extraire les bénéficiaires des lignes suivantes
                        for j in range(i + 1, len(donnees)):
                            beneficiaire_row = donnees[j]
                            if len(beneficiaire_row) >= 2 and beneficiaire_row[1]:
                                nom = str(beneficiaire_row[1]).strip()
                                if nom and not any(x in nom.lower() for x in ['bénéficiaire', 'donataire']):
                                    date_naissance = str(beneficiaire_row[2]).strip() if len(beneficiaire_row) > 2 and beneficiaire_row[2] else None
                                    
                                    # Extraire le numéro d'identité
                                    numero_identite = None
                                    for col_idx in range(3, len(beneficiaire_row)):
                                        if beneficiaire_row[col_idx] and str(beneficiaire_row[col_idx]).strip() != '-':
                                            cell_value = str(beneficiaire_row[col_idx]).strip()
                                            if re.match(r'^\d{3}\s*\d{3}\s*\d{3}$|^\d{9,}$', cell_value.replace(' ', '')):
                                                numero_identite = cell_value
                                                break
                                    
                                    beneficiaires.append({'nom': nom, 'date_naissance': date_naissance, 'numero_identite': numero_identite})
                        break
        
        # Si toujours pas de bénéficiaires, continuer (peut-être une radiation ou autre)
        if not beneficiaires:
            continue
            
        # Récupérer la date d'acte la plus récente de cette formalité
        dates = proprietaires.get('dates', [])
        if not dates:
            continue
            
        date_acte_str = None
        for date_entry in dates:
            if 'date_acte' in date_entry:
                date_acte_str = date_entry['date_acte']
                break
                
        if not date_acte_str:
            continue
            
        try:
            date_acte = datetime.strptime(date_acte_str, '%d/%m/%Y')
        except:
            continue
            
        # Traiter chaque immeuble de cette formalité
        for immeuble in proprietaires.get('immeubles', []):
            commune = immeuble.get('commune', '')
            adresse = immeuble.get('adresse', '')
            lots = immeuble.get('lots', '')
            volume = immeuble.get('volume', '')
            type_droit = immeuble.get('type_droit', '')
            beneficiaire_ref = immeuble.get('beneficiaire_ref', '1')
            
            # Trouver le nom, la date de naissance et le numéro d'identité du bénéficiaire
            beneficiaire_nom = None
            beneficiaire_date_naissance = None
            beneficiaire_numero_identite = None
            try:
                beneficiaire_num = int(beneficiaire_ref)
                # Si on a des bénéficiaires, essayer de trouver le bon
                if beneficiaires:
                    # Si le numéro correspond à un index valide (en base 1)
                    if beneficiaire_num <= len(beneficiaires):
                        beneficiaire_data = beneficiaires[beneficiaire_num - 1]
                        beneficiaire_nom = beneficiaire_data['nom']
                        beneficiaire_date_naissance = beneficiaire_data.get('date_naissance')
                        beneficiaire_numero_identite = beneficiaire_data.get('numero_identite')
                    else:
                        # Si le numéro est trop grand, prendre le dernier
                        beneficiaire_data = beneficiaires[-1]
                        beneficiaire_nom = beneficiaire_data['nom']
                        beneficiaire_date_naissance = beneficiaire_data.get('date_naissance')
                        beneficiaire_numero_identite = beneficiaire_data.get('numero_identite')
            except:
                pass
            
            # Si pas trouvé, prendre le premier bénéficiaire disponible
            if not beneficiaire_nom and beneficiaires:
                beneficiaire_data = beneficiaires[0]
                beneficiaire_nom = beneficiaire_data['nom']
                beneficiaire_date_naissance = beneficiaire_data.get('date_naissance')
                beneficiaire_numero_identite = beneficiaire_data.get('numero_identite')
                    
            if not beneficiaire_nom:
                continue
                
            # Créer une clé unique pour l'immeuble
            immeuble_key = f"{commune}_{adresse}".replace(' ', '_').replace('/', '_')
            
            # Traiter chaque lot individuellement
            if lots and lots != '-':
                lots_individuels = []
                
                # Parser les lots (format: "144", "145 à 147", "101\n103 à 106\n111")
                for lot_group in lots.replace('\n', ',').split(','):
                    lot_group = lot_group.strip()
                    if 'à' in lot_group:
                        # Range de lots (ex: "145 à 147")
                        try:
                            debut, fin = lot_group.split('à')
                            debut = int(debut.strip())
                            fin = int(fin.strip())
                            lots_individuels.extend(range(debut, fin + 1))
                        except:
                            lots_individuels.append(lot_group)
                    elif lot_group.isdigit():
                        lots_individuels.append(int(lot_group))
                    elif lot_group:
                        lots_individuels.append(lot_group)
                        
                # Enregistrer chaque lot
                for lot in lots_individuels:
                    lot_key = f"{immeuble_key}_lot_{lot}"
                    
                    # Vérifier si on a déjà un propriétaire pour ce lot
                    if lot_key not in proprietaires_actuels or proprietaires_actuels[lot_key]['date_acte'] < date_acte:
                        proprietaires_actuels[lot_key] = {
                            'commune': commune,
                            'adresse': adresse,
                            'lot': str(lot),
                            'volume': volume,
                            'proprietaire': beneficiaire_nom,
                            'date_naissance': beneficiaire_date_naissance,
                            'numero_identite': beneficiaire_numero_identite,
                            'type_droit': type_droit,
                            'date_acte': date_acte,
                            'date_acte_str': date_acte_str,
                            'formalite_pages': f"{formalite['page_debut']}-{formalite['page_fin']}"
                        }
            else:
                # Immeuble sans lots spécifiques
                immeuble_key_complet = f"{immeuble_key}_sans_lot"
                
                if immeuble_key_complet not in proprietaires_actuels or proprietaires_actuels[immeuble_key_complet]['date_acte'] < date_acte:
                    proprietaires_actuels[immeuble_key_complet] = {
                        'commune': commune,
                        'adresse': adresse,
                        'lot': 'Sans lot spécifique',
                        'volume': volume,
                        'proprietaire': beneficiaire_nom,
                        'date_naissance': beneficiaire_date_naissance,
                        'numero_identite': beneficiaire_numero_identite,
                        'type_droit': type_droit,
                        'date_acte': date_acte,
                        'date_acte_str': date_acte_str,
                        'formalite_pages': f"{formalite['page_debut']}-{formalite['page_fin']}"
                    }
    
    # Convertir en format plus lisible
    result = {}
    for key, data in proprietaires_actuels.items():
        # Grouper par immeuble
        immeuble_id = f"{data['commune']} {data['adresse']}"
        if immeuble_id not in result:
            result[immeuble_id] = {
                'commune': data['commune'],
                'adresse': data['adresse'],
                'lots': []
            }
            
        result[immeuble_id]['lots'].append({
            'lot': data['lot'],
            'volume': data['volume'],
            'proprietaire': data['proprietaire'],
            'date_naissance': data['date_naissance'],
            'numero_identite': data['numero_identite'],
            'type_droit': data['type_droit'],
            'date_acte': data['date_acte_str'],
            'formalite_pages': data['formalite_pages']
        })
    
    # Trier les lots par numéro
    for immeuble in result.values():
        immeuble['lots'].sort(key=lambda x: int(x['lot']) if str(x['lot']).isdigit() else 999999)
    
    return result

def extraire_charges_actives(formalites: List[Dict]) -> Dict:
    """
    Extrait les charges, privilèges et hypothèques actives des formalités de type 'Charge'.
    Une formalité = une charge. Elle est radiée si on détecte 'radiation totale' ou 'radiation simplifiée totale'.
    """
    charges_actives = []
    charges_radiees = []
    
    for formalite in formalites:
        if formalite.get('categorie', '').lower() != 'charge':
            continue
            
        texte_complet = formalite.get('texte', '')
        
        # Détecter radiation totale ou radiation simplifiée totale (insensible à la casse)
        a_radiation_totale = bool(re.search(r'radiation\s+(totale|simplifi[eé]e\s+totale)', texte_complet, re.IGNORECASE))
        
        # Extraire le titre principal depuis les tables (format: "TITRE PAGE X À PAGE Y")
        titre = None
        for table in formalite.get('tables', []):
            donnees = table.get('donnees', [])
            for row in donnees:
                for cell in row:
                    if cell and isinstance(cell, str) and 'PAGE' in cell.upper() and 'À PAGE' in cell.upper():
                        # Extraire le titre tel qu'il est, sans filtrage
                        titre = cell.strip()
                        break
                if titre:
                    break
            if titre:
                break
        
        # Si pas trouvé dans les tables, chercher dans le texte
        if not titre:
            lignes = texte_complet.split('\n')
            for ligne in lignes:
                if 'PAGE' in ligne.upper() and 'À PAGE' in ligne.upper():
                    titre = ligne.strip()
                    break
        
        # Extraire les sous-formalités avec leurs dates et montants
        sous_formalites = []
        for match in re.finditer(r'Formalité\s+(\d+)[^:]*:([^\\n]+)', texte_complet, re.IGNORECASE):
            numero = match.group(1)
            description = match.group(2).strip()
            
            # Chercher les dates d'exigibilité et d'effet pour cette sous-formalité
            dates_exigibilite = []
            dates_effet = []
            montants = []
            
            # Zone de texte après cette formalité (jusqu'à la suivante ou fin)
            start_pos = match.end()
            next_match = re.search(r'Formalité\s+\d+', texte_complet[start_pos:], re.IGNORECASE)
            end_pos = start_pos + next_match.start() if next_match else len(texte_complet)
            zone_formalite = texte_complet[start_pos:end_pos]
            
            # Extraire dates d'extrême exigibilité
            for date_match in re.finditer(r'date d\'extrême exigibilité\s*:\s*(\d{2}/\d{2}/\d{4})', zone_formalite, re.IGNORECASE):
                dates_exigibilite.append(date_match.group(1))
            
            # Extraire dates d'extrême effet
            for date_match in re.finditer(r'date d\'extrême effet\s*:\s*(\d{2}/\d{2}/\d{4})', zone_formalite, re.IGNORECASE):
                dates_effet.append(date_match.group(1))
            
            # Extraire montants
            for montant_match in re.finditer(r'montant\s+principal\s*:\s*([\d\s,\.]+)\s*eur', zone_formalite, re.IGNORECASE):
                montants.append({'type': 'principal', 'montant': montant_match.group(1).strip()})
            
            sous_formalites.append({
                'numero': numero,
                'description': description,
                'dates_exigibilite': dates_exigibilite,
                'dates_effet': dates_effet,
                'montants': montants
            })
        
        # Créer la charge simplifiée
        charge = {
            'page_debut': formalite.get('page_debut'),
            'page_fin': formalite.get('page_fin'),
            'titre': titre,
            'sous_formalites': sous_formalites,
            'a_radiation_totale': a_radiation_totale,
            'statut': 'RADIEE' if a_radiation_totale else 'ACTIVE'
        }
        
        # Ajouter à la liste appropriée
        if a_radiation_totale:
            charges_radiees.append(charge)
        else:
            charges_actives.append(charge)
    
    return {
        'charges_actives': charges_actives,
        'charges_radiees': charges_radiees,
        'resume': {
            'nb_charges_totales': len(charges_actives) + len(charges_radiees),
            'nb_charges_actives': len(charges_actives),
            'nb_charges_radiees': len(charges_radiees)
        }
    }

def grouper_par_proprietaire(proprietaires_actuels: Dict) -> Dict:
    """
    Groupe les biens par propriétaire au lieu de grouper par immeuble
    """
    proprietaires_biens = {}
    
    for immeuble_id, immeuble_data in proprietaires_actuels.items():
        commune = immeuble_data['commune']
        adresse = immeuble_data['adresse']
        
        for lot_data in immeuble_data['lots']:
            proprietaire = lot_data['proprietaire']
            date_naissance = lot_data['date_naissance']
            numero_identite = lot_data['numero_identite']
            
            # Créer la clé du propriétaire
            if proprietaire not in proprietaires_biens:
                proprietaires_biens[proprietaire] = {
                    'date_naissance': date_naissance,
                    'numero_identite': numero_identite,
                    'biens': []
                }
            
            # Ajouter le bien à ce propriétaire
            bien = {
                'commune': commune,
                'adresse': adresse,
                'lot': lot_data['lot'],
                'volume': lot_data['volume'],
                'type_droit': lot_data['type_droit'],
                'date_acte': lot_data['date_acte'],
                'formalite_pages': lot_data['formalite_pages']
            }
            
            proprietaires_biens[proprietaire]['biens'].append(bien)
    
    # Trier les biens de chaque propriétaire par commune puis adresse
    for proprietaire_data in proprietaires_biens.values():
        proprietaire_data['biens'].sort(key=lambda x: (x['commune'], x['adresse'], x['lot']))
    
    return proprietaires_biens

def sauvegarder_formalites_json(formalites: List[Dict], pdf_name: str, immeubles_flux: List[Dict] = None):
    # Créer un dossier spécifique pour cet EHF
    output_folder = os.path.join("formalites_json", pdf_name)
    os.makedirs(output_folder, exist_ok=True)
    
    # Calculer les propriétaires actuels
    proprietaires_actuels = determiner_proprietaires_actuels(formalites)
    
    # Créer le groupement par propriétaire
    proprietaires_biens = grouper_par_proprietaire(proprietaires_actuels)
    
    # Extraire les charges, privilèges et hypothèques actives
    charges_data = extraire_charges_actives(formalites)
    
    data = {
        'immeubles_flux': immeubles_flux or [], 
        'formalites': formalites, 
        'proprietaires_actuels': proprietaires_actuels, 
        'proprietaires_biens': proprietaires_biens,
        'charges_actives': charges_data['charges_actives'],
        'charges_radiees': charges_data['charges_radiees'],
        'resume': {
            'nb_immeubles_tables': len(immeubles_flux or []), 
            'nb_formalites': len(formalites), 
            'nb_total_tables': sum(f.get('nb_tables', 0) for f in formalites) + len(immeubles_flux or []), 
            'nb_immeubles_avec_proprietaires': len(proprietaires_actuels), 
            'nb_proprietaires_uniques': len(proprietaires_biens),
            'nb_charges_totales': charges_data['resume']['nb_charges_totales'],
            'nb_charges_actives': charges_data['resume']['nb_charges_actives'],
            'nb_charges_radiees': charges_data['resume']['nb_charges_radiees']
        }
    }
    json_file = os.path.join(output_folder, f"{pdf_name}_complet.json")
    with open(json_file, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Sauvegarder les propriétaires actuels dans un fichier séparé (format original)
    proprietaires_file = os.path.join(output_folder, f"{pdf_name}_proprietaires_actuels.json")
    with open(proprietaires_file, 'w', encoding='utf-8') as f: json.dump(proprietaires_actuels, f, ensure_ascii=False, indent=2)
    
    # Sauvegarder le nouveau format groupé par propriétaire
    proprietaires_biens_file = os.path.join(output_folder, f"{pdf_name}_par_proprietaire.json")
    with open(proprietaires_biens_file, 'w', encoding='utf-8') as f: json.dump(proprietaires_biens, f, ensure_ascii=False, indent=2)
    
    # Sauvegarder les charges actives dans un fichier séparé
    charges_actives_file = os.path.join(output_folder, f"{pdf_name}_charges_actives.json")
    with open(charges_actives_file, 'w', encoding='utf-8') as f: json.dump(charges_data, f, ensure_ascii=False, indent=2)
    
    if immeubles_flux:
        with open(os.path.join(output_folder, f"{pdf_name}_immeubles_flux.json"), 'w', encoding='utf-8') as f: json.dump(immeubles_flux, f, ensure_ascii=False, indent=2)
    for i, formalite in enumerate(formalites):
        with open(os.path.join(output_folder, f"{pdf_name}_formalite_{i+1}.json"), 'w', encoding='utf-8') as f: json.dump(formalite, f, ensure_ascii=False, indent=2)
    return json_file


def main():
    import sys
    
    # Si un fichier spécifique est passé en argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            print(f"🔄 Traitement de {os.path.basename(file_path)}...")
            
            # Extraire les pages de formalités
            formalites_pages = get_formalites_pages(file_path)
            
            # Extraire les formalités complètes
            formalites = get_formalites_completes(file_path, formalites_pages)
            
            # Extraire les immeubles flux
            immeubles_flux = extraire_immeubles_flux(file_path)
            
            if formalites:
                # Générer le nom EHF à partir du nom de fichier
                ehf_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Sauvegarder les résultats
                json_file = sauvegarder_formalites_json(formalites, ehf_name, immeubles_flux)
                
                print(f"✅ {os.path.basename(file_path)} traité avec succès")
                print(f"💾 Résultats sauvegardés dans formalites_json/{ehf_name}/")
            else:
                print(f"❌ Aucune formalité trouvée dans {os.path.basename(file_path)}")
        else:
            print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    # Traiter automatiquement tous les EHF disponibles
    ehfs_folder = "EHFs"
    if not os.path.exists(ehfs_folder):
        print(f"❌ Dossier {ehfs_folder} non trouvé")
        return
    
    ehf_files = [f for f in os.listdir(ehfs_folder) if f.endswith('.pdf') and f.startswith('EHF')]
    ehf_files.sort()
    
    if not ehf_files:
        print(f"❌ Aucun fichier EHF*.pdf trouvé dans {ehfs_folder}")
        return
    
    print(f"📁 {len(ehf_files)} fichiers EHF trouvés: {', '.join(ehf_files)}")
    
    total_formalites = 0
    total_proprietaires = 0
    for ehf_file in ehf_files:
        pdf_path = os.path.join(ehfs_folder, ehf_file)
        print(f"\n🔄 Traitement de {ehf_file}...")
        
        immeubles_flux = extraire_immeubles_flux(pdf_path)
        formalites_pages = get_formalites_pages(pdf_path)
        
        if formalites_pages:
            formalites = get_formalites_completes(pdf_path, formalites_pages)
            ehf_name = ehf_file.replace('.pdf', '')
            sauvegarder_formalites_json(formalites, ehf_name, immeubles_flux)
            
            # Compter les formalités avec propriétaires
            formalites_avec_proprietaires = sum(1 for f in formalites if f.get('proprietaires', {}).get('disposants') and f.get('proprietaires', {}).get('beneficiaires'))
            
            # Compter les propriétaires actuels
            proprietaires_file = f"formalites_json/{ehf_name}/{ehf_name}_proprietaires_actuels.json"
            nb_proprietaires = 0
            if os.path.exists(proprietaires_file):
                with open(proprietaires_file, 'r', encoding='utf-8') as f:
                    proprietaires_data = json.load(f)
                    nb_proprietaires = sum(len(immeuble['lots']) for immeuble in proprietaires_data.values())
            
            # Compter les charges actives
            charges_file = f"formalites_json/{ehf_name}/{ehf_name}_charges_actives.json"
            nb_charges_actives = 0
            nb_charges_radiees = 0
            if os.path.exists(charges_file):
                with open(charges_file, 'r', encoding='utf-8') as f:
                    charges_data = json.load(f)
                    nb_charges_actives = len(charges_data.get('charges_actives', []))
                    nb_charges_radiees = len(charges_data.get('charges_radiees', []))
            
            print(f"✅ {ehf_file} traité:")
            print(f"   📋 {len(formalites)} formalités totales")
            print(f"   🏠 {formalites_avec_proprietaires} avec changements de propriété")
            print(f"   👤 {nb_proprietaires} propriétaires actuels identifiés")
            print(f"   🏢 {len(immeubles_flux)} tables immeubles flux")
            print(f"   ⚖️  {nb_charges_actives} charges/privilèges/hypothèques actives")
            print(f"   ❌ {nb_charges_radiees} charges radiées")
            
            total_formalites += len(formalites)
            total_proprietaires += nb_proprietaires
        else:
            print(f"❌ Aucune formalité trouvée dans {ehf_file}")
    
    print(f"\n🎯 RÉSUMÉ FINAL:")
    print(f"   📊 {len(ehf_files)} EHF traités")
    print(f"   📋 {total_formalites} formalités totales extraites")
    print(f"   👤 {total_proprietaires} propriétaires actuels identifiés")
    print(f"   💾 Fichiers sauvegardés dans formalites_json/")

if __name__ == "__main__": 
    main()
