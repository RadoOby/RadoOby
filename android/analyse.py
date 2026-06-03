#!/usr/bin/env python3
"""
Claude Trading - Analyse TradingView automatique avec rapport vocal.
Utilise l'API Anthropic directement via requests (sans SDK).
"""

import subprocess
import base64
import os
import time
import sys
from pathlib import Path
import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
INTERVALLE = 5 * 60  # 5 minutes
DOSSIER_PINE = Path.home() / "tradingview" / "pine_scripts"

PROMPT = """Tu es un trader algorithmique expert. Analyse ce graphique TradingView.

RAPPORT VOCAL (4 phrases max, style radio, langage parlé):
[ton rapport ici: tendance, entrée probable, stop-loss, signal ACHAT/VENTE/ATTENDRE]

---PINE SCRIPT---
//@version=5
[script Pine Script complet avec: indicateurs visibles, logique entrée/sortie, SL/TP, alertes]
---FIN PINE SCRIPT---"""


def appeler_claude(image_base64: str) -> str:
    cle = os.environ.get("ANTHROPIC_API_KEY", "")
    if not cle:
        raise ValueError("ANTHROPIC_API_KEY manquante")

    reponse = requests.post(
        API_URL,
        headers={
            "x-api-key": cle,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }],
        },
        timeout=60,
    )

    if reponse.status_code != 200:
        raise RuntimeError(f"Erreur API: {reponse.status_code} - {reponse.text}")

    return reponse.json()["content"][0]["text"]


def prendre_screenshot() -> str:
    chemin = str(Path.home() / "tradingview" / "capture.png")
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["termux-screenshot", "-f", chemin], capture_output=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(f"Screenshot échoué: {r.stderr.decode()}")
    return chemin


def extraire_sections(texte: str) -> tuple[str, str]:
    vocal, pine = texte, ""
    if "RAPPORT VOCAL" in texte:
        debut = texte.find("RAPPORT VOCAL") + len("RAPPORT VOCAL")
        fin = texte.find("---PINE SCRIPT---") if "---PINE SCRIPT---" in texte else len(texte)
        vocal = texte[debut:fin].strip().lstrip(":").strip()
    if "---PINE SCRIPT---" in texte and "---FIN PINE SCRIPT---" in texte:
        debut = texte.find("---PINE SCRIPT---") + len("---PINE SCRIPT---")
        fin = texte.find("---FIN PINE SCRIPT---")
        pine = texte[debut:fin].strip()
    return vocal, pine


def sauvegarder_pine(pine: str) -> str:
    DOSSIER_PINE.mkdir(parents=True, exist_ok=True)
    fichier = DOSSIER_PINE / f"strategie_{time.strftime('%Y%m%d_%H%M%S')}.pine"
    fichier.write_text(pine, encoding="utf-8")
    return str(fichier)


def parler(texte: str) -> None:
    propre = texte.replace("*", "").replace("#", "").replace("`", "").replace("-", "")
    subprocess.run(["termux-tts-speak", "-l", "fr", propre[:500]], timeout=60)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR: clé API manquante.")
        print("Tapez: export ANTHROPIC_API_KEY='votre_cle'")
        sys.exit(1)

    parler("Claude Trading démarré. Surveillance toutes les 5 minutes.")
    print("Ouvrez TradingView sur votre graphique. Analyse dans 5 secondes...\n")
    time.sleep(5)

    compteur = 0
    while True:
        compteur += 1
        print(f"\n{'='*40}")
        print(f"Analyse #{compteur} — {time.strftime('%H:%M:%S')}")
        print("Capture TradingView...")

        try:
            screenshot = prendre_screenshot()
            print("Envoi à Claude...")
            texte = appeler_claude(base64.standard_b64encode(open(screenshot, "rb").read()).decode())
            vocal, pine = extraire_sections(texte)

            print(f"\nRAPPORT:\n{vocal}")
            parler(vocal)

            if pine:
                fichier = sauvegarder_pine(pine)
                print(f"\nPine Script sauvegardé: {fichier}")
                parler("Pine Script généré. Copiez-le dans TradingView.")

        except Exception as e:
            print(f"Erreur: {e}")

        print(f"\nProchaine analyse dans 5 minutes...")
        time.sleep(INTERVALLE)


if __name__ == "__main__":
    main()
