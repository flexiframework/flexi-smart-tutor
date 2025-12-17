import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- الإعدادات الثابتة ---
MY_API_KEY = "AIzaSyAz6ttWI1mpHMvjWYsW7ljfdOS7efBvM44"
genai.configure(api_key=MY_API_KEY)

# إعداد الصفحة
st.set_page_config(page_title="المعلم الذكي التفاعلي", layout="wide", page_icon="🏆")

# تخصيص الواجهة بـ CSS
st.markdown("""
    <style>
    .main { background-color: #f0f4f8; }
    .lesson-box { padding: 30px; border-radius: 20px; border-right: 12px solid #1a73e8; background-color: #ffffff; box-shadow: 0 8px 30px rgba(0,0,0,0.05); color: #2c3e50; line-height: 1.8; margin-bottom: 20px; }
    .highlight-title { color: #1a73e8; font-weight: bold; background-color: #e8f0fe; padding: 8px 15px; border-radius: 10px; display: inline-block; margin-bottom: 10px; }
    .score-board { background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .badge-card { background-color: #ffffff; border: 2px solid #ffd700; padding: 5px 10px; border-radius: 10px; display: inline-block; margin: 5px; color: #1e3c72; font-weight: bold; }
    .question-box { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 15px; }
    .correct-msg { color: #155724; background-color: #d4edda; padding: 10px; border-radius: 8px; margin-top: 5px; }
    .wrong-msg { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 8px; margin-top: 5px; }
    .stButton>button { border-radius: 12px; font-weight: bold; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- وظائف مساعدة ---
def get_youtube_video(query, language):
    suffix = " educational" if language != "العربية" else " تعليمي"
    try:
        query_string = urllib.parse.urlencode({"search_query": query + suffix})
        format_url = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r"watch\?v=(\S{11})", format_url.read().decode())
        if search_results: return "https://www.youtube.com/embed/" + search_results[0]
    except: return None

# --- نظام الذاكرة (Session State) ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'answered' not in st.session_state: st.session_state.answered = set()

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("🏆 لوحة الإنجازات")
    st.markdown(f"### النقاط: `{st.session_state.score}`")
    if st.session_state.score >= 30: st.markdown('<div class="badge-card">🥇 العبقري</div>', unsafe_allow_html=True)
    elif st.session_state.score >= 10: st.markdown('<div class="badge-card">🥈 المجتهد</div>', unsafe_allow_html=True)
    
    st.divider()
    st.header("⚙️ معايير التخصيص")
    student_name = st.text_input("اسم الطالب:", placeholder="أدخل اسمك هنا")
    language = st.selectbox("لغة الشرح:", ["العربية", "English", "Français", "Deutsch"])
    age = st.number_input("السن:", min_value=5, value=12)
    gender = st.selectbox("الجنس:", ["ذكر", "أنثى"])
    level = st.selectbox("المستوى الأكاديمي:", ["مبتدئ", "متوسط", "متقدم"])
    learning_style = st.selectbox("نمط المتعلم:", ["بصري (Visual)", "سمعي (Auditory)", "حركي (Kinesthetic)"])

# --- المنطقة الرئيسية ---
st.title("🌟 منصة التعلم الذكي الشخصية")
source_content = st.text_area("أدخل موضوع الدرس أو النص الأصلي:", height=100)

if st.button("ابدأ رحلة التعلم 🚀"):
    if not source_content or not student_name:
        st.error("من فضلك أدخل اسمك وموضوع الدرس!")
    else:
        try:
            model_list = genai.list_models()
            available_models = [m.name for m in model_list if 'generateContent' in m.supported_generation_methods]
            selected_model = next((m for m in available_models if "1.5-flash" in m), available_models[0])
            model = genai.GenerativeModel(selected_model)
            
            lang_map = {"العربية": "Arabic", "English": "English", "Français": "French", "Deutsch": "German"}
            prompt = f"""
            Personal Tutor Mode: Create a lesson for '{student_name}'. 
            Language: {lang_map[language]}, Gender: {gender}, Age: {age}, Level: {level}, Style: {learning_style}.
            Content: '{source_content}'
            Structure:
            1. Welcome Greet {student_name} personally.
            2. Lesson Body (based on {learning_style}). Use ### for headers.
            3. Image desc in [[ ]].
            4. 4 Questions total: Format EXACTLY:
               Q: [Question]
               A) [Opt]
               B) [Opt]
               C) [Opt]
               Correct: [Letter]
               Explanation: [Note]
            Ensure total response is in {lang_map[language]}.
            """
            
            with st.spinner(f'جاري تصميم درس خاص بـ {student_name}... ⏳'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.answered = set()
                
                # توليد الصوت (تنقية سريعة)
                clean_for_audio = re.sub(r'\[\[.*?\]\]', '', st.session_state.lesson_data.split("Q:")[0])
                clean_for_audio = re.sub(r'[^\w\s\u0621-\u064A]', '', clean_for_audio)
                lang_code = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}[language]
                tts = gTTS(text=clean_for_audio, lang=lang_code)
                tts.save("current_lesson.mp3")
                st.rerun()

        except Exception as e: st.error(f"خطأ: {e}")

# --- عرض الدرس والأسئلة التفاعلية ---
if st.session_state.lesson_data:
    content = st.session_state.lesson_data
    direction = "rtl" if language == "العربية" else "ltr"
    
    # لوحة النقاط
    st.markdown(f'<div class="score-board"><h2>لوحة إنجازات {student_name}</h2><h3>النقاط: {st.session_state.score}</h3></div>', unsafe_allow_html=True)

    # 1. الشرح
    st.markdown("### 📖 الدرس")
    lesson_body = content.split("Q:")[0]
    st.audio("current_lesson.mp3")
    
    display_text = lesson_body.replace("###", "<span class='highlight-title'>📌 ").replace("\n", "</span><br>")
    st.markdown(f'<div class="lesson-box" style="direction: {direction};">{display_text}</div>', unsafe_allow_html=True)
    
    # 2. الوسائط
    image_match = re.search(r'\[\[(.*?)\]\]', lesson_body)
    if image_match:
        st.image(f"https://pollinations.ai/p/{image_match.group(1).replace(' ', '%20')}?width=1024&height=1024&model=flux")
    
    video_url = get_youtube_video(source_content, language)
    if video_url:
        st.markdown(f'<iframe width="100%" height="500" src="{video_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

    # 3. الأسئلة التفاعلية
    st.divider()
    st.header("🧠 اختبار التحدي الذكي")
    questions = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(questions):
        q_text = q_raw.split("A)")[0].strip()
        options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
        
        st.markdown(f'<div class="question-box" style="direction: {direction};">', unsafe_allow_html=True)
        st.write(f"**س{i+1}: {q_text}**")
        
        if options:
            choice = st.radio(f"اختر إجابة س{i+1}", options, key=f"q_{i}")
            if st.button(f"تأكيد إجابة س{i+1}", key=f"btn_{i}"):
                if i not in st.session_state.answered:
                    if choice[0] == correct.strip():
                        st.session_state.score += 10
                        st.markdown(f'<div class="correct-msg">✅ رائع يا {student_name}! +10 نقاط. {expl}</div>', unsafe_allow_html=True)
                        if st.session_state.score >= (len(questions) * 10): st.balloons()
                    else:
                        st.markdown(f'<div class="wrong-msg">❌ إجابة خاطئة. الصحيح هو {correct}. {expl}</div>', unsafe_allow_html=True)
                    st.session_state.answered.add(i)
                else: st.warning("تمت الإجابة مسبقاً!")
        st.markdown('</div>', unsafe_allow_html=True)