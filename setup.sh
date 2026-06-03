#!/bin/bash
set -e

echo "=== TradingView MCP Setup ==="

if [ ! -d "tradingview-mcp" ]; then
  echo "Cloning tradingview-mcp..."
  git clone https://github.com/tradesdontlie/tradingview-mcp.git
else
  echo "Mise a jour de tradingview-mcp..."
  cd tradingview-mcp && git pull && cd ..
fi

echo "Installation des dependances..."
cd tradingview-mcp && npm install && cd ..

echo ""
echo "=== Installation terminee! ==="
echo ""
echo "Etapes suivantes:"
echo ""
echo "1. Lancez TradingView Desktop en mode debug:"
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "   bash tradingview-mcp/scripts/launch_tv_debug_mac.sh"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  echo "   bash tradingview-mcp/scripts/launch_tv_debug_linux.sh"
fi
echo ""
echo "2. Ouvrez Claude Code dans ce dossier"
echo "3. Dites a Claude: 'Use tv_health_check to verify TradingView is connected'"
