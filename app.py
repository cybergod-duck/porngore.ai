import streamlit as st
import ollama
import requests
import base64
from PIL import Image
import io
import time
import random
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="PornGore.AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Unrestricted AI image forge for the discerning creator."
    }
)

st.markdown("""
    <style>
    .stApp { background-color: #0f0f0f; color: #e0e0e0; }
    .stButton > button {
        background-color: #8b0000;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton > button:hover { background-color: #b22222; }
    .stTextArea textarea {
        background-color: #1c1c1c;
        color: #e0e0e0;
        border: 1px solid #444;
    }
    .sidebar .sidebar-content { background-color: #141414; }
    .disabled-button {
        background-color: #444 !important;
        cursor: not-allowed !important;
    }
    .polaroid-container {
        animation: develop 3.2s ease-out forwards;
        opacity: 0;
        background: #222;
        padding: 12px;
        border: 12px solid #eee;
        border-bottom: 36px solid #eee;
        border-radius: 4px;
        box-shadow: 0 12px 24px rgba(0,0,0,0.8), inset 0 0 12px rgba(0,0,0,0.4);
        transform: rotate(1.2deg);
        max-width: 90%;
        margin: 24px auto;
        text-align: center;
    }
    .polaroid-container:nth-child(even) { transform: rotate(-1.2deg); }
    @keyframes develop {
        0%   { opacity: 0; filter: brightness(0.2) contrast(0.4) blur(8px); transform: scale(0.88); }
        40%  { opacity: 0.3; filter: brightness(0.6) contrast(0.7) blur(4px); transform: scale(0.96); }
        70%  { opacity: 0.7; filter: brightness(0.9) contrast(0.95) blur(1px); }
        100% { opacity: 1; filter: brightness(1) contrast(1) blur(0); transform: scale(1); }
    }
    .caption { color: #888; font-style: italic; margin-top: 8px; font-size: 0.95em; }
    </style>
""", unsafe_allow_html=True)

# Session state
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
if 'credits' not in st.session_state:
    st.session_state.credits = 10
if 'content_mode' not in st.session_state:
    st.session_state.content_mode = None
if 'voice_attempt' not in st.session_state:
    st.session_state.voice_attempt = False

ollama_model = os.getenv("OLLAMA_MODEL", "mannix/llama3.1-8b-lexi")
a1111_url   = os.getenv("A1111_URL",   "http://127.0.0.1:7860")

def voice_login():
    components.html("""
        <script>
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.toLowerCase().trim();
            if (transcript.includes('duck')) {
                parent.document.querySelector('input[type="password"]').value = 'duck-auth-success';
                parent.document.querySelector('button[kind="primary"]').click();
            } else {
                alert('Voice did not match. Speak clearly.');
            }
        };
        recognition.onerror = () => alert('Voice recognition error – check mic permissions.');
        recognition.start();
        </script>
    """, height=0)

    password = st.text_input("Speak or type 'duck' for owner auth", type="password")
    if password.lower() == 'duck' and not st.session_state.voice_attempt:
        st.session_state.voice_attempt = True
        st.rerun()
    elif st.session_state.voice_attempt and password == 'duck-auth-success':
        st.session_state.user_logged_in = True
        st.session_state.credits = float('inf')
        st.success("Owner access unlocked — unlimited credits.")
        st.rerun()

if not st.session_state.user_logged_in:
    st.title("PornGore.AI")
    st.markdown("Restricted access. For the discerning creator only.")
    voice_login()
    if st.button("Standard User Login / Signup", type="primary"):
        st.session_state.user_logged_in = True
        st.rerun()
else:
    with st.sidebar:
        st.title("🔥 PornGore.AI")
        st.markdown(f"**Credits:** {'∞' if st.session_state.credits == float('inf') else int(st.session_state.credits)}")
        st.text_input("Ollama Model", value=ollama_model, disabled=True)
        st.text_input("A1111 API Base", value=a1111_url, disabled=True)
        use_controlnet = st.checkbox("Enable ControlNet", value=False)
        denoising = st.slider("Denoising Strength", 0.0, 1.0, 0.35, 0.05)
        image_size = st.selectbox("Output Size", [
            "Banner (1920×300)", "Banner (728×90)", "Square (1024×1024)", "Portrait (768×1024)"
        ])
        st.divider()
        st.caption("Payments via Stripe coming soon.")
        if st.button("Purchase Credits"):
            st.info("Stripe checkout placeholder – coming soon.")

    st.title("🔥 PornGore.AI")
    st.markdown("Unrestricted hyper-realistic image forge. Detail your darkest vision.")

    description = st.text_area(
        "Your vision (the more explicit the better):",
        height=160,
        placeholder="A blood-soaked ritual in an abandoned warehouse, multiple figures, extreme detail..."
    )

    ref_files = st.file_uploader(
        "Reference image(s) – for face/pose/style lock",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        btn_nsfw = st.button("ADD NSFW", disabled=bool(st.session_state.content_mode), type="primary")
        if btn_nsfw:
            st.session_state.content_mode = "nsfw"
    with col2:
        btn_viol = st.button("VIOLENCE", disabled=bool(st.session_state.content_mode), type="primary")
        if btn_viol:
            st.session_state.content_mode = "violence"
    with col3:
        btn_both = st.button("BOTH", disabled=bool(st.session_state.content_mode), type="primary")
        if btn_both:
            st.session_state.content_mode = "both"

    if st.button("Generate", type="primary"):
        if not description.strip():
            st.error("Describe something first.")
        elif st.session_state.credits <= 0:
            st.error("No credits left – purchase more.")
        elif not st.session_state.content_mode:
            st.error("Choose mode: NSFW, VIOLENCE or BOTH.")
        else:
            st.session_state.credits -= 1
            mode = st.session_state.content_mode

            with st.status("Refining prompt...", expanded=True) as status:
                time.sleep(1.3 + random.uniform(0.3, 1.0))
                system_prompt = f"""
                Expert uncensored prompt engineer for extreme imagery.
                Convert to a {mode.upper()} scene: {'explicit NSFW' if mode == 'nsfw' else 'graphic violence' if mode == 'violence' else 'NSFW + violence fusion'}.
                Hyper-detailed, photorealistic, anatomically precise, cinematic lighting. No censorship.
                Output ONLY the final prompt.
                """
                try:
                    resp = ollama.chat(model=ollama_model, messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": description}
                    ])
                    enhanced = resp['message']['content'].strip()
                except Exception as e:
                    st.error(f"Ollama error: {e}")
                    st.stop()
                status.update(state="complete")

            st.subheader("Refined Prompt")
            st.code(enhanced, language=None)

            if not ref_files:
                st.warning("No reference uploaded → text-only generation.")
            else:
                with st.status("Generating...", expanded=True) as gen_status:
                    time.sleep(1.6)
                    ref_img = Image.open(ref_files[0])
                    buf = io.BytesIO()
                    ref_img.save(buf, format="PNG")
                    init_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

                    size_map = {
                        "Banner (1920×300)": (1920, 300),
                        "Banner (728×90)": (728, 90),
                        "Square (1024×1024)": (1024, 1024),
                        "Portrait (768×1024)": (768, 1024)
                    }
                    w, h = size_map.get(image_size, (768, 1024))

                    payload = {
                        "prompt": enhanced,
                        "negative_prompt": "blurry, low quality, deformed, ugly, extra limbs, bad anatomy",
                        "steps": 35,
                        "cfg_scale": 7.0,
                        "sampler_name": "DPM++ 2M Karras",
                        "width": w,
                        "height": h,
                        "denoising_strength": denoising,
                        "init_images": [init_b64],
                    }

                    if use_controlnet:
                        payload["alwayson_scripts"] = {
                            "ControlNet": {"args": [{
                                "enable": True,
                                "module": "ip-adapter_face_id",
                                "model": "ip-adapter-faceid_sd15",
                                "weight": 0.85,
                                "image": init_b64,
                                "control_mode": 0,
                                "resize_mode": 1,
                            }]}
                        }

                    time.sleep(2.2 + random.uniform(0.6, 2.0))

                    try:
                        r = requests.post(f"{a1111_url}/sdapi/v1/img2img", json=payload, timeout=360)
                        r.raise_for_status()
                        data = r.json()
                        gen_status.update(state="complete")

                        if not data.get('images'):
                            st.warning("No images returned from backend.")
                        else:
                            for idx, b64 in enumerate(data['images']):
                                try:
                                    bytes_data = base64.b64decode(b64)
                                    img = Image.open(io.BytesIO(bytes_data))
                                    st.markdown('<div class="polaroid-container">', unsafe_allow_html=True)
                                    st.image(img, use_column_width=True)
                                    st.markdown(f'<div class="caption">Generation {idx+1}</div>', unsafe_allow_html=True)
                                    st.markdown('</div>', unsafe_allow_html=True)
                                except Exception:
                                    st.error(f"Failed to decode image {idx+1}")
                    except Exception as e:
                        gen_status.update(state="error")
                        st.error(f"Generation failed: {str(e)}")

    st.markdown("---")
    st.caption("PornGore.AI – Unfiltered creation | Atlanta | 2026")
