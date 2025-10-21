# -- coding: utf-8 --

# -----------------------------------------------------
# خادم Flask لتقديم الـ HTML (Frontend) ونقاط نهاية الـ API (Backend)
# -----------------------------------------------------

from flask import Flask, request, jsonify, render_template # استيراد render_template
from flask_cors import CORS
import os
import random
import time 

# -----------------------------------------------------
# ثوابت وبيانات (لم يتم تغيير هذا الجزء)
# -----------------------------------------------------

APP_ID = 'soil_agent_app'
BASE_IMAGE_DIR = '' 
IMG_SIZE = (224, 224)
CLASS_NAMES = ['Alluvial_Soil','Black_Soil','Laterite_Soil','Red_Soil','Yellow_Soil']

CROP_PROPERTIES = {
    'تمر': [0.4, 0.7, 0.9, 8000],
    'عنب': [0.6, 0.5, 0.7, 15000],
    'طماطم': [0.9, 0.6, 0.8, 40000],
    'بطاطا': [0.7, 0.5, 0.6, 25000],
    'قمح_صلب': [0.5, 0.3, 0.5, 3000],
    'شعير': [0.4, 0.3, 0.4, 3500],
    'زيتون': [0.3, 0.7, 0.8, 10000],
    'بقوليات': [0.5, 0.4, 0.6, 1500],
    'بطيخ': [0.7, 0.5, 0.7, 30000]
}

BASE_COSTS_PER_HA = {
    'seed_dzd': 50000, 'water_dzd': 70000, 'fertilizer_dzd': 40000, 
    'pesticide_dzd': 20000, 'labor_dzd': 120000
}

PRICE_PER_KG_DZD = {
    'تمر': 450, 'عنب': 200, 'طماطم': 80, 'بطاطا': 60, 
    'قمح_صلب': 50, 'شعير': 40, 'زيتون': 350, 'بقوليات': 150, 'بطيخ': 70
}

WATER_NEED_M3_HA = {
    'تمر': 5000, 'عنب': 6500, 'طماطم': 9000, 'بطاطا': 7500, 
    'قمح_صلب': 4500, 'شعير': 4000, 'زيتون': 3000, 'بقوليات': 5500, 'بطيخ': 7000
}

PREF_OPTIONS_MAP = {
    "زيادة الأرباح المالية": "high_profit",
    "استهلاك ماء منخفض": "low_water",
    "تحسين كفاءة الأداء": "improve_efficiency",
    "لا شيء (معايير عامة)": "none"
}

GLOBAL_HISTORICAL_ANALYSIS = None

# -----------------------------------------------------
# دوال المحاكاة (لم يتم تغيير هذا الجزء)
# -----------------------------------------------------

def predict_soil_type(image_path):
    """محاكاة تحليل صورة التربة بدون نموذج ML حقيقي."""
    if not image_path:
        return random.choice(CLASS_NAMES)

    name_lower = image_path.lower()
    if "red" in name_lower:
        return "Red_Soil"
    elif "black" in name_lower:
        return "Black_Soil"
    elif "alluvial" in name_lower:
        return "Alluvial_Soil"
    elif "yellow" in name_lower:
        return "Yellow_Soil"
    elif "laterite" in name_lower:
        return "Laterite_Soil"

    return random.choice(CLASS_NAMES)

def determine_suitability(soil_type, area_sqm, prev_crops_str, farmer_pref, desired_crop, historical_analysis=None):
    area_ha = area_sqm / 10000
    prev_crops = [c.strip().lower() for c in prev_crops_str.split(',') if c.strip()]
    suitability_scores = []

    SOIL_BONUS = {
        'Alluvial_Soil': { 'تمر': 1.2, 'قمح_صلب': 1.1, 'طماطم': 1.05 },
        'Black_Soil': { 'قمح_صلب': 1.15, 'بطاطا': 1.1, 'بطيخ': 1.0 },
        'Laterite_Soil': { 'زيتون': 1.2, 'عنب': 1.1, 'تمر': 1.0 },
        'Red_Soil': { 'بطاطا': 1.05, 'طماطم': 1.1, 'قمح_صلب': 1.0 },
        'Yellow_Soil': { 'بقوليات': 1.15, 'شعير': 1.1, 'عنب': 1.0 }
    }

    for crop, prop in CROP_PROPERTIES.items():
        water_need, cost_ratio, profit_ratio, _ = prop
        base_score = (profit_ratio * 0.4) + ((1 - water_need) * 0.3) + ((1 - cost_ratio) * 0.3)
        base_score *= SOIL_BONUS.get(soil_type, {}).get(crop, 1.0)

        if farmer_pref == 'high_profit':
            base_score *= (1 + profit_ratio * 0.3)
        elif farmer_pref == 'low_water':
            base_score *= (1 + (1 - water_need) * 0.3)
        elif farmer_pref == 'improve_efficiency' and historical_analysis and 'water_efficiency_ratio' in historical_analysis:
            base_score *= (1 + historical_analysis.get('water_efficiency_ratio', 0) * 0.05) 

        if crop.lower() in prev_crops:
            base_score *= 0.8

        if desired_crop and crop.lower().strip() == desired_crop.lower().strip():
            base_score *= 1.3

        final_score = min(100, max(0, base_score * 80 + 10))
        suitability_scores.append({'crop': crop, 'score': round(final_score,1)})

    suitability_scores.sort(key=lambda x: x['score'], reverse=True)
    return suitability_scores

def generate_detailed_report(selected_crop, area_sqm, soil_type, location_name, recommendations, historical_analysis):
    area_ha = area_sqm / 10000
    details = CROP_PROPERTIES.get(selected_crop)
    current_score = next((r['score'] for r in recommendations if r['crop'] == selected_crop), 0.0)

    if not details:
        return "خطأ: لا توجد بيانات تفصيلية (CROP_PROPERTIES) للمحصول المحدد. يرجى اختيار محصول من القائمة المقترحة."

    base_cost_per_ha = sum(BASE_COSTS_PER_HA.values())
    total_cost = base_cost_per_ha * area_ha
    expected_yield_kg_ha = details[3]
    expected_yield = expected_yield_kg_ha * area_ha
    price_per_kg = PRICE_PER_KG_DZD.get(selected_crop, 100)
    total_revenue = expected_yield * price_per_kg
    net_profit = total_revenue - total_cost
    water_need_m3 = WATER_NEED_M3_HA.get(selected_crop, 5000) * area_ha

    soil_type_ar = {
        'Alluvial_Soil': 'تربة طينية/رسوبية', 'Black_Soil': 'تربة سوداء',
        'Laterite_Soil': 'تربة لاتيريتية', 'Red_Soil': 'تربة حمراء',
        'Yellow_Soil': 'تربة صفراء'
    }.get(soil_type, 'غير محدد')
    
    report_date = time.strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
=====================================================
** تقرير الخطة الزراعية والمالية التفصيلي للموسم**
=====================================================
الموقع: {location_name}
تاريخ التقرير: {report_date}
نوع التربة المُحدد: {soil_type_ar}

I. التوصية الرئيسية والملاءمة
المحصول المقترح: {selected_crop}
مستوى الملاءمة: {current_score:.1f}%

II. الخطة المالية المتوقعة (لـ {area_ha:.2f} هكتار)
| البند | التقدير (د.ج) |
| :--- | :--- |
| الإيرادات الكلية | {total_revenue:,.0f} |
| إجمالي التكاليف | {total_cost:,.0f} |
| الربح الصافي المتوقع | **{net_profit:,.0f}** |

III. المؤشرات الزراعية
| المؤشر | القيمة | الوحدة |
| :--- | :--- | :--- |
| المساحة الكلية | {area_sqm:,.0f} | م² |
| المردود المتوقع | {expected_yield:,.0f} | كغم |
| الاحتياج المائي الكلي | {water_need_m3:,.0f} | م³ |
=====================================================
"""
    return report.strip()

# -----------------------------------------------------
# خادم Flask
# -----------------------------------------------------

# تهيئة Flask مع تحديد مسار مجلد الـ templates
app = Flask(__name__, template_folder='templates') 
CORS(app) 

# ↓↓↓↓↓↓↓↓↓↓↓↓↓ تم إضافة هذا لتقديم الـ HTML ↓↓↓↓↓↓↓↓↓↓↓↓↓
@app.route('/', methods=['GET'])
def home():
    """الرد على طلبات GET للمسار الأساسي لتقديم الواجهة الأمامية."""
    # يجب أن يكون ملف index_final.html موجودًا في مجلد templates/
    return render_template('index_final.html')
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

@app.route('/api/analyze_soil', methods=['POST'])
def api_analyze_soil():
    data = request.json
    try:
        image_path = data.get('image_path')
        area_sqm = float(data.get('area_sqm', 10000)) 
        prev_crops_str = data.get('prev_crops_str', '')
        farmer_pref = data.get('farmer_pref', 'none')
        desired_crop = data.get('desired_crop', '')

        soil_type = predict_soil_type(image_path)
        recommendations = determine_suitability(
            soil_type, area_sqm, prev_crops_str, farmer_pref, desired_crop, GLOBAL_HISTORICAL_ANALYSIS
        )

        return jsonify({'soil_type': soil_type, 'recommendations': recommendations})
    except Exception as e:
        return jsonify({'error': f"خطأ في تحليل التربة: {str(e)}"}), 500

@app.route('/api/generate_plan', methods=['POST'])
def api_generate_plan():
    data = request.json
    try:
        selected_crop = data.get('selected_crop')
        if not selected_crop or selected_crop not in CROP_PROPERTIES:
            return jsonify({'error': "لم يتم تحديد المحصول بشكل صحيح أو لا توجد بيانات لهذا المحصول."}), 400
            
        area_sqm = float(data.get('area_sqm', 10000))
        soil_type = data.get('soil_type')
        location_name = data.get('location_name')
        recommendations = data.get('recommendations', [])

        report_text = generate_detailed_report(
            selected_crop, area_sqm, soil_type, location_name, recommendations, GLOBAL_HISTORICAL_ANALYSIS
        )

        return jsonify({'report': report_text})
    except Exception as e:
        return jsonify({'error': f"خطأ في توليد الخطة: {str(e)}"}), 500

@app.route('/api/analyze_historical', methods=['POST'])
def api_analyze_historical():
    global GLOBAL_HISTORICAL_ANALYSIS
    data = request.json
    try:
        actual_yield = float(data.get('actual_yield', 0))
        area_sqm = float(data.get('area_sqm', 10000))
        actual_water = float(data.get('actual_water', 1)) 
        
        if actual_water <= 0 or actual_yield <= 0:
             return jsonify({'error': "يجب أن تكون كمية الماء والمردود أكبر من صفر."}), 400
             
        area_ha = area_sqm / 10000
        water_efficiency_ratio = (actual_yield / area_ha) / actual_water
        
        GLOBAL_HISTORICAL_ANALYSIS = {
            'previous_crop': data.get('crop'),
            'water_efficiency_ratio': water_efficiency_ratio,
            'message': f"تم تحليل الأداء التاريخي لـ {data.get('crop')} بنجاح. كفاءة الماء: {water_efficiency_ratio:.2f} كغم/م³."
        }
        
        return jsonify({'message': GLOBAL_HISTORICAL_ANALYSIS['message'], 'analysis': GLOBAL_HISTORICAL_ANALYSIS})

    except Exception as e:
        return jsonify({'error': f"خطأ في معالجة البيانات التاريخية: {str(e)}"}), 500

if __name__ == '__main__':
    # لتشغيل Render، قد تحتاج إلى إضافة 'host='0.0.0.0'
    app.run(debug=True)


