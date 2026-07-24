import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Pramaan-AI Gateway")

# Groq Client (Free API key from console.groq.com)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    user_input: str
    language: str = "English"  # Default fallback

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pramaan AI Gateway</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eef2f5; margin: 0; padding: 20px; text-align: center; }
            .card { background: white; max-width: 600px; margin: 20px auto; padding: 30px; border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.1); }
            h2 { color: #2c3e50; margin-bottom: 5px; }
            p.sub { color: #7f8c8d; font-size: 14px; margin-top: 0; }
            label { font-weight: bold; display: block; margin: 15px 0 5px; text-align: left; }
            select, input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
            .btn-group { display: flex; gap: 10px; margin-top: 20px; }
            button { flex: 1; padding: 14px; font-size: 15px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.2s; }
            .btn-chat { background: #2980b9; color: white; }
            .btn-voice { background: #e74c3c; color: white; }
            .btn-send { background: #2ecc71; color: white; width: 100%; margin-top: 15px; }
            button:hover { opacity: 0.9; }
            #status { margin-top: 15px; font-weight: bold; color: #34495e; min-height: 20px; }
            #timer { color: #e67e22; font-size: 18px; font-weight: bold; margin-top: 10px; }
            #responseBox { margin-top: 20px; padding: 15px; background: #f8f9fa; border-left: 4px solid #2980b9; border-radius: 6px; text-align: left; white-space: pre-wrap; display: none; }
        </style>
    </head>
    <body>

        <div class="card">
            <h2>Pramaan AI Gateway</h2>
            <p class="sub">Multilingual Chat & Voice Assistant</p>

            <label for="langSelect">1. Select Language:</label>
            <select id="langSelect" onchange="updateLangCode()">
                <option value="English" data-code="en-IN">English</option>
                <option value="Telugu" data-code="te-IN">తెలుగు (Telugu)</option>
                <option value="Tamil" data-code="ta-IN">தமிழ் (Tamil)</option>
                <option value="Kannada" data-code="kn-IN">ಕನ್ನಡ (Kannada)</option>
                <option value="Malayalam" data-code="ml-IN">മലയാളം (Malayalam)</option>
                <option value="Hindi" data-code="hi-IN">हिन्दी (Hindi)</option>
            </select>

            <label for="userInput">2. Your Input:</label>
            <input type="text" id="userInput" placeholder="Type text OR click 'Record Voice' below...">

            <div class="btn-group">
                <button class="btn-voice" onclick="startRecording()">🎙️ Record Voice</button>
            </div>

            <button class="btn-send" onclick="sendQuestion()">🚀 Send to Pramaan AI</button>

            <div id="status"></div>
            <div id="timer"></div>
            <div id="responseBox"></div>
        </div>

        <script>
            let speechLangCode = 'en-IN';

            function updateLangCode() {
                const select = document.getElementById('langSelect');
                speechLangCode = select.options[select.selectedIndex].getAttribute('data-code');
            }

            function startRecording() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Speech recognition is not supported in this browser. Please use Google Chrome.");
                    return;
                }

                const recognition = new SpeechRecognition();
                recognition.lang = speechLangCode;
                recognition.interimResults = false;

                document.getElementById('status').innerText = "🎙️ Listening... Speak now in " + document.getElementById('langSelect').value;
                recognition.start();

                recognition.onresult = function(event) {
                    const transcript = event.results[0][0].transcript;
                    document.getElementById('userInput').value = transcript;
                    document.getElementById('status').innerText = "✅ Voice captured successfully!";
                };

                recognition.onerror = function(event) {
                    document.getElementById('status').innerText = "❌ Voice Error: " + event.error;
                };
            }

            async function sendQuestion() {
                const text = document.getElementById('userInput').value;
                const lang = document.getElementById('langSelect').value;
                const statusDiv = document.getElementById('status');
                const timerDiv = document.getElementById('timer');
                const responseBox = document.getElementById('responseBox');

                if (!text.trim()) {
                    alert("Please enter text or record voice first!");
                    return;
                }

                statusDiv.innerText = "⏳ Pramaan AI is thinking...";
                timerDiv.innerText = "";
                responseBox.style.display = "none";

                try {
                    const res = await fetch('/v1/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_input: text, language: lang })
                    });

                    const data = await res.json();
                    const reply = data.response || "No response received.";

                    // Display text immediately
                    responseBox.innerText = reply;
                    responseBox.style.display = "block";
                    statusDiv.innerText = "✅ Response received!";

                    // Start 30-Second Audio Countdown
                    let countdown = 30;
                    timerDiv.innerText = `🔊 Audio voice output playing in ${countdown} seconds...`;

                    const interval = setInterval(() => {
                        countdown--;
                        if (countdown > 0) {
                            timerDiv.innerText = `🔊 Audio voice output playing in ${countdown} seconds...`;
                        } else {
                            clearInterval(interval);
                            timerDiv.innerText = "🔊 Playing voice output now!";
                            speakOutput(reply, speechLangCode);
                        }
                    }, 1000);

                } catch (err) {
                    statusDiv.innerText = "❌ Error connecting to server.";
                    console.error(err);
                }
            }

            function speakOutput(text, langCode) {
                window.speechSynthesis.cancel(); // Clear queued speech
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = langCode;
                window.speechSynthesis.speak(utterance);
            }
        </script>
    </body>
    </html>
    """

@app.post("/v1/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        prompt = (
            f"You are Pramaan AI. Respond accurately to the user's input. "
            f"Mandatory requirement: Provide the entire response ONLY in {request.language} language.\n\n"
            f"User input: {request.user_input}"
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
