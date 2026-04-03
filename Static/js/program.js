
        // === Глобальные переменные ===
        let selectedImage = null;
        
        // === Инициализация ===
        document.addEventListener('DOMContentLoaded', function() {
            setupDragAndDrop();
            setupFileInput();
        });
        
        // === Drag & Drop для зоны загрузки ===
        function setupDragAndDrop() {
            const dropZone = document.querySelector('.upload-label');
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => {
                    dropZone.style.borderColor = '#3a6d8c';
                    dropZone.style.background = '#f0f7fb';
                }, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => {
                    dropZone.style.borderColor = '#4682A9';
                    dropZone.style.background = '#f8fafc';
                }, false);
            });
            
            dropZone.addEventListener('drop', handleDrop, false);
        }
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length) handleFiles(files[0]);
        }
        
        // === Выбор файла через input ===
        function setupFileInput() {
            document.getElementById('handwritingImage').addEventListener('change', function(e) {
                if (this.files[0]) handleFiles(this.files[0]);
            });
        }
        
        function handleFiles(file) {
    // Валидация типа
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        alert('❌ Поддерживаются только JPG, PNG и WebP');
        return;
    }
    // Валидация размера (10 МБ)
    if (file.size > 10 * 1024 * 1024) {
        alert('❌ Файл слишком большой (макс. 10 МБ)');
        return;
    }
    
    // Предпросмотр
    selectedImage = file;
    const reader = new FileReader();
    reader.onload = function(e) {
        const previewImg = document.getElementById('previewImg');
        const imagePreview = document.getElementById('imagePreview');
        const uploadLabel = document.getElementById('uploadLabel');
        
        previewImg.src = e.target.result;
        
        // Показываем превью
        imagePreview.classList.add('show');
        
        // Скрываем зону загрузки
        if (uploadLabel) {
            uploadLabel.classList.add('hidden');
        }
        
        document.getElementById('analyzeBtn').disabled = false;
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedImage = null;
    const imagePreview = document.getElementById('imagePreview');
    const uploadLabel = document.getElementById('uploadLabel');
    const previewImg = document.getElementById('previewImg');
    
    // Очищаем
    previewImg.src = '';
    document.getElementById('handwritingImage').value = '';
    
    // Скрываем превью
    imagePreview.classList.remove('show');
    
    // Показываем зону загрузки
    if (uploadLabel) {
        uploadLabel.classList.remove('hidden');
    }
    
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('result').style.display = 'none';
}
        
        // === Выбор примера текста ===
        function selectSample(card, text) {
            // Копирование в буфер
            navigator.clipboard.writeText(text).then(() => {
                const hint = card.querySelector('.copy-hint');
                const original = hint.textContent;
                hint.textContent = '✓ Скопировано!';
                setTimeout(() => hint.textContent = original, 2000);
            });
            
            // Подсветка выбранной карточки
            document.querySelectorAll('.sample-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            
            // Подсказка
            alert('✅ Текст скопирован!\n\nПерепишите его от руки на белом листе, сфотографируйте и загрузите выше.');
        }
        
        // === Запуск анализа ===
        async function runAnalysis() {
            if (!selectedImage) {
                alert('❌ Пожалуйста, загрузите фото почерка');
                return;
            }
            
            // Показываем индикатор загрузки
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;
            
            try {
                const formData = new FormData();
                formData.append('image', selectedImage);
                
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult(data);
                } else {
                    showError(data.error || 'Ошибка анализа');
                }
                
            } catch (error) {
                console.error('Analysis error:', error);
                showError('Не удалось подключиться к серверу. Проверьте соединение.');
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('analyzeBtn').disabled = false;
            }
        }
        
        // === Отображение результата ===
       // === Отображение результата ===
            function showResult(data) {
                // Основной результат
                document.getElementById('recommendedSport').textContent = data.sport;
                document.getElementById('confidence').textContent = data.confidence;
                
                // Убираем reason
                const reasonElement = document.getElementById('reasonText');
                if (reasonElement) {
                    reasonElement.style.display = 'none';
                }
                
                // Альтернативные виды спорта — УВЕЛИЧЕННЫЕ
                const alternativesContainer = document.getElementById('additionalRecs');
                if (data.alternative_sports && data.alternative_sports.length > 0) {
                    alternativesContainer.style.display = 'block';
                    alternativesContainer.querySelector('h4').textContent = '📋 Альтернативные виды спорта:';
                    
                    const recList = alternativesContainer.querySelector('.rec-list');
                    recList.innerHTML = data.alternative_sports.map(alt => {
                        return `
                            <div class="rec-item" style="display: block; margin-bottom: 15px; padding: 20px; background: rgba(255,255,255,0.15); border-radius: 8px; font-size: 18px;">
                                <strong style="font-size: 20px;">${alt.rank}. ${alt.sport}</strong>
                                <span style="margin-left: 15px; color: #fffbde; font-weight: bold;">(${alt.confidence}%)</span>
                            </div>
                        `;
                    }).join('');
                } else {
                    alternativesContainer.style.display = 'none';
                }
                
                
            }
                    
        // === Ошибка ===
        function showError(message) {
            alert('❌ ' + message);
        }