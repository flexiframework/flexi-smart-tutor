import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import uuid
import os

# =========================
# 1. API CONFIGURATION
# =========================
st.set_page_config(
    page_title="Flexi Academy AI Tutor",
    layout="wide",
    page_icon="🎓"
)

if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Gemini API key not found in Streamlit secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])


def get_smart_model():
    try:
        models = [
            m.name for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        for m in ["models/gemini-1.5-flash", "models/gemini-pro"]:
            if m in models:
                return m
        return models[0]
    except:
        return "models/gemini-1.5-flash"


# =========================
# 2. SESSION STATE
# =========================
defaults = {
    "lesson_data": None,
    "quiz_data": [],
    "user_scores": {},
    "total_points": 0,
    "audio_file": None
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================
# 3. STYLING
# =========================
st.markdown("""
<style>
:root {
  --flexi-blue: #1e3a8a;
  --flexi-orange: #f97316;
}
.lesson-box {
  padding: 30px;
  border-radius: 15px;
  background: white;
  border-top: 5px solid var(--flexi-blue);
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.quiz-container {
  background-color: #f1f8e9;
  padding: 25px;
  border-radius: 20px;
  border: 1px solid #c5e1a5;
  margin-bottom: 20px;
}
img {
  border-radius: 15px;
  margin: 15px 0;
  width: 100%;
  max-height: 400px;
  object-fit: contain;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 4. SIDEBAR
# =========================
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=220)
    st.header("👤 Student Profile")

    student_name = st.text_input("Name", "Learner")
    age = st.number_input("Age", 5, 18, 12)
    gender = st.selectbox("Gender", ["Male", "Female"])
    academic_level = st.selectbox("Academic Level", ["Beginner", "Intermediate", "Advanced"])
    content_lang = st.selectbox("Language", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style", [
        "Visual (6+ Images)",
        "Auditory (Deep Text)",
        "Kinesthetic (Activities)"
    ])
    path = st.radio("Learning Path", [
        "Standard Interactive Lesson",
        "Comic Story Experience"
    ])

    st.divider()
    st.metric("🎯 Flexi Points", st.session_state.total_points)
    st.progress(min(st.session_state.total_points, 100) / 100)


# =========================
# 5. QUIZ PARSER
# =========================
def parse_quiz(text):
    quiz = []
    matches = re.findall(
        r"Q:\s*(.*?)\nA\)\s*(.*?)\nB\)\s*(.*?)\nC\)\s*(.*?)\nCorrect:\s*([ABC])\nExplanation:\s*(.*?)(?=\nQ:|$)",
        text,
        re.S
    )
    for m in matches:
        quiz.append(m)
    return quiz


# =========================
# 6. MAIN UI
# =========================
st.title("🎓 Flexi Academy AI Tutor")

topic = st.text_area(
    "What topic would you like to learn today?",
    placeholder="e.g. How volcanoes erupt, Solar System, Algebra basics..."
)

if st.button("🚀 Start Learning"):
    if not topic.strip():
        st.error("Please enter a topic.")
    else:
        with st.spinner("Creating your personalized lesson..."):
            model = genai.GenerativeModel(get_smart_model())

            prompt = f"""
You are a professional AI tutor at Flexi Academy.

Student:
Name: {student_name}
Age: {age}
Level: {academic_level}
Language: {content_lang}
Learning Style: {style}
Path: {path}

Topic: {topic}

RULES:
1. Explain clearly for the student's age.
2. Use [[IMAGE PROMPT]] tags (minimum 6).
3. End with EXACTLY 5 MCQs in this format:

Q: Question
A) option
B) option
C) option
Correct: A
Explanation: short explanation
"""

            response = model.generate_content(prompt)
            st.session_state.lesson_data = response.text
            st.session_state.quiz_data = parse_quiz(response.text)
            st.session_state.user_scores = {}
            st.session_state.total_points = 0

            # Audio
            clean_text = re.sub(r"\[\[.*?\]\]", "", response.text.split("Q:")[0])
            lang_map = {"English": "en", "العربية": "ar", "Français": "fr"}

            audio_name = f"audio_{uuid.uuid4().hex}.mp3"
            gTTS(clean_text[:800], lang=lang_map[content_lang]).save(audio_name)
            st.session_state.audio_file = audio_name

            st.rerun()


# =========================
# 7. RENDER LESSON
# =========================
if st.session_state.lesson_data:
    direction = "rtl" if content_lang == "العربية" else "ltr"

    if st.session_state.audio_file:
        st.audio(st.session_state.audio_file)

    raw = st.session_state.lesson_data
    lesson_text = raw.split("Q:")[0]

    segments = re.split(r"\[\[(.*?)\]\]", lesson_text)

    st.markdown(f"<div style='direction:{direction}'>", unsafe_allow_html=True)

    for i, seg in enumerate(segments):
        if i % 2 == 0:
            if seg.strip():
                st.markdown(
                    f"<div class='lesson-box'>{seg.replace(chr(10), '<br>')}</div>",
                    unsafe_allow_html=True
                )
        else:
            img_url = f"https://pollinations.ai/p/{seg.replace(' ', '%20')}?width=800&height=400&seed={i}"
            st.image(img_url, caption=seg)

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # 8. QUIZ
    # =========================
    st.divider()
    st.header("🧠 Knowledge Challenge")

    for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
        qid = f"q_{idx}"

        with st.container():
            st.markdown(f"<div class='quiz-container' style='direction:{direction}'>", unsafe_allow_html=True)

            st.subheader(f"Question {idx+1}")
            st.write(q)

            options = [f"A) {a}", f"B) {b}", f"C) {c}"]
            choice = st.radio("Choose:", options, key=qid)

            if st.button("Check Answer ✔️", key=f"btn_{idx}"):
                selected = choice[0]
                if qid not in st.session_state.user_scores:
                    correct_flag = selected == correct
                    st.session_state.user_scores[qid] = correct_flag
                    if correct_flag:
                        st.session_state.total_points += 20
                    st.rerun()

            if qid in st.session_state.user_scores:
                if st.session_state.user_scores[qid]:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Wrong. Correct answer: {correct}")
                    st.info(f"💡 {expl}")

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.total_points >= 100:
        st.balloons()
        st.success("🏆 Congratulations! You mastered this lesson!")
