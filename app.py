# app.py
import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import SPORT_TRAITS_DB
from graphology_engine import analyze_handwriting_goldberg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), template_folder=os.path.join(BASE_DIR, 'templates'))
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["30 per hour", "10 per minute"])

# app.py

def calculate_sport_recommendations(graphology_result):
    if "error" in graphology_result:
        return graphology_result
    
    from config import TRAITS_SYNONYMS, SPORT_TRAITS_DB
    
    trait_scores = graphology_result.get("scores", {})
    detected_traits = set(graphology_result.get("traits", []))
    metrics = graphology_result.get("metrics", {})
    
    # Вспомогательная функция: есть ли такая черта или её синоним?
    def has_trait(target_trait):
        if target_trait in detected_traits:
            return True
        synonyms = TRAITS_SYNONYMS.get(target_trait, [])
        for syn in synonyms:
            if syn in detected_traits:
                return True
        return False

    sport_results = []
    
    for sport_name, data in SPORT_TRAITS_DB.items():
        required_traits = data["required_traits"]
        total_required = len(required_traits)
        
        matched_count = 0
        raw_score = 0
        
        # Считаем количество совпадений
        for trait in required_traits:
            if has_trait(trait):
                matched_count += 1
                # Добавляем базовый балл за совпадение черты
                raw_score += trait_scores.get(trait, 50) 

        # === РАСЧЕТ ПРОЦЕНТА (Упрощенный) ===
        
        # 1. Базовый процент: доля совпавших черт (0-100%)
        base_percent = (matched_count / total_required) * 100 if total_required > 0 else 0
        
        # 2. Бонусы за метрики (добавляют до 10-15% точности)
        bonus = 0
        
        slant = metrics.get("slant")
        pressure = metrics.get("pressure")
        
        # Если спорт требует дисциплины/рациональности, а почерк вертикальный
        if slant == "vertical":
            if any(t in required_traits for t in ["самодисциплинированный", "организованный", "рациональный", "сдержанный", "спокойный"]):
                bonus += 10
                
        # Если спорт требует силы воли, а нажим сильный
        if pressure == "heavy":
            if any(t in required_traits for t in ["решительный", "амбициозный", "настойчивый", "волевой", "смелый"]):
                bonus += 10
        elif pressure == "light":
             # Легкий нажим для тактильных/тонких видов
             if any(t in required_traits for t in ["внимательный", "эмпатичный", "тактичный", "гибкий", "рефлексивный"]):
                 bonus += 5

        # Итоговый процент
        final_confidence = int(base_percent + bonus)
        
        # Ограничиваем диапазон от 30% до 99%
        final_confidence = max(30, min(99, final_confidence))
        
        sport_results.append({
            "sport": sport_name,
            "confidence": final_confidence,
            "matched_count": matched_count,
            "total_required": total_required,
            "group_type": data["group_type"]
        })

    # Сортировка: сначала по уверенности, потом по количеству совпадений
    sorted_sports = sorted(sport_results, key=lambda x: (x["confidence"], x["matched_count"]), reverse=True)
    
    top_3 = sorted_sports[:3]
    
    return {"top_3": top_3}



@app.route('/')
def home():
    return render_template('SignSport-2.0.html')

@app.route('/analyze')
def analyze_page():
    return render_template('program.html')

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze_endpoint():
    if request.files and 'image' in request.files:
        image_file = request.files['image']
        if not image_file.filename:
            return jsonify({"error": "Файл не выбран"}), 400
        
        allowed = {'.png', '.jpg', '.jpeg', '.webp'}
        ext = os.path.splitext(image_file.filename)[1].lower()
        if ext not in allowed:
            return jsonify({"error": "Формат не поддерживается"}), 400
        
        graphology_result = analyze_handwriting_goldberg(image_file)
        if "error" in graphology_result:
            return jsonify(graphology_result), 400
        
        recommendation = calculate_sport_recommendations(graphology_result)
        return jsonify(recommendation)
    
    return jsonify({"error": "Загрузите фото почерка."}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"🚀 SignSport запускается на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)