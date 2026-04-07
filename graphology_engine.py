# graphology_engine.py
import cv2
import numpy as np
import logging
from config import (
    ZONE_INTERPRETATION, FORM_TO_FUNCTION, 
    SLANT_INTERPRETATION, PRESSURE_INTERPRETATION
)

logger = logging.getLogger(__name__)

SPACING_INTERPRETATION = {
    "wide": ["независимый", "свободолюбивый", "нуждающийся_в_пространстве", "экстравертированный"],
    "medium": ["адаптивный", "социально_нормированный", "гибкий"],
    "narrow": ["склонный_к_контакту", "навязчивый", "интровертированный", "экономный"]
}

MARGIN_INTERPRETATION = {
    "large_left": ["прошлое_важно", "осторожный", "сдержанный"],
    "small_left": ["импульсивный", "будущее_важно", "активный"],
    "large_right": ["будущее_важно", "целеустремленный", "сдержанный"],
    "small_right": ["нетерпеливый", "щедрый", "импульсивный"]
}

def analyze_handwriting_goldberg(image_file):
    try:
        # === 1. ПОДГОТОВКА ИЗОБРАЖЕНИЯ ===
        image_file.seek(0)
        image_bytes = image_file.read()
        
        if not image_bytes:
            return {"error": "Файл пуст"}

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            return {"error": "Не удалось прочитать изображение."}
            
        img = np.ascontiguousarray(img)
        _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        height, width = img.shape
        
        # === 2. МАКРОСТРУКТУРА ===
        non_zero_rows = np.any(binary, axis=1)
        non_zero_cols = np.any(binary, axis=0)
        
        text_top = np.argmax(non_zero_rows)
        text_bottom = len(non_zero_rows) - np.argmax(non_zero_rows[::-1])
        text_left = np.argmax(non_zero_cols)
        text_right = len(non_zero_cols) - np.argmax(non_zero_cols[::-1])
        
        text_height = text_bottom - text_top
        text_width = text_right - text_left
        
        if text_height <= 0 or text_width <= 0:
             return {"error": "Текст не обнаружен."}

        top_margin_pct = text_top / height
        bottom_margin_pct = (height - text_bottom) / height
        left_margin_pct = text_left / width
        right_margin_pct = (width - text_right) / width
        
        organization_score = 10 if 0.05 <= (top_margin_pct + bottom_margin_pct + left_margin_pct + right_margin_pct)/4 <= 0.2 else 5

        margin_traits = []
        if left_margin_pct > 0.15: margin_traits.extend(MARGIN_INTERPRETATION["large_left"])
        elif left_margin_pct < 0.05: margin_traits.extend(MARGIN_INTERPRETATION["small_left"])
        if right_margin_pct > 0.15: margin_traits.extend(MARGIN_INTERPRETATION["large_right"])
        elif right_margin_pct < 0.05: margin_traits.extend(MARGIN_INTERPRETATION["small_right"])

        # === 3. МЕЖСТРОЧНЫЙ ИНТЕРВАЛ ===
        horizontal_projection = np.sum(binary, axis=1)
        kernel_size = 5
        smooth_proj = np.convolve(horizontal_projection, np.ones(kernel_size)/kernel_size, mode='same')

        lines_y = []
        in_line = False
        threshold = np.mean(smooth_proj) * 0.5
        
        for y in range(height):
            if smooth_proj[y] > threshold:
                if not in_line:
                    lines_y.append(y)
                    in_line = True
            else:
                in_line = False
        
        line_heights = [lines_y[i+1] - lines_y[i] for i in range(len(lines_y) - 1)] if len(lines_y) > 1 else []
        avg_line_dist = np.mean(line_heights) if line_heights else 0
        avg_char_height = text_height / max(len(lines_y), 1) 
        
        relative_spacing = avg_line_dist / avg_char_height if avg_char_height > 0 else 1
        
        if relative_spacing > 1.5: spacing_category = "wide"
        elif relative_spacing < 0.8: spacing_category = "narrow"
        else: spacing_category = "medium"

        # === 4. КОНТУРЫ ===
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {"error": "Контуры не найдены."}

        zone_scores = {"upper": 0, "middle": 0, "lower": 0}
        
        # Безопасный проход по контурам
        for i in range(len(contours)):
            cnt = contours[i]
            # Убеждаемся, что работаем с массивом точек
            if not isinstance(cnt, np.ndarray):
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 10: continue
            
            center_y = y + h / 2
            rel_y = (center_y - text_top) / text_height if text_height > 0 else 0.5
            
            if rel_y < 0.33: zone_scores["upper"] += h
            elif rel_y < 0.66: zone_scores["middle"] += h
            else: zone_scores["lower"] += h
        
        total_zone = sum(zone_scores.values())
        zone_ratios = {k: v / total_zone if total_zone > 0 else 0.33 for k, v in zone_scores.items()}
        
        # === 5. НАКЛОН ===
        slant_scores = []
        for i in range(len(contours)):
            cnt = contours[i]
            if not isinstance(cnt, np.ndarray) or len(cnt) < 10: continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 15: continue
            
            top_points = []
            bottom_points = []
            
            # Проходим по точкам контура безопасно
            for j in range(len(cnt)):
                point = cnt[j][0] # Получаем координаты [x, y]
                px, py = point[0], point[1]
                
                if py < y + h/3:
                    top_points.append(px)
                elif py > y + 2*h/3:
                    bottom_points.append(px)
                    
            if top_points and bottom_points:
                avg_top_x = np.mean(top_points)
                avg_bottom_x = np.mean(bottom_points)
                slant_scores.append((avg_top_x - avg_bottom_x) / h)
        
        avg_slant = np.mean(slant_scores) if slant_scores else 0
        slant_category = "right" if avg_slant > 0.1 else ("left" if avg_slant < -0.1 else "vertical")
        
        # === 6. НАЖИМ ===
        stroke_pixels = img[img < 200]
        avg_intensity = np.mean(stroke_pixels) if len(stroke_pixels) > 0 else 255
        pressure_score = (255 - avg_intensity) / 2.55
        pressure_category = "heavy" if pressure_score > 60 else ("light" if pressure_score < 30 else "medium")
        
        # === 7. ФОРМА ===
        form_scores = {"arcade": 0, "garland": 0, "angle": 0, "thread": 0}
        for i in range(len(contours)):
            cnt = contours[i]
            if not isinstance(cnt, np.ndarray) or len(cnt) < 8: continue
            
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            if len(approx) >= 4:
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                cnt_area = cv2.contourArea(cnt)
                solidity = cnt_area / hull_area if hull_area > 0 else 0
                
                if solidity > 0.9: form_scores["arcade"] += 1
                elif solidity < 0.7: form_scores["garland"] += 1
                elif len(approx) > 6: form_scores["thread"] += 1
                else: form_scores["angle"] += 1
        
        dominant_form = max(form_scores, key=form_scores.get) if sum(form_scores.values()) > 0 else "arcade"

        # === 8. РАЗМЕР И СКОРОСТЬ ===
        middle_zone_heights = []
        for i in range(len(contours)):
            cnt = contours[i]
            if not isinstance(cnt, np.ndarray): continue
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 10: continue
            
            center_y = y + h / 2
            rel_y = (center_y - text_top) / text_height if text_height > 0 else 0.5
            
            if 0.33 <= rel_y < 0.66:
                middle_zone_heights.append(h)
        
        avg_letter_height = np.mean(middle_zone_heights) if middle_zone_heights else 0
        relative_size = avg_letter_height / text_height if text_height > 0 else 0
        
        size_category = "large" if relative_size > 0.15 else ("small" if relative_size < 0.05 else "medium")

        speed_indicators = 0
        if dominant_form in ["thread", "arcade"]: speed_indicators += 1
        if slant_category == "right": speed_indicators += 1
        if pressure_category != "heavy": speed_indicators += 1
            
        speed_category = "fast" if speed_indicators >= 2 else ("medium" if speed_indicators == 1 else "slow")

        # === 9. СИНТЕЗ ===
        detected_traits = []
        trait_scores = {}
        
        def add_traits(trait_list, score_val):
            if not isinstance(trait_list, list):
                return # Защита от передачи не-списка
            for t in trait_list:
                detected_traits.append(t)
                trait_scores[t] = trait_scores.get(t, 0) + score_val

        # Старые признаки
        if zone_ratios["upper"] > 0.4: 
            add_traits(ZONE_INTERPRETATION["upper"]["traits_if_developed"], 8)
        if zone_ratios["middle"] > 0.4: 
            add_traits(ZONE_INTERPRETATION["middle"]["traits_if_balanced"], 10)
        if zone_ratios["lower"] > 0.4: 
            add_traits(ZONE_INTERPRETATION["lower"]["traits_if_developed"], 7)
            
        add_traits(SLANT_INTERPRETATION[slant_category]["traits"], 6)
        add_traits(PRESSURE_INTERPRETATION[pressure_category]["traits"], 5)
        add_traits(FORM_TO_FUNCTION[dominant_form]["traits"], 7)
        
        # Новые признаки: Размер и Скорость (используем глобальные словари или определенные выше)
        # Убедимся, что категории имеют правильные строковые значения
        if size_category not in ["large", "medium", "small"]:
            size_category = "medium" # Фоллбек
            
        if speed_category not in ["fast", "medium", "slow"]:
            speed_category = "medium" # Фоллбек
            
        if spacing_category not in ["wide", "medium", "narrow"]:
            spacing_category = "medium" # Фоллбек

        SIZE_INTERPRETATION_LOCAL = {
            "large": ["экстравертированный", "просторный", "демонстративный", "общительный"],
            "medium": ["адаптивный", "социально_нормированный", "гибкий"],
            "small": ["интровертированный", "скромный", "внимательный_к_деталям", "сосредоточенный"]
        }
        
        SPEED_INTERPRETATION_LOCAL = {
            "fast": ["динамичный", "реактивный", "импульсивный", "быстро_принимающий_решения"],
            "medium": ["уравновешенный", "адаптивный", "стабильный"],
            "slow": ["вдумчивый", "концентрированный", "методичный", "осторожный"]
        }

        # Теперь обращаемся безопасно
        add_traits(SIZE_INTERPRETATION_LOCAL.get(size_category, []), 6)
        add_traits(SPEED_INTERPRETATION_LOCAL.get(speed_category, []), 6)
        add_traits(SPACING_INTERPRETATION.get(spacing_category, []), 5)
        add_traits(margin_traits, 4)

        if organization_score >= 8:
            detected_traits.append("хорошая_адаптация")
            trait_scores["хорошая_адаптация"] = 9
            
        trait_scores = {k: min(100, int(v)) for k, v in trait_scores.items()}
        
        return {
            "traits": list(set(detected_traits)),
            "scores": trait_scores,
            "metrics": {
                "slant": slant_category, "pressure": pressure_category, "dominant_form": dominant_form,
                "size": size_category, "speed": speed_category, "spacing": spacing_category,
                "margins": {"left": round(left_margin_pct, 2), "right": round(right_margin_pct, 2)},
                "zone_ratios": {k: round(v, 2) for k, v in zone_ratios.items()},
                "organization_score": organization_score
            }
        }
        
    except Exception as e:
        logger.error(f"Graphology error: {e}", exc_info=True)
        return {"error": f"Ошибка анализа: {str(e)}"}