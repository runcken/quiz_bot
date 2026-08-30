import json
import redis
from environs import Env


if __name__ == '__main__':
    env = Env()
    env.read_env()

    REDIS_DB_URL = env.str('REDIS_DB_URL')
    DB_PASSWORD = env.str('DB_PASSWORD')
    DB_PORT = env.str('DB_PORT')

    REDIS_URL = f"redis://default:{DB_PASSWORD}@{REDIS_DB_URL}:{DB_PORT}"

    r = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        r.ping()
        print("Успешное подключение к Redis Cloud!")

    except redis.exceptions.ConnectionError as e:
        print(f"Ошибка подключения: {e}")
        return


    file_path = 'quiz.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as quiz_file:
            quiz = json.load(quiz_file)

    except FileNotFoundError:
        print(f"Файл {file_path} не найден. Проверьте путь.")
        exit(1)

    questions = [{
        "id": i+1,
        "question": q,
        "answer": a
        } for i, (q, a) in enumerate(quiz.items())
    ]

    redis_key = "quiz:questions"
    r.delete(redis_key)
    for item in questions:
        r.rpush(redis_key, json.dumps(item, ensure_ascii=False))

    print(f"Загружено {len(questions)} вопросов в ключ {redis_key}")

    r.set("quiz:raw_dict", json.dumps(quiz, ensure_ascii=False))
    print("Резервная копия сохранена в ключ 'quiz:raw_dict'")
