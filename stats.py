import os


def analyze_file(filepath):
    """
    Анализирует один файл и возвращает количество общих, пустых и
    комментированных строк, учитывая многострочные комментарии (docstrings).
    """
    total_lines = 0
    empty_lines = 0
    comment_lines = 0
    in_multiline_comment = False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                total_lines += 1
                stripped_line = line.strip()

                if not stripped_line:
                    empty_lines += 1
                    continue

                # Логика для отслеживания состояния внутри/вне многострочного комментария
                if in_multiline_comment:
                    comment_lines += 1
                    # Если в строке есть закрывающие кавычки, выходим из состояния
                    if '"""' in stripped_line or "'''" in stripped_line:
                        in_multiline_comment = False
                    continue

                # Проверяем, не начинается ли строка с однострочного комментария
                if stripped_line.startswith("#"):
                    comment_lines += 1
                    continue

                # Проверяем на начало многострочного комментария
                if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                    comment_lines += 1
                    # Если комментарий не закрывается на той же строке,
                    # входим в состояние многострочного комментария
                    if not (stripped_line.endswith('"""') or stripped_line.endswith("'''")) or len(stripped_line) <= 3:
                        in_multiline_comment = True
                    continue

                # Все остальные строки считаются кодом
                # (даже если у них есть комментарий в конце, т.к. это строка с кодом)

    except (UnicodeDecodeError, FileNotFoundError) as e:
        print(f"Не удалось прочитать файл: {filepath}, ошибка: {e}")
        return 0, 0, 0

    return total_lines, empty_lines, comment_lines


def is_test_file(filepath, root_dir):
    """
    Проверяет, является ли файл тестовым согласно заданным правилам.
    """
    filename = os.path.basename(filepath)

    if filename == "conftest.py":
        return True
    if filename.startswith("test_"):
        return True
    if filename.endswith("_test.py"):
        return True
    # Проверяем, есть ли папка 'tests' в пути к файлу
    if os.path.sep + "tests" + os.path.sep in os.path.sep + root_dir + os.path.sep:
        return True

    return False


def print_stats(title, stats):
    """
    Красиво выводит на экран собранную статистику.
    """
    print("-" * 30)
    print(title)
    print("-" * 30)
    print(f"Всего строк: {stats['total']}")
    print(f"Пустых строк: {stats['empty']}")
    print(f"Строк с комментариями: {stats['comment']}")
    code_lines = stats["total"] - stats["empty"] - stats["comment"]
    print(f"Строк с кодом: {code_lines}")
    print()


def main():
    """
    Основная функция для сбора и вывода статистики.
    """
    project_stats = {"total": 0, "empty": 0, "comment": 0}
    test_stats = {"total": 0, "empty": 0, "comment": 0}

    exclude_dirs = {".git", "venv", ".venv", "__pycache__", ".idea", "build", "dist"}
    current_script_name = os.path.basename(__file__)

    for root, dirs, files in os.walk(".", topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in files:
            if filename.endswith(".py"):
                if filename == current_script_name and root == ".":
                    continue

                filepath = os.path.join(root, filename)

                total, empty, comment = analyze_file(filepath)

                project_stats["total"] += total
                project_stats["empty"] += empty
                project_stats["comment"] += comment

                if is_test_file(filepath, root):
                    test_stats["total"] += total
                    test_stats["empty"] += empty
                    test_stats["comment"] += comment

    print_stats("Общая статистика по файлам .py", project_stats)
    print_stats("Статистика по тестам", test_stats)


if __name__ == "__main__":
    main()
