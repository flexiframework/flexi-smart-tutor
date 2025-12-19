import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time

# --- 1. الإعدادات ---
st.set_page_config(page_title="Flexi Academy AI", layout="wide")

# تأكد من أن مفتاح الـ API موجود قبل البدء
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ قم بإضافة الـ API Key في الـ Secrets باسم GEMINI_API_KEY")
    st.stop()

# --- 2. تهيئة الجلسة ---
if 'content' not in st.session_state: st.session_state.content = ""
if 'quiz' not in st.session_state: st.session_state.quiz = []
if 'score' not in st.session_state: st.session_state.score = 0
if 'answers' not in st.session_state: st.session_state.answers = {}
if 'content_mode' not in st.session_state: st.session_state.content_mode = ""

# --- 3. الواجهة الجانبية ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("👤 Profile & Settings")
    
    st_mode = st.radio(
        "Choose Content Mode 📖:",
        ["Interactive Lesson (درس تفاعلي)", "Comic Story (قصة مصورة)"],
        index=0
    )
    st.divider()
    
    st_name = st.text_input("Name", "Learner")
    st_age = st.number_input("Age", 5, 100, 12)
    st_level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
    st_lang = st.selectbox("Language", ["English", "العربية"])
    st_style = st.selectbox("Learning Style 🧠", ["Visual", "Auditory", "Kinesthetic"])
    
    st.divider()
    if st.button("🔄 Reset App"):
        st.session_state.clear()
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
        st.rerun()

# --- 4. منطق التوليد ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What do you want to explore?", placeholder="e.g. Ancient Egypt")

if st.button("Generate Content 🚀"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            st.session_state.content_mode = st_mode
            
            # --- الحل النهائي لخطأ 404 ---
            # تعريف الموديل داخل زر الضغط لضمان تحميل الإعدادات أولاً
            model = genai.GenerativeModel(
                model_name="models/gemini-1.5-flash"
            )
            
            base_prompt = f"""
            Target Audience: Name: {st_name}, Age: {st_age}, Level: {st_level}, Language: {st_lang}, Style: {st_style}.
            Topic: {topic}.
            Requirements: Use 6 [[detailed image prompt]] tags.
            End the response with '---QUIZ---' and 5 MCQs in this format:
            Q: Question | A: Option1 | B: Option2 | C: Option3 | Correct: A/B/C | Expl: Explanation
            """

            if st_mode == "Interactive Lesson (درس تفاعلي)":
                specific_instructions = "Role: Expert Tutor. Create a structured academic lesson."
            else:
                specific_instructions = "Role: Comic Writer. Create a script with 6 Panels. Format: **PANEL X** [[image prompt]]"

            with st.spinner(f'Flexi is creating your {st_mode}...'):
                response = model.generate_content(base_prompt + specific_instructions)
                full_response = response.text
                
                if "---QUIZ---" in full_response:
                    lesson, quiz_raw = full_response.split("---QUIZ---")
                else:
                    lesson, quiz_raw = full_response, ""
                
                st.session_state.content = lesson
                # Regex مطور لتجنب أي أخطاء في التنسيق
                st.session_state.quiz = re.findall(r"Q:\s*(.*?)\s*\|\s*A:\s*(.*?)\s*\|\s*B:\s*(.*?)\s*\|\s*C:\s*(.*?)\s*\|\s*Correct:\s*(.*?)\s*\|\s*Expl:\s*(.*)", quiz_raw)
                st.session_state.score = 0
                st.session_state.answers = {}
                
                # الصوت
                try:
                    clean = re.sub(r'\[\[.*?\]\]', '', lesson[:700])
                    tts = gTTS(text=clean, lang='en' if st_lang=="English" else 'ar')
                    tts.save("voice.mp3")
                except:
                    pass
                
                st.rerun()
        except Exception as e:
            st.error(f"حدث خطأ أثناء الاتصال بـ Gemini: {e}")

# --- 5. عرض النتائج ---
if st.session_state.content:
    if os.path.exists("voice.mp3"):
        st.audio("voice.mp3")
    
    direction = "rtl" if st_lang == "العربية" else "ltr"
    st.markdown(f'<div dir="{direction}" style="text-align: {"right" if st_lang=="العربية" else "left"}">', unsafe_allow_html=True)
    
    parts = re.split(r'\[\[(.*?)\]\]', st.session_state.content)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            if p.strip():
                st.markdown(f'<div style="background:white; padding:15px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:black;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            # عرض الصور باستخدام محرك Pollinations
            st.image(f"https://pollinations.ai/p/{p.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
    # الكويز
    if st.session_state.quiz:
        st.divider()
        st.header("🧠 Knowledge Challenge")
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz):
            qid = f"q_{idx}"
            st.write(f"**Q{idx+1}:** {q.strip()}")
            choice = st.radio("Choose:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
            if st.button(f"Submit Q{idx+1}", key=f"btn_{idx}"):
                if qid not in st.session_state.answers:
                    # التحقق من الإجابة (تجاهل المسافات وحالة الأحرف)
                    is_correct = choice.strip().startswith(correct.strip().upper())
                    st.session_state.answers[qid] = {"res": is_correct, "expl": expl, "c": correct}
                    if is_correct: st.session_state.score += 20
                    st.rerun()
            
            if qid in st.session_state.answers:
                ans = st.session_state.answers[qid]
                if ans["res"]: st.success("Correct! 🌟")
                else: st.error(f"Wrong. Answer is {ans['c']}. {ans['expl']}")

    st.markdown('</div>', unsafe_allow_html=True)
