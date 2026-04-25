"""
AI-based Complaint Resolution System backend.

How to run:
pip install flask flask-cors python-dotenv requests
python app.py
"""

import json
import os
import random
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

# Bengaluru locality reference points used for the geographic heatmap.
LOCATION_POINTS = {
    "Majestic": (12.9762, 77.5710),
    "Malleswaram": (13.0030, 77.5696),
    "Rajajinagar": (12.9912, 77.5523),
    "Yeshwanthpur": (13.0210, 77.5531),
    "Hebbal": (13.0358, 77.5910),
    "Indiranagar": (12.9784, 77.6408),
    "Koramangala": (12.9352, 77.6245),
    "HSR Layout": (12.9116, 77.6474),
    "Jayanagar": (12.9250, 77.5938),
    "BTM Layout": (12.9166, 77.6101),
    "Electronic City": (12.8459, 77.6600),
    "Marathahalli": (12.9592, 77.6974),
    "Bellandur": (12.9295, 77.6787),
    "Whitefield": (12.9698, 77.7500),
    "Banashankari": (12.9250, 77.5466),
    "Basavanagudi": (12.9415, 77.5757),
    "MG Road": (12.9755, 77.6050),
}


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
            area TEXT,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    # Lightweight migration for existing databases.
    existing_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(complaints)").fetchall()
    }
    if "area" not in existing_columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN area TEXT")
    if "latitude" not in existing_columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN latitude REAL")
    if "longitude" not in existing_columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN longitude REAL")

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

    if "fire" in lower_text or "smoke" in lower_text:
        return {
            "category": "Fire",
            "department": "Fire",
            "priority": "High",
            "response": "Emergency team will be informed immediately and dispatched.",
        }

    if "road" in lower_text or "pothole" in lower_text:
        return {
            "category": "Road",
            "department": "Road",
            "priority": "Medium",
            "response": "Road maintenance team will inspect and schedule a fix.",
        }

    if "water" in lower_text or "leakage" in lower_text:
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


def resolve_location_point(location: str) -> tuple[str, float, float]:
    text = location.strip().lower()

    if text:
        for area, (lat, lng) in LOCATION_POINTS.items():
            if area.lower() in text:
                return area, lat, lng

    # Default anchor if location is missing or unmatched.
    default_area = "MG Road"
    default_lat, default_lng = LOCATION_POINTS[default_area]
    return default_area, default_lat, default_lng


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
    area, latitude, longitude = resolve_location_point(location)

    cursor.execute(
        """
        INSERT INTO complaints (
            user_id, text, location, image, category, department, priority, response, status, area, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            area,
            latitude,
            longitude,
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
# Heatmap and insights
# -----------------------------------------------------------------------------
@app.get("/insights/heatmap")
def get_heatmap_data():
    department = str(request.args.get("department", "")).strip().lower()
    user_id = request.args.get("user_id")
    locality_names = list(LOCATION_POINTS.keys())
    locality_placeholders = ",".join("?" for _ in locality_names)

    query = f"""
        SELECT
            area,
            COALESCE(latitude, 0) AS latitude,
            COALESCE(longitude, 0) AS longitude,
            COUNT(*) AS count
        FROM complaints
        WHERE area IN ({locality_placeholders})
    """
    params: list[Any] = list(locality_names)

    if department:
        if department not in ALLOWED_AUTHORITY_DEPARTMENTS:
            return json_error("Invalid department", 400)
        query += " AND lower(department) = ?"
        params.append(department)

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    query += " GROUP BY area, latitude, longitude ORDER BY count DESC"

    connection = get_db_connection()
    rows = connection.execute(query, params).fetchall()
    connection.close()

    points = [
        {
            "area": row["area"] or "Unknown",
            "lat": row["latitude"],
            "lng": row["longitude"],
            "weight": row["count"],
        }
        for row in rows
    ]

    return jsonify({"points": points, "total_areas": len(points)}), 200


@app.get("/insights/summary")
def get_insights_summary():
    department = str(request.args.get("department", "")).strip().lower()
    user_id = request.args.get("user_id")
    locality_names = list(LOCATION_POINTS.keys())
    locality_placeholders = ",".join("?" for _ in locality_names)

    where_parts = [f"area IN ({locality_placeholders})"]
    params: list[Any] = list(locality_names)

    if department:
        if department not in ALLOWED_AUTHORITY_DEPARTMENTS:
            return json_error("Invalid department", 400)
        where_parts.append("lower(department) = ?")
        params.append(department)

    if user_id:
        where_parts.append("user_id = ?")
        params.append(user_id)

    where_clause = " AND ".join(where_parts)

    connection = get_db_connection()
    total = connection.execute(
        f"SELECT COUNT(*) AS c FROM complaints WHERE {where_clause}",
        params,
    ).fetchone()["c"]

    top_areas = connection.execute(
        f"""
        SELECT area, COUNT(*) AS count
        FROM complaints
        WHERE {where_clause}
        GROUP BY area
        ORDER BY count DESC
        LIMIT 5
        """,
        params,
    ).fetchall()

    by_status = connection.execute(
        f"""
        SELECT status, COUNT(*) AS count
        FROM complaints
        WHERE {where_clause}
        GROUP BY status
        ORDER BY count DESC
        """,
        params,
    ).fetchall()
    connection.close()

    return jsonify(
        {
            "total_complaints": total,
            "top_areas": [{"area": row["area"] or "Unknown", "count": row["count"]} for row in top_areas],
            "status_breakdown": [{"status": row["status"], "count": row["count"]} for row in by_status],
        }
    ), 200


@app.post("/seed/demo-complaints")
def seed_demo_complaints():
    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 30))
    count = max(1, min(count, 200))

    sample_texts = {
        "Electricity": [
            "Street lights are not working in Indiranagar.",
            "Power outage reported in Koramangala apartment block.",
            "Frequent short-circuit issue near Whitefield commercial street.",
        ],
        "Water": [
            "No water supply reported in Jayanagar apartment lane.",
            "Water leakage near Bellandur pipeline.",
            "Drinking water cooler is empty in Malleswaram market area.",
        ],
        "Road": [
            "Large pothole near MG Road service lane.",
            "Internal road surface damaged in Banashankari.",
            "Rainwater logging at Marathahalli junction.",
        ],
        "Fire": [
            "Smoke detected near Hebbal market warehouse.",
            "Fire extinguisher missing in Whitefield office building.",
            "Burning smell noticed near Koramangala kitchen area.",
        ],
        "Garbage": [
            "Garbage bins are overflowing in HSR Layout.",
            "Waste not collected from Rajajinagar street.",
            "Bad smell from dumped garbage behind Yeshwanthpur market.",
        ],
    }

    department_choices = ["Electricity", "Water", "Road", "Fire", "Garbage"]
    statuses = ["Pending", "In Process", "Completed", "Rejected"]
    area_choices = list(LOCATION_POINTS.keys())

    connection = get_db_connection()
    cursor = connection.cursor()

    # Create or reuse a dedicated demo user.
    demo_phone = "9990001111"
    demo_user = cursor.execute("SELECT id FROM users WHERE phone = ?", (demo_phone,)).fetchone()
    if demo_user:
        user_id = demo_user["id"]
    else:
        cursor.execute(
            "INSERT INTO users (name, phone, password) VALUES (?, ?, ?)",
            ("Demo User", demo_phone, "demo123"),
        )
        user_id = cursor.lastrowid

    for _ in range(count):
        dept = random.choice(department_choices)
        area = random.choice(area_choices)
        lat, lng = LOCATION_POINTS[area]
        text = random.choice(sample_texts[dept])
        priority = random.choice(["Low", "Medium", "High"])
        status = random.choice(statuses)

        cursor.execute(
            """
            INSERT INTO complaints (
                user_id, text, location, image, category, department, priority, response, status, area, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                text,
                area,
                None,
                dept,
                dept,
                priority,
                "Demo complaint generated for heatmap insights.",
                status,
                area,
                lat,
                lng,
            ),
        )

    connection.commit()
    connection.close()

    return jsonify({"message": "Demo complaints seeded", "count": count}), 201


# -----------------------------------------------------------------------------
# Start the app
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)