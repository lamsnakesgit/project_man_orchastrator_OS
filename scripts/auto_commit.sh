#!/bin/bash
# Авто-коммит изменений проекта каждые 5 минут.
# Добавлено в cron: */5 * * * * /Users/higherpower/Desktop/1_Active_Projects/2\ Ai_agents/1_project_man_orchastrator_OS_/scripts/auto_commit.sh

set -e

PROJECT_DIR="/Users/higherpower/Desktop/1_Active_Projects/2 Ai_agents/1_project_man_orchastrator_OS_"
cd "$PROJECT_DIR" || exit 1

# Проверяем, есть ли изменения
if [ -z "$(git status --porcelain)" ]; then
    exit 0
fi

# Добавляем все изменения, делаем коммит с timestamp
BRANCH=$(git branch --show-current)
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")

git add -A
git commit -m "auto: checkpoint ${TIMESTAMP} [${BRANCH}]" --quiet

# Пытаемся запушить, если есть remote
if git remote -v > /dev/null 2>&1; then
    git push origin "$BRANCH" --quiet 2>/dev/null || echo "push failed, будет повтор"
fi
