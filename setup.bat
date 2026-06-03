@echo off
echo === TradingView MCP Setup ===

if not exist "tradingview-mcp" (
    echo Telechargement de tradingview-mcp...
    git clone https://github.com/tradesdontlie/tradingview-mcp.git
) else (
    echo Mise a jour de tradingview-mcp...
    cd tradingview-mcp && git pull && cd ..
)

echo Installation des dependances...
cd tradingview-mcp && npm install && cd ..

echo.
echo === Installation terminee! ===
echo.
echo Etapes suivantes:
echo.
echo 1. Lancez TradingView Desktop en mode debug:
echo    tradingview-mcp\scripts\launch_tv_debug.bat
echo.
echo 2. Ouvrez Claude Code dans ce dossier
echo 3. Dites a Claude: "Use tv_health_check to verify TradingView is connected"
echo.
pause
