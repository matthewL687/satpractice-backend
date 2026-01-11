import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

API_ENDPOINT = "https://api.openai.com/v1/responses"


# ✅ Robust CORS (echo Origin for best browser compatibility)
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


# ✅ Universal preflight handler for any /api/* route
@app.route("/api/<path:_>", methods=["OPTIONS"])
def api_preflight(_):
    return ("", 204)


@app.get("/api/debug")
def debug():
    """
    Safe debug endpoint: confirms whether OPENAI_API_KEY is present.
    Does NOT reveal the full key.
    """
    key = os.getenv("OPENAI_API_KEY", "")
    return jsonify({
        "has_key": bool(key),
        "prefix": key[:7],
        "suffix": key[-4:] if len(key) >= 4 else "",
        "length": len(key),
    })


def generate_sat_question(section: str, topic: str, difficulty: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

    prompt = f"""
You are an SAT test writer. Create one original SAT-style question from the section "{section}"
and the topic "{topic}".

Difficulty level: {difficulty}

Difficulty guidelines:
- Easy: Straightforward wording, minimal traps, clear answer choice.
- Medium: Moderate complexity, plausible distractors, some reasoning required.
- Hard: Subtle distinctions, close answer choices, deeper reasoning required.

Requirements:
- The question should match official SAT style and tone.
- Provide exactly 4 answer choices (A–D).
- Clearly indicate the correct answer.
- Include a step-by-step explanation justifying why the correct answer is correct
  and why the others are incorrect.
- Use clear, concise language appropriate for high school students.

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
        # ✅ reduce a bit to avoid timeouts on serverless
        "max_output_tokens": 750,
        "temperature": 0.5,
    }

    r = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=60)

    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI API error ({r.status_code}): {r.text}")

    data = r.json()

    text = data.get("output_text")
    if text:
        return text

    try:
        return data["output"][0]["content"][0]["text"]
    except Exception:
        raise RuntimeError(f"Unexpected response format from OpenAI: {data}")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ✅ Handle both POST and OPTIONS on the same route
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

    allowed_sections = {"Reading and Writing", "Math"}
    allowed_difficulties = {"Easy", "Medium", "Hard"}

    if section not in allowed_sections:
        return jsonify({"error": f"Invalid section: {section}"}), 400
    if difficulty not in allowed_difficulties:
        return jsonify({"error": f"Invalid difficulty: {difficulty}"}), 400

    try:
        text = generate_sat_question(section, topic, difficulty)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
