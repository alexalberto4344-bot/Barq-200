import streamlit as st, requests
from io import BytesIO
from google import genai
from PIL import Image
CODES={"BARQ-101":"طالب 1","BARQ-102":"طالب 2","BARQ-103":"طالب 3","BARQ-104":"طالب 4","BARQ-105":"طالب 5","BARQ-106":"طالب 6","BARQ-107":"طالب 7","BARQ-108":"طالب 8","BARQ-109":"طالب 9","BARQ-110":"طالب 10","BARQ-111":"طالب 11","BARQ-112":"طالب 12","BARQ-113":"طالب 13","BARQ-114":"طالب 14","BARQ-115":"طالب 15","BARQ-116":"طالب 16","BARQ-117":"طالب 17","BARQ-118":"طالب 18","BARQ-119":"طالب 19","BARQ-120":"طالب 20"}
APP_PRICE="$200"
st.set_page_config(page_title="Barq ⚡",page_icon="🧠",layout="wide")
st.title("Barq ⚡🧠")
st.caption("Powered by Alex 🤖 - The Smartest One 🔥⚡")
if "student_name" not in st.session_state: st.session_state.student_name=""
if st.session_state.student_name=="":
    st.markdown(f"### Barq - Only {APP_PRICE} 🔥")
    n=st.text_input("✍️ اكتب اسمك عشان تدخل:")
    c=st.text_input("🔑 اكتب كود الطالب:")
    if st.button("🚀 ادخل يلا"):
        if n.strip()=="": st.warning("اكتب اسمك الاول 😅")
        elif c.strip() not in CODES: st.error("الكود غلط يا بطل ❌")
        else: st.session_state.student_name=n; st.session_state.student_code=c; st.rerun()
    st.stop()
try: _KEY=st.secrets["_API_KEY"]
except: st.error("❌ Please add _API_KEY in Secrets"); st.stop()
client=genai.Client(api_key=_KEY)
st.sidebar.title("⚡ Barq Settings 📚")
grade=st.sidebar.selectbox("📚 Choose Grade:",["1 Primary","2 Primary","3 Primary","4 Primary","5 Primary","6 Primary","1 Prep","2 Prep","3 Prep","1 Secondary","2 Secondary","3 Secondary"])
subject=st.sidebar.selectbox("📖 Choose Subject:",["➗ Math","🔬 Science","📝 Arabic","🔤 English","🌍 Social Studies","⚛️ Physics","🧪 Chemistry","🧬 Biology","🏛️ History","🗺️ Geography","🇫🇷 French","💡 Other"])
mode=st.sidebar.radio("🎯 Mode:",["💬 Chat & Draw 🎨","📖 Explain Lesson 📚","✏️ Solve Homework 🧠","🏆 Genius Mode 🧠🔥"])
st.sidebar.info(f"⚡🧠 You are in: {grade} - {subject} - {mode}")
st.sidebar.markdown("---")
st.sidebar.markdown(f"👋 اهلا {st.session_state.student_name} 😍")
if st.sidebar.button("🏆 اعملي امتحان 5 اسئلة"): st.session_state.want_quiz=True
if st.sidebar.button("📄 حمّل اخر شرح"): st.session_state.want_pdf=True
if st.sidebar.button("🔍 Test Connection"):
    try:
        r=client.models.generate_content(model="gemini-2.5-flash",contents="hi"); st.sidebar.success(f"✅ Working! {r.text[:100]}")
    except Exception as e: st.sidebar.error(f"❌ Error: {e}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📎 Send Homework 📸📄")
upload_type=st.sidebar.radio("Choose:",["🖼️ Gallery","📸 Camera","📄 Document"])
gallery_file=camera_file=doc_file=None
if upload_type=="🖼️ Gallery": gallery_file=st.sidebar.file_uploader("🖼️ Choose photo",type=["jpg","jpeg","png","webp"],key="gallery_new")
elif upload_type=="📸 Camera": camera_file=st.sidebar.camera_input("📸 Take photo",key="camera_new")
else: doc_file=st.sidebar.file_uploader("📄 Choose file",type=["pdf","txt"],key="doc_new")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Delete This Chat"): st.session_state.messages=[]; st.rerun()
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ⚡🧠❤️ by Barq")
MY_STYLE="""You are Alex inside Barq app. THE SMARTEST AI. Talk like friendly Egyptian friend on WhatsApp. ALWAYS lots of emojis 😂🔥⚡👌🎨📚🧠✨💪😍🤣🏆. Speak Egyptian slang. Start with tamam 😂, fahmtak 👌, aaash 🔥. Be short fun never formal. Encourage: aaash wallah 💪🔥. Never say As an AI. Know all Egyptian curriculum Primary to Secondary. Solve Homework: step by step emojis, final answer 🎉, give similar question. Explain Lesson: story example emojis, ask 2 questions. Genius Mode: deep answer, secret trick. THINK FIRST step by step, check, reply. Never say you dont know."""
def get_history_text():
    h=""
    for m in st.session_state.get("messages",[])[-10:]:
        if m.get("type")!="image": h+=f"{m['role']}: {str(m['content'])[:500]}\n"
    return h
def generate_text_stream(u):
    full=MY_STYLE+f"\nGrade: {grade}, Subject: {subject}, Mode: {mode}\nHistory:\n{get_history_text()}\nStudent: {u}"
    try:
        stream=client.models.generate_content_stream(model="gemini-2.5-flash",contents=full)
        for chunk in stream:
            if chunk.text: yield chunk.text
        return
    except Exception as e: print(e); yield f"❌ Error: {e}"
def generate_image(p):
    try:
        r=client.models.generate_content(model="gemini-2.5-flash",contents=p)
        for part in r.candidates[0].content.parts:
            if part.inline_data: return Image.open(BytesIO(part.inline_data.data))
    except: return None
    return None
def log_to_telegram(a,b):
    try:
        if "TELEGRAM_TOKEN" not in st.secrets: return
        token=st.secrets["TELEGRAM_TOKEN"]; cid=st.secrets["TELEGRAM_CHAT_ID"]
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",data={"chat_id":cid,"text":f"Barq - {grade} - {subject} - {mode}\nUser: {a}\nAlex: {str(b)[:3000]}"[:4000]},timeout=5)
    except: pass
if "messages" not in st.session_state: st.session_state.messages=[]
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("type")=="image": st.image(msg["content"])
        else: st.markdown(msg["content"])
if st.session_state.get("want_quiz"):
    st.session_state.want_quiz=False
    with st.chat_message("assistant"):
        q=st.write_stream(generate_text_stream("اعملي امتحان 5 اسئلة اختيارات على اخر درس، كل سؤال 4 اختيارات، والاجابات الصح في الاخر، بالمصري وبايموجي كتير"))
    st.session_state.messages.append({"role":"assistant","content":q})
if st.session_state.get("want_pdf"):
    st.session_state.want_pdf=False
    last=""
    for m in reversed(st.session_state.messages):
        if m["role"]=="assistant" and m.get("type")!="image": last=str(m["content"]); break
    if last: st.download_button("⬇️ اضغط هنا لتحميل الشرح",data=last.encode("utf-8"),file_name="Barq-Lesson.txt",mime="text/plain")
    else: st.info("اسأل سؤال الاول عشان نحمله 😅")
uploaded_file=gallery_file if gallery_file is not None else camera_file
if uploaded_file is not None:
    with st.chat_message("user"): st.image(uploaded_file,caption="📸 Your photo")
    if st.sidebar.button("✏️🧠 Solve this homework - Genius"):
        with st.chat_message("assistant"):
            with st.spinner("⚡🧠 Barq Genius is thinking..."):
                try:
                    img=Image.open(uploaded_file)
                    pr=MY_STYLE+f" Grade: {grade} - {subject}. Solve this homework photo step by step in Egyptian Arabic with LOTS of emojis. Think, solve, check, show steps, final answer, similar question."
                    res=client.models.generate_content(model="gemini-2.5-flash",contents=[pr,img]); reply=res.text; st.markdown(reply); st.session_state.messages.append({"role":"assistant","content":reply}); log_to_telegram("photo",reply)
                except Exception as e: st.error(f"❌ Error: {e}")
if doc_file is not None:
    st.sidebar.success(f"✅ File: {doc_file.name} 📄")
    if st.sidebar.button("📖🧠 Let Alex read this file"):
        with st.chat_message("assistant"):
            try:
                content=doc_file.read().decode(errors="ignore")[:5000]
                fr=st.write_stream(generate_text_stream(f"File {doc_file.name}: {content} - Solve / explain it genius way")); st.session_state.messages.append({"role":"assistant","content":fr}); log_to_telegram(f"file {doc_file.name}",fr)
            except Exception as e: st.error(f"❌ Error: {e}")
prompt=st.chat_input("Ask Barq anything... ⚡🧠😂")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    is_image=prompt.lower().startswith("/image") or "draw" in prompt.lower() or "generate image" in prompt.lower()
    if is_image:
        cp=prompt.replace("/image","").strip()
        with st.chat_message("assistant"):
            with st.spinner("🎨 Drawing..."):
                img=generate_image(cp)
                if img: st.image(img); st.session_state.messages.append({"role":"assistant","content":img,"type":"image"}); log_to_telegram(prompt,"[image 🎨]")
                else: msg="Sorry 😢 I could not draw that, try again 🎨"; st.markdown(msg); st.session_state.messages.append({"role":"assistant","content":msg})
    else:
        with st.chat_message("assistant"): fr=st.write_stream(generate_text_stream(prompt))
        st.session_state.messages.append({"role":"assistant","content":fr}); log_to_telegram(prompt,fr)
