# QUIZ BOTS
TG & VK quiz bots

## How to install
Clone repository to your local device. To avoid problems with installing required additinal packages, its strongly to use a virtual environment virtualenv/venv, for example:

```
python3 -m venv venv
source myenv/bin/activate
```

## Requirements
Python3.12 should be already installed. Then use pip (or pip3, if there is a conflict with Python2) to install dependencies:

```
pip install -r requirements.txt
```

The script uses additinal packages:

- environs==14.5.0
- setuptools<70.0.0
- urllib3<2.0.0
- python-telegram-bot==13.7
- redis==8.1.0
- vk_api==11.10.1

Environment variables

- TG_TOKEN - telegram token
- REDIS_DB_URL - redis cloud database address
- DB_PORT - redis cloud database port
- DB_PASSWORD - redis cloud database password
- VK_TOKEN - vk token
- VK_GROUP_ID - vk group id

Put .env file to project folder.
.env contains text data without quotes.

## Run
Launch on Linux(Python 3) or Windows:

Telegram bot:

```
python3 tg_bot.py
```

VK bot:

```
python3 vk_bot.py
```

and you will can play quiz.

For creating json file wih questions/answers from txt file use create_quiz_json.py script. Use upload_to_redis.py for upload json file to redis cloud database.

```
python3 create_quiz_json.py
python3 upload_to_redis.py
```

## Project Goals
The code is written for educational purposes on online-course for web-developers dvmn.org.

## Links
- @CosmicPicturesViewerBot
- vk.ru/club241107972

