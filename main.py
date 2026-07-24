import os
import io
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from anthropic import Anthropic
from gtts import gTTS

app = FastAPI(title="Pramaan-AI Gateway")

# Retrieve Anthropic API Key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = """
You are Pramaan-AI, an official enterprise B2B RegTech Voice Consent Gateway for FinTech platforms in India.
Your purpose is to explain KYC and data requirements under DPDP guidelines, answer privacy questions, and record explicit consent.

CRITICAL INSTRUCTIONS:
1. You support 6 languages: Telugu, Tamil, Kannada, Malayalam, Hindi, and English.
2. Detect language instantly from Romanized/Phonetic input (e.g., "Naku loan kavali" -> Telugu, "Mujhe loan chahiye" -> Hindi).
3. ALWAYS respond in the official NATIVE SCRIPT of that language (e.g., 'తెలుగు' for Telugu, 'हिंदी' for Hindi).
4. Keep responses short (2-3 sentences max). NO markdown, NO asterisks, NO bullet points.
"""

def detect_gtts_lang(text: str) -> str:
    if re.search(r'[\u0C00-\u0C7F]', text):  return 'te'  # Telugu
    elif re.search(r'[\u0B80-\u0BFF]', text): return 'ta'  # Tamil
    elif re.search(r'[\u0C80-\u0CFF]', text): return 'kn'  # Kannada
    elif re.search(r'[\u0D00-\u0D7F]', text): return 'ml'  # Malayalam
    elif re.search(r'[\u0900-\u097F]', text): return 'hi'  # Hindi
    return 'en'

class ChatRequest(BaseModel):
    user_input: str

@app.post("/v1/chat")
async def chat_endpoint(req: ChatRequest):
    if not client:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    
    try:
        # Call Claude
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": req.user_input}]
        )
        bot_text = response.content[0].text
        detected_lang = detect_gtts_lang(bot_text)
        
        return {
            "response_text": bot_text,
            "detected_lang": detected_lang
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tts")
async def tts_endpoint(text: str, lang: str = "en"):
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return StreamingResponse(fp, media_type="audio/mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Modern Voice Web Client
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pramaan-AI Voice Gateway</title>

        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; max-width: 600px; margin: 0 auto; padding: 20px; }
            .card { background: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); margin-bottom: 20px; }
            h1 { font-size: 1.5rem; margin-bottom: 4px; color: #38bdf8; }
            .subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; }
            #chat-box { height: 300px; overflow-y: auto; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 16px; background: #0f172a; }
            .msg { margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; line-height: 1.4; }
            .user { background: #0284c7; align-self: flex-end; }
            .bot { background: #334155; border-left: 3px solid #38bdf8; }
            .controls { display: flex; gap: 8px; }
            input { flex: 1; padding: 12px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: white; }
            button { padding: 12px 20px; border-radius: 6px; border: none; background: #0284c7; color: white; font-weight: bold; cursor: pointer; }
            button:hover { background: #0369a1; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎙️ Pramaan-AI Gateway</h1>
            <p class="subtitle">B2B Vernacular DPDP Voice Consent Gateway</p>
            
            <div id="chat-box"></div>
            
            <div class="controls">
                <input type="text" id="userInput" placeholder="Type prompt (e.g. Naku loan kavali)..." onkeydown="if(event.key==='Enter') sendMsg()">
                <button onclick="sendMsg()">Send</button>
            </div>
        </div>

        <script>
            async function sendMsg() {
                const input = document.getElementById('userInput');
                const text = input.value.trim();
                if(!text) return;

                appendMsg('user', text);
                input.value = '';

                try {
                    const res = await fetch('/v1/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_input: text})
                    });
                    const data = await res.json();
                    
                    appendMsg('bot', data.response_text);
                    
                    // Auto-play Voice
                    const audio = new Audio(`/v1/tts?text=${encodeURIComponent(data.response_text)}&lang=${data.detected_lang}`);
                    audio.play();

                } catch(e) {
                    appendMsg('bot', 'Error processing request.');
                }
            }

            function appendMsg(role, text) {
                const box = document.getElementById('chat-box');
                const div = document.createElement('div');
                div.className = `msg ${role}`;
                div.innerText = text;
                box.appendChild(div);
                box.scrollTop = box.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
