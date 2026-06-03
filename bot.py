import os
import base64
from collections import defaultdict
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

client = Anthropic()

SYSTEM_PROMPT = """Tu es un expert en analyse technique des marchés financiers spécialisé dans TradingView.
Quand tu reçois un graphique, tu analyses:
- La tendance générale (haussière / baissière / latérale)
- Les niveaux clés de support et résistance
- Les indicateurs visibles (RSI, MACD, moyennes mobiles, volume, etc.)
- Les patterns chartistes (épaule-tête-épaule, triangles, drapeaux, etc.)
- Un signal clair: ACHAT / VENTE / NEUTRE avec la zone d'entrée, le stop-loss et l'objectif

Tes réponses sont concises, en français, et structurées avec des émojis pour la lisibilité.
Si la question est sur un actif sans graphique, tu fournis une analyse basée sur le contexte donné."""

# Historique de conversation par utilisateur (max 10 messages)
conversation_history: dict[int, list] = defaultdict(list)
MAX_HISTORY = 10


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conversation_history[update.effective_user.id].clear()
    await update.message.reply_text(
        "👋 Bonjour! Je suis votre assistant trading IA powered by Claude.\n\n"
        "Vous pouvez:\n"
        "📸 Envoyer un screenshot TradingView → j'analyse le graphique\n"
        "💬 Poser une question → ex: 'BTC/USD 4H, RSI à 28, que penses-tu?'\n\n"
        "Utilisez /reset pour effacer l'historique de conversation."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conversation_history[update.effective_user.id].clear()
    await update.message.reply_text("🔄 Historique effacé. Nouvelle conversation!")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text("🔍 Analyse du graphique en cours...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    image_data = base64.standard_b64encode(bytes(file_bytes)).decode("utf-8")

    caption = update.message.caption or "Analyse ce graphique TradingView en détail."

    history = conversation_history[user_id]
    history.append({
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data},
            },
            {"type": "text", "text": caption},
        ],
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=history[-MAX_HISTORY:],
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})

    await _send_long_message(update, reply)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text

    history = conversation_history[user_id]
    history.append({"role": "user", "content": text})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=history[-MAX_HISTORY:],
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})

    await _send_long_message(update, reply)


async def _send_long_message(update: Update, text: str) -> None:
    # Telegram limite à 4096 caractères par message
    if len(text) <= 4096:
        await update.message.reply_text(text)
    else:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(text[i:i + 4096])


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    # ANTHROPIC_API_KEY est lu automatiquement par la lib anthropic
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot démarré...")
    app.run_polling()


if __name__ == "__main__":
    main()
