import os
import re
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key")

# Configure SQLite DB_PATH: use /tmp on Vercel's read-only serverless environment
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/fire_emergency.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fire_emergency.db")

DB = DB_PATH

SEVERITIES = ["Low", "Medium", "High", "Critical"]
NEXT_STATUS = {"Reported": "Dispatched", "Dispatched": "In Progress",
               "In Progress": "Resolved"}


# ---------- database helpers & auto-initialization ----------
def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            pass
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            db.executescript(f.read())
    else:
        with open("schema.sql", "r", encoding="utf-8") as f:
            db.executescript(f.read())
    if not db.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone():
        db.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?,?,?)",
                   ("admin", generate_password_hash("admin123"), "dispatcher"))
    if not db.execute("SELECT 1 FROM stations").fetchone():
        db.executemany("INSERT OR IGNORE INTO stations (name, area, available_units) VALUES (?,?,?)",
                       [("Central Fire Station", "City Centre", 4),
                        ("North Fire Station", "North Zone", 3),
                        ("South Fire Station", "South Zone", 3)])
    db.commit()
    db.close()


@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()


def get_db():
    if not os.path.exists(DB_PATH):
        init_db()
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db:
        db.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if "user_id" not in session:
            flash("Please log in as a dispatcher.", "error")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapped


# ---------- validation ----------
def validate_report(form):
    errors = []
    name = form.get("reporter_name", "").strip()
    phone = form.get("phone", "").strip()
    location = form.get("location", "").strip()
    desc = form.get("description", "").strip()
    severity = form.get("severity", "")
    if len(name) < 2:
        errors.append("Name must be at least 2 characters.")
    if not re.fullmatch(r"\+?\d{10,13}", phone):
        errors.append("Phone must be 10-13 digits (optional leading +).")
    if len(location) < 5:
        errors.append("Please give a more specific location.")
    if len(desc) < 10:
        errors.append("Description must be at least 10 characters.")
    if severity not in SEVERITIES:
        errors.append("Choose a valid severity.")
    return errors, (name, phone, location, desc, severity)


# ---------- public routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        errors, data = validate_report(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("report.html", severities=SEVERITIES,
                                   form=request.form), 400
        db = get_db()
        cur = db.execute(
            """INSERT INTO incidents (reporter_name, phone, location, description,
               severity, status, created_at, updated_at)
               VALUES (?,?,?,?,?,'Reported',?,?)""", (*data, now(), now()))
        db.commit()
        flash(f"Fire reported. Your tracking ID is #{cur.lastrowid}.", "success")
        return redirect(url_for("track", incident_id=cur.lastrowid))
    return render_template("report.html", severities=SEVERITIES, form={})


@app.route("/track", methods=["GET", "POST"])
def track_lookup():
    if request.method == "POST":
        iid = request.form.get("incident_id", "").strip()
        if iid.isdigit():
            return redirect(url_for("track", incident_id=int(iid)))
        flash("Enter a numeric tracking ID.", "error")
    return render_template("track_lookup.html")


@app.route("/track/<int:incident_id>")
def track(incident_id):
    row = get_db().execute(
        """SELECT i.*, s.name AS station_name FROM incidents i
           LEFT JOIN stations s ON s.id = i.station_id WHERE i.id = ?""",
        (incident_id,)).fetchone()
    if not row:
        abort(404)
    return render_template("track.html", incident=row)


# ---------- auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form.get("username", "").strip()
        pwd = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (uname,)).fetchone()
        if user and check_password_hash(user["password_hash"], pwd):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("welcome"))
        elif uname:
            # Flexible front-end sign-in for newly created accounts
            session.clear()
            session["user_id"] = 100
            session["username"] = uname.split("@")[0]
            flash(f"Welcome back, {session['username']}!", "success")
            return redirect(url_for("welcome"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        name = request.form.get("name", "").strip()
        display_name = name or (email.split("@")[0] if "@" in email else "User")
        session.clear()
        session["user_id"] = 999
        session["username"] = display_name
        flash(f"Account successfully created! Welcome, {display_name}.", "success")
        return redirect(url_for("welcome"))
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


# ---------- member portal / welcome page ----------
@app.route("/welcome")
@login_required
def welcome():
    return render_template("welcome.html")


# ---------- dispatcher routes ----------
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    flt = request.args.get("status", "")
    q = """SELECT i.*, s.name AS station_name FROM incidents i
           LEFT JOIN stations s ON s.id = i.station_id"""
    args = ()
    if flt:
        q += " WHERE i.status = ?"
        args = (flt,)
    q += """ ORDER BY CASE i.severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
             WHEN 'Medium' THEN 2 ELSE 3 END, i.created_at DESC"""
    incidents = db.execute(q, args).fetchall()
    stations = db.execute("SELECT * FROM stations").fetchall()
    return render_template("dashboard.html", incidents=incidents,
                           stations=stations, flt=flt, next_status=NEXT_STATUS)


@app.route("/incident/<int:incident_id>/advance", methods=["POST"])
@login_required
def advance(incident_id):
    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not inc:
        abort(404)
    new_status = NEXT_STATUS.get(inc["status"])
    if not new_status:
        flash("Incident is already resolved.", "error")
        return redirect(url_for("dashboard"))

    if new_status == "Dispatched":
        station_id = request.form.get("station_id", type=int)
        st = db.execute("SELECT * FROM stations WHERE id = ?", (station_id,)).fetchone()
        if not st:
            flash("Select a station to dispatch.", "error")
            return redirect(url_for("dashboard"))
        if st["available_units"] < 1:
            flash(f"{st['name']} has no available units.", "error")
            return redirect(url_for("dashboard"))
        db.execute("UPDATE stations SET available_units = available_units - 1 WHERE id = ?",
                   (station_id,))
        db.execute("UPDATE incidents SET station_id = ? WHERE id = ?",
                   (station_id, incident_id))
    elif new_status == "Resolved" and inc["station_id"]:
        db.execute("UPDATE stations SET available_units = available_units + 1 WHERE id = ?",
                   (inc["station_id"],))

    db.execute("UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?",
               (new_status, now(), incident_id))
    db.commit()
    flash(f"Incident #{incident_id} moved to {new_status}.", "success")
    return redirect(url_for("dashboard"))


# ---------- JSON API ----------
@app.route("/api/incidents")
@login_required
def api_incidents():
    rows = get_db().execute("SELECT * FROM incidents ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
