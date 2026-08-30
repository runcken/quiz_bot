import json
import logging
import random
import re
from environs import Env
from redis import Redis
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

env = Env()
env.read_env()

REDIS_DB_URL = env.str('REDIS_DB_URL')
DB_PASSWORD = env.str('DB_PASSWORD')
DB_PORT = env.str('DB_PORT')
TOKEN = env.str('TG_TOKEN')
REDIS_URL = f"redis://default:{DB_PASSWORD}@{REDIS_DB_URL}:{DB_PORT}"

if not TOKEN or not REDIS_URL:
    raise ValueError("Не заданы переменные окружения TG_TOKEN или REDIS_URL")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
try:
    redis_client.ping()
    logger.info("Подключение к Redis установлено")
except Exception as e:
    logger.error(f"Ошибка подключения к Redis: {e}")
    return

MENU, ANSWERING = range(2)


def get_main_keyboard():
    keyboard = [
        ["Новый вопрос", "Сдаться"],
        ["Мой счет"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def extract_keyword(text):
    if not text:
        return ''
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)
    for ch in ['"', "'", '`', '“', '”', '«', '»']:
        text = text.replace(ch, '')
    words = text.split()
    if not words:
        return ''
    first = words[0]
    first = first.strip('.,!?;:')
    return first.lower()


def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text(
        "Привет! Я бот для викторин.\n"
        "Нажми «Новый вопрос», чтобы начать игру.",
        reply_markup=get_main_keyboard()
    )
    return MENU


def handle_new_question_request(update: Update, context: CallbackContext):
    length = redis_client.llen("quiz:questions")
    if length == 0:
        update.message.reply_text(
            "В базе данных пока нет вопросов.",
            reply_markup=get_main_keyboard()
        )
        return MENU

    index = random.randint(0, length - 1)
    item_json = redis_client.lindex("quiz:questions", index)
    try:
        item = json.loads(item_json)
    except json.JSONDecodeError:
        update.message.reply_text("Ошибка формата вопроса. Попробуйте позже.")
        return MENU

    context.user_data['current_question'] = item['question']
    context.user_data['current_answer'] = item['answer']

    update.message.reply_text(
        f"Вопрос: {item['question']}",
        reply_markup=get_main_keyboard()
    )
    return ANSWERING


def handle_surrender_in_menu(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Вы ещё не начали отвечать на вопрос. Нажмите «Новый вопрос».",
        reply_markup=get_main_keyboard()
    )
    return MENU


def handle_surrender_in_game(update: Update, context: CallbackContext):
    if 'current_answer' not in context.user_data:
        update.message.reply_text(
            "Что-то пошло не так. Нажмите «Новый вопрос».",
            reply_markup=get_main_keyboard()
        )
        return MENU

    correct = context.user_data['current_answer']
    update.message.reply_text(
        f"Правильный ответ: {correct}",
        reply_markup=get_main_keyboard()
    )
    return handle_new_question_request(update, context)


def handle_score(update: Update, context: CallbackContext):
    score = context.user_data.get('score', 0)
    update.message.reply_text(
        f"Ваш счёт очков: {score}",
        reply_markup=get_main_keyboard()
    )
    return None


def handle_solution_attempt(update: Update, context: CallbackContext):
    text = update.message.text

    if 'current_answer' not in context.user_data:
        update.message.reply_text(
            "Сначала нажмите «Новый вопрос».",
            reply_markup=get_main_keyboard()
        )
        return ANSWERING

    user_keyword = extract_keyword(text)
    correct_keyword = extract_keyword(context.user_data['current_answer'])

    if not user_keyword or not correct_keyword:
        update.message.reply_text(
            "Не удалось распознать ключевое слово. Попробуйте ещё раз.",
            reply_markup=get_main_keyboard()
        )
        return ANSWERING

    if user_keyword == correct_keyword:
        context.user_data['score'] = context.user_data.get('score', 0) + 1
        update.message.reply_text(
            "Правильно! Поздравляю! Для продолжения нажми «Новый вопрос»",
            reply_markup=get_main_keyboard()
        )
    else:
        update.message.reply_text(
            "Неправильно. Попробуйте ещё раз или нажмите «Сдаться».",
            reply_markup=get_main_keyboard()
        )
    return ANSWERING


def handle_unknown_in_menu(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Пожалуйста, используйте кнопки меню.",
        reply_markup=get_main_keyboard()
    )
    return MENU


def error_handler(update, context):
    logger.error(f"Ошибка при обновлении {update}: {context.error}")
    if update and update.effective_message:
        update.effective_message.reply_text(
            "Произошла внутренняя ошибка. Попробуйте позже."
        )


def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                MessageHandler(
                    Filters.regex('^Новый вопрос$'),
                    handle_new_question_request
                ),
                MessageHandler(
                    Filters.regex('^Сдаться$'),
                    handle_surrender_in_menu
                ),
                MessageHandler(Filters.regex('^Мой счет$'), handle_score),
                MessageHandler(Filters.text, handle_unknown_in_menu),
            ],
            ANSWERING: [
                MessageHandler(
                    Filters.regex('^Новый вопрос$'),
                    handle_new_question_request
                ),
                MessageHandler(
                    Filters.regex('^Сдаться$'),
                    handle_surrender_in_game
                ),
                MessageHandler(Filters.regex('^Мой счет$'), handle_score),
                MessageHandler(Filters.text, handle_solution_attempt),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error_handler)

    logger.info("Бот запущен и готов к работе")
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
