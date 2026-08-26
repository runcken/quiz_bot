import json
import random
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from environs import Env


with open('quiz.json', 'r', encoding='utf-8') as quiz_file:
    QUIZ = json.load(quiz_file)

def get_main_keyboard():
    keyboard = [
        ["Новый вопрос", "Сдаться"],
        ["Мой счет"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def start(update, context):
    context.user_data.clear()
    update.message.reply_text(
        'Привет! Я бот для викторины. Нажми "Новый вопрос":',
        reply_markup=get_main_keyboard()
    )


def handle_message(update, context):
    text = update.message.text
    user_id = update.effective_user.id

    if 'score' not in context.user_data:
        context.user_data['score'] = 0
    if 'current_question' not in context.user_data:
        context.user_data['current_question'] = None
    if 'current_answer' not in context.user_data:
        context.user_data['current_answer'] = None

    if text == "Новый вопрос":
        question, answer = random.choice(list(QUIZ.items()))
        context.user_data['current_question'] = question
        context.user_data['current_answer'] = answer

        update.message.reply_text(
            f"{question}",
            reply_markup=get_main_keyboard()
        )

    elif text == "Сдаться":
        if context.user_data['current_answer']:
            correct = context.user_data['current_answer']
            update.message.reply_text(
                f"Правильный ответ: {correct}",
                reply_markup=get_main_keyboard()
            )
        else:
            update.message.reply_text(
                "Вы еще не начали отвечать на вопрос. Нажмите 'Новый вопрос'.",
                reply_markup=get_main_keyboard()
            )

    elif text == "Мой счет":
        score = context.user_data.get('score', 0)
        update.message.reply_text(
            f"Ваш счет: {score} очков",
            reply_markup=get_main_keyboard()
        )

    else:
        if context.user_data['current_answer'] is not None:
            user_answer = text.lower()
            correct_answer = context.user_data['current_answer'].lower()
            if user_answer == correct_answer:
                context.user_data['score'] += 1
                update.message.reply_text(
                    "Правильно. +1 очко",
                    reply_markup=get_main_keyboard()
                )
            else:
                update.message.reply_text(
                    f"Неправильно. Попробуйте еще раз или нажмите 'Сдаться'.",
                    reply_markup=get_main_keyboard()
                )
        else:
            update.message.reply_text(
                f"Вы написали: {text}\nДля начала игры нажмите 'Новый вопрос'.",
                reply_markup=get_main_keyboard()
            )

def main():
    env = Env()
    env.read_env()
    TOKEN = env.str('TG_TOKEN')

    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )

    updater.start_polling()
    print("Бот запущен...")
    updater.idle()

if __name__ == '__main__':
    main()