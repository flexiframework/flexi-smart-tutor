import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- إعدادات الحماية والأمان ---
# قراءة المفتاح من Streamlit Secrets (التي قمت بإعدادها)
if "MY_API_KEY" in st.secrets:
    api_key = st.secrets["MY_API_KEY"]
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ لم يتم العثور على مفتاح API في الإعدادات السرية (Secrets). يرجى التأكد من إضافة MY_API_KEY في لوحة تحكم Streamlit.")
    st.stop()

# إعداد الصفحة
st.set_page_config(page_title="المعلم الذكي التفاعلي", layout="wide", page_icon="🏆")

# تخصيص الواجهة بـ CSS
st.markdown("""
    <style>
    .main { background-color: #f0f4f8; }
    .lesson-box { padding: 30px; border-radius: 20px; border-right: 12px solid #1a73e8; background-color: #ffffff; box-shadow: 0 8px 30px rgba(0,0,0,0.05); color: #2c3e50; line-height: 1.8; margin-bottom: 20px; text-align: right; }
    .highlight-title { color: #1a73e8; font-weight: bold; background-color: #e8f0fe; padding: 8px 15px; border-radius: 10px; display: inline-block; margin-bottom: 10px; }
    .score-board { background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .badge-card { background-color: #ffffff; border: 2px solid #ffd700; padding: 5px 10px; border-radius: 10px; display: inline-block; margin: 5px; color: #1e3c72; font-weight: bold; }
    .question-box { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 15px; text-align: right; }
    .correct-msg { color: #155724; background-color: #d4edda; padding: 10px; border-radius: 8px; margin-top: 5px; }
    .wrong-msg { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 8px; margin-top: 5px; }
    .stButton>button { border-radius: 12px; font-weight: bold; width: 100%; transition: 0.3s; }
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
    st.markdown(f"### النقاط الحاليّة: `{st.session_state.score}`")
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
source_content = st.text_area("أدخل موضوع الدرس أو النص الأصلي:", height=100, placeholder="مثال: كيف تعمل البراكين؟ أو شرح قانون الجاذبية..")

if st.button("ابدأ رحلة التعلم 🚀"):
    if not source_content or not student_name:
        st.error("من فضلك أدخل اسمك وموضوع الدرس!")
    else:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            lang_map = {"العربية": "Arabic", "English": "English", "Français": "French", "Deutsch": "German"}
            prompt = f"""
            Role: Expert Personal Tutor. Create a comprehensive lesson for '{student_name}'. 
            Target Language: {lang_map[language]}, Student Gender: {gender}, Age: {age}, Level: {level}, Learning Style: {learning_style}.
            Content Topic: '{source_content}'
            
            Structure your response as follows:
            1. Personal Greeting: A warm welcome to {student_name}.
            2. Lesson Content: Deep explanation suitable for {learning_style} style. Use '###' for main section headers.
            3. Visual Prompt: Include an image description for an educational diagram inside double brackets [[like this]].
            4. Assessment: Exactly 4 Multiple Choice Questions.
               Format each question exactly as:
               Q: [The Question]
               A) [Option]
               B) [Option]
               C) [Option]
               Correct: [The Letter A or B or C]
               Explanation: [Why this is correct]
               
            Make sure the entire response is in {lang_map[language]}.
            """
            
            with st.spinner(f'جاري تصميم درس مخصص لك يا {student_name}... ⏳'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.answered = set()
                
                # توليد الصوت للشرح (قبل الأسئلة)
                lesson_text_only = st.session_state.lesson_data.split("Q:")[0]
                clean_audio_text = re.sub(r'\[\[.*?\]\]', '', lesson_text_only)
                lang_code = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}[language]
                tts = gTTS(text=clean_audio_text, lang=lang_code)
                tts.save("current_lesson.mp3")
                st.rerun()

        except Exception as e: 
            st.error(f"حدث خطأ في الاتصال: {e}")

# --- عرض المحتوى التعليمي ---
if st.session_state.lesson_data:
    content = st.session_state.lesson_data
    direction = "rtl" if language == "العربية" else "ltr"
    
    st.markdown(f'<div class="score-board"><h2>بطل اليوم: {student_name}</h2><h3>رصيدك الحالي: {st.session_state.score} نقطة</h3></div>', unsafe_allow_html=True)

    # 1. عرض الدرس
    st.markdown("### 📖 المحتوى التعليمي")
    parts = content.split("Q:")
    lesson_body = parts[0]
    
    if os.path.exists("current_lesson.mp3"):
        st.audio("current_lesson.mp3")
    
    # تنسيق العناوين داخل النص
    styled_text = lesson_body.replace("###", "<br><span class='highlight-title'>📌 ").replace("\n", "</span><br>")
    st.markdown(f'<div class="lesson-box" style="direction: {direction};">{styled_text}</div>', unsafe_allow_html=True)
    
    # 2. الصور والفيديو
    col1, col2 = st.columns(2)
    with col1:
        img_match = re.search(r'\[\[(.*?)\]\]', lesson_body)
        if img_match:
            img_query = img_match.group(1).replace(' ', '%20')
            st.image(f"https://pollinations.ai/p/{img_query}?width=800&height=600&model=flux", caption="رسم توضيحي ذكي للدرس")
    
    with col2:
        v_url = get_youtube_video(source_content, language)
        if v_url:
            st.markdown(f'<iframe width="100%" height="315" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

    # 3. قسم الأسئلة
    st.divider()
    st.header("🧠 اختبر فهمك")
    
    # استخراج الأسئلة باستخدام Regex
    q_pattern = r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)"
    all_questions = re.findall(q_pattern, content, re.DOTALL)
    
    for idx, (q_raw, correct_ans, explanation) in enumerate(all_questions):
        lines = q_raw.strip().split('\n')
        question_text = lines[0]
        choices = [l.strip() for l in lines if l.strip().startswith(('A)', 'B)', 'C)'))]
        
        st.markdown(f'<div class="question-box" style="direction: {direction};">', unsafe_allow_html=True)
        st.write(f"**س {idx+1}:** {question_text}")
        
        if choices:
            user_input = st.radio(f"اختر الإجابة الصحيحة (س{idx+1}):", choices, key=f"radio_{idx}")
            if st.button(f"تأكيد إجابة السؤال {idx+1}", key=f"check_{idx}"):
                if idx not in st.session_state.answered:
                    correct_letter = correct_ans.strip()
                    if user_input.startswith(correct_letter):
                        st.session_state.score += 10
                        st.success(f"إجابة صحيحة يا {student_name}! ✨ {explanation}")
                        if st.session_state.score >= (len(all_questions) * 10):
                            st.balloons()
                    else:
                        st.error(f"للأسف إجابة خاطئة. الإجابة الصحيحة هي {correct_letter}. {explanation}")
                    st.session_state.answered.add(idx)
                else:
                    st.info("لقد قمت بحل هذا السؤال بالفعل.")
        st.markdown('</div>', unsafe_allow_html=True)
