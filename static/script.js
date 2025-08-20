// ... (все константы вверху остаются без изменений)
const askButton = document.getElementById('askButton');
const questionInput = document.getElementById('questionInput');
const responseArea = document.getElementById('responseArea');
const pageSelect = document.getElementById('pageSelect');
const micButton = document.getElementById('micButton');


// ===============================================================
// --- ОБНОВЛЕННЫЙ БЛОК: Улучшенная функция синтеза речи ---
// ===============================================================

// Глобальная переменная для хранения голосов, чтобы не искать их каждый раз
let voices = [];

// Функция для получения и сохранения списка голосов
const populateVoiceList = () => {
    voices = window.speechSynthesis.getVoices();
    // Выведем в консоль все доступные голоса, чтобы вы могли посмотреть
    console.log("Доступные голоса:", voices);
};

// Запускаем функцию, когда голоса загрузятся
populateVoiceList();
if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = populateVoiceList;
}

const speak = (text) => {
    // Прекращаем любое предыдущее воспроизведение, если оно есть
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    
    // --- Логика выбора лучшего голоса ---
    // Ищем русский голос от Google, он обычно самый качественный.
    // Если его нет, ищем любой другой русский голос.
    const russianVoice = voices.find(voice => voice.name === 'Google русский') || voices.find(voice => voice.lang === 'ru-RU');
    
    if (russianVoice) {
        utterance.voice = russianVoice;
    }

    // Настройка голоса (можете поиграть с этими значениями)
    utterance.pitch = 1; // Высота голоса (от 0 до 2)
    utterance.rate = 1; // Скорость речи (от 0.1 до 10)
    
    window.speechSynthesis.speak(utterance);
};

// ===============================================================
// ... (остальной код sendQuestion и логика распознавания речи остаются БЕЗ ИЗМЕНЕНИЙ) ...
// ===============================================================

const sendQuestion = async () => {
    const question = questionInput.value;
    if (!question) {
        alert('Пожалуйста, введите ваш вопрос.');
        return;
    }
    responseArea.innerText = 'Думаю над вашим вопросом...';

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                url: pageSelect.value
            })
        });
        const data = await response.json();

        if (data.answer) {
            const answerText = data.answer;
            responseArea.innerText = answerText;
            speak(answerText);
        } else {
            const errorText = 'Произошла ошибка: ' + (data.error || 'Неизвестная ошибка');
            responseArea.innerText = errorText;
            speak(errorText);
        }
    } catch (error) {
        console.error('Ошибка при отправке запроса:', error);
        const errorText = 'Не удалось связаться с сервером. Убедитесь, что он запущен.';
        responseArea.innerText = errorText;
        speak(errorText);
    }
};

askButton.addEventListener('click', sendQuestion);

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = false;

    micButton.addEventListener('click', () => {
        // Прерываем речь ассистента, если пользователь решил задать новый вопрос
        window.speechSynthesis.cancel(); 
        recognition.start();
    });

    recognition.onstart = () => {
        micButton.classList.add('is-listening');
        micButton.innerText = '...';
    };

    recognition.onend = () => {
        micButton.classList.remove('is-listening');
        micButton.innerText = '🎤';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        questionInput.value = transcript;
        sendQuestion(); 
    };

    recognition.onerror = (event) => {
        alert('Произошла ошибка распознавания: ' + event.error);
    };

} else {
    console.log('Ваш браузер не поддерживает Web Speech API');
    micButton.style.display = 'none';
}