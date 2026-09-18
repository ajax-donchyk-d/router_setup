#!/usr/bin/env bash

# Переходимо в директорію, де лежить сам скрипт (корінь проєкту)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1

# Перевірка наявності .env
if [ ! -f ".env" ]; then
    echo
    echo "[WARNING] .env not found. Create it from .env.example and fill values:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    echo
fi

read -r -p "Do you wish to install project's venv and system dependencies? (Y/n): " REPLY

if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    # Перевірка чи встановлений uv
    if ! command -v uv &> /dev/null; then
        echo "[INFO] Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Додаємо uv до PATH для поточної сесії
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    echo "[INFO] Syncing environment via uv..."
    uv sync
fi