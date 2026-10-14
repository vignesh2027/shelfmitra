"""Knows what a medicine is from the name printed on an invoice.

Two layers:
1. Common Indian brands mapped to their active ingredient (public facts).
2. Ingredient keywords, so generic names on an invoice are recognised too.
The ingredient decides the drug class (ATC group) that the risk model uses;
medicines outside the eight classes in the reference data get "OTHER", and
the model then relies on the shop's own sales for them.
"""
from __future__ import annotations

import re

# ingredient keyword -> ATC group used by the reference sales data
INGREDIENT_CLASS = {
    "diclofenac": "M01AB", "aceclofenac": "M01AB", "etodolac": "M01AB", "indomethacin": "M01AB",
    "ibuprofen": "M01AE", "naproxen": "M01AE", "ketoprofen": "M01AE", "dexketoprofen": "M01AE", "flurbiprofen": "M01AE",
    "aspirin": "N02BA", "acetylsalicylic": "N02BA",
    "paracetamol": "N02BE", "acetaminophen": "N02BE",
    "alprazolam": "N05B", "clonazepam": "N05B", "lorazepam": "N05B", "diazepam": "N05B", "etizolam": "N05B", "buspirone": "N05B",
    "zolpidem": "N05C", "nitrazepam": "N05C", "melatonin": "N05C", "zopiclone": "N05C",
    "salbutamol": "R03", "levosalbutamol": "R03", "montelukast": "R03", "budesonide": "R03", "formoterol": "R03",
    "salmeterol": "R03", "tiotropium": "R03", "theophylline": "R03", "doxofylline": "R03", "ipratropium": "R03",
    "cetirizine": "R06", "levocetirizine": "R06", "fexofenadine": "R06", "loratadine": "R06", "desloratadine": "R06",
    "chlorpheniramine": "R06", "bilastine": "R06", "hydroxyzine": "R06", "ebastine": "R06", "rupatadine": "R06",
}

# brand (as printed, upper case) -> ingredient(s)
BRANDS = {
    "DOLO": "paracetamol", "CROCIN": "paracetamol", "CALPOL": "paracetamol", "PARACIP": "paracetamol", "P 500": "paracetamol",
    "PACIMOL": "paracetamol", "SUMO": "nimesulide + paracetamol", "COMBIFLAM": "ibuprofen + paracetamol",
    "BRUFEN": "ibuprofen", "IBUGESIC": "ibuprofen", "FLEXON": "ibuprofen + paracetamol", "NAPROSYN": "naproxen",
    "VOVERAN": "diclofenac", "VOLINI": "diclofenac", "DICLOGESIC": "diclofenac", "ZERODOL": "aceclofenac",
    "HIFENAC": "aceclofenac", "ACECLO": "aceclofenac", "ECOSPRIN": "aspirin", "DISPRIN": "aspirin", "LOPRIN": "aspirin",
    "ALPRAX": "alprazolam", "RESTYL": "alprazolam", "TRIKA": "alprazolam", "RIVOTRIL": "clonazepam", "CLONOTRIL": "clonazepam",
    "ATIVAN": "lorazepam", "CALMPOSE": "diazepam", "ETILAAM": "etizolam", "ZOLFRESH": "zolpidem", "STILNOCT": "zolpidem",
    "NITRAVET": "nitrazepam", "MELOSET": "melatonin",
    "ASTHALIN": "salbutamol", "LEVOLIN": "levosalbutamol", "MONTAIR": "montelukast + levocetirizine",
    "MONTEK": "montelukast + levocetirizine", "BUDECORT": "budesonide", "FORACORT": "formoterol + budesonide",
    "SEROFLO": "salmeterol + fluticasone", "TIOVA": "tiotropium", "DERIPHYLLIN": "theophylline", "DOXOBID": "doxofylline",
    "ALLEGRA": "fexofenadine", "CETZINE": "cetirizine", "OKACET": "cetirizine", "ALERID": "cetirizine",
    "LEVOCET": "levocetirizine", "XYZAL": "levocetirizine", "TELEKAST": "montelukast + fexofenadine", "LORFAST": "loratadine",
    "AVIL": "pheniramine", "ATARAX": "hydroxyzine", "BILAXTEN": "bilastine", "EBAST": "ebastine", "RUPANEX": "rupatadine",
    # common medicines outside the eight reference classes (ingredient known, class OTHER)
    "PAN": "pantoprazole", "PANTOCID": "pantoprazole", "RANTAC": "ranitidine", "OMEZ": "omeprazole", "RAZO": "rabeprazole",
    "AZITHRAL": "azithromycin", "AZEE": "azithromycin", "AUGMENTIN": "amoxicillin + clavulanate", "MOX": "amoxicillin",
    "TAXIM": "cefixime", "CIPLOX": "ciprofloxacin", "SHELCAL": "calcium + vitamin d3", "BECOSULES": "vitamin b complex",
    "LIMCEE": "vitamin c", "ZINCOVIT": "multivitamin + zinc", "GLYCOMET": "metformin", "JANUVIA": "sitagliptin",
    "TELMA": "telmisartan", "AMLONG": "amlodipine", "THYRONORM": "levothyroxine", "ELTROXIN": "levothyroxine",
    "ROSUVAS": "rosuvastatin", "ATORVA": "atorvastatin", "ONDEM": "ondansetron", "EMESET": "ondansetron",
    "DIGENE": "antacid", "GELUSIL": "antacid", "ELECTRAL": "oral rehydration salts", "ORS": "oral rehydration salts",
    "BETADINE": "povidone iodine", "SOFRAMYCIN": "framycetin", "CANDID": "clotrimazole", "BENADRYL": "diphenhydramine",
    "GRILINCTUS": "cough syrup combination", "ASCORIL": "cough syrup combination",
}


def lookup(product: str) -> dict:
    """{'composition', 'category'} for a product name as printed; empty when unknown."""
    name = re.sub(r"[^A-Z0-9 ]", " ", product.upper())
    composition = None
    for brand in sorted(BRANDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(brand)}\b", name):
            composition = BRANDS[brand]
            break
    text = (composition or name).lower()
    category = next((cls for ing, cls in INGREDIENT_CLASS.items() if re.search(rf"\b{ing}\b", text)), None)
    if composition is None and category is None:
        return {}
    return {"composition": composition or next(i for i in INGREDIENT_CLASS if re.search(rf"\b{i}\b", text)),
            "category": category or "OTHER"}
