import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

API_ENDPOINT = "https://api.openai.com/v1/responses"


def generate_sat_question(section: str, topic: str, difficulty: str) -> str:
    api_key = "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"
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

    # Prompt structure based on your original script :contentReference[oaicite:1]{index=1}
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
        "max_output_tokens": 750,
        "temperature": 0.5,
    }

    r = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=60)

    # Raise helpful error if request fails
    try:
        r.raise_for_status()
    except requests.HTTPError:
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text}
        raise RuntimeError(f"OpenAI API error ({r.status_code}): {err}")

    data = r.json()

    # Prefer stable shortcut when present
    text = data.get("output_text")
    if text:
        return text

    # Fallback to nested format
    try:
        return data["output"][0]["content"][0]["text"]
    except Exception:
        raise RuntimeError(f"Unexpected response format: {data}")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/generate-question")
def api_generate_question():
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
