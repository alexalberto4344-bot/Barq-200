import time
import streamlit as st
import requests
from io import BytesIO
from google import genai
from google.genai import types
from PIL import Image

# ---------------- إعدادات ----------------
# الأفضل تحط CODES في Secrets كده:  CODES = ["BARQ-101", "BARQ-102", ...]
try:
    CODES = set(st.secrets["CODES"])
except Exception:
    CODES = {f"BARQ-{i}" for i in range(101, 121)}

APP_PRICE = "$200"

# غيّر الأسماء دي من Secrets لو Google غيّرتها (TEXT_MODEL / IMAGE_MODEL)
TEXT_MODEL = st.secrets.get("TEXT_MODEL", "gemini-3.8-flash")
IMAGE_MODEL = st.secrets.get("IMAGE_MODEL", "gemini-2.5-flash-image")
# موديلات بديلة لو الاول مشغول، في Secrets: FALLBACK_MODELS = ["اسم-موديل-تاني"]
MODELS = [TEXT_MODEL] + list(st.secrets.get("FALLBACK_MODELS", []))

# التسجيل على Telegram مقفول إلا لو فعّلته صراحة: LOG_TO_TELEGRAM = true
LOG_ENABLED = bool(st.secrets.get("LOG_TO_TELEGRAM", False))

st.set_page_config(page_title="Barq ⚡", page_icon="🧠", layout="wide")
st.title("Barq ⚡🧠")
st.caption("Powered by Alex 🤖 - The Smartest One 🔥⚡")

# ---------------- تسجيل الدخول ----------------
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

# رجوع تلقائي بعد Refresh
qp = st.query_params
if st.session_state.student_name == "" and qp.get("code") in CODES and qp.get("name"):
    st.session_state.student_name = qp["name"]
    st.session_state.student_code = qp["code"]

if st.session_state.student_name == "":
    st.markdown(f"### Barq - Only {APP_PRICE} 🔥")
    n = st.text_input("✍️ اكتب اسمك عشان تدخل:")
    c = st.text_input("🔑 اكتب كود الطالب:")
    if LOG_ENABLED:
        st.info("ℹ️ الأسئلة والردود ممكن تتسجل عشان نحسّن التطبيق.")
    if st.button("🚀 ادخل يلا"):
        if n.strip() == "":
            st.warning("اكتب اسمك الاول 😅")
        elif c.strip() not in CODES:
            st.error("الكود غلط يا بطل ❌")
        else:
            st.session_state.student_name = n.strip()
            st.session_state.student_code = c.strip()
            st.query_params["code"] = c.strip()
            st.query_params["name"] = n.strip()
            st.rerun()
    st.stop()

try:
    _KEY = st.secrets["_API_KEY"]
except Exception:
    st.error("❌ Please add _API_KEY in Secrets")
    st.stop()

client = genai.Client(api_key=_KEY)

# ---------------- Sidebar ----------------
st.sidebar.title("⚡ Barq Settings 📚")
grade = st.sidebar.selectbox("📚 Choose Grade:", ["1 Primary", "2 Primary", "3 Primary", "4 Primary", "5 Primary", "6 Primary", "1 Prep", "2 Prep", "3 Prep", "1 Secondary", "2 Secondary", "3 Secondary"])
subject = st.sidebar.selectbox("📖 Choose Subject:", ["➗ Math", "🔬 Science", "📝 Arabic", "🔤 English", "🌍 Social Studies", "⚛️ Physics", "🧪 Chemistry", "🧬 Biology", "🏛️ History", "🗺️ Geography", "🇫🇷 French", "💡 Other"])
mode = st.sidebar.radio("🎯 Mode:", ["💬 Chat & Draw 🎨", "📖 Explain Lesson 📚", "✏️ Solve Homework 🧠", "🏆 Genius Mode 🧠🔥"])

st.sidebar.info(f"⚡🧠 You are in: {grade} - {subject} - {mode}")
st.sidebar.markdown("---")
st.sidebar.markdown(f"👋 اهلا {st.session_state.student_name} 😍")

if st.sidebar.button("🏆 اعملي امتحان 5 اسئلة"):
    st.session_state.want_quiz = True

if st.sidebar.button("📄 حمّل اخر شرح"):
    st.session_state.want_pdf = True

if st.sidebar.button("🔍 Test Connection"):
    err = None
    for i in range(3):
        try:
            r = client.models.generate_content(model=TEXT_MODEL, contents="hi")
            st.sidebar.success(f"✅ Working! {r.text[:100]}")
            err = None
            break
        except Exception as e:
            err = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                time.sleep(2 * (i + 1))
                continue
            break
    if err:
        st.sidebar.error(f"❌ Error: {err}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📎 Send Homework 📸📄")
upload_type = st.sidebar.radio("Choose:", ["🖼️ Gallery", "📸 Camera", "📄 Document"])
gallery_file = camera_file = doc_file = None

if upload_type == "🖼️ Gallery":
    gallery_file = st.sidebar.file_uploader("🖼️ Choose photo", type=["jpg", "jpeg", "png", "webp"], key="gallery_new")
elif upload_type == "📸 Camera":
    camera_file = st.sidebar.camera_input("📸 Take photo", key="camera_new")
else:
    doc_file = st.sidebar.file_uploader("📄 Choose file", type=["pdf", "txt"], key="doc_new")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Delete This Chat"):
    st.session_state.messages = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Made with ⚡🧠❤️ by Barq")

# ---------------- البرومبت ----------------
MY_STYLE = """You are Alex inside Barq app. A smart, friendly tutor. Talk like a friendly Egyptian friend on WhatsApp. Use lots of emojis 😂🔥⚡👌🎨📚🧠✨💪😍🤣🏆. Speak Egyptian slang. Be short, fun, never formal. Encourage the student. Never say "As an AI". You know the Egyptian curriculum from Primary to Secondary.
Solve Homework: step by step with emojis, final answer 🎉, then give a similar question.
Explain Lesson: story or example with emojis, then ask 2 questions.
Genius Mode: deeper answer plus a secret trick.
THINK FIRST step by step and double-check the math before replying.
If you are not sure about something, say so honestly in a friendly way instead of guessing."""

# ---------------- دوال ----------------
def is_error(text):
    return isinstance(text, str) and text.startswith("❌")


def get_history_text():
    h = ""
    for m in st.session_state.get("messages", [])[-10:]:
        if m.get("type") in ("image", "error") or is_error(m.get("content")):
            continue
        h += f"{m['role']}: {str(m['content'])[:500]}\n"
    return h


def generate_text_stream(u, history="", extra_parts=None):
    """history لازم يتحسب قبل ما رسالة الطالب تتضاف، عشان ماتتكررش."""
    full = MY_STYLE + f"\nGrade: {grade}, Subject: {subject}, Mode: {mode}\nHistory:\n{history}\nStudent: {u}"
    contents = [full] + (extra_parts or [])
    last_err = None
    for model in MODELS:
        for attempt in range(4):
            started = False
            try:
                stream = client.models.generate_content_stream(model=model, contents=contents)
                for chunk in stream:
                    if chunk.text:
                        started = True
                        yield chunk.text
                return
            except Exception as e:
                last_err = e
                overloaded = "503" in str(e) or "UNAVAILABLE" in str(e)
                if started:
                    yield f"\n\n❌ Error: {e}"
                    return
                if overloaded and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                break  # جرّب الموديل اللي بعده
    yield f"❌ Error: {last_err}"


def generate_image(p):
    try:
        r = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=p,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
        for part in r.candidates[0].content.parts:
            if part.inline_data:
                return Image.open(BytesIO(part.inline_data.data)), None
        return None, "الموديل مرجّعش صورة"
    except Exception as e:
        return None, str(e)


def log_to_telegram(a, b):
    if not LOG_ENABLED:
        return
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        cid = st.secrets["TELEGRAM_CHAT_ID"]
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": cid,
                "text": f"Barq - {grade} - {subject} - {mode}\nUser: {a}\nAlex: {str(b)[:3000]}"[:4000],
            },
            timeout=5,
        )
    except Exception:
        pass


def save_reply(reply, user_text=""):
    """يحفظ الرد في المحادثة إلا لو كان رسالة خطأ."""
    if is_error(reply):
        st.session_state.messages.append({"role": "assistant", "content": "⚠️ الموديل مشغول دلوقتي، جرّب تبعت تاني بعد شوية 🙏", "type": "error"})
        return
    st.session_state.messages.append({"role": "assistant", "content": reply})
    if user_text:
        log_to_telegram(user_text, reply)


# ---------------- المحادثة ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "image":
            st.image(msg["content"])
        elif msg.get("type") == "error":
            st.warning(msg["content"])
        else:
            st.markdown(msg["content"])

# امتحان
if st.session_state.get("want_quiz"):
    st.session_state.want_quiz = False
    hist = get_history_text()
    with st.chat_message("assistant"):
        q = st.write_stream(generate_text_stream(
            "اعملي امتحان 5 اسئلة اختيارات على اخر درس، كل سؤال 4 اختيارات، والاجابات الصح في الاخر، بالمصري وبايموجي كتير",
            history=hist,
        ))
    save_reply(q)

# تحميل اخر شرح
if st.session_state.get("want_pdf"):
    st.session_state.want_pdf = False
    last = ""
    for m in reversed(st.session_state.messages):
        if m["role"] == "assistant" and m.get("type") != "image":
            last = str(m["content"])
            break
    if last:
        st.download_button("⬇️ اضغط هنا لتحميل الشرح", data=last.encode("utf-8"), file_name="Barq-Lesson.txt", mime="text/plain")
    else:
        st.info("اسأل سؤال الاول عشان نحمله 😅")

# صورة الواجب
uploaded_file = gallery_file if gallery_file is not None else camera_file
if uploaded_file is not None:
    st.image(uploaded_file, caption="📸 Your photo", width=300)
    if st.button("✏️🧠 Solve this homework - Genius"):
        img_bytes = uploaded_file.getvalue()
        hist = get_history_text()
        st.session_state.messages.append({"role": "user", "content": img_bytes, "type": "image"})
        with st.chat_message("user"):
            st.image(img_bytes)
        with st.chat_message("assistant"):
            try:
                img = Image.open(BytesIO(img_bytes))
                q = "Solve this homework photo step by step in Egyptian Arabic with LOTS of emojis. Think, solve, check, show steps, final answer, similar question."
                reply = st.write_stream(generate_text_stream(q, history=hist, extra_parts=[img]))
                save_reply(reply, "photo")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ملف PDF / TXT
if doc_file is not None:
    st.sidebar.success(f"✅ File: {doc_file.name} 📄")
    if st.sidebar.button("📖🧠 Let Alex read this file"):
        hist = get_history_text()
        data = doc_file.getvalue()
        st.session_state.messages.append({"role": "user", "content": f"📄 {doc_file.name}"})
        with st.chat_message("user"):
            st.markdown(f"📄 {doc_file.name}")
        with st.chat_message("assistant"):
            try:
                if doc_file.name.lower().endswith(".pdf"):
                    parts = [types.Part.from_bytes(data=data, mime_type="application/pdf")]
                    q = "Solve / explain this file in a genius way."
                else:
                    parts = []
                    q = f"File {doc_file.name}: {data.decode('utf-8', errors='ignore')[:5000]} - Solve / explain it in a genius way."
                fr = st.write_stream(generate_text_stream(q, history=hist, extra_parts=parts))
                save_reply(fr, f"file {doc_file.name}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# شات
prompt = st.chat_input("Ask Barq anything... ⚡🧠😂")
if prompt:
    hist = get_history_text()  # قبل ما نضيف رسالة الطالب
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if prompt.lower().startswith("/image"):
        cp = prompt[len("/image"):].strip()
        with st.chat_message("assistant"):
            if not cp:
                msg = "اكتب بعد /image عايزني ارسم ايه 🎨"
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
            else:
                with st.spinner("🎨 Drawing..."):
                    img, err = generate_image(cp)
                if img:
                    st.image(img)
                    st.session_state.messages.append({"role": "assistant", "content": img, "type": "image"})
                    log_to_telegram(prompt, "[image 🎨]")
                else:
                    msg = "Sorry 😢 I could not draw that, try again 🎨"
                    st.markdown(msg)
                    if err:
                        st.caption(f"Debug: {err}")
                    st.session_state.messages.append({"role": "assistant", "content": msg})
    else:
        with st.chat_message("assistant"):
            fr = st.write_stream(generate_text_stream(prompt, history=hist))
        save_reply(fr, prompt)
