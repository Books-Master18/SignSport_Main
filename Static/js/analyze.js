// SignSport — Клиентский код с загрузкой изображения и анализом через нейросеть

document.addEventListener('DOMContentLoaded', function () {
    // Работаем только на странице анализа
    if (!window.location.pathname.startsWith('/analyze')) return;

    const modal = document.getElementById('warningModal');
    const fileInput = document.getElementById('handwritingImage'); // 🔥 Было: reportInput
    const analyzeBtn = document.querySelector('.analyze-button');
    const declineBtn = document.getElementById('declineBtn');
    const acceptBtn = document.getElementById('acceptBtn');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');

    if (!modal) return;

    // Блокируем интерфейс до подтверждения
    if (fileInput) fileInput.disabled = true;
    if (analyzeBtn) analyzeBtn.disabled = true;
    modal.style.display = 'flex';

    // Подтверждение
    acceptBtn?.addEventListener('click', () => {
        modal.style.display = 'none';
        if (fileInput) fileInput.disabled = false;
        if (analyzeBtn) analyzeBtn.disabled = false;
    });

    // Отказ
    declineBtn?.addEventListener('click', () => {
        window.location.href = '/goodbye';
    });

    // 🔥 Превью изображения при выборе файла
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    previewImg.src = event.target.result;
                    imagePreview.style.display = 'block';
                    if (analyzeBtn) analyzeBtn.disabled = false;
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

// 🔥 Функция очистки выбранного изображения
function clearImage() {
    const fileInput = document.getElementById('handwritingImage');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const analyzeBtn = document.querySelector('.analyze-button');
    
    if (fileInput) fileInput.value = '';
    imagePreview.style.display = 'none';
    previewImg.src = '';
    if (analyzeBtn) analyzeBtn.disabled = true;
}

// 🔥 Основная функция анализа — ТЕПЕРЬ РАБОТАЕТ С ИЗОБРАЖЕНИЕМ
async function runAnalysis() {
    const fileInput = document.getElementById("handwritingImage"); // 🔥 Было: reportInput
    const file = fileInput?.files?.[0];
    
    const btn = document.querySelector(".analyze-button");
    const resultDiv = document.getElementById("result");

    // 🔥 Проверка файла вместо текста
    if (!file) {
        alert("Пожалуйста, загрузите фото с почерком");
        return;
    }

    // Проверка размера файла (опционально, но полезно)
    if (file.size > 10 * 1024 * 1024) { // 10 MB limit
        alert("Файл слишком большой. Пожалуйста, выберите изображение до 10 МБ");
        return;
    }

    const originalBtnText = btn?.textContent || "Анализировать";
    if (btn) {
        btn.disabled = true;
        btn.textContent = "🔄 Анализирую почерк...";
    }

    resultDiv.style.display = "none";
    resultDiv.innerHTML = "";
    resultDiv.style.opacity = "0";

    try {
        // 🔥 Формируем FormData для отправки файла
        const formData = new FormData();
        formData.append("image", file); // Имя "image" должно совпадать с backend!

        const response = await fetch("/api/analyze", { // 🔥 Тот же endpoint, но теперь с файлом
            method: "POST",
            // 🔥 Content-Type НЕ указываем — браузер сам поставит multipart/form-data с boundary
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Ошибка сервера");
        }

        let resultHTML = `
            <div class="result-header">
                <span class="checkmark">✅</span>
                <strong>Рекомендация готова!</strong>
            </div>
            <div class="result-container">
                <h3>🎯 Основная рекомендация:</h3>
                <div class="main-recommendation">
                    <div class="sport-name">${data.sport}</div>
                    <div class="confidence">Уверенность: ${data.confidence}%</div>
                    <div class="reason">${data.reason || ""}</div>
                </div>
        `;

        // Альтернативные варианты (оставляем как было)
        if (data.additional_recommendations && data.additional_recommendations.length > 0) {
            resultHTML += `
                <div class="alternative-recommendations">
                    <h4>🔄 Альтернативные варианты:</h4>
                    <div class="alternatives-list">
            `;
            data.additional_recommendations.forEach((rec, index) => {
                resultHTML += `
                    <div class="alternative-item">
                        <span class="alt-sport">${index + 1}. ${rec.sport}</span>
                        <span class="alt-confidence">${rec.confidence}%</span>
                    </div>
                `;
            });
            resultHTML += `
                    </div>
                </div>
            `;
        }

        resultHTML += `</div>`;
        resultDiv.innerHTML = resultHTML;
        resultDiv.style.display = "block";

        // Плавное появление
        setTimeout(() => {
            resultDiv.style.transition = "opacity 0.5s ease";
            resultDiv.style.opacity = "1";
        }, 50);

    } catch (error) {
        console.error("Ошибка запроса:", error);
        resultDiv.innerHTML = `
            <div class="result-header">
                <span style="font-size: 24px; margin-right: 10px;"></span>
                <strong>Ошибка анализа</strong>
            </div>
            <div class="error-message">
                <p style="color: #c0392b; padding: 15px; background: #f8d7da; border-radius: 5px; margin: 15px 0;">
                    ❌ ${error.message || "Не удалось подключиться к серверу"}
                </p>
            </div>
        `;
        resultDiv.style.display = "block";
        resultDiv.style.opacity = "1";
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalBtnText;
        }
    }
}