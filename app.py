import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

OPENAI_API_ENDPOINT = "https://api.openai.com/v1/responses"


# =========================
# CORS (robust + safe)
# =========================
@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"

    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


# Universal OPTIONS handler
@app.route("/api/<path:_>", methods=["OPTIONS"])
def api_preflight(_):
    return ("", 204)


# =========================
# Debug endpoints
# =========================
@app.get("/api/debug")
def debug():
    key = os.getenv("OPENAI_API_KEY", "")
    return jsonify({
        "has_key": bool(key),
        "length": len(key),
        "prefix": key[:7],
        "suffix": key[-4:] if len(key) >= 4 else "",
    })


@app.get("/api/whereami")
def whereami():
    return jsonify({
        "host": request.headers.get("Host"),
        "origin": request.headers.get("Origin"),
        "x_vercel_id": request.headers.get("X-Vercel-Id"),
        "x_forwarded_host": request.headers.get("X-Forwarded-Host"),
        "x_forwarded_proto": request.headers.get("X-Forwarded-Proto"),
    })


# =========================
# Core logic
# =========================
def generate_sat_question(section: str, topic: str, difficulty: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    prompt = f"""
You are an SAT test writer. Create one original SAT-style question from the section "{section}"
and the topic "{topic}".

Difficulty level: {difficulty}

Requirements:
- SAT style and tone
- Exactly 4 answer choices (A–D)
- Clearly mark the correct answer
- Step-by-step explanation
- Clear, concise language

Output format:
Question
Answer Choices (A–D)
Correct Answer
Explanation
""".strip()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": prompt,
        "max_output_tokens": 450,
        "temperature": 0.5,
    }

    r = requests.post(
        OPENAI_API_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=60
    )

    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI API error ({r.status_code}): {r.text}")

    data = r.json()

    if "output_text" in data:
        return data["output_text"]

    try:
        return data["output"][0]["content"][0]["text"]
    except Exception:
        raise RuntimeError(f"Unexpected OpenAI response: {data}")


# =========================
# API route
# =========================
@app.route("/api/generate-question", methods=["POST", "OPTIONS"])
def api_generate_question():
    if request.method == "OPTIONS":
        return ("", 204)

    body = request.get_json(silent=True) or {}

    section = (body.get("section") or "").strip()
    topic = (body.get("topic") or "").strip()
    difficulty = (body.get("difficulty") or "").strip()

    if not section or not topic or not difficulty:
        return jsonify({"error": "Missing section/topic/difficulty"}), 400

    if section not in {"Reading and Writing", "Math"}:
        return jsonify({"error": f"Invalid section: {section}"}), 400

    if difficulty not in {"Easy", "Medium", "Hard"}:
        return jsonify({"error": f"Invalid difficulty: {difficulty}"}), 400

    try:
        text = generate_sat_question(section, topic, difficulty)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# Frontend
# =========================
@app.get("/")
def index():
    return send_from_directory("static", "index.html")


# Local dev only
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
