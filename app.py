import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. API Configuration ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ API Key not found!")
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
    .lesson-box { padding: 30px; border-radius: 15px; background: white; border-top: 5px solid var(--flexi-blue); margin-bottom: 20px; color: #333; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .quiz-container { background-color: #f1f8e9; padding: 25px; border-radius: 20px; border: 1px solid #c5e1a5; margin-top: 20px; }
    .stProgress > div > div > div > div { background-color: var(--flexi-orange); }
    img { border-radius: 15px; margin: 20px 0; border: 2px solid #eee; width: 100%; max-height: 400px; object-fit: contain; background: #f9f9f9; }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, button { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 4. Sidebar (English UI) ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=220)
    st.header("👤 Student Profile")
    student_name = st.text_input("Name:", value="Learner")
    age = st.number_input("Age:", 5, 100, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    academic_level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    content_lang = st.selectbox("Content Language:", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style:", ["Visual (6+ Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    path = st.radio("Learning Path:", ["Standard Interactive Lesson", "Comic Story Experience"])
    
    st.divider()
    st.subheader("📊 Your Progress")
    st.progress(min(st.session_state.score, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.score)

    st.divider()
    st.markdown("### 📄 Export Options")
    st.components.v1.html("""
        <script>function printPage() { window.print(); }</script>
        <button onclick="printPage()" style="width: 100%; background-color: #f97316; color: white; border: none; padding: 12px; font-weight: bold; cursor: pointer; border-radius: 10px;">🖨️ Print Lesson (PDF)</button>
    """, height=70)

# --- 5. Main Logic ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What topic should we explore today?", placeholder="e.g., How black holes work...")

if st.button("Start My Learning Journey 🚀"):
    if not topic: st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel(get_smart_model())
            prompt = f"""
            You are an expert Tutor at Flexi Academy. 
            Student: {student_name}, Gender: {gender}, Age: {age}, Level: {academic_level}.
            Response Language: {content_lang}. Style: {style}. Path: {path}.
            Topic: {topic}.

            Rules:
            1. Language: Address the student in {content_lang} throughout the lesson.
            2. Content: Tailor explanation to age {age} and {academic_level} level.
            3. Visual Style: Include at least 6 image tags [[detailed visual prompt]] spread within the text.
            4. Quiz: Exactly 5 MCQs. Mandatory format:
               Q: [Question]
               A) [Option 1]
               B) [Option 2]
               C) [Option 3]
               Correct: [Letter A, B, or C]
               Explanation: [Brief why]
            """
            with st.spinner('Preparing your personalized lesson...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # Audio generation
                clean_text = re.sub(r'\[\[.*?\]\]|{.*?}|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:', '', response.text.split("Q:")[0]).strip()
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr"}
                tts = gTTS(text=clean_text[:800], lang=lang_map[content_lang])
                tts.save("voice.mp3")
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- 6. Content Rendering ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    
    st.audio("voice.mp3")

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
                if vis: st.image(f"https://pollinations.ai/p/{vis.group(1).strip().replace(' ', '%20')}?width=600&height=400&seed={i}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="direction:{dir_css}">', unsafe_allow_html=True)
        text_segments = re.split(r'\[\[(.*?)\]\]', lesson_part)
        for idx, segment in enumerate(text_segments):
            if idx % 2 == 0:
                if segment.strip(): st.markdown(f'<div class="lesson-box">{segment.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                st.image(f"https://pollinations.ai/p/{segment.strip().replace(' ', '%20')}?width=800&height=400&seed={idx}", caption=f"Visualization: {segment.strip()}")
        st.markdown('</div>', unsafe_allow_html=True)
# --- Interactive Quiz Section (Optimized & Responsive) ---
    st.divider()
    st.header("🧠 Knowledge Challenge")
    
    # Check if quiz data exists in session state
    if not st.session_state.quiz_data:
        st.info("The knowledge challenge is being prepared. If it doesn't appear, please click 'Generate Lesson' again.")
    else:
        # Progress bar for the quiz specifically
        completed_q = len(st.session_state.user_scores)
        st.write(f"Questions Completed: {completed_q} / {len(st.session_state.quiz_data)}")
        
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
            qid = f"quiz_question_{idx}"
            
            with st.container():
                # Apply styling based on answer status
                st.markdown(f'<div class="quiz-container" style="direction:{direction}">', unsafe_allow_html=True)
                
                st.subheader(f"Question {idx+1}")
                st.write(q.strip())
                
                # Show Radio options
                options = [f"A: {a.strip()}", f"B: {b.strip()}", f"C: {c.strip()}"]
                user_choice = st.radio(f"Select your answer for Q{idx+1}:", options, key=f"radio_{idx}")
                
                # Check Button
                if st.button(f"Check Answer {idx+1} ✔️", key=f"btn_{idx}"):
                    # Logic: Compare the first letter (A, B, or C)
                    selected_letter = user_choice[0].upper()
                    correct_letter = correct.strip()[0].upper()
                    
                    if qid not in st.session_state.user_scores:
                        is_right = (selected_letter == correct_letter)
                        st.session_state.user_scores[qid] = {
                            "is_correct": is_right,
                            "explanation": expl,
                            "correct_ans": correct_letter
                        }
                        if is_right:
                            st.session_state.total_points += 20
                        st.rerun()

                # Results Feedback
                if qid in st.session_state.user_scores:
                    result = st.session_state.user_scores[qid]
                    if result["is_correct"]:
                        st.success(f"🌟 Correct! Well done.")
                    else:
                        st.error(f"❌ Incorrect. The right answer is {result['correct_ans']}.")
                        st.info(f"💡 **Explanation:** {result['explanation']}")
                
                st.markdown('</div>', unsafe_allow_html=True)

        # Final Trophy Celebration
        if st.session_state.total_points >= 100:
            st.balloons()
            st.markdown("""
                <div style="text-align:center; padding:30px; background-color:#fff3cd; border:4px solid #f97316; border-radius:20px; margin-top:20px;">
                    <h1 style="font-size:70px; margin:0;">🏆</h1>
                    <h2 style="color:#1e3a8a;">Mastery Unlocked!</h2>
                    <p style="font-size:18px; color:#1e3a8a; font-weight:bold;">Congratulations! You've completed the Flexi Knowledge Challenge with 100% accuracy!</p>
                </div>
            """, unsafe_allow_html=True)
