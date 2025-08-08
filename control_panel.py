import os
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.getenv("CONTROL_PANEL_SECRET", "default_secret")
PASSWORD = os.getenv("CONTROL_PANEL_PASSWORD")
COUNT_FILE = "solved_count.json"

def get_solved_count():
    if os.path.exists(COUNT_FILE):
        try:
            import json
            with open(COUNT_FILE, "r") as f:
                return json.load(f).get("count", 0)
        except Exception:
            return 0
    return 0

def reset_solved_count():
    import json
    with open(COUNT_FILE, "w") as f:
        json.dump({"count": 0}, f)

PANEL_HTML = """
<!doctype html>
<title>SpamuBot Control Panel</title>
<h2>SpamuBot Control Panel</h2>
{% if not session.get('logged_in') %}
  <form method="post">
    <input type="password" name="password" placeholder="Password" autofocus>
    <input type="submit" value="Login">
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
  </form>
{% else %}
  <p>Welcome to the control panel!</p>
  <h3>Bot Info</h3>
  <ul>
    <li>Solved Counter: <b>{{ solved_count }}</b></li>
  </ul>
  <h3>Actions</h3>
  <form method="post" action="{{ url_for('reset_counter') }}">
    <button type="submit" onclick="return confirm('Reset solved counter?')">Reset Solved Counter</button>
  </form>
  <form method="post" action="{{ url_for('shutdown') }}">
    <button type="submit" style="color:red;" onclick="return confirm('Shutdown bot?')">Shutdown Bot</button>
  </form>
  <form method="post" action="{{ url_for('logout') }}">
    <button type="submit">Logout</button>
  </form>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Incorrect password."
    solved_count = get_solved_count() if session.get("logged_in") else None
    return render_template_string(PANEL_HTML, error=error, solved_count=solved_count)

@app.route("/reset_counter", methods=["POST"])
def reset_counter():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    reset_solved_count()
    return redirect(url_for("index"))

@app.route("/shutdown", methods=["POST"])
def shutdown():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    os._exit(0)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))

def start_control_panel():
    app.run(host="0.0.0.0", port=5000)
