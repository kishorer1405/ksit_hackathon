"""
AI-based Complaint Resolution System backend.

How to run:
pip install flask flask-cors python-dotenv requests
python app.py
"""

import json
import os
import re
import sqlite3
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS


# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "complaints.db")
ALLOWED_STATUSES = {"Pending", "In Process", "Completed", "Rejected"}
ALLOWED_AUTHORITY_DEPARTMENTS = {"fire", "water", "electricity", "road", "garbage"}


# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------
def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    connection = get_db_connection()
    cursor = connection.cursor()

    # Users table: citizen accounts
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    # Authorities table: government department accounts
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS authorities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    # Complaints table: complaint records and AI output
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            location TEXT,
            image TEXT,
            category TEXT NOT NULL,
            department TEXT NOT NULL,
            priority TEXT NOT NULL,
            response TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    connection.commit()
    connection.close()


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------
def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def json_error(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def validate_required_fields(data: Dict[str, Any], fields: list[str]) -> Optional[str]:
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return field
    return None


def extract_json_from_text(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    # Remove fenced markdown if the model wraps JSON in code blocks.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def normalize_ai_result(data: Dict[str, Any], complaint_text: str) -> Dict[str, str]:
    category = str(data.get("category", "")).strip().title()
    department = str(data.get("department", "")).strip().title()
    priority = str(data.get("priority", "")).strip().title()
    response = str(data.get("response", "")).strip()

    category_map = {
        "Electrical": "Electrical",
        "Water": "Water",
        "Garbage": "Garbage",
        "Road": "Road",
        "Fire": "Fire",
        "Other": "Other",
    }

    department_map = {
        "Electrical": "Electricity",
        "Water": "Water",
        "Garbage": "Garbage",
        "Road": "Road",
        "Fire": "Fire",
        "Other": "Other",
    }

    if category not in category_map:
        return fallback_analysis(complaint_text)

    if department not in department_map:
        department = department_map[category]

    if priority not in {"Low", "Medium", "High"}:
        priority = "Medium"

    if not response:
        response = "Your complaint has been received and will be reviewed soon."

    return {
        "category": category,
        "department": department_map.get(category, department),
        "priority": priority,
        "response": response,
    }


def fallback_analysis(text: str) -> Dict[str, str]:
    lower_text = text.lower()

    if "light" in lower_text:
        return {
            "category": "Electrical",
            "department": "Electricity",
            "priority": "Medium",
            "response": "Technician will be assigned and the issue will be checked soon.",
        }

    if "water" in lower_text:
        return {
            "category": "Water",
            "department": "Water",
            "priority": "Medium",
            "response": "The water department will inspect the issue and respond soon.",
        }

    if "garbage" in lower_text:
        return {
            "category": "Garbage",
            "department": "Garbage",
            "priority": "Medium",
            "response": "Cleaning staff will be assigned to resolve this issue shortly.",
        }

    return {
        "category": "Other",
        "department": "Other",
        "priority": "Low",
        "response": "Your complaint has been logged and will be reviewed by the concerned team.",
    }


# -----------------------------------------------------------------------------
# AI analysis function
# -----------------------------------------------------------------------------
def analyze_complaint(text: str) -> Dict[str, str]:
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    prompt = f"""
You are a complaint analysis assistant.
Analyze the complaint and return ONLY valid JSON with these keys:
category, department, priority, response.

Rules:
- category must be one of: Electrical, Water, Garbage, Road, Fire, Other
- department must be one of: Electricity, Water, Garbage, Road, Fire, Other
- priority must be one of: Low, Medium, High
- response must be short and helpful
- Return only JSON, no markdown, no explanation

Complaint: {text}
""".strip()

    try:
        if gemini_key:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={gemini_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return normalize_ai_result(extract_json_from_text(raw_text), text)

        if openai_key:
            url = "https://api.openai.com/v1/responses"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4.1-mini",
                "input": prompt,
                "temperature": 0.2,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            raw_text = data["output"][0]["content"][0]["text"]
            return normalize_ai_result(extract_json_from_text(raw_text), text)

    except Exception:
        # If the AI call fails or the response cannot be parsed, use the fallback.
        return fallback_analysis(text)

    # If no API key is configured, use the simple fallback.
    return fallback_analysis(text)


# -----------------------------------------------------------------------------
# Basic pages and health check
# -----------------------------------------------------------------------------
@app.get("/")
def home():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Complaint Resolution API</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #f8fbff, #e8f1ff);
            color: #1f2937;
          }
          .card {
            background: white;
            padding: 32px;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            max-width: 560px;
            width: calc(100% - 32px);
          }
          h1 { margin: 0 0 12px; font-size: 28px; }
          p { margin: 0 0 12px; line-height: 1.6; }
          code {
            display: block;
            background: #f3f4f6;
            padding: 12px;
            border-radius: 10px;
            overflow-x: auto;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Complaint Resolution API</h1>
          <p>The backend is running successfully.</p>
          <p>Available endpoints:</p>
          <code>POST /user/register</code>
          <code>POST /user/login</code>
          <code>POST /authority/register</code>
          <code>POST /authority/login</code>
          <code>POST /complaint</code>
          <code>GET /user/complaints/&lt;user_id&gt;</code>
          <code>GET /authority/complaints/&lt;department&gt;</code>
          <code>PUT /complaint/status</code>
        </div>
      </body>
    </html>
    """


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# -----------------------------------------------------------------------------
# User authentication
# -----------------------------------------------------------------------------
@app.post("/user/register")
def user_register():
    #data = request.get_json(silent=True) or {}
    data = request.json or {}
    missing = validate_required_fields(data, ["name", "phone", "password"])
    if missing:
        return json_error(f"Missing field: {missing}")

    name = data["name"].strip()
    phone = data["phone"].strip()
    password = data["password"].strip()

    connection = get_db_connection()
    cursor = connection.cursor()

    existing_user = cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
    if existing_user:
        connection.close()
        return json_error("User already exists with this phone number", 409)

    cursor.execute(
        "INSERT INTO users (name, phone, password) VALUES (?, ?, ?)",
        (name, phone, password),
    )
    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201


@app.post("/user/login")
def user_login():
    data = request.get_json(silent=True) or {}
    missing = validate_required_fields(data, ["phone", "password"])
    if missing:
        return json_error(f"Missing field: {missing}")

    phone = data["phone"].strip()
    password = data["password"].strip()

    connection = get_db_connection()
    user = connection.execute(
        "SELECT id, name, phone FROM users WHERE phone = ? AND password = ?",
        (phone, password),
    ).fetchone()
    connection.close()

    if not user:
        return json_error("Invalid user credentials", 401)

    return jsonify({"message": "Login successful", "user": row_to_dict(user)}), 200


# -----------------------------------------------------------------------------
# Authority authentication
# -----------------------------------------------------------------------------
@app.post("/authority/register")
def authority_register():
    data = request.get_json(silent=True) or {}
    missing = validate_required_fields(data, ["name", "phone", "department", "password"])
    if missing:
        return json_error(f"Missing field: {missing}")

    name = data["name"].strip()
    phone = data["phone"].strip()
    department = data["department"].strip().lower()
    password = data["password"].strip()

    if department not in ALLOWED_AUTHORITY_DEPARTMENTS:
        return json_error("Invalid department", 400)

    connection = get_db_connection()
    cursor = connection.cursor()

    existing_authority = cursor.execute(
        "SELECT id FROM authorities WHERE phone = ?",
        (phone,),
    ).fetchone()
    if existing_authority:
        connection.close()
        return json_error("Authority already exists with this phone number", 409)

    cursor.execute(
        "INSERT INTO authorities (name, phone, department, password) VALUES (?, ?, ?, ?)",
        (name, phone, department, password),
    )
    connection.commit()
    authority_id = cursor.lastrowid
    connection.close()

    return jsonify({"message": "Authority registered successfully", "authority_id": authority_id}), 201


@app.post("/authority/login")
def authority_login():
    data = request.get_json(silent=True) or {}
    missing = validate_required_fields(data, ["phone", "password", "department"])
    if missing:
        return json_error(f"Missing field: {missing}")

    phone = data["phone"].strip()
    password = data["password"].strip()
    department = data["department"].strip().lower()

    connection = get_db_connection()
    authority = connection.execute(
        "SELECT id, name, phone, department FROM authorities WHERE phone = ? AND password = ? AND lower(department) = ?",
        (phone, password, department),
    ).fetchone()
    connection.close()

    if not authority:
        return json_error("Invalid authority credentials", 401)

    return jsonify({"message": "Login successful", "authority": row_to_dict(authority)}), 200


# -----------------------------------------------------------------------------
# Complaint submission and retrieval
# -----------------------------------------------------------------------------
@app.post("/complaint")
def create_complaint():
    data = request.get_json(silent=True) or {}
    missing = validate_required_fields(data, ["user_id", "text"])
    if missing:
        return json_error(f"Missing field: {missing}")

    user_id = data["user_id"]
    text = str(data["text"]).strip()
    location = str(data.get("location", "")).strip()
    image = data.get("image")

    if not text:
        return json_error("Complaint text cannot be empty")

    connection = get_db_connection()
    cursor = connection.cursor()

    user = cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        connection.close()
        return json_error("User not found", 404)

    ai_result = analyze_complaint(text)

    cursor.execute(
        """
        INSERT INTO complaints (
            user_id, text, location, image, category, department, priority, response, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            text,
            location,
            image,
            ai_result["category"],
            ai_result["department"],
            ai_result["priority"],
            ai_result["response"],
            "Pending",
        ),
    )
    connection.commit()
    complaint_id = cursor.lastrowid

    complaint = cursor.execute(
        "SELECT * FROM complaints WHERE id = ?",
        (complaint_id,),
    ).fetchone()
    connection.close()

    return jsonify({"message": "Complaint submitted successfully", "complaint": row_to_dict(complaint)}), 201


@app.get("/user/complaints/<int:user_id>")
def get_user_complaints(user_id: int):
    connection = get_db_connection()
    user = connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        connection.close()
        return json_error("User not found", 404)

    complaints = connection.execute(
        "SELECT * FROM complaints WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    connection.close()

    return jsonify({"complaints": [row_to_dict(row) for row in complaints]}), 200


@app.get("/authority/complaints/<department>")
def get_authority_complaints(department: str):
    normalized_department = department.strip().lower()
    if normalized_department not in ALLOWED_AUTHORITY_DEPARTMENTS:
        return json_error("Invalid department", 400)

    connection = get_db_connection()
    complaints = connection.execute(
        "SELECT * FROM complaints WHERE lower(department) = ? ORDER BY id DESC",
        (normalized_department,),
    ).fetchall()
    connection.close()

    return jsonify({"complaints": [row_to_dict(row) for row in complaints]}), 200


# -----------------------------------------------------------------------------
# Complaint status update
# -----------------------------------------------------------------------------
@app.put("/complaint/status")
def update_complaint_status():
    data = request.get_json(silent=True) or {}
    missing = validate_required_fields(data, ["complaint_id", "status"])
    if missing:
        return json_error(f"Missing field: {missing}")

    complaint_id = data["complaint_id"]
    status = str(data["status"]).strip().title()

    if status not in ALLOWED_STATUSES:
        return json_error("Invalid status", 400)

    connection = get_db_connection()
    cursor = connection.cursor()

    complaint = cursor.execute(
        "SELECT id FROM complaints WHERE id = ?",
        (complaint_id,),
    ).fetchone()
    if not complaint:
        connection.close()
        return json_error("Complaint not found", 404)

    cursor.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (status, complaint_id),
    )
    connection.commit()

    updated_complaint = cursor.execute(
        "SELECT * FROM complaints WHERE id = ?",
        (complaint_id,),
    ).fetchone()
    connection.close()

    return jsonify({"message": "Status updated successfully", "complaint": row_to_dict(updated_complaint)}), 200


# -----------------------------------------------------------------------------
# Start the app
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)