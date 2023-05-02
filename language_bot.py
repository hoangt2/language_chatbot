from dotenv.main import load_dotenv
import os
import logging
import openai
import replicate
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, 
                          ContextTypes, 
                          CommandHandler, 
                          filters, 
                          MessageHandler,
                          ConversationHandler)

import urllib.request
from moviepy.editor import AudioFileClip

load_dotenv()
openai.api_key = os.environ['OPENAI_API_KEY']

### LOGGING
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

### START MENU

MODE, CHAT, LANGUAGE, TEXT_TO_TRANSLATE = range (4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Generic Chat", "Translation"]]
    await update.message.reply_text(
        "Hello, I am your Finnish languague trainer. Choose the chat mode:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Chat or Translation?"
        ),
    )
    return MODE

### GENERIC CHAT


messages = [{"role": "system", "content": "You are a Finnish language teacher named Anna"}]

async def generic_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    logger.info("User: %s", update.message.text)

    messages.append({"role": "user", "content": update.message.text})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    ChatGPT_reply = response["choices"][0]["message"]["content"]

    logger.info("Response from ChatGPT: %s", ChatGPT_reply)

    await update.message.reply_text(text=f"*[Bot]:* {ChatGPT_reply}", parse_mode= 'MARKDOWN')
    messages.append({"role": "assistant", "content": ChatGPT_reply})

    return CHAT

### TRANSLATION

async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''Starts the conversation and asks the user about which language they want to translate'''
    reply_keyboard = [['🇬🇧 English', '🇫🇮 Finnish','🇮🇹 Italian']]

    logger.info('User chose Translation')

    await update.message.reply_text(
        "Which destination language do you want to translate to?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Choose the destination language"
        ),
    )

    return LANGUAGE


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected language and ask for the text to translate"""
    translation_language = update.message.text

    logger.info("Language chosen: %s", translation_language)

    user_data = context.user_data
    user_data['translation_language'] = translation_language

    await update.message.reply_text(
        "Type the text you want to translate to " + translation_language,
        reply_markup=ReplyKeyboardRemove(),
    )

    return TEXT_TO_TRANSLATE

async def text_to_translate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''Get the text and return the translation'''
    logger.info("Text to translate: %s", update.message.text)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'system','content': 'Translate the text to ' + context.user_data['translation_language']},
                  {'role':'user','content': update.message.text}
                  ]
    )
    ChatGPT_reply = response["choices"][0]["message"]["content"]
    logger.info("Response from ChatGPT: %s", ChatGPT_reply)
    await update.message.reply_text(text=f"*[Translation]:* {ChatGPT_reply}", parse_mode= 'MARKDOWN')

    return TEXT_TO_TRANSLATE

### VOICE MESSAGE
async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("User sent a voice message")
    await update.message.reply_text("I've received a voice message! Please give me a second to respond :)")
    file_info = await context.bot.getFile(update.message.voice.file_id)
    urllib.request.urlretrieve(file_info.file_path, "voice_message.oga")
    audio_clip = AudioFileClip("voice_message.oga")
    audio_clip.write_audiofile("voice_message.mp3")
    audio_file = open("voice_message.mp3", "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file).text
    
    await update.message.reply_text(text=f"*[You]:* _{transcript}_", parse_mode='MARKDOWN')
    messages.append({"role": "user", "content": transcript})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    ChatGPT_reply = response["choices"][0]["message"]["content"]
    await update.message.reply_text(text=f"*[Bot]:* {ChatGPT_reply}", parse_mode='MARKDOWN')
    messages.append({"role": "assistant", "content": ChatGPT_reply})

### IMAGE CAPTION
async def image_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("User sent a photo")
    await update.message.reply_text("I have received a photo, let me give you the caption about it")
    file_info = await context.bot.getFile(update.message.photo[3].file_id) #0 for thumbnail and 3 for bigger size
    urllib.request.urlretrieve(file_info.file_path, 'photo.jpg')

    caption_ENG = replicate.run(
    "salesforce/blip:2e1dddc8621f72155f24cf2e0adbde548458d3cab9f00c0139eea840d0ac4746",
    input={"image": open("photo.jpg", "rb")}
    )
    translation = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{'role':'system','content': 'Translate the text to Finnish and Italian, put it in this format: ENG: <original text> \n FI: <text> \n IT: <text>'},
                  {'role':'user','content': caption_ENG}
                  ]
    )
    caption = translation["choices"][0]["message"]["content"]
    logger.info("Response from ChatGPT: %s", caption)
    await update.message.reply_text(text=f"{caption}", parse_mode= 'MARKDOWN')

### End the chat
async def quit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Quit chat"""
    logger.info("User quitted the chat.")
    await update.message.reply_text(
        "You quitted chat", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token(os.environ['TELEGRAM_BOT_TOKEN']).build()
    
    start_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODE: [
                MessageHandler(filters.Regex('^(Generic Chat)$'), generic_chat),
                MessageHandler(filters.Regex('^(Translation)$'), translate),
            ],
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generic_chat),
                   MessageHandler(filters.VOICE, voice_message),
                   MessageHandler(filters.PHOTO, image_caption)
                   ],
            LANGUAGE: [MessageHandler(filters.Regex("^(🇫🇮 Finnish|🇬🇧 English|🇮🇹 Italian)$"), language)],
            TEXT_TO_TRANSLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_translate)],
        },
        fallbacks=[CommandHandler("quit", quit)],
    )

    application.add_handler(start_handler)

    application.run_polling()

if __name__ == '__main__':
    main()