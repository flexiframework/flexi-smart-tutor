import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time

# --- 1. الإعدادات الأساسية (التي لا تخطئ) ---
st.set_page_config(page_title="Flexi Academy Tutor", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ API Key is missing in Streamlit Secrets!")
    st.stop()

# --- 2. تهيئة الحالة (Session State) ---
# نضمن أن كل شيء معرف منذ البداية لمنع الأخطاء
if 'lesson_content' not in st.session_state: st.session_state.lesson_content = ""
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'user_scores' not in st.session_state: st.session_state.user_scores = {}
if 'total_points' not in st.session_state: st.session_state.total_points = 0

# --- 3. الواجهة الجانبية ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("Settings")
    lang = st.selectbox("Language", ["English", "العربية"])
    level = st.selectbox("Level", ["Beginner", "Advanced"])
    st.divider()
    st.metric("Score 🎯", st.session_state.total_points)
    if st.button("Reset All"): # زر لإعادة التصفير في حال التعليق
        st.session_state.clear()
        st.rerun()

# --- 4. منطق توليد الدرس (مع معالجة الأخطاء) ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What do you want to learn today?", placeholder="Enter topic...")

if st.button("Start Lesson 🚀"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            # نستخدم الموديل الأكثر استقراراً حالياً
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Tutor: Flexi Academy. Level: {level}. Language: {lang}. Topic: {topic}.
            1. Explain the topic clearly with 3-4 sections.
            2. For each section, add one tag like [[visual prompt]] for an image.
            3. End with '---QUIZ---' and 3 MCQs in this format:
               Q: Question | A: Opt1 | B: Opt2 | C: Opt3 | Correct: A/B/C | Expl: Why
            """
            
            with st.spinner('Flexi is thinking...'):
                response = model.generate_content(prompt)
                full_text = response.text
                
                # تقسيم النص بذكاء
                if "---QUIZ---" in full_text:
                    lesson_part, quiz_part = full_text.split("---QUIZ---")
                else:
                    lesson_part, quiz_part = full_text, ""
                
                # حفظ البيانات
                st.session_state.lesson_content = lesson_part
                st.session_state.quiz_data = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz_part)
                st.session_state.user_scores = {}
                st.session_state.total_points = 0
                
                # توليد الصوت (اختياري، لن يعطل الكود إذا فشل)
                try:
                    clean_text = re.sub(r'\[\[.*?\]\]', '', lesson_part[:500])
                    tts = gTTS(text=clean_text, lang='en' if lang=="English" else 'ar')
                    tts.save("voice.mp3")
                except: pass
                
                st.rerun()
                
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")

# --- 5. عرض المحتوى ---
if st.session_state.lesson_content:
    if os.path.exists("voice.mp3"):
        st.audio("voice.mp3")
    
    # تنسيق العرض حسب اللغة
    direction = "rtl" if lang == "العربية" else "ltr"
    st.markdown(f'<div style="direction:{direction}; text-align:{"right" if lang=="العربية" else "left"}">', unsafe_allow_html=True)
    
    segments = re.split(r'\[\[(.*?)\]\]', st.session_state.lesson_content)
    for i, seg in enumerate(segments):
        if i % 2 == 0:
            if seg.strip(): st.markdown(f'<div class="lesson-box" style="background:#fff; padding:20px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:#333;">{seg.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{seg.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. عرض الأسئلة التفاعلية ---
    if st.session_state.quiz_data:
        st.header("🧠 Quick Quiz")
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
            qid = f"q_{idx}"
            st.subheader(f"Q{idx+1}: {q.strip()}")
            choice = st.radio("Choose one:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
            
            if st.button(f"Submit Q{idx+1}", key=f"btn_{idx}"):
                if qid not in st.session_state.user_scores:
                    is_correct = choice[0].upper() == correct.strip()[0].upper()
                    st.session_state.user_scores[qid] = is_correct
                    if is_correct: st.session_state.total_points += 10
                    st.rerun()
            
            if qid in st.session_state.user_scores:
                if st.session_state.user_scores[qid]: st.success("Correct! 🌟")
                else: st.error(f"Incorrect. The answer is {correct}. {expl}")
