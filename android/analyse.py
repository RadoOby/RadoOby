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
TIMEFRAMES = ["D1", "H4", "H1", "M15", "M5", "M1"]

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


def trouver_derniere_image() -> str:
    """Trouve la dernière image sauvegardée depuis TradingView."""
    dossiers = [
        Path("/sdcard/Pictures"),
        Path("/sdcard/DCIM"),
        Path("/sdcard/Pictures/TradingView"),
        Path("/sdcard/Download"),
    ]
    derniere = None
    derniere_mtime = 0
    for dossier in dossiers:
        if not dossier.exists():
            continue
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            for f in dossier.glob(ext):
                if f.stat().st_mtime > derniere_mtime:
                    derniere_mtime = f.stat().st_mtime
                    derniere = f
    if not derniere:
        raise RuntimeError("Aucune image trouvée. Sauvegardez un graphique TradingView d'abord.")
    return str(derniere)


def attendre_nouvelle_image(timeout: int = 60) -> str:
    """Attend qu'une nouvelle image apparaisse dans la galerie."""
    dossiers = [
        Path("/sdcard/Pictures"),
        Path("/sdcard/DCIM"),
        Path("/sdcard/Pictures/TradingView"),
        Path("/sdcard/Download"),
    ]
    # Snapshot des fichiers existants
    existants = set()
    for d in dossiers:
        if d.exists():
            for ext in ("*.png", "*.jpg", "*.jpeg"):
                existants.update(str(f) for f in d.glob(ext))

    print(f"En attente d'une nouvelle image ({timeout}s max)...")
    debut = time.time()
    while time.time() - debut < timeout:
        for d in dossiers:
            if not d.exists():
                continue
            for ext in ("*.png", "*.jpg", "*.jpeg"):
                for f in d.glob(ext):
                    if str(f) not in existants:
                        time.sleep(0.5)  # laisser le fichier finir d'écrire
                        return str(f)
        time.sleep(1)
    raise RuntimeError("Timeout: aucune nouvelle image reçue.")


def prendre_screenshot(nom: str = "capture") -> str:
    """Utilise la dernière image sauvegardée depuis TradingView."""
    return trouver_derniere_image()


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
    """Demande à l'utilisateur de sauvegarder le graphique TF depuis TradingView."""
    print(f"\n>>> Dans TradingView, passez sur {tf} puis: Partager → Enregistrer l'image")
    parler(f"Passez sur {tf} dans TradingView et sauvegardez le graphique.")
    return attendre_nouvelle_image(timeout=120)


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

        print("Dans TradingView: Partager → Enregistrer l'image")
        parler("Sauvegardez le graphique dans TradingView maintenant.")
        try:
            screenshot = attendre_nouvelle_image(timeout=60)
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
    """Analyse automatique: attend une nouvelle image TradingView."""
    parler("Claude SMC ICT démarré. Sauvegardez vos graphiques TradingView pour les analyser.")
    print("Dans TradingView: Partager → Enregistrer l'image\n")
    print("Le script analyse chaque nouvelle image automatiquement.\n")

    compteur = 0
    while True:
        compteur += 1
        print(f"\n{'='*40}")
        print(f"En attente du graphique #{compteur} — {time.strftime('%H:%M:%S')}")
        print("Sauvegardez un graphique TradingView...")

        try:
            screenshot = attendre_nouvelle_image(timeout=INTERVALLE)
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
