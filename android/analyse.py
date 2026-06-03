#!/usr/bin/env python3
"""
Analyse automatique TradingView toutes les 5 minutes avec rapport vocal.
Nécessite: Termux + Termux:API + pip install anthropic
"""

import subprocess
import base64
import os
import time
import sys

from anthropic import Anthropic

client = Anthropic()

INTERVALLE_SECONDES = 5 * 60  # 5 minutes

PROMPT_ANALYSE = """Tu es un trader professionnel. Regarde ce graphique TradingView et donne un rapport vocal COURT (4 phrases maximum, langage parlé naturel) :

1. Tendance : haussière, baissière ou latérale
2. Entrée probable : zone de prix ou niveau clé
3. Stop-loss : niveau de protection
4. Signal final : ACHAT, VENTE ou ATTENDRE

Parle comme si tu lisais un bulletin radio de trading. Sois direct et précis."""


def prendre_screenshot() -> str:
    chemin = "/sdcard/tv_capture.png"
    resultat = subprocess.run(
        ["termux-screenshot", "-f", chemin],
        capture_output=True,
        text=True
    )
    if resultat.returncode != 0:
        raise RuntimeError(f"Erreur screenshot: {resultat.stderr}")
    return chemin


def encoder_image(chemin: str) -> str:
    with open(chemin, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyser_graphique(chemin_image: str) -> str:
    image_data = encoder_image(chemin_image)
    reponse = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
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
    return reponse.content[0].text


def parler(texte: str) -> None:
    subprocess.run(["termux-tts-speak", texte])


def afficher_et_parler(message: str) -> None:
    print(message)
    parler(message)


def boucle_principale() -> None:
    afficher_et_parler("Surveillance TradingView démarrée. Analyse toutes les 5 minutes.")

    compteur = 0
    while True:
        compteur += 1
        horodatage = time.strftime("%H:%M:%S")
        print(f"\n[{horodatage}] Analyse #{compteur} en cours...")

        try:
            screenshot = prendre_screenshot()
            analyse = analyser_graphique(screenshot)
            print(f"\n{'='*40}")
            print(analyse)
            print('='*40)
            parler(analyse)

        except FileNotFoundError:
            msg = "Erreur: termux-api non installé. Installez le package termux-api."
            print(msg)
            parler(msg)
            sys.exit(1)

        except Exception as e:
            msg = f"Erreur lors de l'analyse: {str(e)}"
            print(msg)

        print(f"\nProchaine analyse dans 5 minutes...")
        time.sleep(INTERVALLE_SECONDES)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR: Variable ANTHROPIC_API_KEY manquante.")
        print("Ajoutez dans ~/.bashrc: export ANTHROPIC_API_KEY='votre_cle'")
        sys.exit(1)

    boucle_principale()
