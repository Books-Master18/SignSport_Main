# test_opencv.py
import requests

# Тест с текстом
response = requests.post(
    "http://127.0.0.1:5000/api/analyze",
    json={"text": "Я люблю командную работу и активные виды спорта"},
    headers={"Content-Type": "application/json"}
)
print("📝 Текстовый тест:", response.json())

# Тест с изображением (раскомментируй, если есть файл)
# with open('handwriting.jpg', 'rb') as f:
#     response = requests.post(
#         "http://127.0.0.1:5000/api/analyze",
#         files={"image": f}
#     )
#     print("🖼️ Анализ фото:", response.json())