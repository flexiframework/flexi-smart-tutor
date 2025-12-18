import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time

# --- 1. إعدادات الأمان والربط ---
st.set_page_config(page_title="Flexi Academy AI", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ API Key missing in Secrets!")
    st.stop()

# --- 2. دالة اكتشاف الموديل (لحل خطأ 404 نهائياً) ---
def find_working_model():
    try:
        # البحث عن كل الموديلات التي تدعم توليد المحتوى في حسابك
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # ترتيب الأولوية: الفلاش الأحدث ثم البرو ثم القديم
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro", "gemini-1.5-flash"]
        for p in priority:
            if p in available_models:
                return p
        return available_models[0] if available_models else None
    except Exception as e:
        st.error(f"Error listing models: {e}")
        return None

# --- 3. تهيئة الجلسة ---
if 'content' not in st.session_state: st.session_state.content = ""
if 'quiz' not in st.session_state: st.session_state.quiz = []
if 'score' not in st.session_state: st.session_state.score = 0
if 'answers' not in st.session_state: st.session_state.answers = {}

# --- 4. القائمة الجانبية (إعادة كافة الخصائص) ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("👤 Student Profile")
    st_name = st.text_input("Name", "Student")
    st_age = st.number_input("Age", 5, 100, 12)
    st_gender = st.selectbox("Gender", ["Male", "Female"])
    st_level = st.selectbox("Academic Level", ["Beginner", "Intermediate", "Advanced"])
    st_lang = st.selectbox("Language", ["English", "العربية"])
    
    st.divider()
    if st.button("🔄 Reset Experience"):
        st.session_state.clear()
        st.rerun()

# --- 5. منطق التوليد ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What topic would you like to explore?", placeholder="e.g. Gravity")

if st.button("Generate Lesson 🚀"):
    working_model_name = find_working_model()
    
    if not topic:
        st.warning("Please enter a topic.")
    elif not working_model_name:
        st.error("No compatible models found in your API key settings.")
    else:
        try:
            model = genai.GenerativeModel(working_model_name)
            
            prompt = f"""
            You are a tutor at Flexi Academy. 
            Student: {st_name}, Gender: {st_gender}, Age: {st_age}, Level: {st_level}.
            Language: {st_lang}. Topic: {topic}.
            
            Instructions:
            1. Explain the topic in 4 clear parts. Use language suitable for age {st_age}.
            2. Add 6 image tags like [[visual prompt]] throughout the text.
            3. End with '---QUIZ_START---' and 5 MCQs:
               Q: Question | A: Opt1 | B: Opt2 | C: Opt3 | Correct: A/B/C | Expl: Why
            """
            
            with st.spinner(f'Flexi is using {working_model_name}... Please wait...'):
                response = model.generate_content(prompt)
                full_text = response.text
                
                # تقسيم النص
                if "---QUIZ_START---" in full_text:
                    lesson, quiz = full_text.split("---QUIZ_START---")
                else:
                    lesson, quiz = full_text, ""
                
                st.session_state.content = lesson
                st.session_state.quiz = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz)
                st.session_state.score = 0
                st.session_state.answers = {}
                
                # صوت الدرس
                try:
                    clean_txt = re.sub(r'\[\[.*?\]\]', '', lesson[:600])
                    tts = gTTS(text=clean_txt, lang='en' if st_lang=="English" else 'ar')
                    tts.save("voice.mp3")
                except: pass
                
                st.rerun()
        except Exception as e:
            st.error(f"Technical Error: {e}")

# --- 6. عرض النتائج ---
if st.session_state.content:
    if os.path.exists("voice.mp3"): st.audio("voice.mp3")
    
    direction = "rtl" if st_lang == "العربية" else "ltr"
    st.markdown(f'<div style="direction:{direction}">', unsafe_allow_html=True)
    
    # عرض النصوص والصور
    parts = re.split(r'\[\[(.*?)\]\]', st.session_state.content)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            if p.strip(): st.markdown(f'<div style="background:white; padding:20px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:#333;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{p.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
    # عرض الأسئلة
    if st.session_state.quiz:
        st.divider()
        st.header("🧠 Knowledge Challenge")
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz):
            qid = f"q_{idx}"
            st.write(f"**Q{idx+1}:** {q.strip()}")
            choice = st.radio("Choose:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
            
            if st.button(f"Submit Q{idx+1}", key=f"b_{idx}"):
                if qid not in st.session_state.answers:
                    is_correct = choice[0].upper() == correct.strip()[0].upper()
                    st.session_state.answers[qid] = {"res": is_correct, "expl": expl, "c": correct}
                    if is_correct: st.session_state.score += 20
                    st.rerun()
            
            if qid in st.session_state.answers:
                ans = st.session_state.answers[qid]
                if ans["res"]: st.success("Correct! 🌟")
                else: st.error(f"Wrong. Answer is {ans['c']}. {ans['expl']}")
