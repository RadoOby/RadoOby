#!/usr/bin/env python3
"""
Claude prend le contrôle de l'analyse TradingView sur Android.
- Capture l'écran TradingView automatiquement
- Analyse le graphique (tendance, entrée, SL, TP)
- Génère le Pine Script correspondant
- Lit le rapport à voix haute
- Sauvegarde le Pine Script prêt à copier dans TradingView
"""

import subprocess
import base64
import os
import time
import sys
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()

INTERVALLE = 5 * 60  # 5 minutes
DOSSIER_SCRIPTS = Path.home() / "tradingview" / "pine_scripts"

PROMPT_ANALYSE = """Tu es un trader algorithmique expert. Analyse ce graphique TradingView en détail.

Donne exactement ce format:

RAPPORT VOCAL (à lire à voix haute, 4 phrases max, style radio):
[ton rapport vocal ici]

---PINE SCRIPT---
//@version=5
[ton script Pine Script complet ici, avec stratégie d'entrée basée sur ce que tu vois sur le graphique]
---FIN PINE SCRIPT---

Le Pine Script doit inclure:
- Les indicateurs que tu identifies sur le graphique (RSI, MA, MACD, Bollinger, etc.)
- La logique d'entrée ACHAT et VENTE basée sur l'analyse
- Un stop-loss et take-profit calculés
- Des alertes (alertcondition)
- Des labels sur le graphique pour les signaux"""


def prendre_screenshot() -> str:
    chemin = str(Path.home() / "tradingview" / "capture.png")
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    resultat = subprocess.run(
        ["termux-screenshot", "-f", chemin],
        capture_output=True, text=True, timeout=15
    )
    if resultat.returncode != 0:
        raise RuntimeError(f"Screenshot échoué: {resultat.stderr}")
    return chemin


def encoder_image(chemin: str) -> str:
    with open(chemin, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyser(chemin_image: str) -> dict:
    image_data = encoder_image(chemin_image)
    reponse = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                },
                {"type": "text", "text": PROMPT_ANALYSE},
            ],
        }]
    )
    texte = reponse.content[0].text
    return extraire_sections(texte)


def extraire_sections(texte: str) -> dict:
    vocal = ""
    pine = ""

    # Extraire le rapport vocal
    if "RAPPORT VOCAL" in texte:
        debut = texte.find("RAPPORT VOCAL") + len("RAPPORT VOCAL")
        # Chercher la fin (soit --- soit la fin du texte)
        fin = texte.find("---PINE SCRIPT---")
        if fin == -1:
            fin = len(texte)
        vocal = texte[debut:fin].strip().lstrip(":").strip()

    # Extraire le Pine Script
    if "---PINE SCRIPT---" in texte and "---FIN PINE SCRIPT---" in texte:
        debut = texte.find("---PINE SCRIPT---") + len("---PINE SCRIPT---")
        fin = texte.find("---FIN PINE SCRIPT---")
        pine = texte[debut:fin].strip()

    return {"vocal": vocal or texte[:500], "pine": pine}


def sauvegarder_pine(pine_script: str, compteur: int) -> str:
    DOSSIER_SCRIPTS.mkdir(parents=True, exist_ok=True)
    horodatage = time.strftime("%Y%m%d_%H%M%S")
    fichier = DOSSIER_SCRIPTS / f"strategie_{horodatage}.pine"
    fichier.write_text(pine_script, encoding="utf-8")
    return str(fichier)


def parler(texte: str) -> None:
    # Nettoyer le texte pour la synthèse vocale (enlever markdown)
    texte_propre = texte.replace("*", "").replace("#", "").replace("`", "")
    subprocess.run(["termux-tts-speak", "-l", "fr", texte_propre], timeout=60)


def afficher_separateur(titre: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {titre}")
    print('='*50)


def boucle_principale() -> None:
    parler("Claude Trading démarré. Je surveille TradingView.")
    print("\nOuvrez TradingView sur votre graphique.")
    print("Je l'analyserai toutes les 5 minutes.\n")

    compteur = 0
    while True:
        compteur += 1
        horodatage = time.strftime("%H:%M:%S")

        afficher_separateur(f"Analyse #{compteur} — {horodatage}")
        print("Capture de l'écran TradingView...")

        try:
            screenshot = prendre_screenshot()
            print("Envoi à Claude pour analyse...")
            resultat = analyser(screenshot)

            # Afficher et lire le rapport vocal
            afficher_separateur("RAPPORT")
            print(resultat["vocal"])
            parler(resultat["vocal"])

            # Sauvegarder et afficher le Pine Script
            if resultat["pine"]:
                fichier = sauvegarder_pine(resultat["pine"], compteur)
                afficher_separateur("PINE SCRIPT GÉNÉRÉ")
                print(resultat["pine"])
                print(f"\nSauvegardé: {fichier}")
                parler("Pine Script généré et sauvegardé. Copiez-le dans l'éditeur TradingView.")

        except FileNotFoundError:
            msg = "Erreur: installez le package termux-api dans Termux."
            print(msg)
            parler(msg)
            sys.exit(1)
        except Exception as e:
            erreur = f"Erreur analyse: {str(e)}"
            print(erreur)

        print(f"\nProchaine analyse dans 5 minutes...")
        time.sleep(INTERVALLE)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR: clé API manquante.")
        print("Commande: export ANTHROPIC_API_KEY='votre_cle'")
        sys.exit(1)
    boucle_principale()
