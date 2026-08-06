# Архитектура: Автономная параллельная разработка (Antigravity + Google Cloud)

Проект: 1_project_man_orchastrator_OS_
Завершённость: [███████░░░░░] 40% — plan + bugfix

> 📄 **Полный план автономной разработки:** см. `docs/AUTONOMOUS_DEV_PLAN.md`
> (готовый стек, фазы, Asana-трекер, бюджет, риски).

## Что строим глобально

Система, где идея/задача из Telegram превращается в автономную работу агентов:
агенты параллельно выполняют задачи по нескольким проектам, пока не выполнятся
критерии приёмки (тесты + PR + QA). Человек управляет через Telegram/дашборд,
не сидя в чате с каждым агентом.

## Паттерн borodutch (из статьи) → наша адаптация

| Роль в статье | Оригинал | Наша замена | Статус |
|---|---|---|---|
| Трекер задач (source of truth) | Kaneo (self-hosted) | TaskStore + Redis + фронтенд | ✅ уже есть |
| Диспетчер (роутинг задач в worktree) | Symphony | Celery + worktree_manager | ✅ уже есть |
| Кодер (исполнение) | Codex | Antigravity SDK (google.antigravity) | ✅ уже есть |
| PM-слой (Telegram) | OpenClaw | Telegram webhook + FastAPI | ✅ уже есть |
| QA (браузер/ручной) | Codex Computer Use | Antigravity SDK + Playwright | ⬜ добавить |
| Облачный рантайм | Home server | Google Cloud ($300 триал) | ⬜ добавить |

**Вывод: текущий проект — это уже 60% стека borodutch.** Не нужно строить с нуля.

## Стек

### Локально (Mac)
- **FastAPI** — API-шлюз + Telegram webhook (уже есть)
- **Celery + Redis** — очередь задач, параллельные воркеры (уже есть)
- **TaskStore** — состояние задач (уже есть)
- **worktree_manager** — изолированные git worktrees (уже есть)
- **Antigravity SDK** — агент-исполнитель (уже есть, нужен фикс)

### Облако (Google Cloud, $300 триал)
- **Gemini Enterprise Agent Platform (Vertex AI)** — рантайм агентов
- **Antigravity SDK с `vertex=True`** — агенты работают в облаке, не на Mac
- **Gemini 3.5 Flash** — дефолтная модель (дёшево: $0.50/M input, $3.00/M output)
- **Gemini 3.1 Flash-Lite** — для простых задач ($0.25/$1.50)
- **Gemini 3.1 Pro** — для сложных задач ($2/$12)

### Подписки Antigravity
- **Free** — базовый доступ (индивид)
- **AI Pro** — текущая подписка пользователя
- **AI Ultra $100** — 5x лимиты
- **AI Ultra $200** — 20x лимиты

## Целевой цикл (loop)

```
1. Идея/задача → Telegram (#task #web "сделать X")
2. FastAPI парсит → TaskStore (status: queued)
3. Celery воркер подхватывает → worktree (изолированная папка)
4. Antigravity SDK (vertex=True) исполняет:
   - пишет код
   - запускает тесты
   - git commit + push
   - открывает Draft PR
5. Статус → in_progress → review
6. QA-агент (Antigravity + browser) проверяет реальный UI
7. Если ок → merge + deploy → done
   Если нет → rework → возврат в очередь
8. Уведомление в Telegram: "Задача X: PR #123, тесты прошли"
```

## Параллельность

- **Celery воркеры**: `celery -A tasks worker --concurrency=4` — 4 задачи параллельно
- **Worktrees**: каждая задача в своей папке `~/.worktrees/task-<id>`
- **Проекты**: каждый проект = свой репозиторий + профиль (web, mobile, marketing)

## Статусы задач (state machine)

```
queued → in_progress → review → done
                    ↘ rework → in_progress
                    ↘ failed
```

- `queued` — ждёт воркера
- `in_progress` — агент работает
- `review` — PR открыт, ждёт QA
- `rework` — QA не прошёл, вернуть агенту
- `done` — терминальный
- `failed` — ошибка

## Что нужно сделать (по шагам)

### ✅ Фаза 0: Фикс и запуск (сделано)
1. ✅ Починен баг в `agent.py`: `api_key=api_key` → чтение из env + `vertex=True`
2. ✅ Добавлены статусы `review`/`rework` в `TaskStore`
3. ✅ Исправлена маршрутизация Asana в `notifier.py`
4. ✅ Все 35 тестов проходят
5. ⬜ Настроить Google Cloud: проект, billing, ADC
6. ⬜ Запустить Celery worker + FastAPI + Redis
7. ⬜ Проверить: задача → код → PR

### Фаза 2: Параллельность и трекинг (2-3 дня)
6. Добавить статусы `review`, `rework` в TaskStore
7. Добавить QA-агента (Antigravity SDK + browser)
8. Улучшить фронтенд-дашборд (канбан)
9. Добавить уведомления в Telegram по каждому статусу

### Фаза 3: Мульти-проект (3-5 дней)
10. Реестр проектов (repo_url, repo_ref, slug) — как в Symphony
11. Роутинг задач по проектам
12. Параллельные воркеры на несколько проектов
13. Автоматический merge + deploy

## Репозитории для изучения

- `backmeupplz/symphony` — диспетчер задач (оригинал)
- `openclaw/openclaw` — PM-слой через Telegram
- `Enderfga/claw-orchestrator` — обёртка для Antigravity CLI (мульти-агент)
- `andyrewlee/awesome-agent-orchestrators` — список оркестраторов
- `google-antigravity/antigravity-sdk-python` — официальный SDK

## Бюджет

| Ресурс | Стоимость |
|---|---|
| Google Cloud триал | $300 (90 дней) |
| Antigravity AI Pro | уже есть |
| Antigravity AI Ultra | $100-200/мес (опционально) |
| Gemini 3.5 Flash | $0.30/M input, $3.00/M output |
| Gemini 3.1 Flash-Lite | $0.25/M input, $1.50/M output |

**Стратегия:** $300 триал на Gemini API через Vertex. Antigravity Free/Pro для
локальных задач. AI Ultra — только если упрёмся в лимиты.

## Риски

- $300 триал быстро уходит при активной разработке (4 метра биллинга)
- Antigravity SDK ещё молодой (v0.1.7) — API может меняться
- Браузерный QA требует Playwright/Computer Use — отдельная настройка
- Параллельные агенты в одном репо могут конфликтовать — нужны worktrees (уже есть)