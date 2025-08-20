# ===============================================================
# ШАГ 1: Импорт необходимых "инструментов" (библиотек)
# ===============================================================
import os
import google.generativeai as genai
# --- ИЗМЕНЕНИЕ: Добавили 'render_template' ---
from flask import Flask, request, jsonify, render_template 
from dotenv import load_dotenv
from flask_cors import CORS

# ===============================================================
# ШАГ 2: Начальная настройка
# ===============================================================

load_dotenv()

# Создаем главный объект нашего веб-приложения
app = Flask(__name__)
# ВАЖНО: Flask будет сам искать папки 'templates' и 'static' на одном уровне с app.py

app.json.ensure_ascii = False
CORS(app)

# ===============================================================
# ШАГ 3: Настройка доступа к Gemini API
# ===============================================================
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Модель Gemini успешно настроена.")
except Exception as e:
    print(f"Ошибка при настройке Gemini: {e}")
    model = None

# ===============================================================
# ШАГ 4: Маршруты (обработка URL-адресов)
# ===============================================================

# --- НОВЫЙ МАРШРУТ ДЛЯ ГЛАВНОЙ СТРАНИЦЫ ---
# Этот блок кода отвечает за то, что увидит пользователь,
# когда зайдет на адрес http://127.0.0.1:5000/
@app.route("/")
def home():
    """Отдает пользователю нашу главную HTML-страницу."""
    # Flask автоматически ищет 'index.html' в папке 'templates'
    return render_template("index.html")


# --- СТАРЫЙ МАРШРУТ ДЛЯ API (ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ) ---
# Этот блок отвечает за обработку запросов от нашего JavaScript,
# которые приходят на адрес http://127.0.0.1:5000/api/ask
@app.route("/api/ask", methods=['POST'])
def ask_agent():
    """Принимает вопрос и URL, отдает ответ от Gemini."""
    if not model:
        return jsonify({"error": "Модель ИИ не инициализирована"}), 500

    request_data = request.get_json()

    if not request_data or 'question' not in request_data or 'url' not in request_data:
        return jsonify({"error": "В запросе отсутствуют поля 'question' или 'url'"}), 400

    user_question = request_data['question']
    nurbank_url = request_data['url']
    
    prompt = f"""
    Ты — полезный ассистент сайта Nurbank.
    Твоя задача — ответить на вопрос пользователя, основываясь ИСКЛЮЧИТЕЛЬНО на информации
    с предоставленной веб-страницы. Не придумывай ничего от себя.
    
    Веб-страница для анализа: {nurbank_url}
    
    Вопрос пользователя: "{user_question}"
    
    Твой ответ:
    """

    try:
        response = model.generate_content(prompt)
        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"Ошибка при вызове Gemini API: {e}")
        return jsonify({"error": "Произошла ошибка при обработке вашего запроса"}), 500

# ===============================================================
# ШАГ 5: Запускаем наш сервер
# ===============================================================
if __name__ == "__main__":
    # Теперь эта команда запускает и API, и отдачу веб-страницы
    app.run(debug=True, port=5000)