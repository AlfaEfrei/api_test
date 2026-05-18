from flask import Flask, jsonify, redirect, render_template, url_for

from storage import get_last_run, init_db, list_runs, save_run
from tester.runner import run_all_tests

app = Flask(__name__)
init_db()


@app.get("/")
def index():
    return redirect(url_for("dashboard"))


@app.get("/run")
def run_tests():
    """Déclenche un run de tests et l'enregistre en SQLite."""
    result = run_all_tests()
    save_run(result)
    return jsonify(result)


@app.get("/dashboard")
def dashboard():
    runs = list_runs(limit=20)
    return render_template("dashboard.html", runs=runs, last_run=runs[0] if runs else None)


@app.get("/api/runs")
def api_runs():
    return jsonify(list_runs(limit=50))


@app.get("/health")
def health():
    last = get_last_run()
    if not last:
        return jsonify({"status": "unknown", "message": "Aucun run enregistré"}), 200

    failed = last["summary"].get("failed", 1)
    status = "healthy" if failed == 0 else "degraded"
    http_code = 200 if failed == 0 else 503
    return jsonify({
        "status": status,
        "last_run_at": last["timestamp"],
        "summary": last["summary"],
    }), http_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
