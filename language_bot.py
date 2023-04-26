import logging
import openai
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, 
                          ContextTypes, 
                          CommandHandler, 
                          filters, 
                          MessageHandler,
                          ConversationHandler)




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

openai.api_key = "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"
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


### End the chat
async def quit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Quit chat"""
    logger.info("User quitted the chat.")
    await update.message.reply_text(
        "You quitted chat", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token('6078244379:AAFXxyhuMewvk6F3ZuY1NrhfUh_SC4AozmE').build()
    
    start_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODE: [
                MessageHandler(filters.Regex('^(Generic Chat)$'), generic_chat),
                MessageHandler(filters.Regex('^(Translation)$'), translate),
            ],
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generic_chat)],
            LANGUAGE: [MessageHandler(filters.Regex("^(🇫🇮 Finnish|🇬🇧 English|🇮🇹 Italian)$"), language)],
            TEXT_TO_TRANSLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_translate)],
        },
        fallbacks=[CommandHandler("quit", quit)],
    )

    application.add_handler(start_handler)

    application.run_polling()

if __name__ == '__main__':
    main()