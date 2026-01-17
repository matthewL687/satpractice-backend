# app.py
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
def _extract_response_text(data: dict) -> str:
    """
    Robustly extract text from the Responses API payload.
    Works across different response shapes.
    """
    if isinstance(data, dict) and isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    out = data.get("output")
    if isinstance(out, list):
        chunks = []
        for item in out:
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                # Common shapes: {"type":"output_text","text":"..."} or {"text":"..."}
                if isinstance(c.get("text"), str):
                    chunks.append(c["text"])
        text = "\n".join(chunks).strip()
        if text:
            return text

    raise RuntimeError("Could not extract text from model response.")


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
- Do not include any extra headings or text outside the specified format

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
    return _extract_response_text(data)


# =========================
# API route
# =========================
@app.post("/api/generate-question")
def api_generate_question():
    body = request.get_json() or {}

    section = (body.get("section") or "").strip()
    topic = (body.get("topic") or "").strip()
    difficulty = (body.get("difficulty") or "").strip()

    if not section or not topic or not difficulty:
        return jsonify({"error": "Missing fields"}), 400

    try:
        text = generate_sat_question(section, topic, difficulty)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# Frontend / static
# =========================
@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/<path:path>")
def static_proxy(path):
    # optional: serve any other static files you add later
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
