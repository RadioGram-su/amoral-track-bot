# Скилы Claude Code для этого репозитория

Папка `.claude/` подхватывается Claude Code автоматически: скилы (`skills/`), агенты (`agents/`) и
команды (`commands/`) становятся доступны в любой сессии, открытой на этом репозитории.
Пиши задачу обычными словами, нужный скил включится сам. Команды вызываются через `/имя`.

## 🎬 Мультики, Shorts и YouTube

| Скил | Что делает | Источник |
|------|------------|----------|
| `cartoon-shorts-studio` | Конвейер оригинальных 2D/3D мультиков для Shorts с телефона: персонаж, стиль, раскадровка, промпты, монтаж, упаковка | написан для этого репо |
| `youtube` | Рост канала: хуки, сценарии с удержанием, Shorts, SEO, обложки, аналитика, монетизация (`/youtube shorts`, `/youtube hook` …) | [AgriciDaniel/claude-youtube](https://github.com/AgriciDaniel/claude-youtube), MIT |
| `kling-ai` | Промпты для Kling: image-to-video, раскадровки, консистентность персонажа | [maciejdzierzek/kling-ai-prompt-generator](https://github.com/maciejdzierzek/kling-ai-prompt-generator), MIT |
| `video-thumbnail` | 4 варианта обложки 16:9 или 9:16 (нужен `GEMINI_API_KEY`) | [aabrole/claude-video-thumbnail-skill](https://github.com/aabrole/claude-video-thumbnail-skill), MIT |
| `remotion-*` (13 шт.) | Анимация кодом и рендер MP4 (2D, 3D через `@remotion/three`, субтитры) | [remotion-dev/skills](https://github.com/remotion-dev/skills), официальные |

## 💰 Заработок, продажи, маркетинг

`lead-finder`, `proposal-builder`, `outreach-composer`, `grow-pipeline`, `speed-to-lead`, `invoice-chase`,
`content-strategy`, `social-content-engine`, `seo-ai-visibility`, `ad-manager`, `growth-pulse`, `marketing-monday`,
`campaign-plan`, `content-creation`, `draft-content`, `email-sequence`, `brand-review`, `mkt-competitive-brief`,
`mkt-seo-audit`, `draft-outreach`, `handle-objection`, `competitive-intelligence`.

## 📊 Продукт

`product-brainstorming`, `pm-competitive-brief`, `metrics-review`, `write-spec`, `roadmap-update`, `synthesize-research`.

## 🛠 Разработка

Скилы: `architecture`, `system-design`, `eng-code-review`, `debug`, `testing-strategy`, `tech-debt`,
`deploy-checklist`, `documentation`, `frontend-design`.
Команды: `/feature-dev`, `/review-pr`, `/pr-review-multi`.
Агенты: `code-explorer`, `code-architect`, `code-reviewer`, `pr-code-reviewer`, `code-simplifier`,
`comment-analyzer`, `pr-test-analyzer`, `silent-failure-hunter`, `type-design-analyzer`.

Источник: [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) и
[anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official), Apache-2.0
(см. `LICENSE-anthropic-plugins.txt`). Скилы, совпадавшие по имени со встроенными, переименованы.
