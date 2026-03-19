# =============================================================================
# === SignSport 2.1 — Графологический анализ по методике И. Гольдберг ===
# === Источник: «Психология почерка», Инесса Гольдберг, 2023 ===
# =============================================================================

import os, re, json, logging, io, numpy as np, cv2
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image

# === Настройка ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'Static'), template_folder=os.path.join(BASE_DIR, 'templates'))
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["30 per hour", "10 per minute"])


# =============================================================================
# === ГРАФОЛОГИЧЕСКАЯ БАЗА ЗНАНИЙ (по Гольдберг) ===
# =============================================================================

# Три зоны букв → психологические аспекты (Гольдберг, гл. «Три измерения»)
ZONE_INTERPRETATION = {
    "upper": {
        "aspect": "Супер-Эго: идеалы, амбиции, интеллектуальные интересы",
        "traits_if_developed": ["целеустремленность", "аналитичность", "стратегическое_мышление"],
        "traits_if_underdeveloped": ["прагматизм", "конкретное_мышление"]
    },
    "middle": {
        "aspect": "Эго: самоощущение, эмоциональный баланс, социальная адаптация",
        "traits_if_balanced": ["эмоционально_устойчивый", "адаптивный", "коммуникабельный"],
        "traits_if_imbalanced": ["неуверенность", "внутренний_конфликт", "социальная_тревожность"]
    },
    "lower": {
        "aspect": "Ид: витальность, инстинкты, материальные потребности",
        "traits_if_developed": ["энергичный", "решительный", "практичный"],
        "traits_if_suppressed": ["сдержанный", "рефлексивный", "осторожный"]
    }
}

# Формы букв ↔ психические функции (Юнг/Гольдберг)
FORM_TO_FUNCTION = {
    "arcade": {"function": "логика", "traits": ["рассудительный", "организованный", "рациональный"]},
    "garland": {"function": "этика", "traits": ["эмпатичный", "коммуникабельный", "гибкий"]},
    "angle": {"function": "сенсорика", "traits": ["конкретный", "настойчивый", "практичный"]},
    "thread": {"function": "интуиция", "traits": ["креативный", "вариативный", "стратегический"]}
}

# Наклон → эмоциональная ориентация (Гольдберг, табл. 15)
SLANT_INTERPRETATION = {
    "right": {"orientation": "экстраверсия", "traits": ["открытый", "общительный", "импульсивный"]},
    "vertical": {"orientation": "контроль", "traits": ["сдержанный", "рациональный", "самодисциплинированный"]},
    "left": {"orientation": "интроверсия", "traits": ["рефлексивный", "осторожный", "независимый"]}
}

# Нажим → глубинная энергия (Гольдберг, табл. 21)
PRESSURE_INTERPRETATION = {
    "heavy": {"energy": "высокая", "traits": ["решительный", "настойчивый", "амбициозный"]},
    "medium": {"energy": "умеренная", "traits": ["уравновешенный", "адаптивный", "стрессоустойчивый"]},
    "light": {"energy": "чувствительная", "traits": ["внимательный", "эмпатичный", "рефлексивный"]}
}

# База спорта ↔ черты (из вашей таблицы + графологическая логика)
SPORT_TRAITS_DB = {
    "Футбол ⚽": {
        "required_traits": [
            "общительный", "смелый", "уверенный_в_себе", "инициативный",
            "эмоционально_устойчивый", "открытый_к_командной_работе",
            "целеустремленный", "склонный_к_риску", "ответственный", "эмпатичный"
        ],
        "group_type": "team"
    },
    "Гандбол 🤾": {
        "required_traits": [
            "общительный", "умеет_работать_в_команде", "энергичный", "решительный",
            "эмоционально_устойчив", "устойчивый_к_стрессу", "целеустремлённый",
            "трудолюбивый", "стойкий", "неконфликтный", "сдержанный"
        ],
        "group_type": "team"
    },
    "Водное поло 🤽": {
        "required_traits": [
            "общительный", "стрессоустойчивый", "реалистично_оценивает_свои_силы",
            "настойчивый", "упорный", "дисциплинированный", "целеустремленный",
            "внимательный", "сообразительный"
        ],
        "group_type": "team"
    },
    "Волейбол 🏐": {
        "required_traits": [
            "коммуникабельный", "активный", "уравновешенный", "стрессоустойчивый",
            "инициативный", "оптимистичный", "дисциплинированный", "командный",
            "адаптивный", "упорный", "умеет_управлять_эмоциями", "трудолюбивый"
        ],
        "group_type": "team"
    },
    "Плавание 🏊": {
        "required_traits": [
            "предпочитает_индивидуальную_работу", "эмоционально_уравновешенный",
            "спокойный", "высокий_самоконтроль", "дисциплинированный",
            "терпеливый", "увлеченный", "целеустремленный"
        ],
        "group_type": "individual"
    },
    "Фигурное катание ⛸️": {
        "required_traits": [
            "умеет_фокусироваться", "эмоционально_устойчив", "внимательный",
            "сдержанный", "стойкий", "дисциплинированный", "трудолюбивый",
            "комфортно_чувствует_себя_на_публике", "предпочитает_стабильность",
            "организованный", "предпочитает_планирование", "не_любит_импровизировать",
            "внешне_сдержан"
        ],
        "group_type": "individual"
    },
    "Тяжёлая атлетика 🏋️": {
        "required_traits": [
            "эмоционально_устойчивый", "добросовестный", "уравновешенный",
            "самодисциплинированный", "целеустремленный", "амбициозный",
            "сконцентрированный", "упорный", "решительный", "терпелив", "методичен"
        ],
        "group_type": "individual"
    },
    "Фехтование 🤺": {
        "required_traits": [
            "креативный", "склонен_экспериментировать", "гибкий_в_принятии_решений",
            "ответственный", "обладает_высоким_самоконтролем", "настойчивый",
            "артистичный", "внимательный", "эмоционально_устойчив", "аналитичный",
            "стратегически_мыслящий", "смелый", "авантюрный", "инициативен", "стрессоустойчив"
        ],
        "group_type": "individual"
    },
    "Шахматы ♟️": {
        "required_traits": [
            "спокойный", "аналитичный", "стратегически_мыслящий", "усидчивый",
            "эмоционально_устойчивый", "сосредоточенный", "организованный",
            "терпеливый", "рациональный", "рассудительный", "осторожный",
            "сосредоточен_на_внутреннем_процессе"
        ],
        "group_type": "individual"
    },
    "Хоккей 🏒": {
        "required_traits": [
            "эмоционально_устойчивый", "сосредоточенный", "внимательный",
            "проницательный", "решительный", "смелый", "настойчивый",
            "инициативный", "обладает_высокой_выдержкой", "командный"
        ],
        "group_type": "team"
    },
    "Теннис 🎾": {
        "required_traits": [
            "коммуникабельный", "эмоционально_устойчивый", "рассудительный",
            "упорный", "умеет_владеть_собой", "целеустремлённый", "решительный",
            "ответственный", "рациональный", "организованный"
        ],
        "group_type": "individual_or_pair"
    },
    "Конный спорт 🐎": {
        "required_traits": [
            "самостоятельный", "уравновешенный", "решительный", "рассудительный",
            "независимый", "стрессоустойчивый", "обладающий_самоконтролем",
            "способен_к_глубокому_партнерскому_взаимодействию_с_животным",
            "ответственный", "открытый"
        ],
        "group_type": "individual_with_animal"
    }
}

# =============================================================================
# === ГРАФОЛОГИЧЕСКИЙ АНАЛИЗ (по методике Гольдберг) ===
# =============================================================================

def analyze_handwriting_goldberg(image_file):
    """
    Анализирует почерк по принципам Инессы Гольдберг:
    - Макро-/микроструктура
    - Три зоны букв
    - Форма, наклон, нажим, скорость
    - Синтезная интерпретация
    
    Возвращает: traits, scores, metrics, confidence
    """
    try:
        # Подготовка изображения
        image_file.seek(0)
        image_bytes = image_file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"error": "Не удалось прочитать изображение"}
        
        # Бинаризация для контуров
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # === 1. МАКРОСТРУКТУРА (организация пространства) ===
        # Поля, расстояния между строками, равномерность
        height, width = img.shape
        non_zero_rows = np.any(binary, axis=1)
        text_top = np.argmax(non_zero_rows)
        text_bottom = len(non_zero_rows) - np.argmax(non_zero_rows[::-1])
        text_height = text_bottom - text_top
        
        # Оценка полей (Гольдберг: верхние поля = ценностный уровень)
        top_margin = text_top / height
        bottom_margin = (height - text_bottom) / height
        organization_score = 0
        if 0.1 <= top_margin <= 0.3 and 0.1 <= bottom_margin <= 0.3:
            organization_score = 10  # Хорошая организация
        elif top_margin < 0.05 or bottom_margin < 0.05:
            organization_score = 3   # Экспансия / тревожность
        else:
            organization_score = 6   # Умеренно
        
        # === 2. МИКРОСТРУКТУРА (качество штриха) ===
        # Контраст, перепады нажима, гладкость линий
        edges = cv2.Canny(img, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # Оценка «гладкости» (CNT-RLS: contraction vs release)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        smoothness_scores = []
        for cnt in contours:
            if len(cnt) >= 5:
                # Аппроксимация полигоном: чем больше точек — тем менее гладкий контур
                epsilon = 0.01 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                smoothness_scores.append(len(approx) / len(cnt))
        avg_smoothness = np.mean(smoothness_scores) if smoothness_scores else 0.5
        # Высокая гладкость = RLS (расслабление), низкая = CNT (напряжение)
        cnt_rls_score = min(10, max(0, int((1 - avg_smoothness) * 20)))
        
        # === 3. ТРИ ЗОНЫ БУКВ ===
        # Выделяем контуры и классифицируем по вертикальному положению
        zone_scores = {"upper": 0, "middle": 0, "lower": 0}
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 10: continue  # Фильтр шума
            center_y = y + h / 2
            # Нормализуем относительно текста
            rel_y = (center_y - text_top) / text_height if text_height > 0 else 0.5
            if rel_y < 0.33:
                zone_scores["upper"] += h
            elif rel_y < 0.66:
                zone_scores["middle"] += h
            else:
                zone_scores["lower"] += h
        
        total_zone = sum(zone_scores.values())
        zone_ratios = {k: v / total_zone if total_zone > 0 else 0.33 for k, v in zone_scores.items()}
        
        # === 4. НАКЛОН (по градиентам) ===
        # Простая эвристика: смещение верхних точек относительно нижних
        slant_scores = []
        for cnt in contours:
            if len(cnt) < 10: continue
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 15: continue
            # Берём верхнюю и нижнюю треть контура
            top_points = [p[0] for p in cnt if p[0][1] < y + h/3]
            bottom_points = [p[0] for p in cnt if p[0][1] > y + 2*h/3]
            if top_points and bottom_points:
                avg_top_x = np.mean([p[0] for p in top_points])
                avg_bottom_x = np.mean([p[0] for p in bottom_points])
                slant = avg_top_x - avg_bottom_x
                slant_scores.append(slant / h)  # Нормализуем по высоте
        avg_slant = np.mean(slant_scores) if slant_scores else 0
        # Интерпретация: >0.1 = right, <-0.1 = left, else vertical
        slant_category = "right" if avg_slant > 0.1 else ("left" if avg_slant < -0.1 else "vertical")
        
        # === 5. НАЖИМ (по интенсивности пикселей) ===
        # Чем темнее штрих — тем сильнее нажим (упрощённо)
        stroke_pixels = img[img < 200]  # Тёмные пиксели
        avg_intensity = np.mean(stroke_pixels) if len(stroke_pixels) > 0 else 255
        pressure_score = (255 - avg_intensity) / 2.55  # 0-100
        pressure_category = "heavy" if pressure_score > 60 else ("light" if pressure_score < 30 else "medium")
        
        # === 6. ФОРМА БУКВ (аркады/гирлянды/углы/нити) ===
        # Эвристика: соотношение выпуклостей/вогнутостей в контурах
        form_scores = {"arcade": 0, "garland": 0, "angle": 0, "thread": 0}
        for cnt in contours:
            if len(cnt) < 8: continue
            # Аппроксимируем и считаем углы
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) >= 4:
                # Больше углов → angle, плавные кривые → garland/arcade
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                cnt_area = cv2.contourArea(cnt)
                solidity = cnt_area / hull_area if hull_area > 0 else 0
                if solidity > 0.9:
                    form_scores["arcade"] += 1  # Выпуклые
                elif solidity < 0.7:
                    form_scores["garland"] += 1  # Вогнутые
                elif len(approx) > 6:
                    form_scores["thread"] += 1  # Нитеобразные
                else:
                    form_scores["angle"] += 1  # Угловатые
        dominant_form = max(form_scores, key=form_scores.get) if sum(form_scores.values()) > 0 else "arcade"
        
        # === 7. СКОРОСТЬ (по признакам Гольдберг, табл. 4) ===
        # Упрощённая оценка: прогрессивность линий + упрощение форм
        speed_indicators = 0
        if avg_smoothness < 0.6: speed_indicators += 1  # Гладкие линии
        if zone_ratios["middle"] > 0.4: speed_indicators += 1  # Доминанта средней зоны
        if pressure_category != "heavy": speed_indicators += 1  # Не чрезмерный нажим
        if organization_score >= 6: speed_indicators += 1  # Хорошая организация
        speed_category = "fast" if speed_indicators >= 3 else ("slow" if speed_indicators <= 1 else "medium")
        
        # === 8. СИНТЕЗ: извлечение черт ===
        detected_traits = []
        trait_scores = {}
        
        # Зоны → черты
        if zone_ratios["upper"] > 0.4:
            for t in ZONE_INTERPRETATION["upper"]["traits_if_developed"]:
                detected_traits.append(t)
                trait_scores[t] = trait_scores.get(t, 0) + 8
        if zone_ratios["middle"] > 0.4:
            for t in ZONE_INTERPRETATION["middle"]["traits_if_balanced"]:
                detected_traits.append(t)
                trait_scores[t] = trait_scores.get(t, 0) + 10
        if zone_ratios["lower"] > 0.4:
            for t in ZONE_INTERPRETATION["lower"]["traits_if_developed"]:
                detected_traits.append(t)
                trait_scores[t] = trait_scores.get(t, 0) + 7
        
        # Наклон → черты
        for t in SLANT_INTERPRETATION[slant_category]["traits"]:
            detected_traits.append(t)
            trait_scores[t] = trait_scores.get(t, 0) + 6
        
        # Нажим → черты
        for t in PRESSURE_INTERPRETATION[pressure_category]["traits"]:
            detected_traits.append(t)
            trait_scores[t] = trait_scores.get(t, 0) + 5
        
        # Форма → черты (Юнг/Гольдберг)
        for t in FORM_TO_FUNCTION[dominant_form]["traits"]:
            detected_traits.append(t)
            trait_scores[t] = trait_scores.get(t, 0) + 7
        
        # Организация → адаптивность
        if organization_score >= 8:
            detected_traits.append("хорошая_адаптация")
            trait_scores["хорошая_адаптация"] = 9
        
        # Нормализация баллов
        trait_scores = {k: min(100, int(v)) for k, v in trait_scores.items()}
        
        logger.info(f"Goldberg analysis: slant={slant_category}, pressure={pressure_category}, form={dominant_form}, speed={speed_category}")
        
        return {
            "traits": list(set(detected_traits)),
            "scores": trait_scores,
            "metrics": {
                "slant": slant_category,
                "pressure": pressure_category,
                "dominant_form": dominant_form,
                "speed": speed_category,
                "zone_ratios": {k: round(v, 2) for k, v in zone_ratios.items()},
                "organization_score": organization_score,
                "cnt_rls": cnt_rls_score
            },
            "methodology_note": "Анализ выполнен по принципам И. Гольдберг (упрощённая реализация). Требуется синтезная интерпретация специалистом."
        }
        
    except Exception as e:
        logger.error(f"Goldberg analysis error: {e}", exc_info=True)
        return {"error": f"Ошибка анализа: {str(e)}"}

# =============================================================================
# === РЕКОМЕНДАЦИЯ СПОРТА (синтез черт → спорт) ===
# =============================================================================

def calculate_sport_recommendations(graphology_result):
    """Сопоставляет графологические черты с видами спорта по базе данных."""
    
    if "error" in graphology_result:
        return graphology_result
    
    trait_scores = graphology_result.get("scores", {})
    detected_traits = set(graphology_result.get("traits", []))
    metrics = graphology_result.get("metrics", {})
    
    sport_scores = {}
    
    for sport, data in SPORT_TRAITS_DB.items():
        score = 0
        matched = []
        
        # Сопоставление черт
        for trait in data["required_traits"]:
            if trait in trait_scores:
                score += trait_scores[trait] * 0.9
                matched.append(trait)
            elif trait in detected_traits:
                score += 12
                matched.append(trait)
        
        # Бонусы за метрики (графологическая логика)
        if metrics.get("slant") == "vertical" and "аналитичный" in data["required_traits"]:
            score += 8
        if metrics.get("pressure") == "heavy" and "решительный" in data["required_traits"]:
            score += 7
        if metrics.get("dominant_form") == "arcade" and "рациональный" in data["required_traits"]:
            score += 6
        if metrics.get("organization_score", 0) >= 8 and "хорошая_адаптация" in detected_traits:
            score += 5
        
        if score > 0:
            sport_scores[sport] = {
                "score": score,
                "matched_traits": matched,
                "group_type": data["group_type"]
            }
    
    # Если нет совпадений — универсальная рекомендация
    if not sport_scores:
        return {
            "sport": "Рекомендуется консультация спортивного психолога",
            "confidence": 40,
            "alternative_sports": [],
        }
    
    # Сортировка и выбор топ-5 (увеличили с 3 до 5)
    sorted_sports = sorted(sport_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    main = sorted_sports[0]
    alternatives = sorted_sports[1:3]  # Показываем до 5 альтернатив
    
    # Формируем расширенные альтернативные рекомендации
    enhanced_alternatives = []
    for i, alt in enumerate(alternatives, 1):
        alt_data = alt[1]
        enhanced_alternatives.append({
            "rank": i,  # Позиция в рейтинге
            "sport": alt[0],
            "confidence": min(95, int(alt_data["score"])),
            "matched_traits_count": len(alt_data["matched_traits"]),
            "top_matched_traits": alt_data["matched_traits"][:4],  # Top 4 совпавшие черты
            "group_type": alt_data["group_type"]
        })
    
    return {
        "sport": main[0],
        "confidence": min(95, max(50, int(main[1]["score"]))),
        "matched_traits": main[1]["matched_traits"][:6],  # Top 6 черт
        "group_type": main[1]["group_type"],
        "alternative_sports": enhanced_alternatives,  # Улучшенное поле с альтернативами
        "total_alternatives": len(enhanced_alternatives),  # Количество альтернатив
        "metrics_summary": {
            "slant": metrics.get("slant"),
            "pressure": metrics.get("pressure"),
            "form": metrics.get("dominant_form"),
            "organization": metrics.get("organization_score")
        },
    }

# =============================================================================
# === ТЕКСТОВЫЙ АНАЛИЗ (резервный метод) ===
# =============================================================================

def analyze_with_text(text):
    """Анализ по текстовому описанию характера (упрощённый)."""
    if len(text) < 5:
        return {"error": "Введите больше текста."}
    
    text_lower = text.lower()
    scores = {}
    
    for sport, data in SPORT_TRAITS_DB.items():
        score = 0
        for trait in data["required_traits"]:
            if trait.replace("_", " ") in text_lower or trait in text_lower:
                score += 18
        if score > 0:
            scores[sport] = {"score": score, "group_type": data["group_type"]}
    
    if not scores:
        return {
            "sport": "Универсальный спорт (плавание, бег, йога)",
            "confidence": 50,
            "alternative_sports": [],
        }
    
    sorted_sports = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    main = sorted_sports[0]
    alternatives = sorted_sports[1:6]
    
    # Формируем альтернативные рекомендации
    enhanced_alternatives = []
    for i, alt in enumerate(alternatives, 1):
        enhanced_alternatives.append({
            "rank": i,
            "sport": alt[0],
            "confidence": min(95, alt[1]["score"])
        })
    
    return {
        "sport": main[0],
        "confidence": min(95, main[1]["score"]),
        "group_type": main[1].get("group_type", "unknown"),
        "alternative_sports": enhanced_alternatives,
        "total_alternatives": len(enhanced_alternatives),
    }

# =============================================================================
# === FLASK-РОУТЫ ===
# =============================================================================

@app.route('/')
def home():
    return render_template('SignSport-2.0.html')

@app.route('/analyze')
def analyze_page():
    return render_template('program.html')

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze_endpoint():
    """Гибридный эндпоинт: Фото → Гольдберг-анализ, Текст → правила."""
    
    # 🖼️ Анализ изображения
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
    
    # 📝 Текстовый анализ
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "Загрузите фото или введите описание характера."}), 400
    
    result = analyze_with_text(text)
    return jsonify(result)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Страница не найдена"}), 404

@app.errorhandler(429)
def rate_limit(e):
    return jsonify({"error": "Слишком много запросов"}), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({"error": "Внутренняя ошибка сервера"}), 500

# =============================================================================
# === ЗАПУСК ===
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"🚀 SignSport запускается на порту {port}, debug={debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)