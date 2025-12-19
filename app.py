import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time

# --- 1. الإعدادات ---
st.set_page_config(page_title="Flexi Academy AI", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    # نقوم فقط بضبط الإعدادات هنا
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ قم بإضافة الـ API Key في الـ Secrets!")
    st.stop()


# --- 2. تهيئة الجلسة ---
if 'content' not in st.session_state: st.session_state.content = ""
if 'quiz' not in st.session_state: st.session_state.quiz = []
if 'score' not in st.session_state: st.session_state.score = 0
if 'answers' not in st.session_state: st.session_state.answers = {}

# --- 3. الواجهة الجانبية ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=180)
    st.header("👤 Profile & Settings")
    
    # --- إضافة جديدة: اختيار نوع المحتوى ---
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
        st.rerun()

# --- 4. منطق التوليد ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_input("What do you want to explore?", placeholder="e.g. Ancient Egypt")

if st.button("Generate Content 🚀"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            # حفظ النمط المختار لاستخدامه في العرض
            st.session_state.content_mode = st_mode
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # --- تصميم الأوامر بناءً على النمط المختار ---
            base_prompt = f"""
            Target Audience: Student Name: {st_name}, Age: {st_age}, Level: {st_level}, Language: {st_lang}, Style: {st_style}.
            Topic: {topic}.
            Requirements: Use exactly 6 [[detailed image prompt]] tags suitable for an image generator.
            End the response with the separator '---QUIZ---' followed by 5 multiple choice questions in this format:
            Q: Question text | A: Option1 | B: Option2 | C: Option3 | Correct: A/B/C | Expl: Short explanation
            """

            if st_mode == "Interactive Lesson (درس تفاعلي)":
                # برومبت الدرس الأكاديمي
                specific_instructions = """
                Role: Expert Tutor.
                Task: Create a clear, structured academic lesson structured in 4 distinct sections. Explain key concepts clearly.
                If style is Kinesthetic, include a small practical activity suggestion.
                """
            else:
                # برومبت القصة المصورة
                specific_instructions = """
                Role: Creative Comic Book Writer.
                Task: Create a thrilling educational comic story script structured into 6 Panels.
                Format each panel as: 
                **PANEL X**
                (Narrator box text or character dialogue here)
                [[detailed visual description of the action in this panel]]
                Focus on action, dialogue, and a narrative arc that teaches the topic.
                """

            final_prompt = base_prompt + specific_instructions
            
            with st.spinner(f'Flexi is creating your {st_mode}...'):
                response = model.generate_content(final_prompt)
                
                if "---QUIZ---" in response.text:
                    lesson, quiz = response.text.split("---QUIZ---")
                else:
                    lesson, quiz = response.text, ""
                
                st.session_state.content = lesson
                st.session_state.quiz = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz)
                st.session_state.score = 0
                st.session_state.answers = {}
                
                # الصوت
                try:
                    clean = re.sub(r'\[\[.*?\]\]', '', lesson[:700])
                    # تنظيف إضافي للقصة المصورة لإزالة عناوين اللوحات من الصوت
                    clean = re.sub(r'\*\*PANEL \d+\*\*', '', clean) 
                    gTTS(text=clean, lang='en' if st_lang=="English" else 'ar').save("voice.mp3")
                except: pass
                
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. عرض النتائج ---
if st.session_state.content:
    if os.path.exists("voice.mp3"):
        st.write("🎧 **Listen:**")
        st.audio("voice.mp3")
    
    direction = "rtl" if st_lang == "العربية" else "ltr"
    st.markdown(f'<div style="direction:{direction}">', unsafe_allow_html=True)
    
    # تغيير عنوان القسم بناءً على النمط
    if "Comic" in st.session_state.content_mode:
        st.subheader("🖼️ Your Comic Story Adventure")
    else:
        st.subheader("📘 Your Interactive Lesson")

    parts = re.split(r'\[\[(.*?)\]\]', st.session_state.content)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            if p.strip(): 
                # تنسيق مختلف قليلاً للقصة (خط أكبر للحوار)
                if "Comic" in st.session_state.content_mode:
                     st.markdown(f'<div style="background:#fdf2e9; padding:20px; border-radius:15px; border-left:5px solid #d97706; margin:15px 0; color:#333; font-size:1.1em; font-family:Comic Sans MS, cursive;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                else:
                    # تنسيق الدرس العادي
                    st.markdown(f'<div style="background:white; padding:20px; border-radius:10px; border-left:5px solid #1e3a8a; margin:10px 0; color:#333; line-height:1.6;">{p.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            # الصور
            st.image(f"https://pollinations.ai/p/{p.strip().replace(' ', '%20')}?width=800&height=400&seed={i}")
    
    # الكويز
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


