#!/usr/bin/env python3
"""
Claude Trading - Deux modes:
  python analyse.py        → surveillance auto toutes les 5 minutes
  python analyse.py chat   → questions/réponses vocales instantanées
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
INTERVALLE = 5 * 60
DOSSIER_PINE = Path.home() / "tradingview" / "pine_scripts"

PROMPT_AUTO = """Tu es un trader expert. Analyse ce graphique TradingView.

RAPPORT VOCAL (4 phrases max, style radio):
[tendance, entrée probable, stop-loss, signal ACHAT/VENTE/ATTENDRE]

---PINE SCRIPT---
//@version=5
[script complet: indicateurs visibles, logique entrée/sortie, SL/TP, alertes]
---FIN PINE SCRIPT---"""

PROMPT_CHAT = """Tu es un trader expert. L'utilisateur pose une question sur ce graphique TradingView.
Réponds en 3 phrases maximum, en français, style parlé naturel (sera lu à voix haute).
Sois direct et précis: tendance, niveaux clés, recommandation."""


def appeler_claude(messages: list) -> str:
    cle = os.environ.get("ANTHROPIC_API_KEY", "")
    reponse = requests.post(
        API_URL,
        headers={
            "x-api-key": cle,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 1500, "messages": messages},
        timeout=60,
    )
    if reponse.status_code != 200:
        raise RuntimeError(f"Erreur API {reponse.status_code}: {reponse.text}")
    return reponse.json()["content"][0]["text"]


def prendre_screenshot() -> str:
    chemin = str(Path.home() / "tradingview" / "capture.png")
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["termux-screenshot", "-f", chemin], capture_output=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(f"Screenshot échoué: {r.stderr.decode()}")
    return chemin


def image_en_base64(chemin: str) -> str:
    with open(chemin, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()


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
    propre = (texte.replace("*", "").replace("#", "")
              .replace("`", "").replace("-", " ").replace("_", " "))
    subprocess.run(["termux-tts-speak", "-l", "fr", propre[:600]], timeout=90)


def mode_chat() -> None:
    """Mode interactif: questions/réponses vocales en temps réel."""
    print("\n=== MODE CHAT VOCAL ===")
    print("Ouvrez TradingView sur votre graphique.")
    print("Tapez votre question, Claude répond à voix haute.")
    print("(tapez 'quitter' pour arrêter)\n")
    parler("Mode chat activé. Posez vos questions.")

    while True:
        try:
            question = input("Votre question > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir!")
            break

        if question.lower() in ("quitter", "exit", "q"):
            parler("Au revoir.")
            break

        if not question:
            continue

        print("Capture + analyse en cours...")
        try:
            screenshot = prendre_screenshot()
            img = image_en_base64(screenshot)
            reponse = appeler_claude([{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img},
                    },
                    {"type": "text", "text": f"{PROMPT_CHAT}\n\nQuestion: {question}"},
                ],
            }])
            print(f"\nClaude: {reponse}\n")
            parler(reponse)
        except Exception as e:
            print(f"Erreur: {e}")


def mode_auto() -> None:
    """Mode automatique: analyse toutes les 5 minutes."""
    parler("Claude Trading démarré. Surveillance toutes les 5 minutes.")
    print("Ouvrez TradingView. Première analyse dans 5 secondes...\n")
    time.sleep(5)

    compteur = 0
    while True:
        compteur += 1
        print(f"\n{'='*40}")
        print(f"Analyse #{compteur} — {time.strftime('%H:%M:%S')}")
        print("Capture TradingView...")
        try:
            screenshot = prendre_screenshot()
            img = image_en_base64(screenshot)
            texte = appeler_claude([{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img},
                    },
                    {"type": "text", "text": PROMPT_AUTO},
                ],
            }])
            vocal, pine = extraire_sections(texte)
            print(f"\nRAPPORT:\n{vocal}")
            parler(vocal)
            if pine:
                fichier = sauvegarder_pine(pine)
                print(f"\nPine Script: {fichier}")
                parler("Pine Script généré. Copiez-le dans TradingView.")
        except Exception as e:
            print(f"Erreur: {e}")

        print(f"\nProchaine analyse dans 5 minutes...")
        time.sleep(INTERVALLE)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR: clé API manquante.")
        print("Tapez: export ANTHROPIC_API_KEY='votre_cle'")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "chat":
        mode_chat()
    else:
        mode_auto()
