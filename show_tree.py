"""
Print a clean project tree, skipping noise directories.
Usage:
    python show_tree.py                # print to console
    python show_tree.py tree.txt       # save to file
"""
import os
import sys

IGNORE_DIRS = {
    ".git", ".venv", "venv", "env",
    "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache",
    ".vite", ".idea", ".vscode",
    "coverage", "htmlcov",
}

IGNORE_FILES = {".DS_Store", "Thumbs.db"}

ROOT = os.path.abspath(os.path.dirname(__file__))


def walk(path: str, prefix: str, out: list[str]) -> None:
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return

    dirs = [e for e in entries if os.path.isdir(os.path.join(path, e)) and e not in IGNORE_DIRS]
    files = [e for e in entries if os.path.isfile(os.path.join(path, e)) and e not in IGNORE_FILES]

    for i, d in enumerate(dirs):
        is_last = (i == len(dirs) - 1) and not files
        out.append(f"{prefix}{'└── ' if is_last else '├── '}{d}/")
        walk(os.path.join(path, d), prefix + ("    " if is_last else "│   "), out)

    for i, f in enumerate(files):
        is_last = i == len(files) - 1
        out.append(f"{prefix}{'└── ' if is_last else '├── '}{f}")


def main() -> None:
    out: list[str] = [os.path.basename(ROOT) + "/"]
    walk(ROOT, "", out)
    text = "\n".join(out)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"Wrote {sys.argv[1]} ({len(out)} entries).")
    else:
        print(text)


if __name__ == "__main__":
    main()