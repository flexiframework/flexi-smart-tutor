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
# --- 3. الواجهة الجانبية (تمت إضافة نمط التعلم هنا) ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("👤 Profile")
    st_name = st.text_input("Name", "Learner")
    st_age = st.number_input("Age", 5, 100, 12)
    st_level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
    st_lang = st.selectbox("Language", ["English", "العربية"])
    
    # إضافة عنصر نمط الطالب
    st_style = st.selectbox("Learning Style 🧠", [
        "Visual (بصري)", 
        "Auditory (سمعي)", 
        "Kinesthetic (حركي)"
    ])
    
    st.divider()
    if st.button("🔄 Reset App"):
        st.session_state.clear()
        st.rerun()

# --- 4. منطق التوليد ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What do you want to learn?", placeholder="e.g. Solar System")

if st.button("Generate Lesson 🚀"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # تحديث الـ Prompt ليشمل نمط التعلم
            prompt = f"""
            You are a professional teacher at Flexi Academy. 
            Student Profile:
            - Name: {st_name}
            - Age: {st_age}
            - Level: {st_level}
            - Language: {st_lang}
            - Learning Style: {st_style}
            
            Instructions based on Style:
            - If Visual: Include vivid descriptions and exactly 6 [[image prompts]].
            - If Auditory: Use a storytelling tone and rhythmic language.
            - If Kinesthetic: Include a 'Small Activity' or 'Home Experiment' section.
            
            Task: Explain '{topic}' clearly. 
            Format: Divide into 4 sections. Use [[image prompt]] tags.
            End with '---QUIZ---' then 5 MCQs:
            Q: Question | A: Opt1 | B: Opt2 | C: Opt3 | Correct: A/B/C | Expl: Why
            """
            
            with st.spinner(f'Flexi is preparing a {st_style} lesson for you...'):
                response = model.generate_content(prompt)
                
                if "---QUIZ---" in response.text:
                    lesson, quiz = response.text.split("---QUIZ---")
                else:
                    lesson, quiz = response.text, ""
                
                st.session_state.content = lesson
                st.session_state.quiz = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz)
                st.session_state.score = 0
                st.session_state.answers = {}
                
                # إنشاء الصوت (مهم جداً للنمط السمعي)
                try:
                    clean = re.sub(r'\[\[.*?\]\]', '', lesson[:700])
                    gTTS(text=clean, lang='en' if st_lang=="English" else 'ar').save("voice.mp3")
                except: pass
                
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. عرض النتائج ---
if st.session_state.content:
    # لنمط التعلم السمعي، يظهر المشغل الصوتي في الأعلى بشكل بارز
    if os.path.exists("voice.mp3"):
        st.write("🎧 **Listen to your lesson:**")
        st.audio("voice.mp3")
    
    direction = "rtl" if st_lang == "العربية" else "ltr"
    st.markdown(f'<div style="direction:{direction}">', unsafe_allow_html=True)
    
    parts = re.split(r'\[\[(.*?)\]\]', st.session_state.content)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            if p.strip(): 
                st.markdown(f'<div style="background:white; padding:20px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:#333; line-height:1.6;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            # الصور تظهر بوضوح للنمط البصري
            st.image(f"https://pollinations.ai/p/{p.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
    # عرض الكويز بنفس الطريقة المستقرة
    if st.session_state.quiz:
        st.divider()
        st.header("🧠 Knowledge Challenge")
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz):
            qid = f"q_{idx}"
            st.write(f"**Q{idx+1}:** {q.strip()}")
            choice = st.radio("Choose answer:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
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
