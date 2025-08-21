#!/usr/bin/env bash
# exit on error
set -o errexit

# Устанавливаем зависимости для Chrome и сам Chrome
apt-get update
apt-get install -y chromium-browser chromium-chromedriver

# Устанавливаем наши Python-библиотеки
pip install -r requirements.txt