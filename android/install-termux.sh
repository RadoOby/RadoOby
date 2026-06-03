#!/data/data/com.termux/files/usr/bin/bash
# Lancez ce script dans Termux après installation

echo "=== Installation de l'analyse TradingView ==="

# Mise à jour des paquets
pkg update -y && pkg upgrade -y

# Installer Python et termux-api
pkg install -y python termux-api

# Installer la librairie Claude
pip install anthropic

# Créer le dossier de travail
mkdir -p ~/tradingview

# Télécharger le script d'analyse
curl -o ~/tradingview/analyse.py \
  https://raw.githubusercontent.com/RadoOby/RadoOby/main/android/analyse.py

# Rendre exécutable
chmod +x ~/tradingview/analyse.py

echo ""
echo "=== Installation terminée! ==="
echo ""
echo "Étape suivante: ajoutez votre clé API Claude"
echo "Collez cette commande et remplacez YOUR_KEY:"
echo ""
echo "  echo 'export ANTHROPIC_API_KEY=YOUR_KEY' >> ~/.bashrc && source ~/.bashrc"
echo ""
echo "Ensuite lancez l'analyse:"
echo "  python ~/tradingview/analyse.py"
