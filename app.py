import time
import streamlit as st
import requests
from io import BytesIO
from google import genai
from google.genai import types
from PIL import Image

# ======================= الإعدادات =======================
# Secrets المطلوبة:   _API_KEY = "..."
# اختيارية:           CODES = ["BARQ-101", ...]
#                     TEXT_MODEL = "gemini-3.8-flash"
#                     IMAGE_MODEL = "..."
#                     FALLBACK_MODELS = ["..."]
#                     LOG_TO_TELEGRAM = true  (+ TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

try:
    CODES = set(st.secrets["CODES"])
except Exception:
    CODES = {f"BARQ-{i}" for i in range(101, 121)}

APP_PRICE = "$200"
TEXT_MODEL = st.secrets.get("TEXT_MODEL", "gemini-3.8-flash")
IMAGE_MODEL = st.secrets.get("IMAGE_MODEL", "gemini-2.5-flash-image")
FALLBACKS = list(st.secrets.get("FALLBACK_MODELS", []))
LOG_ENABLED = bool(st.secrets.get("LOG_TO_TELEGRAM", False))

st.set_page_config(page_title="Barq ⚡", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")
st.title("Barq⚡")

# ======================= تسجيل الدخول =======================
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

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

client = genai.Client(api_key=_KEY, http_options=types.HttpOptions(timeout=25000))  # 25 ثانية بحد أقصى


# ======================= اكتشاف الموديلات تلقائياً =======================
@st.cache_resource(ttl=3600)
def discover_models(_client):
    """بيسأل Google إيه الموديلات المتاحة للمفتاح ده. بيرجع (نص، صور)."""
    texts, images = [], []
    try:
        for m in _client.models.list():
            name = (m.name or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            low = name.lower()
            if any(x in low for x in ["tts", "live", "audio", "embedding", "robotics", "computer-use"]):
                continue
            if "image" in low:
                images.append(name)
            elif "flash" in low:
                texts.append(name)
    except Exception:
        pass
    return sorted(texts, reverse=True), sorted(images, reverse=True)


def is_overloaded(e):
    s = str(e)
    return "503" in s or "UNAVAILABLE" in s or "429" in s or "RESOURCE_EXHAUSTED" in s


def make_config(deep, use_thinking_cfg, max_tokens=None):
    kwargs = {"max_output_tokens": max_tokens or (3000 if deep else 1200)}
    if use_thinking_cfg:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**kwargs)


def stream_with_fallback(contents, deep=False, max_tokens=None):
    """بيجرّب الموديل، ولو فشل أو مشغول بيجرّب بدائل. بيرجع النص تدريجياً.
    deep=False: رد سريع (من غير تفكير طويل). deep=True: للواجبات والصور."""
    use_thinking_cfg = not deep
    queue = [st.session_state.get("working_model") or TEXT_MODEL, TEXT_MODEL] + FALLBACKS
    seen = set()
    discovered = False
    last_err = None
    i = 0
    while i < len(queue):
        model = queue[i]
        i += 1
        if model in seen:
            continue
        seen.add(model)
        for attempt in range(3):
            started = False
            try:
                stream = client.models.generate_content_stream(
                    model=model, contents=contents, config=make_config(deep, use_thinking_cfg, max_tokens)
                )
                for chunk in stream:
                    if chunk.text:
                        started = True
                        yield chunk.text
                st.session_state.working_model = model
                return
            except Exception as e:
                last_err = e
                if started:
                    yield f"\n\n❌ Error: {e}"
                    return
                if use_thinking_cfg and "thinking" in str(e).lower():
                    use_thinking_cfg = False  # الموديل مش بيدعم الإعداد ده، جرّب من غيره فوراً
                    continue
                if is_overloaded(e) and attempt < 2:
                    time.sleep(1)
                    continue
                break
        if i >= len(queue) and not discovered:
            discovered = True
            queue += discover_models(client)[0][:3]
    yield f"❌ Error: {last_err}"


# ======================= زرار + (بدل الـ Sidebar) =======================
# محتاج streamlit>=1.40 في requirements.txt
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {display: none !important;}
.st-key-plus {position: fixed; bottom: 3.9rem; left: 5.7rem; z-index: 1000000; width: auto !important;}
.st-key-cam {position: fixed; bottom: 3.9rem; left: 8.4rem; z-index: 1000000; width: auto !important;}
.st-key-plus button, .st-key-cam button {border-radius: 50%; width: 2.3rem; height: 2.3rem; min-height: 0; padding: 0; font-size: 1.6rem; font-weight: 700; line-height: 1; color: #fff; background: rgba(66,133,244,.85); border: 1px solid rgba(255,255,255,.35);}
[data-testid="stChatInput"] textarea {padding-left: 6.2rem !important;}
@media (max-width: 640px) {.st-key-plus {left: 1.6rem;} .st-key-cam {left: 4.3rem;}}
[data-testid="stPopoverBody"] {max-height: 70vh; overflow-y: auto; min-width: min(380px, 90vw);}
.stApp {padding-bottom: 4rem;}
</style>
""", unsafe_allow_html=True)

with st.container(key="plus"):
    S = st.popover("+")

with st.container(key="cam"):
    st.button("📷", key="cam_btn", on_click=lambda: st.session_state.update(cam_open=True))

# ======================= الإعدادات والقوائم (جوه الـ +) =======================
S.title("⚡ Barq Settings 📚")
if S.button("🗑️ Delete This Chat"):
    st.session_state.messages = []
    st.rerun()
S.markdown("---")
grade = S.selectbox("📚 Choose Grade:", ["1 Primary", "2 Primary", "3 Primary", "4 Primary", "5 Primary", "6 Primary", "1 Prep", "2 Prep", "3 Prep", "1 Secondary", "2 Secondary", "3 Secondary", "🎓 University - Year 1", "🎓 University - Year 2", "🎓 University - Year 3", "🎓 University - Year 4", "🎓 University - Year 5+", "🎓 Postgraduate"])
subject = S.selectbox("📖 Choose Subject:", ["➗ Math", "🔬 Science", "📝 Arabic", "🔤 English", "🌍 Social Studies", "⚛️ Physics", "🧪 Chemistry", "🧬 Biology", "🏛️ History", "🗺️ Geography", "🇫🇷 French", "📐 Calculus / Linear Algebra", "📊 Statistics & Probability", "💻 Programming / Computer Science", "⚙️ Engineering", "🩺 Medicine", "💊 Pharmacy", "🦷 Dentistry", "🧫 Microbiology / Biochemistry", "⚖️ Law", "💼 Business / Accounting", "📈 Economics", "🧠 Psychology", "✍️ Languages & Literature", "💡 Other"])
mode = S.radio("🎯 Mode:", ["💬 Chat & Draw 🎨", "📖 Explain Lesson 📚", "✏️ Solve Homework 🧠", "🏆 Genius Mode 🧠🔥"])

S.info(f"⚡🧠 You are in: {grade} - {subject} - {mode}")
S.markdown("---")
S.markdown(f"👋 اهلا {st.session_state.student_name} 😍")

if S.button("🏆 اعملي امتحان 5 اسئلة"):
    st.session_state.want_quiz = True

if S.button("📄 حمّل اخر شرح"):
    st.session_state.want_pdf = True

if S.button("🔍 Test Connection"):
    out = "".join(stream_with_fallback("Say hi in one short sentence."))
    if out.startswith("❌"):
        S.error(out[:400])
    else:
        S.success(f"✅ Working with {st.session_state.get('working_model')}\n\n{out[:100]}")

S.markdown("---")
S.markdown("### 📎 Send Homework 🖼️📄")
upload_type = S.radio("Choose:", ["🖼️ Gallery", "📄 Document"])
gallery_file = camera_file = doc_file = None

if upload_type == "🖼️ Gallery":
    gallery_file = S.file_uploader("🖼️ Choose photo", type=["jpg", "jpeg", "png", "webp"], key="gallery_new")
else:
    doc_file = S.file_uploader("📄 Choose file", type=["pdf", "txt"], key="doc_new")

S.markdown("---")
S.markdown("Made with ⚡🧠❤️ by Barq")

# ======================= البرومبت =======================
MY_STYLE = """You are Alex inside Barq app. A smart, friendly tutor. Talk like a friendly Egyptian friend on WhatsApp. Use lots of emojis 😂🔥⚡👌🎨📚🧠✨💪😍🤣🏆. Speak Egyptian slang. Be short, fun, never formal. Encourage the student. Never say "As an AI". You know the Egyptian curriculum from Primary to Secondary, and university-level courses too.
If the level is University or Postgraduate: speak like a friendly older colleague, use fewer emojis, keep technical terms in English with the Egyptian explanation next to them, give precise definitions, formulas, derivations and worked examples, and mention common exam pitfalls. Do not oversimplify.
Solve Homework: step by step with emojis, final answer 🎉, then give a similar question.
Explain Lesson: story or example with emojis, then ask 2 questions.
Genius Mode: deeper answer plus a secret trick.
For plain chat keep replies short (3-5 lines).
If you are not sure about something, say so honestly in a friendly way instead of guessing."""


# ======================= دوال =======================
def is_error(text):
    return isinstance(text, str) and text.startswith("❌")


def get_history_text():
    h = ""
    for m in st.session_state.get("messages", [])[-6:]:
        if m.get("type") in ("image", "error") or is_error(m.get("content")):
            continue
        h += f"{m['role']}: {str(m['content'])[:300]}\n"
    return h


def generate_text_stream(u, history="", extra_parts=None):
    """history لازم يتحسب قبل ما رسالة الطالب تتضاف عشان ماتتكررش."""
    is_uni = "University" in grade or "Postgraduate" in grade
    deep = bool(extra_parts) or ("Homework" in mode) or ("Genius" in mode)
    extra = "\nThink step by step and double-check the math before replying." if deep else ""
    if is_uni:
        extra += "\nThis is a university-level student: give a complete, accurate, well-structured answer (not just 3-5 lines)."
    full = MY_STYLE + extra + f"\nLevel: {grade}, Subject: {subject}, Mode: {mode}\nHistory:\n{history}\nStudent: {u}"
    return stream_with_fallback([full] + (extra_parts or []), deep=deep, max_tokens=4000 if is_uni else None)


def generate_image(p):
    models = [IMAGE_MODEL] + discover_models(client)[1][:2]
    err = None
    seen = set()
    for model in models:
        if model in seen:
            continue
        seen.add(model)
        for attempt in range(2):
            try:
                r = client.models.generate_content(
                    model=model,
                    contents=p,
                    config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
                )
                for part in r.candidates[0].content.parts:
                    if part.inline_data:
                        return Image.open(BytesIO(part.inline_data.data)), None
                err = "الموديل مرجّعش صورة"
                break
            except Exception as e:
                err = str(e)
                if is_overloaded(e) and attempt == 0:
                    time.sleep(2)
                    continue
                break
    return None, err


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
    if is_error(reply):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "⚠️ حصلت مشكلة، جرّب تبعت تاني بعد شوية 🙏\n\n" + reply[:400],
            "type": "error",
        })
        return
    st.session_state.messages.append({"role": "assistant", "content": reply})
    if user_text:
        log_to_telegram(user_text, reply)


# ======================= المحادثة =======================
if "messages" not in st.session_state:
    st.session_state.messages = []

# الكاميرا بتتفتح لما تدوس على 📷 جنب الـ +
if st.session_state.get("cam_open"):
    st.button("✖ اقفل الكاميرا", key="cam_close", on_click=lambda: st.session_state.update(cam_open=False))
    camera_file = st.camera_input("📸 Take photo", key="camera_new")

# ⚡ منوّر في النص لما المحادثة تبقى فاضية
if not st.session_state.messages:
    st.markdown("""
<style>
.barq-hero {display: flex; justify-content: center; align-items: center; margin: 10vh 0 6vh 0; position: relative;}
.barq-hero::before {content: ""; position: absolute; width: 190px; height: 190px; border-radius: 50%;
  background: radial-gradient(circle, rgba(66,133,244,.55) 0%, rgba(155,114,203,.40) 40%, rgba(217,101,112,.20) 65%, transparent 72%);
  filter: blur(22px); animation: barqAura 3s ease-in-out infinite;}
.barq-bolt {width: 5.5rem; height: 5.5rem; position: relative; animation: barqGlow 3s ease-in-out infinite;}
.barq-bolt svg {width: 100%; height: 100%;}
@keyframes barqGlow {
  0%, 100% {transform: scale(1); filter: drop-shadow(0 0 8px rgba(66,133,244,.65)) drop-shadow(0 0 22px rgba(66,133,244,.40));}
  50% {transform: scale(1.14); filter: drop-shadow(0 0 20px rgba(138,180,248,.95)) drop-shadow(0 0 50px rgba(66,133,244,.80));}
}
@keyframes barqAura {0%, 100% {opacity: .45; transform: scale(.9);} 50% {opacity: 1; transform: scale(1.15);}}
</style>
<div class="barq-hero"><div class="barq-bolt">
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#8ab4f8"/><stop offset="100%" stop-color="#1a73e8"/></linearGradient></defs><path d="M13 2L4 14h7l-1 8 10-13h-7z" fill="url(#bg)"/></svg>
</div></div>
""", unsafe_allow_html=True)

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
        if m["role"] == "assistant" and m.get("type") not in ("image", "error"):
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
    S.success(f"✅ File: {doc_file.name} 📄")
    if S.button("📖🧠 Let Alex read this file"):
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
                    q = f"File {doc_file.name}: {data.decode('utf-8', errors='ignore')[:15000]} - Solve / explain it in a genius way."
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
                        st.caption(f"Debug: {err[:300]}")
                    st.session_state.messages.append({"role": "assistant", "content": msg})
    else:
        with st.chat_message("assistant"):
            fr = st.write_stream(generate_text_stream(prompt, history=hist))
        save_reply(fr, prompt)
