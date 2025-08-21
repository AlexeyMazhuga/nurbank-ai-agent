# Шаг 1: Берем за основу официальный образ Python
FROM python:3.11-slim

# Шаг 2: Устанавливаем системные зависимости, включая Chrome
# Мы делаем это от имени администратора (root) внутри нашего "контейнера"
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    --no-install-recommends

# Шаг 3: Устанавливаем переменную окружения, чтобы Selenium знал, где Chrome
ENV CHROME_BIN /usr/bin/chromium
ENV CHROME_DRIVER_BIN /usr/bin/chromedriver

# Шаг 4: Создаем рабочую папку внутри контейнера
WORKDIR /app

# Шаг 5: Копируем наш "список покупок" и устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Шаг 6: Копируем весь остальной код нашего проекта в контейнер
COPY . .

# Шаг 7: Говорим Docker, какую команду запустить, когда контейнер стартует
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]