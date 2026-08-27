import json
import logging
import random
import re
import time
from environs import Env
from redis import Redis
from requests.exceptions import ReadTimeout
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


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
REDIS_URL = f"redis://default:{DB_PASSWORD}@{REDIS_DB_URL}:{DB_PORT}"
VK_TOKEN = env.str('VK_TOKEN')
GROUP_ID = env.int('VK_GROUP_ID')

if not VK_TOKEN or not GROUP_ID or not REDIS_URL:
    raise ValueError("Не заданы переменные VK_TOKEN, GROUP_ID или REDIS_URL")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
try:
    redis_client.ping()
    logger.info("Подключение к Redis установлено")
except Exception as e:
    logger.error(f"Ошибка подключения к Redis: {e}")
    exit(1)

MENU = 'menu'
ANSWERING = 'answering'


def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


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


def handle_new_question_request(user_id, vk):
    length = redis_client.llen("quiz:questions")
    if length == 0:
        vk.messages.send(
            user_id=user_id,
            message="В базе данных пока нет вопросов.",
            keyboard=get_main_keyboard(),
            random_id=0
        )
        return MENU

    index = random.randint(0, length - 1)
    item_json = redis_client.lindex("quiz:questions", index)
    try:
        item = json.loads(item_json)
    except json.JSONDecodeError:
        vk.messages.send(
            user_id=user_id,
            message="Ошибка формата вопроса. Попробуйте позже.",
            keyboard=get_main_keyboard(),
            random_id=0
        )
        return MENU

    redis_client.hset(f"user:{user_id}", mapping={
        'current_question': item['question'],
        'current_answer': item['answer']
    })

    vk.messages.send(
        user_id=user_id,
        message=f"Вопрос: {item['question']}",
        keyboard=get_main_keyboard(),
        random_id=0
    )
    return ANSWERING


def handle_surrender_in_menu(user_id, vk):
    vk.messages.send(
        user_id=user_id,
        message="Нажмите «Новый вопрос».",
        keyboard=get_main_keyboard(),
        random_id=0
    )
    return MENU


def handle_surrender_in_game(user_id, vk):
    user_data = redis_client.hgetall(f"user:{user_id}")
    if not user_data or 'current_answer' not in user_data:
        vk.messages.send(
            user_id=user_id,
            message="Что-то пошло не так. Нажмите «Новый вопрос».",
            keyboard=get_main_keyboard(),
            random_id=0
        )
        return MENU

    correct = user_data['current_answer']
    vk.messages.send(
        user_id=user_id,
        message=f"Правильный ответ: {correct}",
        keyboard=get_main_keyboard(),
        random_id=0
    )
    return handle_new_question_request(user_id, vk)


def handle_score(user_id, vk):
    score = redis_client.hget(f"user:{user_id}", 'score')
    if score is None:
        score = 0
    vk.messages.send(
        user_id=user_id,
        message=f"Ваш счёт очков: {score}",
        keyboard=get_main_keyboard(),
        random_id=0
    )
    return None


def handle_solution_attempt(user_id, vk, text):
    user_data = redis_client.hgetall(f"user:{user_id}")
    if not user_data or 'current_answer' not in user_data:
        vk.messages.send(
            user_id=user_id,
            message="Сначала нажмите «Новый вопрос».",
            keyboard=get_main_keyboard(),
            random_id=0
        )
        return ANSWERING

    user_keyword = extract_keyword(text)
    correct_keyword = extract_keyword(user_data['current_answer'])

    if not user_keyword or not correct_keyword:
        vk.messages.send(
            user_id=user_id,
            message="Не удалось распознать ответ. Попробуйте ещё раз.",
            keyboard=get_main_keyboard(),
            random_id=0
        )
        return ANSWERING

    if user_keyword == correct_keyword:
        redis_client.hincrby(f"user:{user_id}", 'score', 1)
        vk.messages.send(
            user_id=user_id,
            message="Правильно! Для продолжения нажми «Новый вопрос»",
            keyboard=get_main_keyboard(),
            random_id=0
        )
    else:
        vk.messages.send(
            user_id=user_id,
            message="Неправильно. Попробуйте ещё раз или нажмите «Сдаться».",
            keyboard=get_main_keyboard(),
            random_id=0
        )
    return ANSWERING


def handle_unknown_in_menu(user_id, vk):
    vk.messages.send(
        user_id=user_id,
        message="Пожалуйста, используйте кнопки меню.",
        keyboard=get_main_keyboard(),
        random_id=0
    )
    return MENU


def main():
    vk_session = VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    logger.info("VK бот запущен...")

    while True:
        try:
            longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    message = event.obj.message
                    user_id = message['from_id']
                    if user_id == -GROUP_ID:
                        continue
                    text = message['text'].strip()

                    state = redis_client.hget(f"user:{user_id}", 'state')
                    if state is None:
                        state = MENU
                        redis_client.hset(f"user:{user_id}", 'state', state)

                    if state == MENU:
                        if text == "Новый вопрос":
                            new_state = handle_new_question_request(
                                user_id,
                                vk
                            )
                        elif text == "Сдаться":
                            new_state = handle_surrender_in_menu(user_id, vk)
                        elif text == "Мой счет":
                            new_state = handle_score(user_id, vk)
                        else:
                            new_state = handle_unknown_in_menu(user_id, vk)
                    elif state == ANSWERING:
                        if text == "Новый вопрос":
                            new_state = handle_new_question_request(
                                user_id,
                                vk
                            )
                        elif text == "Сдаться":
                            new_state = handle_surrender_in_game(user_id, vk)
                        elif text == "Мой счет":
                            new_state = handle_score(user_id, vk)
                        else:
                            new_state = handle_solution_attempt(
                                user_id,
                                vk,
                                text
                            )
                    else:
                        new_state = MENU

                    if new_state is not None:
                        redis_client.hset(
                            f"user:{user_id}",
                            'state',
                            new_state
                        )

        except ReadTimeout:
            logger.warning("Таймаут Long Poll. Переподключаемся...")
            time.sleep(2)
            continue
        except Exception as e:
            logger.error(
                f"Критическая ошибка в Long Poll: {e}. Перезапуск через 5 сек"
            )
            time.sleep(5)
            continue


if __name__ == '__main__':
    main()
