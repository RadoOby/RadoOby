#!/usr/bin/env python3
"""
Claude Trading SMC/ICT - Analyse multi-timeframe automatique.

Modes:
  python analyse.py          → surveillance auto toutes les 5 minutes (MTF)
  python analyse.py chat     → questions/réponses vocales instantanées
  python analyse.py mtf      → analyse manuelle multi-timeframe (D1→H4→H1→M15)
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

# Timeframes à analyser en mode MTF (ordre top-down ICT)
TIMEFRAMES = ["D1", "H4", "H1", "M15"]

PROMPT_MTF = """Tu es un expert SMC (Smart Money Concepts) et ICT (Inner Circle Trader).
Tu reçois {nb} graphiques TradingView du MÊME actif sur différentes unités de temps: {tfs}.

Fais une analyse TOP-DOWN complète:

## D1 (Daily) — Biais directionnel
- Tendance HTF, derniers BOS/CHoCH
- Order Blocks D1 actifs
- Niveaux de liquidité majeurs (PDH/PDL, Weekly High/Low)
- Zone Premium ou Discount

## H4 — Structure intermédiaire
- Confirmation du biais D1
- Order Blocks H4 + FVG non comblés
- Prochaine cible de liquidité

## H1 — Structure d'entrée
- CHoCH ou BOS de confirmation
- Order Block d'entrée précis
- FVG sur H1 à surveiller

## M15 — Entrée précise ICT
- Confirmation entrée dans OB H1
- FVG M15 + OTE Fibonacci (61.8-79%)
- Kill Zone active (London/NY)

## SIGNAL FINAL
- Direction: ACHAT / VENTE / NEUTRE
- Zone d'entrée précise
- Stop-Loss: au-dessus/dessous du dernier swing HTF
- TP1 / TP2 / TP3 (prochaines zones de liquidité)
- Probabilité du setup (sur 10)

RAPPORT VOCAL (5 phrases max, style radio):
[biais HTF, structure H1, signal d'entrée M15, SL/TP, probabilité]

---PINE SCRIPT---
//@version=5
[indicateur SMC complet: OB multi-TF, FVG, BOS/CHoCH, niveaux liquidité, alertes d'entrée]
---FIN PINE SCRIPT---"""

PROMPT_AUTO = """Tu es un expert SMC/ICT. Analyse ce graphique TradingView.

Identifie:
- BOS / CHoCH (structure)
- Order Blocks actifs (haussier/baissier)
- Fair Value Gaps non comblés
- Liquidité BSL/SSL ciblée
- Zone Premium/Discount
- OTE Fibonacci (61.8-79%)
- Kill Zone active

RAPPORT VOCAL (4 phrases, style radio):
[biais, zone OB/FVG, entrée OTE, signal ACHAT/VENTE/NEUTRE + SL/TP]

---PINE SCRIPT---
//@version=5
[script SMC: OB, FVG, BOS/CHoCH, liquidité, OTE, alertes]
---FIN PINE SCRIPT---"""

PROMPT_CHAT = """Tu es un expert SMC/ICT. L'utilisateur pose une question sur ce graphique TradingView.
Analyse: Order Blocks, FVG, BOS/CHoCH, liquidité BSL/SSL, Premium/Discount, OTE.
Réponds en 4 phrases max, français, style parlé (sera lu à voix haute).
Donne: biais HTF, zone clé SMC, recommandation d'entrée ICT précise."""


def appeler_claude(messages: list, max_tokens: int = 2500) -> str:
    cle = os.environ.get("ANTHROPIC_API_KEY", "")
    reponse = requests.post(
        API_URL,
        headers={
            "x-api-key": cle,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": max_tokens, "messages": messages},
        timeout=90,
    )
    if reponse.status_code != 200:
        raise RuntimeError(f"Erreur API {reponse.status_code}: {reponse.text}")
    return reponse.json()["content"][0]["text"]


def prendre_screenshot(nom: str = "capture") -> str:
    chemin = str(Path.home() / "tradingview" / f"{nom}.png")
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
    fichier = DOSSIER_PINE / f"smc_{time.strftime('%Y%m%d_%H%M%S')}.pine"
    fichier.write_text(pine, encoding="utf-8")
    return str(fichier)


def parler(texte: str) -> None:
    propre = (texte.replace("*", "").replace("#", "")
              .replace("`", "").replace("-", " ").replace("_", " "))
    subprocess.run(["termux-tts-speak", "-l", "fr", propre[:700]], timeout=120)


def capturer_timeframe(tf: str) -> str:
    """Guide l'utilisateur pour changer de TF et capture le screenshot."""
    print(f"\n>>> Passez sur TradingView en {tf}")
    parler(f"Passez sur {tf}")
    for i in range(8, 0, -1):
        print(f"  Capture dans {i}s...", end="\r")
        time.sleep(1)
    print(f"  Capture {tf}!          ")
    return prendre_screenshot(f"capture_{tf}")


def mode_mtf() -> None:
    """Analyse manuelle multi-timeframe top-down ICT."""
    print("\n=== ANALYSE MULTI-TIMEFRAME SMC/ICT ===")
    print(f"On va capturer: {' → '.join(TIMEFRAMES)}")
    parler("Analyse multi-timeframe démarrée. Je vais capturer 4 unités de temps.")

    images = []
    chemins = []
    for tf in TIMEFRAMES:
        try:
            chemin = capturer_timeframe(tf)
            chemins.append(chemin)
            images.append({
                "tf": tf,
                "data": image_en_base64(chemin)
            })
            print(f"  ✓ {tf} capturé")
        except Exception as e:
            print(f"  ✗ Erreur {tf}: {e}")

    if not images:
        print("Aucune capture réussie.")
        return

    print(f"\nAnalyse SMC/ICT de {len(images)} timeframes en cours...")
    parler("Analyse en cours. Un moment.")

    # Construire le contenu multi-images
    contenu = []
    for img in images:
        contenu.append({"type": "text", "text": f"=== Graphique {img['tf']} ==="})
        contenu.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img["data"]},
        })

    prompt = PROMPT_MTF.format(
        nb=len(images),
        tfs=" → ".join([img["tf"] for img in images])
    )
    contenu.append({"type": "text", "text": prompt})

    texte = appeler_claude([{"role": "user", "content": contenu}], max_tokens=3000)
    vocal, pine = extraire_sections(texte)

    print(f"\n{'='*50}")
    print(texte)
    print('='*50)
    parler(vocal)

    if pine:
        fichier = sauvegarder_pine(pine)
        print(f"\nPine Script SMC sauvegardé: {fichier}")
        parler("Pine Script SMC généré et sauvegardé.")


def mode_chat() -> None:
    """Mode interactif: questions/réponses vocales SMC/ICT."""
    print("\n=== CHAT VOCAL SMC/ICT ===")
    print("Ouvrez TradingView. Tapez votre question.")
    print("(tapez 'mtf' pour analyse multi-TF, 'quitter' pour arrêter)\n")
    parler("Chat SMC ICT activé. Posez vos questions.")

    while True:
        try:
            question = input("Question > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if question.lower() in ("quitter", "exit", "q"):
            parler("Au revoir.")
            break
        if question.lower() == "mtf":
            mode_mtf()
            continue
        if not question:
            continue

        print("Basculez sur TradingView...")
        for i in range(5, 0, -1):
            print(f"  Capture dans {i}s...", end="\r")
            time.sleep(1)
        print("Capture!              ")

        try:
            screenshot = prendre_screenshot()
            img = image_en_base64(screenshot)
            reponse = appeler_claude([{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
                    {"type": "text", "text": f"{PROMPT_CHAT}\n\nQuestion: {question}"},
                ],
            }])
            print(f"\nClaude SMC: {reponse}\n")
            parler(reponse)
        except Exception as e:
            print(f"Erreur: {e}")


def mode_auto() -> None:
    """Analyse automatique toutes les 5 minutes en SMC/ICT."""
    parler("Claude SMC ICT démarré. Analyse automatique toutes les 5 minutes.")
    print("Ouvrez TradingView sur votre graphique.\n")
    time.sleep(5)

    compteur = 0
    while True:
        compteur += 1
        print(f"\n{'='*40}")
        print(f"Analyse SMC #{compteur} — {time.strftime('%H:%M:%S')}")

        try:
            screenshot = prendre_screenshot()
            img = image_en_base64(screenshot)
            texte = appeler_claude([{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
                    {"type": "text", "text": PROMPT_AUTO},
                ],
            }])
            vocal, pine = extraire_sections(texte)
            print(f"\nRAPPORT SMC:\n{vocal}")
            parler(vocal)
            if pine:
                fichier = sauvegarder_pine(pine)
                print(f"\nPine Script: {fichier}")
        except Exception as e:
            print(f"Erreur: {e}")

        print(f"\nProchaine analyse dans 5 minutes...")
        time.sleep(INTERVALLE)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR: clé API manquante.")
        print("Tapez: export ANTHROPIC_API_KEY='votre_cle'")
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode == "chat":
        mode_chat()
    elif mode == "mtf":
        mode_mtf()
    else:
        mode_auto()
