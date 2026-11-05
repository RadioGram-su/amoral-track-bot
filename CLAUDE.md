# Правила работы с репозиторием

## Сначала — карта проекта
1. Открой `PROJECT_MAP.md`: там каждый файл с назначением и символами с номерами строк.
2. Читай только нужные файлы и нужные диапазоны строк по карте, не весь репозиторий.
3. После добавления, удаления или переименования файлов перегенерируй карту:
   `python3 tools/project_map.py` (проверка: `python3 tools/project_map.py --check`).

## Что где лежит
- Корень, `lib/`, `config/`, `data/`, `assets/` — Telegram-бот A-Moral Track (Node.js).
- `games/odna-zhizn/` — игра «Одна жизнь» (Godot 4.7, Android). Дизайн: `games/odna-zhizn/GDD.md`.
- `games/narisuy-geroya/` — игра «Нарисуй героя» (на паузе): модели Blender, шрифт «Каракуля».

## Инструменты окружения (облачная сессия)
- Godot 4.7.2: `/opt/godot/godot` (ссылка `godot`), шаблоны Android: `~/.local/share/godot/export_templates/4.7.2.stable/`.
- Blender как модуль Python: `pip install bpy==5.2.3` (Python 3.13); скрипты моделей: `games/*/tools/blender/`.
- Android SDK: `/opt/android-sdk` (build-tools 35, platform-tools).
- Рендер без экрана: `xvfb-run` + Vulkan lavapipe (`mesa-vulkan-drivers`).

## Правила игры-проектов
- Никаких стандартных шрифтов и стандартных кнопок/окон Godot — только собственная тема и шрифты из `assets/fonts`.
- Модели создаются скриптами Blender (воспроизводимо), не руками и не нейросетями.
- Тексты игры — по-русски, коротко и живо.
