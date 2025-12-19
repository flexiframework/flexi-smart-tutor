import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time

# --- 1. الإعدادات ---
st.set_page_config(page_title="Flexi Academy AI", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ قم بإضافة الـ API Key الجديد في الـ Secrets!")
    st.stop()

# --- 2. تهيئة الجلسة ---
if 'content' not in st.session_state: st.session_state.content = ""
if 'quiz' not in st.session_state: st.session_state.quiz = []
if 'score' not in st.session_state: st.session_state.score = 0
if 'answers' not in st.session_state: st.session_state.answers = {}

# --- 3. الواجهة الجانبية ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("👤 Profile")
    st_name = st.text_input("Name", "Learner")
    st_age = st.number_input("Age", 5, 100, 12)
    st_level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
    st_lang = st.selectbox("Language", ["English", "العربية"])
    
    st.divider()
    if st.button("🔄 Reset App"):
        st.session_state.clear()
        st.rerun()

# --- 4. منطق التوليد (مثبت على 1.5 Flash للحصة الأكبر) ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What do you want to learn?", placeholder="e.g. How planes fly")

if st.button("Generate Lesson 🚀"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            # استخدام موديل 1.5 فلاش تحديداً لأنه يمتلك 1500 طلب يومياً
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are a teacher at Flexi Academy. 
            Student: {st_name}, Age: {st_age}, Level: {st_level}, Language: {st_lang}.
            Explain '{topic}' in 4 sections with 6 [[image prompts]].
            End with '---QUIZ---' then 5 MCQs:
            Q: Question | A: Opt1 | B: Opt2 | C: Opt3 | Correct: A/B/C | Expl: Why
            """
            
            with st.spinner('Flexi is building your lesson...'):
                response = model.generate_content(prompt)
                
                if "---QUIZ---" in response.text:
                    lesson, quiz = response.text.split("---QUIZ---")
                else:
                    lesson, quiz = response.text, ""
                
                st.session_state.content = lesson
                st.session_state.quiz = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz)
                st.session_state.score = 0
                st.session_state.answers = {}
                
                # إنشاء الصوت
                try:
                    clean = re.sub(r'\[\[.*?\]\]', '', lesson[:500])
                    gTTS(text=clean, lang='en' if st_lang=="English" else 'ar').save("voice.mp3")
                except: pass
                
                st.rerun()
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ انتهت حصة الـ API لهذا المفتاح اليوم. يرجى إنشاء مفتاح جديد من Google AI Studio أو المحاولة غداً.")
            else:
                st.error(f"Error: {e}")

# --- 5. عرض النتائج ---
if st.session_state.content:
    if os.path.exists("voice.mp3"): st.audio("voice.mp3")
    
    direction = "rtl" if st_lang == "العربية" else "ltr"
    st.markdown(f'<div style="direction:{direction}">', unsafe_allow_html=True)
    
    parts = re.split(r'\[\[(.*?)\]\]', st.session_state.content)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            if p.strip(): st.markdown(f'<div style="background:white; padding:20px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:#333;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{p.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
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
