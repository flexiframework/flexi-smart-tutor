import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- الإعدادات ---
# --- 1. API Configuration ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ API Key not found in Secrets!")
    st.stop()

st.set_page_config(page_title="منصة فليكسي التعليمية الشاملة", layout="wide", page_icon="🏆")

# تخصيص الواجهة بـ CSS
st.markdown("""
    <style>
    .lesson-box { padding: 25px; border-radius: 15px; border-right: 10px solid #1a73e8; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; color: #2c3e50; }
    .comic-panel { border: 4px solid #000; padding: 15px; background: white; box-shadow: 8px 8px 0px #000; margin-bottom: 20px; }
    .caption-tag { background: #ffde59; color: black; padding: 5px 10px; font-weight: bold; border: 2px solid #000; margin-bottom: 10px; display: inline-block; }
    .dialogue-text { background: #f0f0f0; border-radius: 10px; padding: 10px; border-left: 5px solid #333; font-style: italic; margin-top: 10px; }
    .question-box { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #ddd; margin-top: 15px; }
    @media print { .no-print { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- الوظائف المساعدة ---
def get_available_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((m for m in available_models if "1.5-flash" in m), available_models[0])
    except: return "gemini-1.5-flash"

# --- الحالة (Session State) ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'answered' not in st.session_state: st.session_state.answered = set()

# --- القائمة الجانبية (Sidebar) تضم كل العناصر ---
with st.sidebar:
    st.header("⚙️ تخصيص التجربة")
    student_name = st.text_input("اسم الطالب:", value="بطل فليكسي")
    age = st.number_input("السن:", min_value=5, max_value=100, value=12)
    gender = st.selectbox("الجنس:", ["ذكر", "أنثى"])
    language = st.selectbox("لغة الشرح:", ["العربية", "English", "Français", "Deutsch"])
    level = st.selectbox("المستوى الأكاديمي:", ["مبتدئ", "متوسط", "متقدم"])
    learning_style = st.selectbox("نمط المتعلم الأساسي:", ["بصري (Visual)", "سمعي (Auditory)", "حركي (Kinesthetic)"])
    
    st.divider()
    output_format = st.radio("شكل المخرجات المطلوب:", ["درس تفاعلي عادي", "قصة مصورة (Comic)"])
    
    st.divider()
    if st.button("🖨️ طباعة المحتوى الحالي"):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# --- المنطقة الرئيسية ---
st.title("🌟 منصة فليكسي للتعلم الذكي")
source_content = st.text_area("أدخل موضوع الدرس أو النص المراد شرحه:", placeholder="مثلاً: شرح الدورة الدموية، أو قوانين نيوتن...")

if st.button("توليد المحتوى المخصص 🚀"):
    if not source_content:
        st.error("الرجاء إدخال موضوع للدرس!")
    else:
        try:
            model = genai.GenerativeModel(get_available_model())
            is_comic = "قصة مصورة" in output_format
            
            # بناء البرومبت الشامل بكافة العناصر
            prompt = f"""
            You are an expert tutor. Create an educational content for:
            Student Name: {student_name}, Age: {age}, Gender: {gender}, Level: {level}, Learning Style: {learning_style}.
            Subject: {source_content}
            Language of Response: {language}.

            FORMAT INSTRUCTIONS:
            {"1. COMIC MODE: Create 4 panels. For each use: PANEL X, CAPTION: [narration], DIALOGUE: [speech], VISUAL: [English image description]." if is_comic else "1. LESSON MODE: Personal welcome, detailed explanation using ### for headers, and an image description in [[ ]]."}
            
            2. QUIZ: At the end, include 4 Multiple Choice Questions exactly in this format:
            Q: [Question text]
            A) [Option]
            B) [Option]
            C) [Option]
            Correct: [Letter]
            Explanation: [Short note]
            """
            
            with st.spinner(f'جاري تصميم ال{output_format} لـ {student_name}... ⏳'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.answered = set()
                
                # توليد ملف الصوت
                clean_text = re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:', '', st.session_state.lesson_data.split("Q:")[0])
                lang_code = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}[language]
                gTTS(text=clean_text[:600], lang=lang_code).save("voice.mp3")
                st.rerun()
        except Exception as e: st.error(f"حدث خطأ: {e}")

# --- عرض النتائج ---
if st.session_state.lesson_data:
    content = st.session_state.lesson_data
    direction = "rtl" if language == "العربية" else "ltr"
    
    # مشغل الصوت
    st.audio("voice.mp3")

    if "قصة مصورة" in output_format:
        st.subheader("🖼️ القصة المصورة التعليمية")
        panels = re.split(r'PANEL \d+', content.split("Q:")[0])[1:]
        cols = st.columns(2)
        for i, panel in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown('<div class="comic-panel">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', panel, re.S)
                dia = re.search(r'DIALOGUE:(.*?)(?=VISUAL:|$)', panel, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', panel, re.S)
                
                if cap: st.markdown(f'<div class="caption-tag">🎬 {cap.group(1).strip()}</div>', unsafe_allow_html=True)
                if vis:
                    img_desc = vis.group(1).strip().replace(" ", "%20")
                    st.image(f"https://pollinations.ai/p/comic%20book%20style%20{img_desc}?width=600&height=400&seed={i+7}")
                if dia: st.markdown(f'<div class="dialogue-text">💬 {dia.group(1).strip()}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.subheader("📖 الدرس التفاعلي")
        lesson_text = content.split("Q:")[0]
        st.markdown(f'<div class="lesson-box" style="direction:{direction}">{lesson_text.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)
        
        # صورة الدرس العادي
        img_match = re.search(r'\[\[(.*?)\]\]', lesson_text)
        if img_match:
            st.image(f"https://pollinations.ai/p/{img_match.group(1).replace(' ', '%20')}?width=1024&height=500")

    # --- الأسئلة التفاعلية ---
    st.divider()
    st.header("🧠 اختبر معلوماتك")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        with st.container():
            st.markdown(f'<div class="question-box" style="direction:{direction}">', unsafe_allow_html=True)
            q_text = q_raw.split("A)")[0].strip()
            st.write(f"**س{i+1}: {q_text}**")
            
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if options:
                user_choice = st.radio(f"اختر الإجابة لسؤال {i+1}", options, key=f"q_{i}")
                if st.button(f"تأكيد إجابة {i+1}", key=f"btn_{i}"):
                    if i not in st.session_state.answered:
                        if user_choice[0] == correct.strip():
                            st.success(f"أحسنت! إجابة صحيحة. {expl}")
                            st.session_state.score += 10
                        else:
                            st.error(f"للأسف إجابة خاطئة. الصحيح هو {correct}. {expl}")
                        st.session_state.answered.add(i)
                    else: st.info("تمت الإجابة بالفعل.")
            st.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.metric("نقاط التحدي", st.session_state.score)

