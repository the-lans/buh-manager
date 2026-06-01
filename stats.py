from pathlib import Path
from typing import TypedDict

EXCLUDED_DIRS: set[str] = {".git", "venv", ".venv", "__pycache__", ".idea", "build", "dist"}
PYTHON_SUFFIX = ".py"
TEST_DIR_NAME = "tests"


class LineStats(TypedDict):
    total: int
    empty: int
    comment: int


def analyze_file(filepath: Path) -> LineStats:
    stats: LineStats = {"total": 0, "empty": 0, "comment": 0}
    in_multiline_comment = False

    try:
        with filepath.open("r", encoding="utf-8") as file:
            for line in file:
                stats["total"] += 1
                stripped_line = line.strip()

                if not stripped_line:
                    stats["empty"] += 1
                    continue

                if in_multiline_comment:
                    stats["comment"] += 1
                    if '"""' in stripped_line or "'''" in stripped_line:
                        in_multiline_comment = False
                    continue

                if stripped_line.startswith("#"):
                    stats["comment"] += 1
                    continue

                if stripped_line.startswith(('"""', "'''")):
                    stats["comment"] += 1
                    is_single_line = (
                        len(stripped_line) > 3
                        and (stripped_line.endswith('"""') or stripped_line.endswith("'''"))
                    )
                    if not is_single_line:
                        in_multiline_comment = True
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        print(f"Не удалось прочитать файл: {filepath}, ошибка: {exc}")

    return stats


def is_test_file(filepath: Path) -> bool:
    filename = filepath.name
    return (
        filename == "conftest.py"
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or TEST_DIR_NAME in filepath.parts
    )


def print_stats(title: str, stats: LineStats) -> None:
    print("-" * 30)
    print(title)
    print("-" * 30)
    print(f"Всего строк: {stats['total']}")
    print(f"Пустых строк: {stats['empty']}")
    print(f"Строк с комментариями: {stats['comment']}")
    code_lines = stats["total"] - stats["empty"] - stats["comment"]
    print(f"Строк с кодом: {code_lines}")
    print()


def add_stats(target: LineStats, source: LineStats) -> None:
    target["total"] += source["total"]
    target["empty"] += source["empty"]
    target["comment"] += source["comment"]


def iter_python_files(root: Path) -> list[Path]:
    return [
        filepath
        for filepath in root.rglob(f"*{PYTHON_SUFFIX}")
        if not any(part in EXCLUDED_DIRS for part in filepath.parts)
        and filepath != Path(__file__).resolve()
    ]


def main() -> None:
    project_stats: LineStats = {"total": 0, "empty": 0, "comment": 0}
    test_stats: LineStats = {"total": 0, "empty": 0, "comment": 0}

    for filepath in iter_python_files(Path.cwd()):
        file_stats = analyze_file(filepath)
        add_stats(project_stats, file_stats)
        if is_test_file(filepath):
            add_stats(test_stats, file_stats)

    print_stats("Общая статистика по файлам .py", project_stats)
    print_stats("Статистика по тестам", test_stats)


if __name__ == "__main__":
    main()
