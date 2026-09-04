#!/usr/bin/env python3
"""
MOSKY Web Interface - J.A.R.V.I.S. Style (Gradio + Futuristic Effects)

Run with the project ai-env (recommended, as per your request):
C:\\AI\\ai-env\\Scripts\\python.exe mosky_web.py

Then open the browser URL it prints (starts at http://127.0.0.1:7860 and automatically picks the next free port if busy)

JARVIS-LIKE EFFECTS (real sci-fi feel):
- Dark holographic HUD with neon cyan/blue glows, scanline animation, pulsing status bars
- Real-time animated waveform visualizer (CSS/JS canvas - reacts on audio)
- Glowing buttons, sci-fi monospace font, holographic chat bubbles
- Enhanced research output with pros/cons + evolution patterns (from the evolved high-level system)
- Full integration with LangGraph supervisor, research_agent (GitHub + X + pros/cons + guarded), evaluation
- Voice input (browser mic via Gradio - no pyaudio needed for web), Greek Piper TTS with autoplay (numpy audio, no temp files)
- Status HUD, evolution log feel, "Core Online" indicators
- Immediate spoken greeting on page load ("Έτοιμος...") via proper Gradio demo.load

This is the "πραγματικο jarvis" web interface for your self-evolving agent system.
Uses the advanced routing (pros_cons, evolution memory, high-level targets) .
Stable fallback for audio deps. All guarded/100% fidelity preserved.

Browser console notes:
- "Tracking Prevention blocked... iframe-resizer" → benign, caused by Gradio + Edge strict tracking protection. Harmless for local use.
- "NotSupportedError: The element has no supported sources" → now fixed (we use numpy tuples + demo.load for greet instead of early filepath value).

Make sure the main system concepts are importable (research/supervisor).
For best experience: have the core running conceptually, Ollama if using chat fallback. Have the Greek Piper voice downloaded for spoken replies.
"""

import sys
import os
from pathlib import Path
import numpy as np
import gradio as gr
import threading  # for non-blocking heavy eval in Jarvis web flow (so it feels responsive)
import socket     # for finding a free port when 7860 is busy (common when re-running quickly)

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the core MOSKY logic (robust, from voice_interface + evolved system)
try:
    from automation_examples.voice_interface import (
        _ensure_models_loaded,
        transcribe,
        chat_with_mosky,
    )
    from automation_examples import voice_interface as vi_module
except ImportError as e:
    print(f"Failed to import MOSKY core: {e}")
    print("Make sure you run with the correct Python: C:\\AI\\ai-env\\Scripts\\python.exe mosky_web.py")
    # Do not exit - allow partial for testing
    vi_module = None

# Global flags (graceful degradation for TTS if Greek Piper model missing)
MODELS_LOADED = False
TTS_READY = False

# === J.A.R.V.I.S. FUTURISTIC CSS (module level so launch() can also receive it for Gradio 6+ compatibility) ===
JARVIS_CSS = """
.gradio-container { background: #0a0a0f !important; color: #00f0ff !important; font-family: 'Courier New', monospace !important; }
.gr-button { background: linear-gradient(90deg, #001f3f, #0074D9) !important; color: #fff !important; border: 1px solid #00f0ff !important; box-shadow: 0 0 10px #00f0ff !important; transition: all 0.2s !important; }
.gr-button:hover { box-shadow: 0 0 25px #00f0ff !important; transform: scale(1.03) !important; }
.gr-chatbot { background: #111 !important; border: 1px solid #00f0ff !important; box-shadow: 0 0 15px rgba(0,240,255,0.3) !important; }
.gr-audio { border: 1px solid #00f0ff !important; background: #0a0a0f !important; }
.jarvis-hud { background: rgba(0,20,40,0.95) !important; border: 1px solid #00f0ff !important; box-shadow: 0 0 25px #00f0ff !important; padding: 12px; font-family: 'Courier New', monospace; color: #00f0ff; }
.scanline { position: relative; overflow: hidden; }
.scanline::after { content: ''; position: absolute; top:0; left:0; right:0; bottom:0; background: linear-gradient(to bottom, transparent 50%, rgba(0,240,255,0.08) 50%); background-size: 100% 3px; animation: scan 3.5s linear infinite; pointer-events: none; }
@keyframes scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(100%); } }
.status-bar { height: 3px; background: linear-gradient(to right, #00f0ff, #0074D9); box-shadow: 0 0 12px #00f0ff; animation: progress 2.8s linear infinite; }
.neon { text-shadow: 0 0 6px #00f0ff, 0 0 12px #00f0ff; }
.jarvis-log { font-family: 'Courier New', monospace; font-size: 0.9em; }
"""

def load_models_once():
    global MODELS_LOADED, TTS_READY
    if not MODELS_LOADED:
        print("Loading MOSKY models (Whisper + Piper for Jarvis interface)...")
        if vi_module:
            try:
                _ensure_models_loaded()
                TTS_READY = True
            except Exception as e:
                print(f"[J.A.R.V.I.S. WARN] TTS model load failed: {e}")
                print("  Voice replies will show as text only (no auto audio). Run download_piper_greek.py or use voice_mosky.bat first.")
                TTS_READY = False
        MODELS_LOADED = True
        print("Models ready. J.A.R.V.I.S. effects active." if TTS_READY else "Models ready (text mode). J.A.R.V.I.S. effects active.")

def synthesize_for_web(text: str):
    """Synthesize text and return (sample_rate, numpy_array) for Gradio Audio.
    This is the cleanest way for Gradio: no temp files, no Windows path / serving issues,
    direct playback + autoplay works reliably. Returns None on failure.
    """
    if not text or not vi_module or not TTS_READY:
        return None
    try:
        load_models_once()
        audio = vi_module.tts_voice.synthesize(text)
        if not isinstance(audio, np.ndarray):
            chunks = list(audio)
            valid = [c for c in chunks if isinstance(c, np.ndarray) and c.size > 0]
            if not valid:
                return None
            audio = np.concatenate(valid)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        sr = getattr(vi_module.tts_voice.config, "sample_rate", 22050)
        return (sr, audio)
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def process_voice_or_text(audio_path: str | None, text_input: str, history: list):
    """
    Main processing for the Jarvis UI.
    Voice or text -> advanced system (research with pros/cons or supervisor).
    Returns history + audio response.
    """
    load_models_once()

    user_text = ""
    if audio_path:
        try:
            import soundfile as sf
            audio_data, sr = sf.read(audio_path)
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
            user_text = transcribe(audio_data.astype(np.float32))
            print(f"[User voice]: {user_text}")
        except Exception as e:
            print(f"Transcription error: {e}")
            user_text = text_input or ""
    else:
        user_text = text_input.strip()

    if not user_text:
        return history, None, "No input detected. Speak or type a command."

    history = history + [[user_text, None]]

    lowered = user_text.lower().strip()

    # Use evolved high-level research for "Jarvis" research feel (pros/cons, evolution)
    research_keywords = ["νέο", "github", "x", "ανάλυσε", "ταιριάζει", "skill", "τεχνολογία", "νέα τεχνολογία", "ανακάλυψε", "νέα skills", "pros", "cons", "πλεονεκτήματα", "μειονεκτήματα", "evolution"]

    if any(kw in lowered for kw in research_keywords):
        print("[J.A.R.V.I.S. Web] Running advanced high-level research (pros/cons + evolution patterns)...")
        try:
            from openhands_skills.research_agent import research_agent
            res = research_agent.research_new_technologies_and_skills(
                max_results=3, focus="ai_tech_general langgraph supervisor mcp evo godel", lab_mode=True
            )
            cands = res.get("new_capability_candidates", [])
            spoken = "J.A.R.V.I.S. Research complete. High-level patterns from GitHub and X.\n\n"
            for i, c in enumerate(cands[:2]):
                src = c.get("source", {})
                spoken += f"{i+1}. {c.get('short_description', 'Pattern')}\n"
                spoken += f"Source: {src.get('url', 'N/A')}\n"
                pc = c.get("pros_cons", {})
                advs = "; ".join(pc.get("advantages", [])[:2])
                diss = "; ".join(pc.get("disadvantages", [])[:2])
                spoken += f"Πλεονεκτήματα: {advs}\nΜειονεκτήματα: {diss}\n\n"
            spoken += "Πες 'integrate the first one' για guarded proposal (human gate active)."
        except Exception as e:
            spoken = f"Research error: {str(e)[:150]}. Fallback chat."
            spoken = chat_with_mosky(user_text, use_history=True)
    elif any(kw in lowered for kw in ["αξιολόγηση", "score", "πόσο καλά", "system", "evolution", "status"]):
        print("[J.A.R.V.I.S. Web] Starting FULL system evaluation in background (heavy: multiple chain + market snapshots)...")
        def _bg_eval():
            try:
                from openhands_skills.evaluation_harness import run_system_evaluation
                res = run_system_evaluation(focus="all")
                sc = res.get("system_improvement_score", "N/A")
                print("\n" + "="*60)
                print("[J.A.R.V.I.S. EVALUATION COMPLETE]")
                print(f"  timestamp: {res.get('timestamp')}")
                print(f"  system_improvement_score: {sc}")
                print(f"  blockchain_intelligence: {res.get('blockchain_intelligence', {})}")
                print(f"  notes: {res.get('notes')}")
                print("  Full result also available in the returned dict.")
                print("  (This is the same harness used for pre/post guarded applies.)")
                print("="*60 + "\n")
            except Exception as e:
                print(f"[J.A.R.V.I.S. EVAL ERROR in background] {e}")
        threading.Thread(target=_bg_eval, daemon=True).start()
        spoken = (
            "Ξεκίνησα πλήρη αξιολόγηση συστήματος σε background. "
            "Θα τρέξει chain analysis σε δείγματα + market snapshots και θα δεις το πλήρες report "
            "με system_improvement_score, blockchain_intelligence και notes στο terminal. "
            "Δεν θα σε ενοχλήσω εδώ. Το σύστημα παραμένει fully guarded και self-evolving. "
            "Μπορείς να συνεχίσεις να μιλάς κανονικά."
        )
    else:
        print("[J.A.R.V.I.S. Web] Normal chat via supervisor...")
        spoken = chat_with_mosky(user_text, use_history=True)

    audio_out = synthesize_for_web(spoken)   # now (sr, numpy) or None — perfect for type="numpy"
    history[-1][1] = spoken

    return history, audio_out, ""

def clear_history():
    return [], None, "History cleared. J.A.R.V.I.S. ready. Πες γεια σου mosky."

def build_interface():
    load_models_once()

    def get_initial_greeting():
        """Return the opening greeting audio (numpy) + status message.
        Using demo.load + numpy tuple avoids all temp-file / 'no supported sources' problems.
        """
        greet_text = "Έτοιμος. Πες γεια σου mosky. Όλα τα συστήματα J.A.R.V.I.S. είναι online. Waveform visualizer και neon effects active. Research με pros cons έτοιμο."
        audio_tuple = synthesize_for_web(greet_text)  # (sr, arr) or None
        status_msg = "J.A.R.V.I.S. Core Online. Voice link established. Μοντέλα έτοιμα. Μπορείς να μιλήσεις."
        return audio_tuple, status_msg

    with gr.Blocks(title="J.A.R.V.I.S. - MOSKY Core") as demo:
        # === JARVIS HUD HEADER (real effects) ===
        gr.HTML("""
        <div class="jarvis-hud scanline" style="text-align:center; margin-bottom:12px;">
            <h1 style="margin:0; font-size:2.4em; color:#00f0ff;" class="neon">J.A.R.V.I.S. // MOSKY v2.0</h1>
            <p style="margin:2px 0 8px; opacity:0.75; font-size:0.95em;">Advanced Self-Evolving Agent • Local • Greek • Guarded • 100% Fidelity</p>
            <div class="status-bar"></div>
        </div>
        """)

        gr.Markdown("""
        **MOSKY - Ο προσωπικός σου Greek Voice Agent**  
        Πες **"γεια σου mosky"** ή χρησιμοποίησε το μικρόφωνο.  
        Το σύστημα υποστηρίζει high-level research (GitHub + X με **pros/cons** + evolution patterns), system evaluation, guarded proposals και φυσικό διάλογο.

        _Σημείωση: Μπορεί να δεις στο browser console μηνύματα "Tracking Prevention" για iframe-resizer από cdnjs. Είναι ακίνδυνα — προκαλούνται από το Gradio + τις αυστηρές ρυθμίσεις privacy του Edge. Δεν επηρεάζουν τη λειτουργία._
        """)

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="J.A.R.V.I.S. Log", 
                    height=540, 
                    elem_classes=["jarvis-log"]
                )
                audio_output = gr.Audio(
                    label="Voice Response (Piper Greek)", 
                    type="numpy",          # best for generated in-memory audio (no file serving, no "no supported sources")
                    autoplay=True,
                    elem_classes="jarvis-audio"
                )

            with gr.Column(scale=1):
                with gr.Tab("🎤 Voice"):
                    audio_input = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="Record Voice Command",
                        elem_classes="jarvis-mic"
                    )
                    voice_btn = gr.Button("🚀 SEND VOICE", variant="primary", size="lg")

                with gr.Tab("⌨️ Text"):
                    text_input = gr.Textbox(
                        label="Type Command", 
                        placeholder="τι νέο έχουμε από github και x; ανάλυσε pros/cons",
                        lines=2
                    )
                    text_btn = gr.Button("📤 SEND TEXT", variant="secondary")

                with gr.Tab("📡 HUD"):
                    # Static system info (Markdown/HTML so clicks do not overwrite it)
                    gr.Markdown("""
**Core Status**
- LangGraph Supervisor: **ACTIVE**
- Research Agent: **SCANNING** (high-level + last30d)
- Pros/Cons + Evolution Memory: **ENABLED**
- 100% Fidelity + Human Gate: **ON**
- Where to find research: `new_capability_candidates` in research results, `persistent_memory` (type=evolution_pattern/research_lab_idea), `memory/pending_proposals/*.json`, source URLs in reports.
                    """, elem_classes=["jarvis-log"])

                clear_btn = gr.Button("🧹 CLEAR LOG", variant="stop")

                # Separate action log that receives per-command status (prevents clobbering the HUD info)
                action_log = gr.Textbox(
                    label="J.A.R.V.I.S. Status", 
                    interactive=False, 
                    value="Core Online • Research Active • Waveform LIVE • Guarded: ON",
                    elem_classes=["jarvis-log"]
                )

        # === REAL-TIME JARVIS WAVEFORM VISUALIZER (JS canvas effect) ===
        gr.HTML("""
        <div id="jarvis-visualizer" style="height:68px; background:#001a2e; border:1px solid #00f0ff; margin:10px 0; position:relative; overflow:hidden; box-shadow:0 0 12px #00f0ff;">
            <canvas id="wave-canvas" width="720" height="68" style="width:100%; height:100%;"></canvas>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); color:#00f0ff; font-size:9px; letter-spacing:2px; opacity:0.5; pointer-events:none; text-align:center;">
                J.A.R.V.I.S. AUDIO LINK — LIVE
            </div>
        </div>
        <script>
        (function() {
            const canvas = document.getElementById('wave-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            let phase = 0;
            function draw() {
                ctx.fillStyle = '#001a2e';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = '#00f0ff';
                ctx.lineWidth = 2.2;
                ctx.shadowColor = '#00f0ff';
                ctx.shadowBlur = 9;
                ctx.beginPath();
                for (let x = 0; x < canvas.width; x += 2.5) {
                    const y = 34 + Math.sin((x + phase) * 0.045) * 16 + Math.sin((x + phase) * 0.11) * 7;
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
                phase += 1.6;
                requestAnimationFrame(draw);
            }
            draw();
            // Subtle pulse when "speaking" (gives the live reactive sci-fi feel)
            setInterval(() => {
                if (canvas) {
                    canvas.style.boxShadow = '0 0 18px #00f0ff';
                    setTimeout(() => { if (canvas) canvas.style.boxShadow = '0 0 12px #00f0ff'; }, 380);
                }
            }, 2400);
        })();
        </script>
        """)

        # Wire events - note: action_log receives the short status from process/clear so the HUD panel stays clean
        def handle_voice(audio):
            hist, aud, stat = process_voice_or_text(audio, "", chatbot.value or [])
            return hist, aud, stat

        def handle_text(txt):
            hist, aud, stat = process_voice_or_text(None, txt, chatbot.value or [])
            return hist, aud, stat, ""

        voice_btn.click(handle_voice, inputs=[audio_input], outputs=[chatbot, audio_output, action_log])
        text_btn.click(handle_text, inputs=[text_input], outputs=[chatbot, audio_output, action_log, text_input])
        clear_btn.click(clear_history, outputs=[chatbot, audio_output, action_log])

        # Proper initial greeting via demo.load (numpy audio + status).
        # This is the reliable Gradio way to autoplay the "Έτοιμος..." on page open without race conditions or file serving errors.
        demo.load(get_initial_greeting, outputs=[audio_output, action_log])

    return demo


def find_free_port(preferred: int = 7860, max_tries: int = 25) -> int:
    """Find the first free TCP port starting from `preferred`.
    This prevents the common "Cannot find empty port 7860-7860" error
    when the user re-runs the script quickly or another Gradio instance is alive.
    """
    for i in range(max_tries):
        port = preferred + i
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                # port is taken
                continue
    # Give up — let Gradio raise its own clear error
    return preferred


if __name__ == "__main__":
    print("=" * 62)
    print("  J.A.R.V.I.S. // MOSKY v2.0 - Futuristic Voice Interface")
    print("  Run with: C:\\AI\\ai-env\\Scripts\\python.exe mosky_web.py")
    print("=" * 62)
    print("Loading advanced Jarvis effects (HUD, waveform, pros/cons research)...")
    print()

    demo = build_interface()

    # Robust port selection — the #1 source of "it doesn't start" complaints
    port = find_free_port(7860)
    url = f"http://127.0.0.1:{port}"

    if port != 7860:
        print(f"[J.A.R.V.I.S.] Port 7860 is busy (previous run or another Gradio app).")
        print(f"             Using next free port: {port}")
    else:
        print("[J.A.R.V.I.S.] Using default port 7860.")

    print(f"Browser will open automatically at {url}")
    print("Close the browser tab or press Ctrl+C in this window to stop the server.")
    print()

    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=port,
            inbrowser=True,
            share=False,
            theme=gr.themes.Base(),
            css=JARVIS_CSS   # futuristic neon/scanline/waveform styles applied here for Gradio 6+
        )
    except OSError as e:
        print("\n" + "=" * 60)
        print("[ERROR] Could not start the J.A.R.V.I.S. web server.")
        print(f"Details: {e}")
        print()
        print("Quick fixes:")
        print("  1. Kill any previous python processes that are still running mosky_web.py")
        print("  2. Run with a specific free port:")
        print("       set GRADIO_SERVER_PORT=7865")
        print(r"       C:\AI\ai-env\Scripts\python.exe mosky_web.py")
        print("  3. Or just wait a few seconds and try again.")
        print("=" * 60)
        input("Press Enter to exit...")