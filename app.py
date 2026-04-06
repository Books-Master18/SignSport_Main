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

def calculate_sport_recommendations(graphology_result):
    if "error" in graphology_result:
        return graphology_result
    
    trait_scores = graphology_result.get("scores", {})
    detected_traits = set(graphology_result.get("traits", []))
    metrics = graphology_result.get("metrics", {})
    
    sport_results = []
    
    for sport_name, data in SPORT_TRAITS_DB.items():
        required_traits = data["required_traits"]
        total_required = len(required_traits)
        
        raw_score = 0
        matched_traits_list = []
        
        # Считаем баллы
        for trait in required_traits:
            if trait in trait_scores:
                raw_score += trait_scores[trait] 
                matched_traits_list.append(trait)
            elif trait in detected_traits:
                raw_score += 50 
                matched_traits_list.append(trait)
        
        # Бонусы за метрики
        if metrics.get("slant") == "vertical":
            if "самодисциплинированный" in required_traits or "организованный" in required_traits:
                raw_score += 20
        
        if metrics.get("pressure") == "heavy":
            if "решительный" in required_traits or "амбициозный" in required_traits:
                raw_score += 15

        # Нормализация в проценты
        max_possible_score = (total_required * 100) + 50 
        confidence = int((raw_score / max_possible_score) * 100) if max_possible_score > 0 else 0
        confidence = max(40, min(98, confidence))
        
        sport_results.append({
            "sport": sport_name,
            "confidence": confidence,
            "matched_count": len(matched_traits_list),
            "group_type": data["group_type"]
        })

    # Сортировка и выбор ТОП-3
    sorted_sports = sorted(sport_results, key=lambda x: x["confidence"], reverse=True)
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