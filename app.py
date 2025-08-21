# ===============================================================
# Импорты
# ===============================================================
import os
import io
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from urllib.parse import urljoin
import time

# --- ИЗМЕНЕНИЯ В ИМПОРТАХ SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# УБИРАЕМ webdriver_manager

import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS

# ===============================================================
# Настройка (без изменений)
# ===============================================================
load_dotenv()
app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Модель Gemini успешно настроена.")
except Exception as e:
    print(f"Ошибка при настройке Gemini: {e}")
    model = None

# ===============================================================
# ФИНАЛЬНЫЙ "ОХОТНИК" (Версия 4.0)
# ===============================================================
def fetch_page_content_and_pdfs(url):
    print(f"Начинаю обработку URL: {url}")
    full_context = ""
    KEY_WORDS_IN_LINK = ['тариф', 'услови', 'договор', 'правил', 'rates', 'tariff', 'agreement', 'condition']
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # ВАЖНО: Указываем Selenium, где найти бинарный файл браузера в Docker
    chrome_options.binary_location = "/usr/bin/chromium"
    
    driver = None
    try:
        # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Упрощенный запуск ---
        # Selenium теперь сам найдет или скачает нужный драйвер
        driver = webdriver.Chrome(options=chrome_options)
        
        # --- Остальная логика без изменений ---
        driver.get(url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        for s in soup(["script", "style"]): s.decompose()
        page_text = soup.get_text(separator='\n', strip=True)
        full_context += f"--- ТЕКСТ С ОСНОВНОЙ СТРАНИЦЫ ({url}) ---\n{page_text}\n\n"
        print("Текст с основной страницы успешно извлечен.")

        useful_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            link_text = link.get_text().strip().lower()
            is_useful = False
            if href:
                if href.lower().endswith('.pdf'): is_useful = True
                else:
                    if any(keyword in href.lower() for keyword in KEY_WORDS_IN_LINK): is_useful = True
                    if any(keyword in link_text for keyword in KEY_WORDS_IN_LINK): is_useful = True
            if is_useful:
                full_url = urljoin(url, href)
                useful_links.append(full_url)
        
        useful_links = [link for link in set(useful_links) if link != url]
        print(f"Найдено полезных ссылок для анализа: {len(useful_links)}")
        for link in useful_links: print(f" - {link}")

        for i, link_url in enumerate(useful_links):
            try:
                if link_url.lower().endswith('.pdf'):
                    # ... (код обработки PDF без изменений)
                    pdf_response = requests.get(link_url, headers={'User-Agent': 'Mozilla/5.0'})
                    pdf_response.raise_for_status()
                    pdf_file = io.BytesIO(pdf_response.content)
                    reader = PdfReader(pdf_file)
                    doc_text = ""
                    for page in reader.pages: doc_text += page.extract_text() or ""
                    full_context += f"--- ТЕКСТ ИЗ PDF-ДОКУМЕНТА ({link_url}) ---\n{doc_text}\n\n"
                else:
                    # ... (код обработки HTML без изменений)
                    driver.get(link_url)
                    time.sleep(3)
                    page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    for s in page_soup(["script", "style"]): s.decompose()
                    page_content_text = page_soup.get_text(separator='\n', strip=True)
                    full_context += f"--- ТЕКСТ СО СВЯЗАННОЙ СТРАНИЦЫ ({link_url}) ---\n{page_content_text}\n\n"
            except Exception as e:
                print(f"Не удалось обработать ссылку {link_url}: {e}")
    
    except Exception as e:
        print(f"Произошла общая ошибка в fetch_page_content_and_pdfs: {e}")
    finally:
        if driver:
            driver.quit()

    return full_context

# ===============================================================
# API и запуск (без изменений)
# ===============================================================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/ask", methods=['POST'])
def ask_agent():
    # ... (эта функция остается абсолютно такой же)
    if not model: return jsonify({"error": "Модель ИИ не инициализирована"}), 500
    request_data = request.get_json()
    if not request_data or 'question' not in request_data or 'url' not in request_data:
        return jsonify({"error": "В запросе отсутствуют поля 'question' или 'url'"}), 400
    user_question = request_data['question']
    nurbank_url = request_data['url']
    print("Запускаю сбор информации...")
    context = fetch_page_content_and_pdfs(nurbank_url)
    print("Сбор информации завершен.")
    prompt = f"""
    Ты — полезный ассистент сайта Nurbank.
    Твоя задача — ответить на вопрос пользователя, основываясь ИСКЛЮЧИТЕЛЬНО на предоставленном ниже контексте.
    ...
    --- НАЧАЛО КОНТЕКСТА ---
    {context}
    --- КОНЕЦ КОНТЕКСТА ---
    Вопрос пользователя: "{user_question}"
    Твой ответ:
    """
    try:
        response = model.generate_content(prompt)
        return jsonify({"answer": response.text})
    except Exception as e:
        print(f"Ошибка при вызове Gemini API: {e}")
        return jsonify({"error": "Произошла ошибка при обработке вашего запроса"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)