from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
import re
import numpy as np

from werkzeug.security import generate_password_hash, check_password_hash
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image
import io

app = Flask(__name__, static_folder='.')
app.secret_key = "secret123"
CORS(app, supports_credentials=True)

# ================= CONFIG =================
# Get your free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyDMAdm8fxMdWhAHKS5atECl3iasRywAaUQ"

# Confidence threshold — below this we return "Uncertain"
CONFIDENCE_THRESHOLD = 70.0

# ================= LOAD MODEL =================
model = load_model("final_model.h5")
input_shape = model.input_shape
IMG_HEIGHT = input_shape[1]
IMG_WIDTH  = input_shape[2]

CLASS_LABELS = ["Glioma Tumor", "Meningioma Tumor", "No Tumor", "Pituitary Tumor"]


# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    password TEXT
                )''')
    conn.commit()
    conn.close()

init_db()


# ================= SERVE FRONTEND =================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/auth')
def serve_auth():
    return send_from_directory('.', 'auth.html')

@app.route('/upload')
def serve_upload():
    return send_from_directory('.', 'upload.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)


# ================= VALIDATION =================
def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def valid_password(password):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{6,}$", password)


# ================= REGISTER =================
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    if not valid_password(password):
        return jsonify({"error": "Password must include uppercase, lowercase, number, special character"}), 400

    hashed_password = generate_password_hash(password)
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registered successfully"})
    except:
        return jsonify({"error": "User already exists"}), 400


# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[3], password):
        session['user'] = user[1]
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# ================= CHECK LOGIN =================
@app.route('/check')
def check():
    if 'user' in session:
        return jsonify({"loggedIn": True, "user": session['user']})
    return jsonify({"loggedIn": False})


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.pop('user', None)
    return jsonify({"message": "Logged out"})


# ================= VALIDATE IMAGE WITH GEMINI =================
@app.route('/validate', methods=['POST'])
def validate_image():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        import base64, requests as req, json as pyjson

        img_bytes = file.read()
        b64 = base64.standard_b64encode(img_bytes).decode('utf-8')

        mime_type = file.content_type or "image/jpeg"
        if mime_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            mime_type = "image/jpeg"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64
                        }
                    },
                    {
                        "text": (
                            "Examine this image very carefully. "
                            "Is this a genuine medical brain scan (MRI or CT scan)? "
                            "A valid brain scan: is grayscale or near-grayscale, shows brain anatomy (skull, brain tissue, ventricles), has a dark/black background, looks like a radiology image. "
                            "INVALID images include: logos, photos, illustrations, cartoons, colorful images, animals, people, text documents, screenshots, or anything not a medical brain scan. "
                            "Be strict — if you are not highly confident it is a brain scan, return false. "
                            "Reply with ONLY raw JSON, no markdown, no backticks, no extra text. "
                            "Exact format: {\"valid\": true or false, \"reason\": \"one short sentence\"}"
                        )
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 80
            }
        }

        response = req.post(url, json=payload, timeout=15)
        result = response.json()
        print("Gemini full response:", pyjson.dumps(result, indent=2))  # DEBUG

        if "candidates" not in result:
            error_msg = result.get("error", {}).get("message", "")
            print("Gemini API error:", error_msg)
            # If quota exceeded or API error, fail open so real scans aren't blocked
            return jsonify({"valid": True, "reason": "Validation unavailable, proceeding."})

        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        print("Gemini response:", text)  # DEBUG

        parsed = pyjson.loads(text)
        return jsonify(parsed)

    except Exception as e:
        print("Gemini validation error:", str(e))
        return jsonify({"valid": True, "reason": "Validation unavailable, proceeding."})


# ================= PREDICT =================
@app.route('/predict', methods=['POST'])
def predict():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((IMG_WIDTH, IMG_HEIGHT))

        # No /255 — model has Rescaling layer built in
        img_array = img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)

        predictions = model.predict(img_array)
        predicted_index = int(np.argmax(predictions[0]))
        confidence = float(np.max(predictions[0])) * 100

        # Low confidence → return Uncertain
        if confidence < CONFIDENCE_THRESHOLD:
            return jsonify({
                "result": "Uncertain",
                "confidence": round(confidence, 2),
                "message": "Model confidence too low. Please upload a clearer brain MRI scan."
            })

        return jsonify({
            "result": CLASS_LABELS[predicted_index],
            "confidence": round(confidence, 2),
            "message": ""
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)
