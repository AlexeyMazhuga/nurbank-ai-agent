# ===============================================================
# ШАГ 1: Импорт необходимых "инструментов" (библиотек)
# ===============================================================
import os
import io
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from urllib.parse import urljoin
import time

# --- НОВЫЕ ИМПОРТЫ ДЛЯ SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS

# ===============================================================
# ШАГ 2: Начальная настройка (без изменений)
# ===============================================================
load_dotenv()
app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)

# ===============================================================
# ШАГ 3: Настройка доступа к Gemini API (без изменений)
# ===============================================================
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Модель Gemini успешно настроена.")
except Exception as e:
    print(f"Ошибка при настройке Gemini: {e}")
    model = None

# ===============================================================
# ШАГ 4: САМЫЙ УМНЫЙ "ОХОТНИК" (Версия 3.0 с Selenium)
# ===============================================================
def fetch_page_content_and_pdfs(url):
    print(f"Начинаю обработку URL с помощью Selenium: {url}")
    full_context = ""
    KEY_WORDS_IN_LINK = ['тариф', 'услови', 'договор', 'правил', 'rates', 'tariff', 'agreement', 'condition']
    
    # --- Настройка Selenium для работы в "безголовом" режиме ---
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Не открывать видимое окно браузера
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Используем автоматический установщик драйвера
    service = Service(ChromeDriverManager().install())
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 1. Загружаем основную страницу через Selenium
        driver.get(url)
        print("Ожидаю 3 секунды для прогрузки JS...")
        time.sleep(3) # Даем 3 секунды на прогрузку JavaScript
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 2. Извлекаем текст
        for s in soup(["script", "style"]): s.decompose()
        page_text = soup.get_text(separator='\n', strip=True)
        full_context += f"--- ТЕКСТ С ОСНОВНОЙ СТРАНИЦЫ ({url}) ---\n{page_text}\n\n"
        print("Текст с основной страницы успешно извлечен.")

        # 3. Ищем полезные ссылки
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

        # 4. Обрабатываем каждую ссылку
        for i, link_url in enumerate(useful_links):
            try:
                print(f"Обрабатываю ссылку: {link_url}")
                if link_url.lower().endswith('.pdf'):
                    pdf_response = requests.get(link_url, headers={'User-Agent': 'Mozilla/5.0'})
                    pdf_response.raise_for_status()
                    pdf_file = io.BytesIO(pdf_response.content)
                    reader = PdfReader(pdf_file)
                    doc_text = ""
                    for page in reader.pages:
                        doc_text += page.extract_text() or ""
                    full_context += f"--- ТЕКСТ ИЗ PDF-ДОКУМЕНТА ({link_url}) ---\n{doc_text}\n\n"
                    print(f"Текст из PDF {link_url} успешно извлечен.")
                else:
                    driver.get(link_url)
                    print(f"Ожидаю 3 секунды для прогрузки JS на {link_url}...")
                    time.sleep(3)
                    page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    for s in page_soup(["script", "style"]): s.decompose()
                    page_content_text = page_soup.get_text(separator='\n', strip=True)
                    full_context += f"--- ТЕКСТ СО СВЯЗАННОЙ СТРАНИЦЫ ({link_url}) ---\n{page_content_text}\n\n"
                    print(f"Текст со страницы {link_url} успешно извлечен.")
            except Exception as e:
                print(f"Не удалось обработать ссылку {link_url}: {e}")
    
    except Exception as e:
        print(f"Произошла общая ошибка в fetch_page_content_and_pdfs: {e}")

    finally:
        if driver:
            driver.quit() # Очень важно: всегда закрывать браузер в конце

    return full_context

# ===============================================================
# ШАГ 5: Обновляем основную логику API (без изменений)
# ===============================================================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/ask", methods=['POST'])
def ask_agent():
    if not model:
        return jsonify({"error": "Модель ИИ не инициализирована"}), 500

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
    Контекст включает в себя текст с веб-страницы и текст из всех найденных на ней PDF-документов или связанных страниц с тарифами/условиями.
    Не придумывай ничего от себя. Если ответа нет в тексте, так и скажи.
    
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

# ===============================================================
# ШАГ 6: Запускаем наш сервер (без изменений)
# ===============================================================
if __name__ == "__main__":
    app.run(debug=True, port=5000)