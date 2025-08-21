# Шаг 1: Берем за основу официальный образ Python
FROM python:3.11-slim

# Шаг 2: Устанавливаем ТОЛЬКО сам браузер
RUN apt-get update && apt-get install -y \
    chromium \
    --no-install-recommends

# Шаг 3: Создаем рабочую папку
WORKDIR /app

# Шаг 4: Копируем наш "список покупок" и устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Шаг 5: Копируем весь остальной код
COPY . .

# Шаг 6: Говорим Docker, какую команду запустить
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]