import os
import time
import json
from flask import Flask, request, render_template_string, redirect, url_for, session, abort, jsonify
import threading

app = Flask(__name__)
app.secret_key = os.getenv("CONTROL_PANEL_SECRET", "default_secret")
PASSWORD = os.getenv("CONTROL_PANEL_PASSWORD")
COUNT_FILE = "solved_count.json"
ENABLED_FLAG = "bot_enabled.flag"
STATUS_FILE = "bot_status.txt"
SESSION_TIMEOUT = 900  # 15 minutes
VERSION = "3.3"
def get_solved_count():
    if os.path.exists(COUNT_FILE):
        try:
            with open(COUNT_FILE, "r") as f:
                return json.load(f).get("count", 0)
        except Exception:
            return 0
    return 0

def reset_solved_count():
    with open(COUNT_FILE, "w") as f:
        json.dump({"count": 0}, f)

def is_bot_enabled():
    return os.path.exists(ENABLED_FLAG)

def set_bot_enabled(enabled: bool):
    if enabled:
        with open(ENABLED_FLAG, "w") as f:
            f.write("enabled")
    else:
        if os.path.exists(ENABLED_FLAG):
            os.remove(ENABLED_FLAG)

def get_bot_status_text():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def set_bot_status_text(text):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())

def csrf_token():
    if "csrf_token" not in session:
        import secrets
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]

def check_csrf():
    token = session.get("csrf_token")
    form_token = request.form.get("csrf_token")
    if not token or not form_token or token != form_token:
        abort(400, "CSRF token mismatch")

def check_session_timeout():
    now = int(time.time())
    last = session.get("last_active", now)
    if now - last > SESSION_TIMEOUT:
        session.clear()
        return False
    session["last_active"] = now
    return True

def get_bot_status():
    return {
        "enabled": is_bot_enabled(),
        "solved_count": get_solved_count(),
        "custom_status": get_bot_status_text()
    }

def dashboard_restart():
    os._exit(100)  # Supervisor should restart the process

def dashboard_shutdown():
    os._exit(0)

PANEL_HTML = """
<!doctype html>
<html lang="en">
<head>
  <title>SpamuBot Control Panel</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; background: #f7f7fa; margin: 0; padding: 0; }
    .panel { max-width: 420px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 2em; }
    h2 { margin-top: 0; }
    .info { background: #eef; padding: 1em; border-radius: 5px; margin-bottom: 1em; }
    .actions form { display: inline-block; margin: 0.5em 0.5em 0.5em 0; }
    button { padding: 0.5em 1.2em; border-radius: 4px; border: none; background: #3a7; color: #fff; font-weight: bold; cursor: pointer; }
    button[disabled] { background: #aaa; }
    .danger { background: #c33; }
    .logout { background: #888; }
    .status-enabled { color: #080; font-weight: bold; }
    .status-disabled { color: #c33; font-weight: bold; }
    .footer { margin-top: 2em; color: #888; font-size: 0.9em; text-align: center; }
    .error { color: #c33; }
    .status-edit { margin-top: 1em; }
    input[type="text"] { width: 90%; padding: 0.4em; }
  </style>
</head>
<body>
<div class="panel">
  <h2>SpamuBot Control Panel</h2>
  {% if not session.get('logged_in') %}
    <form method="post">
      <input type="password" name="password" placeholder="Password" autofocus>
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <input type="submit" value="Login">
      {% if error %}<p class="error">{{ error }}</p>{% endif %}
    </form>
  {% else %}
    <div class="info">
      <b>Bot Status:</b>
      {% if bot_enabled %}
        <span class="status-enabled">ENABLED</span>
      {% else %}
        <span class="status-disabled">DISABLED</span>
      {% endif %}
      <br>
      <b>Solved Counter:</b> <span>{{ solved_count }}</span>
      <br>
      <b>Custom Status:</b> <span>{{ custom_status or "(not set)" }}</span>
    </div>
    <div class="actions">
      <form method="post" action="{{ url_for('enable_bot') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" {% if bot_enabled %}disabled{% endif %}>Enable Bot</button>
      </form>
      <form method="post" action="{{ url_for('disable_bot') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" {% if not bot_enabled %}disabled{% endif %}>Disable Bot</button>
      </form>
      <form method="post" action="{{ url_for('reset_counter') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" onclick="return confirm('Reset solved counter?')">Reset Solved Counter</button>
      </form>
      <form method="post" action="{{ url_for('restart') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit">Restart Bot</button>
      </form>
      <form method="post" action="{{ url_for('shutdown') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" class="danger" onclick="return confirm('Shutdown bot?')">Shutdown Bot</button>
      </form>
      <form method="post" action="{{ url_for('logout') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" class="logout">Logout</button>
      </form>
    </div>
    <div class="status-edit">
      <form method="post" action="{{ url_for('edit_status') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="text" name="custom_status" value="{{ custom_status }}" maxlength="100" placeholder="Set custom status...">
        <button type="submit">Update Status</button>
      </form>
      <form method="post" action="{{ url_for('set_counter') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="number" name="solved_count" min="0" value="{{ solved_count }}">
        <button type="submit">Set Solved Counter</button>
      </form>
    </div>
  {% endif %}
  <div class="footer">
    SpamuBot v3.3 HF2 Control Panel &copy; 2025
  </div>
</div>
</body>
</html>
"""

@app.before_request
def before_request():
    if session.get("logged_in"):
        if not check_session_timeout():
            return redirect(url_for("logout"))

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        check_csrf()
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            session["last_active"] = int(time.time())
            csrf_token()  # ensure token is set
            return redirect(url_for("index"))
        else:
            error = "Incorrect password."
    solved_count = get_solved_count() if session.get("logged_in") else None
    bot_enabled = is_bot_enabled() if session.get("logged_in") else None
    custom_status = get_bot_status_text() if session.get("logged_in") else None
    return render_template_string(PANEL_HTML, error=error, solved_count=solved_count, bot_enabled=bot_enabled, csrf_token=csrf_token(), custom_status=custom_status)

@app.route("/enable_bot", methods=["POST"])
def enable_bot():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    set_bot_enabled(True)
    return redirect(url_for("index"))

@app.route("/disable_bot", methods=["POST"])
def disable_bot():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    set_bot_enabled(False)
    return redirect(url_for("index"))

@app.route("/reset_counter", methods=["POST"])
def reset_counter():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    reset_solved_count()
    return redirect(url_for("index"))

@app.route("/set_counter", methods=["POST"])
def set_counter():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    try:
        count = int(request.form.get("solved_count", 0))
        with open(COUNT_FILE, "w") as f:
            json.dump({"count": count}, f)
    except Exception:
        pass
    return redirect(url_for("index"))

@app.route("/edit_status", methods=["POST"])
def edit_status():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    status = request.form.get("custom_status", "")
    set_bot_status_text(status)
    return redirect(url_for("index"))

@app.route("/restart", methods=["POST"])
def restart():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    threading.Thread(target=dashboard_restart, daemon=True).start()
    return "Restarting...", 200

@app.route("/shutdown", methods=["POST"])
def shutdown():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    check_csrf()
    os._exit(0)

@app.route("/logout", methods=["POST"])
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("index"))

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(get_bot_status())

@app.route("/api/enabled", methods=["GET", "POST"])
def api_enabled():
    if request.method == "GET":
        return jsonify({"enabled": is_bot_enabled()})
    elif request.method == "POST":
        enabled = request.json.get("enabled", True)
        set_bot_enabled(bool(enabled))
        return jsonify({"enabled": is_bot_enabled()})

@app.route("/api/solved_count", methods=["GET", "POST"])
def api_solved_count():
    if request.method == "GET":
        return jsonify({"solved_count": get_solved_count()})
    elif request.method == "POST":
        count = int(request.json.get("solved_count", 0))
        with open(COUNT_FILE, "w") as f:
            json.dump({"count": count}, f)
        return jsonify({"solved_count": get_solved_count()})

@app.route("/api/custom_status", methods=["GET", "POST"])
def api_custom_status():
    if request.method == "GET":
        return jsonify({"custom_status": get_bot_status_text()})
    elif request.method == "POST":
        status = request.json.get("custom_status", "")
        set_bot_status_text(status)
        return jsonify({"custom_status": get_bot_status_text()})

@app.route("/api/restart", methods=["POST"])
def api_restart():
    threading.Thread(target=dashboard_restart, daemon=True).start()
    return jsonify({"status": "restarting"})

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    threading.Thread(target=dashboard_shutdown, daemon=True).start()
    return jsonify({"status": "shutting down"})

def start_control_panel():
    app.run(host="0.0.0.0", port=5000)
