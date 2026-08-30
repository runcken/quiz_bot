import json
from pathlib import Path


def parse_quiz_by_double_newlines(text: str) -> dict:
    blocks = text.split('\n\n')

    quiz = {}
    current_question = None

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if block.startswith('Вопрос'):
            parts = block.split('\n', 1)
            current_question = (
                parts[1].strip()
                if len(parts) > 1
                else block.split(':', 1)[-1].strip()
            )

        elif block.startswith('Ответ') and current_question:
            parts = block.split('\n', 1)
            answer = (
                parts[1].strip()
                if len(parts) > 1
                else block.split(':', 1)[-1].strip()
            )

            quiz[current_question] = answer
            current_question = None

    return quiz


if __name__ == '__main__':
    folder_path = 'quiz-questions'

    folder = Path(folder_path)

    if not folder.exists():
        print(f"Папка '{folder_path}' не найдена!")
        exit(1)

    all_questions = {}
    file_counter = 0

    txt_files = list(folder.glob('*.txt'))

    if not txt_files:
        print(f"В папке '{folder_path}' не найдено .txt файлов!")
        exit(1)

    print(f"Найдено {len(txt_files)} файлов для обработки:")

    for txt_file in txt_files:
        print(f"  - {txt_file.name}")

        try:
            with open(txt_file, 'r', encoding='KOI8-R') as input_file:
                raw_text = input_file.read()

            file_questions = parse_quiz_by_double_newlines(raw_text)

            for question, answer in file_questions.items():
                all_questions[question] = answer

            file_counter += 1
            print(f"    Обработано: {len(file_questions)} вопросов")

        except Exception as e:
            print(f"    Ошибка при обработке {txt_file.name}: {e}")

    print(f"\nВсего обработано файлов: {file_counter}")
    print(f"Всего вопросов собрано: {len(all_questions)}")

    output_file = 'quiz.json'
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(all_questions, file, ensure_ascii=False, indent=4)

    print(f"\nРезультат сохранен в '{output_file}'")

    print("\nПример первых 5 вопросов:")
    for i, (q, a) in enumerate(list(all_questions.items())[:5], 1):
        print(f"\n{i}. {q}")
        print(f"   Ответ: {a}")
