from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from environs import Env


def start(update, context):
    update.message.reply_text('Привет! Я синхронный эхо-бот.')


def echo(update, context):
    update.message.reply_text(update.message.text)


def main():
    env = Env()
    env.read_env()

    TOKEN = env.str('TG_TOKEN')

    updater = Updater(token=TOKEN, use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))

    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, echo)
    )

    updater.start_polling()
    print("Бот запущен...")

    updater.idle()


if __name__ == '__main__':
    main()
