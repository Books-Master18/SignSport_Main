let selectedImage = null;

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('handwritingImage');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files[0]) handleFiles(e.target.files[0]);
        });
    }
    setupDragAndDrop();
});

function setupDragAndDrop() {
    const dropZone = document.querySelector('.upload-label');
    if (!dropZone) return;
    // ... (код drag&drop можно оставить прежним, он работает) ...
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
    });
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files.length) handleFiles(dt.files[0]);
    });
}

function handleFiles(file) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        return alert('❌ Только JPG, PNG, WebP');
    }
    selectedImage = file;
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('imagePreview').style.display = 'block';
        document.getElementById('uploadLabel').style.display = 'none';
        document.getElementById('analyzeBtn').disabled = false;
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedImage = null;
    document.getElementById('handwritingImage').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('uploadLabel').style.display = 'block';
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('result').style.display = 'none';
}

async function runAnalysis() {
    if (!selectedImage) return alert('Загрузите фото!');
    
    const btn = document.getElementById('analyzeBtn');
    const loadingEl = document.getElementById('loading');
    const resultEl = document.getElementById('result');
    
    btn.disabled = true;
    btn.innerText = '⏳ Думаю...';
    loadingEl.style.display = 'block';
    resultEl.style.display = 'none';
    
    const formData = new FormData();
    formData.append('image', selectedImage);

    try {
        const response = await fetch('http://127.0.0.1:5000/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.top_3) {
            showResult(data);
        } else {
            alert('Ошибка: ' + (data.error || 'Не удалось получить рекомендацию'));
        }
    } catch (err) {
        console.error(err);
        alert('Сервер не отвечает. Запусти python app.py');
    } finally {
        loadingEl.style.display = 'none';
        btn.disabled = false;
        btn.innerText = '🔍 Получить рекомендацию';
    }
}

function showResult(data) {
    
    const listContainer = document.querySelector('.rec-list');
    if (!listContainer) {
        console.error("❌ ОШИБКА: Не найден элемент .rec-list");
        return;
    }
    
    // 2. Очищаем старые результаты
    listContainer.innerHTML = '';

    // 3. Создаем карточки для ТОП-3
    data.top_3.forEach((item, index) => {
        const rank = index + 1;
        
        // Создаем элемент div
        const div = document.createElement('div');
        div.className = 'rec-item'; // Этот класс есть в твоем CSS!
        
        // Вставляем текст
        div.innerHTML = `
            <strong style="font-size: 18px;">${rank}. ${item.sport}</strong> 
            <span style="float: right; font-weight: bold;">${item.confidence}%</span>
        `;
        
        // Добавляем в список
        listContainer.appendChild(div);
    });

    // 4. Показываем блок результата
    document.getElementById('result').style.display = 'block';
    
    // 5. Прокрутка к результату
    document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
}