from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
import sqlite3
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "smartbikepass_secret_key_2024"

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "instance", "smartbike.db")
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


# ─────────────────────────── DATABASE ───────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id     TEXT UNIQUE NOT NULL,
            full_name   TEXT NOT NULL,
            roll_no     TEXT NOT NULL,
            email       TEXT NOT NULL,
            phone       TEXT NOT NULL,
            department  TEXT NOT NULL,
            year        TEXT NOT NULL,
            vehicle_no  TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            rc_book     TEXT,
            license     TEXT,
            insurance   TEXT,
            status      TEXT DEFAULT 'pending',
            transport_remarks TEXT,
            principal_remarks TEXT,
            transport_reviewed_at TEXT,
            principal_reviewed_at TEXT,
            submitted_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id    TEXT,
            action     TEXT,
            done_by    TEXT,
            remarks    TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)

    # Seed default users (transport & principal)
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("transport", "transport123", "transport"))
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("principal", "principal123", "principal"))
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("admin", "admin123", "admin"))
    except sqlite3.IntegrityError:
        pass  # already seeded

    conn.commit()
    conn.close()


init_db()


# ─────────────────────────── HELPERS ────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, prefix):
    if file and allowed_file(file.filename):
        ext = secure_filename(file.filename).rsplit(".", 1)[-1]
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return filename
    return None


def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login_page"))
            if role and session.get("role") != role and session.get("role") != "admin":
                return jsonify({"error": "Unauthorized"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────── PAGES ──────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/apply")
def apply_page():
    return render_template("apply.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/transport")
def transport_page():
    if "user" not in session or session.get("role") not in ("transport", "admin"):
        return redirect(url_for("login_page"))
    return render_template("transport.html", username=session["user"])


@app.route("/principal")
def principal_page():
    if "user" not in session or session.get("role") not in ("principal", "admin"):
        return redirect(url_for("login_page"))
    return render_template("principal.html", username=session["user"])


@app.route("/approved/<pass_id>")
def approved_page(pass_id):
    conn = get_db()
    app_data = conn.execute(
        "SELECT * FROM applications WHERE pass_id=?", (pass_id,)
    ).fetchone()
    conn.close()
    if not app_data or app_data["status"] != "approved":
        return render_template("not_found.html"), 404
    return render_template("approved.html", data=dict(app_data))


@app.route("/status")
def status_page():
    return render_template("status.html")


@app.route("/admin")
def admin_page():
    if "user" not in session or session.get("role") != "admin":
        return redirect(url_for("login_page"))
    return render_template("admin.html", username=session["user"])


# ─────────────────────────── AUTH APIs ──────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?", (username, password)
    ).fetchone()
    conn.close()
    if user:
        session["user"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"success": True, "role": user["role"]})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@app.route("/api/logout")
def api_logout():
    session.clear()
    return redirect(url_for("login_page"))


# ─────────────────────────── APPLICATION APIs ───────────────────

@app.route("/api/apply", methods=["POST"])
def api_apply():
    try:
        full_name    = request.form.get("full_name", "").strip()
        roll_no      = request.form.get("roll_no", "").strip()
        email        = request.form.get("email", "").strip()
        phone        = request.form.get("phone", "").strip()
        department   = request.form.get("department", "").strip()
        year         = request.form.get("year", "").strip()
        vehicle_no   = request.form.get("vehicle_no", "").strip().upper()
        vehicle_type = request.form.get("vehicle_type", "").strip()

        if not all([full_name, roll_no, email, phone, department, year, vehicle_no, vehicle_type]):
            return jsonify({"success": False, "error": "All fields are required"}), 400

        rc_book  = save_file(request.files.get("rc_book"),  "rc")
        license_ = save_file(request.files.get("license"),  "dl")
        insurance = save_file(request.files.get("insurance"), "ins")

        if not all([rc_book, license_, insurance]):
            return jsonify({"success": False, "error": "All three documents are required"}), 400

        pass_id = "SBPS-" + uuid.uuid4().hex[:8].upper()

        conn = get_db()
        conn.execute("""
            INSERT INTO applications
            (pass_id, full_name, roll_no, email, phone, department, year,
             vehicle_no, vehicle_type, rc_book, license, insurance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pass_id, full_name, roll_no, email, phone, department, year,
              vehicle_no, vehicle_type, rc_book, license_, insurance))
        conn.execute("INSERT INTO audit_log (pass_id, action, done_by) VALUES (?,?,?)",
                     (pass_id, "Application Submitted", full_name))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "pass_id": pass_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/status/<pass_id>")
def api_status(pass_id):
    conn = get_db()
    row = conn.execute(
        "SELECT pass_id, full_name, vehicle_no, status, submitted_at, "
        "transport_remarks, principal_remarks, transport_reviewed_at, principal_reviewed_at "
        "FROM applications WHERE pass_id=?", (pass_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False, "error": "Pass ID not found"}), 404
    return jsonify({"success": True, "data": dict(row)})


# ─────────────────────────── TRANSPORT APIs ─────────────────────

@app.route("/api/transport/applications")
def transport_applications():
    if "user" not in session or session.get("role") not in ("transport", "admin"):
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applications WHERE status IN ('pending','transport_rejected') ORDER BY submitted_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/transport/review/<pass_id>", methods=["POST"])
def transport_review(pass_id):
    if "user" not in session or session.get("role") not in ("transport", "admin"):
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    action  = data.get("action")   # "verify" or "reject"
    remarks = data.get("remarks", "")
    if action not in ("verify", "reject"):
        return jsonify({"error": "Invalid action"}), 400

    new_status = "transport_verified" if action == "verify" else "transport_rejected"
    conn = get_db()
    conn.execute("""
        UPDATE applications SET status=?, transport_remarks=?, transport_reviewed_at=datetime('now','localtime')
        WHERE pass_id=?
    """, (new_status, remarks, pass_id))
    conn.execute("INSERT INTO audit_log (pass_id, action, done_by, remarks) VALUES (?,?,?,?)",
                 (pass_id, f"Transport: {action}", session["user"], remarks))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "status": new_status})


# ─────────────────────────── PRINCIPAL APIs ─────────────────────

@app.route("/api/principal/applications")
def principal_applications():
    if "user" not in session or session.get("role") not in ("principal", "admin"):
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applications WHERE status IN ('transport_verified','principal_rejected') ORDER BY submitted_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/principal/review/<pass_id>", methods=["POST"])
def principal_review(pass_id):
    if "user" not in session or session.get("role") not in ("principal", "admin"):
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    action  = data.get("action")   # "approve" or "reject"
    remarks = data.get("remarks", "")
    if action not in ("approve", "reject"):
        return jsonify({"error": "Invalid action"}), 400

    new_status = "approved" if action == "approve" else "principal_rejected"
    conn = get_db()
    conn.execute("""
        UPDATE applications SET status=?, principal_remarks=?, principal_reviewed_at=datetime('now','localtime')
        WHERE pass_id=?
    """, (new_status, remarks, pass_id))
    conn.execute("INSERT INTO audit_log (pass_id, action, done_by, remarks) VALUES (?,?,?,?)",
                 (pass_id, f"Principal: {action}", session["user"], remarks))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "status": new_status})


# ─────────────────────────── ADMIN APIs ─────────────────────────

@app.route("/api/admin/all")
def admin_all():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    rows = conn.execute("SELECT * FROM applications ORDER BY submitted_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/stats")
def admin_stats():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    stats = {}
    for status in ["pending", "transport_verified", "transport_rejected",
                   "approved", "principal_rejected"]:
        count = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status=?", (status,)
        ).fetchone()[0]
        stats[status] = count
    stats["total"] = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    conn.close()
    return jsonify(stats)


@app.route("/api/admin/log")
def admin_log():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────── UPLOADS ────────────────────────────

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────────────────── MAIN ───────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
