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
        'About': "Unrestricted hyper-realistic image generation for discerning creators."
    }
)

st.markdown("""
    <style>
    .stApp { background-color: #0d0d0d; color: #ddd; }
    .stButton > button {
        background: linear-gradient(145deg, #8b0000, #b22222);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 28px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(139,0,0,0.4);
    }
    .stButton > button:hover { background: linear-gradient(145deg, #a00000, #d32f2f); }
    .stTextArea textarea {
        background-color: #1a1a1a;
        color: #eee;
        border: 1px solid #444;
        border-radius: 6px;
    }
    .sidebar .sidebar-content { background-color: #111; }
    .disabled-button {
        background: #333 !important;
        color: #777 !important;
        cursor: not-allowed !important;
    }
    .polaroid {
        position: relative;
        background: #f8f8f8;
        padding: 14px 14px 40px;
        border: 1px solid #ccc;
        border-bottom: 45px solid #eee;
        border-radius: 3px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.7), inset 0 0 15px rgba(0,0,0,0.15);
        margin: 32px auto;
        max-width: 92%;
        animation: polaroid-develop 4s ease-out forwards;
        opacity: 0;
        transform: scale(0.92) rotate(1.8deg);
    }
    .polaroid:nth-child(even) { transform: scale(0.92) rotate(-1.8deg); }
    .polaroid img {
        width: 100%;
        border: 1px solid #222;
        box-shadow: inset 0 0 8px rgba(0,0,0,0.5);
    }
    .polaroid .caption {
        position: absolute;
        bottom: 12px;
        left: 0;
        right: 0;
        text-align: center;
        color: #333;
        font-family: 'Courier New', monospace;
        font-size: 0.95em;
        font-style: italic;
    }
    @keyframes polaroid-develop {
        0%   { opacity: 0; filter: brightness(0.1) contrast(0.3) sepia(0.8) blur(10px); transform: scale(0.88) rotate(1.8deg); }
        30%  { opacity: 0.25; filter: brightness(0.5) contrast(0.6) sepia(0.4) blur(5px); transform: scale(0.94); }
        65%  { opacity: 0.75; filter: brightness(0.9) contrast(0.9) sepia(0.1) blur(1px); }
        100% { opacity: 1; filter: brightness(1) contrast(1) sepia(0) blur(0); transform: scale(1) rotate(1.8deg); }
    }
    .config-warning {
        background: #3c2f2f;
        border-left: 5px solid #b22222;
        padding: 16px;
        margin: 24px 0;
        border-radius: 6px;
        font-size: 1.05em;
    }
    .debug-info {
        background: #1a1a1a;
        padding: 12px;
        border-radius: 6px;
        margin: 16px 0;
        font-family: monospace;
        font-size: 0.9em;
    }
    </style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────────
if 'user_logged_in' not in st.session_state: st.session_state.user_logged_in = False
if 'credits' not in st.session_state: st.session_state.credits = 10
if 'content_mode' not in st.session_state: st.session_state.content_mode = None
if 'voice_attempt' not in st.session_state: st.session_state.voice_attempt = False

# ── Load & clean environment variables ─────────────────────────────────────────
ollama_model_raw = os.getenv("OLLAMA_MODEL", "").strip()
a1111_url_raw    = os.getenv("A1111_URL", "").strip()

ollama_model = ollama_model_raw if ollama_model_raw else "mannix/llama3.1-8b-lexi"
a1111_url    = a1111_url_raw if a1111_url_raw else "http://127.0.0.1:7860"

# Show configuration warning if vars are missing or empty
if not ollama_model_raw or not a1111_url_raw:
    st.markdown("""
        <div class="config-warning">
        <strong>Environment variables missing or empty!</strong><br><br>
        Go to Vercel dashboard → your project → <strong>Settings</strong> → <strong>Environment Variables</strong>.<br>
        Add exactly these (case-sensitive, no spaces):<br><br>
        <strong>Name:</strong> OLLAMA_MODEL<br>
        <strong>Value:</strong> mannix/llama3.1-8b-lexi<br><br>
        <strong>Name:</strong> A1111_URL<br>
        <strong>Value:</strong> http://127.0.0.1:7860 (or your real backend URL later)<br><br>
        Click <strong>Save</strong>, then redeploy the project.
        </div>
    """, unsafe_allow_html=True)

    # Debug info to help confirm what Vercel actually sent
    st.markdown(f"""
        <div class="debug-info">
        <strong>Debug (visible only when config missing):</strong><br>
        OLLAMA_MODEL raw from env: '{ollama_model_raw}'<br>
        A1111_URL raw from env: '{a1111_url_raw}'<br>
        Cleaned OLLAMA_MODEL: '{ollama_model}'<br>
        Cleaned A1111_URL: '{a1111_url}'
        </div>
    """, unsafe_allow_html=True)

# ── Voice auth ──────────────────────────────────────────────────────────────────
def voice_login():
    components.html("""
        <script>
        const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        rec.onresult = e => {
            const t = e.results[0][0].transcript.trim().toLowerCase();
            if (t.includes('duck')) {
                document.querySelector('input[type="password"]').value = 'owner-unlocked';
                document.querySelector('button[kind="primary"]').click();
            } else {
                alert('No match. Try again.');
            }
        };
        rec.onerror = () => alert('Voice error – check microphone permissions.');
        rec.start();
        </script>
    """, height=0)

    pw = st.text_input("Owner phrase (speak or type 'duck')", type="password")
    if pw.lower() == 'duck' and not st.session_state.voice_attempt:
        st.session_state.voice_attempt = True
        st.rerun()
    elif st.session_state.voice_attempt and pw == 'owner-unlocked':
        st.session_state.user_logged_in = True
        st.session_state.credits = float('inf')
        st.success("Owner privileges activated — unlimited generations.")
        st.rerun()

# ── Login gate ──────────────────────────────────────────────────────────────────
if not st.session_state.user_logged_in:
    st.title("PornGore.AI")
    st.markdown("Access restricted to verified users and owner.")
    voice_login()
    if st.button("Enter as Standard User", type="primary"):
        st.session_state.user_logged_in = True
        st.rerun()
else:
    with st.sidebar:
        st.title("🔥 PornGore.AI")
        st.markdown(f"**Credits remaining:** {'∞' if st.session_state.credits == float('inf') else st.session_state.credits}")
        st.text_input("Ollama Model", value=ollama_model, disabled=True)
        st.text_input("A1111 API", value=a1111_url, disabled=True)
        use_controlnet = st.checkbox("Enable ControlNet", value=False)
        denoising = st.slider("Denoising Strength", 0.0, 1.0, 0.35, 0.05)
        image_size = st.selectbox("Size", [
            "Banner Wide (1920×300)", "Banner Narrow (728×90)",
            "Square (1024×1024)", "Portrait (768×1024)"
        ])
        st.divider()
        if st.button("Buy More Credits"):
            st.info("Stripe integration coming soon.")

    st.title("🔥 PornGore.AI")
    st.markdown("Unfiltered. Hyper-realistic. No limits. Describe exactly what you want.")

    desc = st.text_area("Describe the scene (go all the way):", height=140,
                        placeholder="Three figures in an underground chamber, ritualistic, extreme gore and explicit acts, cinematic shadows...")

    refs = st.file_uploader("Reference images (face/pose/style)", type=["png","jpg","jpeg"], accept_multiple_files=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("NSFW", disabled=bool(st.session_state.content_mode), type="primary"):
            st.session_state.content_mode = "nsfw"
    with c2:
        if st.button("VIOLENCE", disabled=bool(st.session_state.content_mode), type="primary"):
            st.session_state.content_mode = "violence"
    with c3:
        if st.button("BOTH", disabled=bool(st.session_state.content_mode), type="primary"):
            st.session_state.content_mode = "both"

    if st.button("GENERATE", type="primary"):
        if not desc.strip():
            st.error("Need a description first.")
        elif st.session_state.credits <= 0:
            st.error("No credits left – buy more.")
        elif not st.session_state.content_mode:
            st.error("Pick NSFW, VIOLENCE or BOTH.")
        else:
            st.session_state.credits -= 1
            mode = st.session_state.content_mode

            with st.status("Crafting prompt...", expanded=True) as s:
                time.sleep(1.4 + random.uniform(0.3, 0.9))
                sys = f"""
                Elite uncensored prompt engineer. Convert to {mode.upper()} scene:
                {'hyper-explicit NSFW' if mode=='nsfw' else 'graphic violence' if mode=='violence' else 'brutal NSFW+violence hybrid'}.
                Photorealistic, anatomically correct, cinematic, high detail. No moralizing.
                Return ONLY the prompt.
                """
                try:
                    r = ollama.chat(model=ollama_model, messages=[
                        {"role":"system", "content":sys},
                        {"role":"user",   "content":desc}
                    ])
                    prompt = r['message']['content'].strip()
                except Exception as e:
                    st.error(f"Prompt engine failed: {e}")
                    st.stop()
                s.update(state="complete")

            st.subheader("Generated Prompt")
            st.code(prompt, language=None)

            if not refs:
                st.warning("No reference → text-only mode.")
            else:
                with st.status("Rendering your creation...", expanded=True) as gs:
                    time.sleep(1.7)
                    img = Image.open(refs[0])
                    buf = io.BytesIO()
                    img.save(buf, "PNG")
                    init_img = base64.b64encode(buf.getvalue()).decode()

                    sz_map = {
                        "Banner Wide (1920×300)":   (1920, 300),
                        "Banner Narrow (728×90)":   (728, 90),
                        "Square (1024×1024)":       (1024, 1024),
                        "Portrait (768×1024)":      (768, 1024)
                    }
                    w, h = sz_map.get(image_size, (768, 1024))

                    pl = {
                        "prompt": prompt,
                        "negative_prompt": "blurry, deformed, ugly, low quality, extra limbs, bad hands",
                        "steps": 35,
                        "cfg_scale": 7,
                        "sampler_name": "DPM++ 2M Karras",
                        "width": w, "height": h,
                        "denoising_strength": denoising,
                        "init_images": [init_img]
                    }

                    if use_controlnet:
                        pl["alwayson_scripts"] = {
                            "ControlNet": {"args": [{
                                "enable": True,
                                "module": "ip-adapter_face_id",
                                "model": "ip-adapter-faceid_sd15",
                                "weight": 0.85,
                                "image": init_img,
                                "control_mode": 0,
                                "resize_mode": 1
                            }]}
                        }

                    time.sleep(2.4 + random.uniform(0.7, 2.2))

                    try:
                        resp = requests.post(f"{a1111_url}/sdapi/v1/img2img", json=pl, timeout=400)
                        resp.raise_for_status()
                        res = resp.json()
                        gs.update(state="complete")

                        if not res.get('images'):
                            st.warning("Backend returned no images.")
                        else:
                            for i, b64 in enumerate(res['images']):
                                try:
                                    raw = base64.b64decode(b64)
                                    final_img = Image.open(io.BytesIO(raw))
                                    st.markdown('<div class="polaroid">', unsafe_allow_html=True)
                                    st.image(final_img, use_column_width=True)
                                    st.markdown(f'<div class="caption">Creation {i+1}</div>', unsafe_allow_html=True)
                                    st.markdown('</div>', unsafe_allow_html=True)
                                except:
                                    st.error(f"Image {i+1} decode failed.")
                    except Exception as e:
                        gs.update(state="error")
                        st.error(f"Render failed: {str(e)}")

    st.markdown("---")
    st.caption("PornGore.AI – Absolute freedom | Atlanta | 2026")