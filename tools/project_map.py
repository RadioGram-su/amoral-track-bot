#!/usr/bin/env python3
"""
Генератор карты проекта: PROJECT_MAP.md.

Карта нужна, чтобы открывать нужный файл сразу (путь + строка), а не перечитывать
весь репозиторий. Для каждого файла: назначение (первая строка докстринга/комментария)
и список символов с номерами строк (функции, классы, сигналы, константы-экспорты).

    python3 tools/project_map.py          # перегенерировать карту
    python3 tools/project_map.py --check  # код выхода 1, если карта устарела
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "PROJECT_MAP.md")

SKIP_DIRS = {".git", ".godot", "node_modules", "__pycache__", ".import", "build", "export"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".webp", ".glb", ".gltf", ".ttf", ".otf", ".wav", ".ogg", ".mp3",
              ".apk", ".aab", ".zip", ".tpz", ".blend", ".exr", ".hdr", ".import", ".uid", ".res", ".scn"}

SYMBOL_PATTERNS = {
    ".py": [r"^(class\s+\w+)", r"^(def\s+\w+)"],
    ".gd": [r"^(class_name\s+\w+)", r"^(signal\s+\w+)", r"^(func\s+\w+)", r"^(class\s+\w+)", r"^(enum\s+\w+)", r"^(const\s+[A-Z_][A-Z0-9_]+)"],
    ".js": [r"^(?:async\s+)?(function\s+\w+)", r"^(class\s+\w+)", r"^module\.exports\s*=\s*(\{[^}]{0,80})"],
    ".gdshader": [r"^(uniform\s+\w+\s+\w+)", r"^(void\s+\w+)", r"^(\w+\s+\w+\s*\([^)]*\)\s*\{)"],
    ".sh": [r"^(\w+\s*\(\)\s*\{)"],
}


def list_files():
    try:
        out = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, text=True)
        files = [f for f in out.splitlines() if f]
    except Exception:
        files = []
        for dp, dn, fn in os.walk(ROOT):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                files.append(os.path.relpath(os.path.join(dp, f), ROOT))
    res = []
    for f in sorted(set(files)):
        parts = f.split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue
        if f == "PROJECT_MAP.md":
            continue
        if os.path.isfile(os.path.join(ROOT, f)):
            res.append(f)
    return res


def describe(path, text, ext):
    lines = text.splitlines()
    if ext == ".md":
        for l in lines:
            if l.startswith("#"):
                return l.lstrip("# ").strip()
    if ext == ".py":
        m = re.search(r'^\s*("""|\'\'\')\s*\n?(.*?)\n', text, re.S)
        if m:
            first = m.group(2).strip() or (text.split(m.group(1))[1].strip().splitlines() or [""])[0]
            return first
    for l in lines[:12]:
        s = l.strip()
        for pre in ("##", "#", "//", "/**", "*", ";"):
            if s.startswith(pre) and len(s) > len(pre) + 3 and not s.startswith("#!"):
                cand = s[len(pre):].strip(" */")
                if cand and not cand.startswith("@") and "extends" not in cand:
                    return cand
    if ext == ".json":
        m = re.findall(r'^\s{0,2}"([^"]+)"\s*:', text, re.M)
        if m:
            return "ключи: " + ", ".join(m[:8])
    if ext == ".gd":
        m = re.search(r"^extends\s+(\w+)", text, re.M)
        if m:
            return "extends " + m.group(1)
    return ""


def symbols(text, ext):
    pats = SYMBOL_PATTERNS.get(ext)
    if not pats:
        return []
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        for p in pats:
            m = re.match(p, line)
            if m:
                found.append((i, m.group(1).strip()))
                break
    return found


def build():
    files = list_files()
    groups = {}
    for f in files:
        top = f.split("/")[0] if "/" in f else "(корень)"
        if f.startswith("games/"):
            parts = f.split("/")
            top = "/".join(parts[:2])
        groups.setdefault(top, []).append(f)

    out = ["# Карта проекта", "",
           "> Сгенерировано `python3 tools/project_map.py`. Не редактировать вручную —",
           "> перегенерируй после изменений. Формат: `путь` — назначение; ниже символы `строка: имя`.",
           ""]
    for top in sorted(groups):
        out.append(f"## {top}")
        out.append("")
        binaries = []
        for f in groups[top]:
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(ROOT, f)
            if ext in BINARY_EXT:
                binaries.append(f)
                continue
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                binaries.append(f)
                continue
            n = text.count("\n") + 1
            desc = describe(f, text, ext)
            out.append(f"- `{f}` ({n} стр.)" + (f" — {desc}" if desc else ""))
            syms = symbols(text, ext)
            if syms:
                shown = syms[:40]
                out.append("  - " + " · ".join(f"{ln}: `{name}`" for ln, name in shown)
                           + (f" · …ещё {len(syms) - 40}" if len(syms) > 40 else ""))
        if binaries:
            by_dir = {}
            for b in binaries:
                by_dir.setdefault(os.path.dirname(b), []).append(os.path.basename(b))
            for d, names in sorted(by_dir.items()):
                shown = ", ".join(names[:12]) + (f", …ещё {len(names) - 12}" if len(names) > 12 else "")
                out.append(f"- `{d}/` — ресурсы ({len(names)}): {shown}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    content = build()
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != content:
            print("PROJECT_MAP.md устарела: запусти python3 tools/project_map.py")
            sys.exit(1)
        print("PROJECT_MAP.md актуальна")
        sys.exit(0)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("PROJECT_MAP.md:", content.count("\n"), "строк")
