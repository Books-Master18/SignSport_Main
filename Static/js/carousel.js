//Карусель
// Когда страница полностью загрузилась — запускаем карусель
document.addEventListener('DOMContentLoaded', () => {

  // === СБОР ЭЛЕМЕНТОВ СО СТРАНИЦЫ ===
  const reviews = document.querySelectorAll('.review');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const counterEl = document.getElementById('counter'); // добавили счётчик
  let currentIndex = 0;
  const total = reviews.length;

  // Показать текущий анализ + обновить счётчик
  function updateReview() {
    reviews.forEach((review, index) => {
      review.classList.toggle('active', index === currentIndex);
    });
    
    // Обновляем счётчик: "1/4", "2/4" и т.д.
    if (counterEl) {
      counterEl.textContent = `${currentIndex + 1}/${total}`;
    }
  }

  // Переключение вперёд
  function rightScroll() {
    currentIndex = (currentIndex + 1) % total;
    updateReview();
  }

  // Переключение назад
  function leftScroll() {
    currentIndex = (currentIndex - 1 + total) % total;
    updateReview();
  }

  // Подключаем кнопки
  if (prevBtn) {
    prevBtn.addEventListener('click', leftScroll);
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', rightScroll);
  }

  // Поддержка клавиатуры
  document.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') {
      leftScroll();
    } else if (event.key === 'ArrowRight') {
      rightScroll();
    }
  });

  // Инициализация
  updateReview();
});


// Добавляем обработчик ко всем кнопкам копирования
document.querySelectorAll('.copy-code-btn').forEach(button => {
    button.addEventListener('click', function() {
        // Ищем <p> внутри родительского .example-card
        const card = this.closest('.example-card');
        const textElement = card.querySelector('p');
        if (!textElement) return;

        const text = textElement.innerText;
        navigator.clipboard.writeText(text).then(() => {
            const originalIcon = this.innerHTML;
            this.innerHTML = '✅';
            setTimeout(() => {
                this.innerHTML = originalIcon;
            }, 2000);
        });
    });
});