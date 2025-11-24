# telegram_bot.py
import os
from typing import Dict, List

import telebot

from rag_api import get_answer_from_pdf

# Token del bot de Telegram:
# Puedes ponerlo en TELEGRAM_BOT_TOKEN o escribirlo directo aquí.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PONE_TU_TOKEN_AQUI")

if TELEGRAM_BOT_TOKEN.startswith("PONE_TU_TOKEN"):
    raise ValueError("Configura tu TELEGRAM_BOT_TOKEN antes de ejecutar el bot.")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="Markdown")

# Historial simple en memoria: {chat_id: [ {role, content}, ... ]}
chat_histories: Dict[int, List[Dict[str, str]]] = {}


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    chat_id = message.chat.id
    chat_histories[chat_id] = []

    text = (
        "Hola, soy tu chatbot RAG para NT.\n"
        "Puedo responder preguntas basadas en el contenido del PDF cargado.\n\n"
        "Escríbeme una pregunta sobre el documento."
    )
    bot.reply_to(message, text)


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text.strip()

    # Inicializo historial si no existe
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    history = chat_histories[chat_id]

    # Agrego el mensaje del usuario al historial
    history.append({"role": "user", "content": user_text})

    # Llamo a la función RAG para obtener respuesta
    try:
        answer = get_answer_from_pdf(user_text, history)
    except Exception as e:
        print(f"Error al generar respuesta: {e}")
        answer = "Ocurrió un error interno al procesar tu pregunta."

    # Agrego la respuesta del bot al historial
    history.append({"role": "assistant", "content": answer})
    chat_histories[chat_id] = history

    # Envío respuesta al usuario
    bot.reply_to(message, answer)


if __name__ == "__main__":
    print("Bot de Telegram iniciado. Esperando mensajes...")
    bot.infinity_polling()
