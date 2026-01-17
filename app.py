import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

OPENAI_API_ENDPOINT = "https://api.openai.com/v1/responses"


# =========================
# CORS
# =========================
@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    resp.headers["Access-Control-Allow-Origin"] = origin or "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/api/<path:_>", methods=["OPTIONS"])
def api_preflight(_):
    return ("", 204)


# =========================
# Core logic
# =========================
def generate_sat_question(section: str, topic: str, difficulty: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    prompt = f"""
You are an SAT test writer. Create ONE original SAT-style question.

Section: {section}
Topic: {topic}
Difficulty: {difficulty}

STRICT REQUIREMENTS:
- SAT style and tone
- Exactly 4 answer choices labeled A., B., C., D.
- ALL math must be written in LaTeX
- Use $...$ for inline math and $$...$$ for displayed equations
- Do NOT use HTML
- Do NOT explain LaTeX formatting

Output format (plain text only):

Question:
<question text>

Answer Choices:
A. ...
B. ...
C. ...
D. ...

Correct Answer:
<single letter A–D>

Explanation:
<step-by-step explanation with LaTeX>
""".strip()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": prompt,
        "max_output_tokens": 500,
        "temperature": 0.4,
    }

    r = requests.post(
        OPENAI_API_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if r.status_code >= 400:
        raise RuntimeError(r.text)

    data = r.json()

    if "output_text" in data:
        return data["output_text"]

    return data["output"][0]["content"][0]["text"]


# =========================
# API route
# =========================
@app.post("/api/generate-question")
def api_generate_question():
    body = request.get_json() or {}

    section = body.get("section", "").strip()
    topic = body.get("topic", "").strip()
    difficulty = body.get("difficulty", "").strip()

    if not section or not topic or not difficulty:
        return jsonify({"error": "Missing fields"}), 400

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
