import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- API Configuration ---
# Replace with your actual API key
MY_API_KEY = "AIzaSyDSkfYQjDM95v6Lp6M-ti7qR7mMQXkMfbw"
genai.configure(api_key=MY_API_KEY)

st.set_page_config(page_title="Flexy AI Learning Platform", layout="wide", page_icon="🏆")

# --- UI Styling (CSS) ---
st.markdown("""
    <style>
    .lesson-box { padding: 25px; border-radius: 15px; border-left: 10px solid #1a73e8; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; color: #2c3e50; }
    .comic-panel { border: 4px solid #000; padding: 15px; background: white; box-shadow: 8px 8px 0px #000; margin-bottom: 20px; }
    .caption-tag { background: #ffde59; color: black; padding: 5px 10px; font-weight: bold; border: 2px solid #000; margin-bottom: 10px; display: inline-block; }
    .dialogue-text { background: #f0f0f0; border-radius: 10px; padding: 10px; border-left: 5px solid #333; font-style: italic; margin-top: 10px; }
    .quiz-container { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .trophy-box { text-align: center; padding: 30px; background-color: #fff3cd; border: 3px solid #ffeeba; border-radius: 20px; margin-top: 30px; animation: bounce 2s infinite; }
    @keyframes bounce { 0%, 100% {transform: translateY(0);} 50% {transform: translateY(-10px);} }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, iframe, .no-print { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- Robust Model Loader (To fix 404 & 429 Errors) ---
def get_working_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Flash is prioritized for higher rate limits and better stability
        for target in ["1.5-flash", "gemini-pro", "1.0-pro"]:
            for m_name in available_models:
                if target in m_name:
                    return m_name
        return available_models[0]
    except Exception:
        return "models/gemini-1.5-flash-latest"

# --- Helper Functions ---
def get_youtube_video(query, lang):
    suffix = " educational" if lang != "العربية" else " تعليمي"
    try:
        query_string = urllib.parse.urlencode({"search_query": query + suffix})
        format_url = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r"watch\?v=(\S{11})", format_url.read().decode())
        if search_results: return "https://www.youtube.com/embed/" + search_results[0]
    except: return None

def clean_text_for_audio(text):
    text = re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:', '', text)
    text = re.sub(r'[^\w\s\u0621-\u064A.]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

# --- State Management ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- Sidebar (English UI with Full Criteria) ---
with st.sidebar:
    st.header("⚙️ Personalization")
    student_name = st.text_input("Student Name:", value="Learner")
    age = st.number_input("Age:", min_value=5, max_value=100, value=12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    
    # Language Selection for Content
    content_lang = st.selectbox("Language of Study:", ["English", "العربية", "Français", "Deutsch"])
    
    level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    learning_style = st.selectbox("Learning Style:", ["Visual", "Auditory", "Kinesthetic"])
    st.divider()
    output_format = st.radio("Output Format:", ["Standard Lesson", "Comic Story"])
    st.divider()
    st.metric("Total Score 🎯", st.session_state.score)
    st.divider()
    
    st.markdown("### 🖨️ Export Tools")
    print_btn_html = """<button onclick="window.print()" style="width: 100%; background-color: #1a73e8; color: white; padding: 12px; border: none; border-radius: 10px; cursor: pointer; font-weight: bold;">🖨️ Print or Save as PDF</button>"""
    st.components.v1.html(print_btn_html, height=70)

# --- Main Area ---
st.title("🌟 Flexy AI Smart Learning")
topic = st.text_area("What do you want to learn about?", placeholder="Enter a topic (e.g., How black holes are formed)")

if st.button("Generate My Lesson 🚀"):
    if not topic:
        st.error("Please enter a topic first!")
    else:
        try:
            working_model = get_working_model()
            model = genai.GenerativeModel(working_model)
            
            prompt = f"""
            System: You are an expert AI tutor. 
            Instruction: Provide the entire response ONLY in {content_lang}.
            Target Student: {student_name}, Age: {age}, Gender: {gender}, Level: {level}, Style: {learning_style}.
            
            Format:
            - If Lesson: Use ### for headers and include an image description in [[ ]].
            - If Comic: 4 Panels using (PANEL X, CAPTION, DIALOGUE, VISUAL description).
            
            Finally, include 4 Multiple Choice Questions (MCQs):
            Q: [Question]
            A) [Option]
            B) [Option]
            C) [Option]
            Correct: [Letter]
            Explanation: [Brief note]
            """
            with st.spinner(f'Using {working_model} to design your lesson in {content_lang}...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # Audio Generation
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:600], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e: st.error(f"API Error: {e}")

# --- Display Content ---
if st.session_state.lesson_data:
    raw_content = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    if "Comic" in output_format or "قصة" in output_format:
        st.subheader("🖼️ Educational Story Panels")
        panels = re.split(r'PANEL \d+', raw_content.split("Q:")[0])[1:]
        cols = st.columns(2)
        for i, p in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown(f'<div class="comic-panel" style="direction:{dir_css}">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', p, re.S)
                dia = re.search(r'DIALOGUE:(.*?)(?=VISUAL:|$)', p, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', p, re.S)
                if cap: st.markdown(f'<div class="caption-tag">🎬 {cap.group(1).strip()}</div>', unsafe_allow_html=True)
                if vis:
                    img_prompt = vis.group(1).strip().replace(' ', '%20')
                    st.image(f"https://pollinations.ai/p/comic%20style%20{img_prompt}?width=600&height=400&seed={i}")
                if dia: st.markdown(f'<div class="dialogue-text">💬 {dia.group(1).strip()}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.subheader("📖 Personalized Lesson Content")
        v_url = get_youtube_video(topic, content_lang)
        if v_url: st.markdown(f'<iframe width="100%" height="500" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
        
        lesson_body = raw_content.split("Q:")[0]
        img_match = re.search(r'\[\[(.*?)\]\]', lesson_body)
        if img_match:
            img_desc = img_match.group(1).replace(' ', '%20')
            st.image(f"https://pollinations.ai/p/{img_desc}?width=1024&height=500&model=flux")
            
        st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{re.sub(r"\[\[.*?\]\]", "", lesson_body).replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

    # --- Interactive Quiz Section ---
    st.divider()
    st.header("🧠 Test Your Knowledge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw_content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Question {i+1}:** {q_raw.split('A)')[0].strip()}")
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            
            if options:
                user_choice = st.radio(f"Choose your answer for Q{i+1}:", options, key=f"radio_{i}")
                if st.button(f"Check Answer ✔️", key=f"btn_{i}"):
                    is_correct = user_choice[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success(f"Well done! {res['expl']}")
                    else: st.error(f"Incorrect. The right answer was {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Final Achievement ---
    if st.session_state.score >= 40:
        st.balloons()
        st.markdown(f"""
            <div class="trophy-box">
                <h1 style="font-size: 80px;">🏆</h1>
                <h2 style="color: #856404;">Excellent Job, {student_name}!</h2>
                <p style="color: #856404; font-size: 18px;">You've completed the quiz with a perfect score! Keep up the great work.</p>
            </div>
        """, unsafe_allow_html=True)
