import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. Secure API Configuration ---
# يتم جلب المفتاح من Secrets لضمان عدم حظره من جوجل
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.warning("⚠️ API Key not found in Secrets. Using manual entry for testing...")
    MY_API_KEY = "YOUR_MANUAL_KEY_HERE" # ضع مفتاحك هنا فقط إذا كنت تجرّب محلياً

genai.configure(api_key=MY_API_KEY)

st.set_page_config(page_title="Flexy AI Learning Platform", layout="wide", page_icon="🏆")

# --- 2. UI Styling (CSS) ---
st.markdown("""
    <style>
    .lesson-box { padding: 25px; border-radius: 15px; border-left: 10px solid #1a73e8; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; color: #2c3e50; }
    .quiz-container { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .trophy-box { text-align: center; padding: 30px; background-color: #fff3cd; border: 3px solid #ffeeba; border-radius: 20px; margin-top: 30px; animation: bounce 2s infinite; }
    @keyframes bounce { 0%, 100% {transform: translateY(0);} 50% {transform: translateY(-10px);} }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Smart Model Resolver ---
def get_model_name():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest"]
        for p in priority:
            if p in available: return p
        return available[0]
    except:
        return "models/gemini-1.5-flash"

# --- 4. Helper Functions ---
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

# --- 5. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 6. Sidebar (Personalization Criteria) ---
with st.sidebar:
    st.header("⚙️ Personalization")
    student_name = st.text_input("Student Name:", value="Learner")
    age = st.number_input("Student Age:", min_value=5, max_value=90, value=12)
    gender = st.selectbox("Gender:", ["Male", "Female", "Other"])
    content_lang = st.selectbox("Content Language:", ["English", "العربية", "Français", "Deutsch"])
    academic_level = st.selectbox("Academic Level:", ["Elementary", "Middle School", "High School", "University"])
    learning_style = st.selectbox("Learning Style:", ["Visual (Images)", "Auditory (Listening)", "Reading/Writing", "Kinesthetic (Active)"])
    
    st.divider()
    output_format = st.radio("Output Format:", ["Standard Lesson", "Comic Story"])
    st.divider()
    st.metric("Total Score 🎯", st.session_state.score)
    st.divider()
    st.markdown("### 🖨️ Export Tools")
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#1a73e8;color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-weight:bold;">🖨️ Save as PDF</button>""", height=60)

# --- 7. Main Interface ---
st.title("🌟 Flexy AI Smart Learning")
topic = st.text_area("What do you want to learn today?", placeholder="e.g., The life cycle of a butterfly...")

if st.button("Generate My Personalized Lesson 🚀"):
    if not topic:
        st.error("Please enter a topic first!")
    else:
        try:
            active_model = get_model_name()
            model = genai.GenerativeModel(active_model)
            
            prompt = f"""
            Task: Expert Academic Tutor.
            Target Student: {student_name}, Age: {age}, Gender: {gender}, Level: {academic_level}, Style: {learning_style}.
            Instruction: Provide the content ONLY in {content_lang}.
            Topic: {topic}.
            Format: {output_format}. 
            Requirements:
            1. Clear headers using ###.
            2. If lesson, include an image prompt in [[ ]].
            3. Include 4 MCQs at the end in this format:
               Q: [Question]
               A) [Option] B) [Option] C) [Option]
               Correct: [Letter]
               Explanation: [Brief note]
            """
            with st.spinner(f'Designing your lesson using {active_model}...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # Audio
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:600], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 8. Content Display ---
if st.session_state.lesson_data:
    content = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    # Display Video & Lesson
    v_url = get_youtube_video(topic, content_lang)
    if v_url: st.markdown(f'<iframe width="100%" height="500" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
    
    lesson_body = content.split("Q:")[0]
    img_match = re.search(r'\[\[(.*?)\]\]', lesson_body)
    if img_match: st.image(f"https://pollinations.ai/p/{img_match.group(1).replace(' ', '%20')}?width=1024&height=500")
    
    st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{lesson_body.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

    # --- 9. Interactive Quiz ---
    st.divider()
    st.header("🧠 Knowledge Check")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Question {i+1}:** {q_raw.split('A)')[0].strip()}")
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if options:
                choice = st.radio(f"Select your answer for Q{i+1}:", options, key=f"r_{i}")
                if st.button(f"Confirm Answer {i+1} ✔️", key=f"b_{i}"):
                    is_correct = choice[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("Correct! Well done.")
                    else: st.error(f"Incorrect. The right answer is {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 10. Trophy Award ---
    if st.session_state.score >= 40:
        st.balloons()
        st.markdown(f'<div class="trophy-box"><h1>🏆</h1><h2>Perfect Score, {student_name}!</h2><p>You have mastered this topic!</p></div>', unsafe_allow_html=True)
