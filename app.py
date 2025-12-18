import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. API Configuration & Smart Resolver ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ API Key not found in Secrets!")
    st.stop()

genai.configure(api_key=MY_API_KEY)

def get_smart_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ["models/gemini-1.5-flash", "models/gemini-pro"]
        for model_path in priority_list:
            if model_path in available_models: return model_path
        return available_models[0]
    except: return "models/gemini-1.5-flash"

# --- 2. UI Styling ---
st.set_page_config(page_title="Flexi Academy AI Tutor", layout="wide", page_icon="🎓")
st.markdown("""
    <style>
    :root { --flexi-blue: #1e3a8a; --flexi-orange: #f97316; }
    .lesson-box { padding: 30px; border-radius: 15px; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-top: 5px solid var(--flexi-blue); margin-bottom: 20px; }
    .comic-panel { border: 3px solid var(--flexi-blue); padding: 15px; background: white; border-radius: 12px; margin-bottom: 20px; text-align: center; }
    .quiz-container { background-color: #f1f8e9; padding: 25px; border-radius: 20px; border: 1px solid #c5e1a5; margin-top: 20px; }
    .stProgress > div > div > div > div { background-color: var(--flexi-orange); }
    img { border-radius: 15px; margin: 15px 0; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 4. Sidebar ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=220)
    student_name = st.text_input("Student Name:", value="Learner")
    age = st.number_input("Age:", 5, 100, 12)
    content_lang = st.selectbox("Language:", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style:", ["Visual (Many Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    path = st.radio("Learning Path:", ["Standard Interactive Lesson", "Comic Story Experience"])
    st.divider()
    st.subheader("📊 Progress")
    st.progress(min(st.session_state.score, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.score)

# --- 5. Main Logic ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What topic should we explore?", placeholder="e.g., Water Cycle")

if st.button("Generate Experience 🚀"):
    if not topic: st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel(get_smart_model())
            prompt = f"""
            Role: Expert Tutor at Flexi Academy. Language: {content_lang}.
            Student: {student_name}, Age: {age}, Style: {style}. Topic: {topic}. Path: {path}.
            
            Structure:
            1. Core Lesson: 
               - If Visual: Must include 6 different [[Image Description]] tags spaced out between paragraphs.
               - If Kinesthetic: Include 3 {{Activity}} boxes.
            2. Comic Path: 4 Panels with (PANEL X, CAPTION, DIALOGUE, VISUAL Description).
            3. Resources: 2 real URLs (NASA, PhET, etc.).
            4. Assessment: Exactly 5 MCQs (Q:, A) B) C), Correct:, Explanation:).
            """
            with st.spinner('Building your Flexi lesson...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- 6. Content Rendering ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    
    # Separation of Lesson and Quiz
    parts = raw.split("Q:")
    lesson_part = parts[0]
    quiz_part = "Q:" + "Q:".join(parts[1:]) if len(parts) > 1 else ""

    if "Comic" in path:
        st.subheader("🖼️ Your Learning Story")
        panels = re.split(r'PANEL \d+', lesson_part)[1:]
        cols = st.columns(2)
        for i, p in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown(f'<div class="comic-panel" style="direction:{dir_css}">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', p, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', p, re.S)
                if cap: st.write(f"🎬 {cap.group(1).strip()}")
                if vis: st.image(f"https://pollinations.ai/p/comic%20style%20{vis.group(1).strip().replace(' ', '%20')}?width=600&height=400&seed={i}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Rendering lesson with IN-TEXT Images
        st.markdown(f'<div style="direction:{dir_css}">', unsafe_allow_html=True)
        
        # Split text by image tags to insert images in-between
        text_segments = re.split(r'\[\[(.*?)\]\]', lesson_part)
        for idx, segment in enumerate(text_segments):
            if idx % 2 == 0: # This is text
                st.markdown(f'<div class="lesson-box">{segment.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else: # This is an image prompt
                st.image(f"https://pollinations.ai/p/{segment.strip().replace(' ', '%20')}?width=800&height=400&seed={idx}", caption=f"Visual: {segment.strip()}")
        
        # Activities for Kinesthetic
        activities = re.findall(r'{(.*?)}', lesson_part)
        for act in activities:
            st.markdown(f'<div class="activity-box">🏃 Activity: {act}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Interactive Quiz Section ---
    st.divider()
    st.header("🧠 Knowledge Challenge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", quiz_part, re.DOTALL)
    
    if not q_blocks:
        st.info("Generating questions... please wait.")
    else:
        for i, (q_raw, correct, expl) in enumerate(q_blocks):
            qid = f"q_{i}"
            with st.container():
                st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
                st.write(f"**Question {i+1}:** {q_raw.split('A)')[0].strip()}")
                opts = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
                if opts:
                    ans = st.radio(f"Select your answer for Q{i+1}:", opts, key=f"ans_{i}")
                    if st.button(f"Submit Q{i+1}", key=f"btn_{i}"):
                        is_correct = ans[0] == correct.strip()
                        if qid not in st.session_state.quiz_results:
                            st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                            if is_correct: st.session_state.score += 20
                            st.rerun()
                    if qid in st.session_state.quiz_results:
                        res = st.session_state.quiz_results[qid]
                        if res["correct"]: st.success("Correct! Well done.")
                        else: st.error(f"Not quite. The correct answer is {res['ans']}. {res['expl']}")
                st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.score >= 100:
        st.balloons()
        st.success("🏆 Mastery Unlocked! You've completed the lesson perfectly.")
