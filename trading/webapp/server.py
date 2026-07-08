"""The local web app — your trading operating system in a browser.

Start it with:

    python -m trading.webapp

then open the address it prints (http://127.0.0.1:8787) in any browser.
It runs only on your own machine; nothing is exposed to the internet.

The browser shows a live view and lets you approve/reject trades with
buttons. Every button press calls this server, which runs the SAME rules and
broker path as the command-line tools — the web app is a friendlier face on
the identical engine, not a second system.
"""

import io
import threading
from contextlib import redirect_stdout
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from trading.webapp import actions

app = Flask(__name__, static_folder=None)
_STATIC = Path(__file__).resolve().parent / "static"

# Background job state (digest / review are slow — run off the request thread).
_job = {"running": False, "kind": None, "log": "", "done": False, "error": None}
_job_lock = threading.Lock()


def _run_job(kind: str) -> None:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            if kind == "digest":
                from trading.digest import main as digest_main
                digest_main()
            elif kind == "review":
                from trading.review import main as review_main
                review_main()
        with _job_lock:
            _job.update(running=False, done=True, log=buf.getvalue(), error=None)
    except Exception as e:  # noqa: BLE001
        with _job_lock:
            _job.update(running=False, done=True, log=buf.getvalue(), error=str(e))


@app.route("/")
def index():
    return send_from_directory(_STATIC, "app.html")


@app.route("/api/state")
def api_state():
    try:
        return jsonify({"ok": True, "state": actions.full_state()})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "message": str(e)}), 200


@app.route("/api/chart/<ticker>")
def api_chart(ticker):
    try:
        return jsonify({"ok": True, "chart": actions.chart_data(ticker)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "message": str(e)}), 200


@app.route("/api/approve/<int:rec_id>", methods=["POST"])
def api_approve(rec_id):
    return jsonify(actions.approve(rec_id))


@app.route("/api/reject/<int:rec_id>", methods=["POST"])
def api_reject(rec_id):
    reason = (request.json or {}).get("reason", "") if request.is_json else ""
    return jsonify(actions.reject(rec_id, reason))


@app.route("/api/run/<kind>", methods=["POST"])
def api_run(kind):
    if kind not in ("digest", "review"):
        return jsonify({"ok": False, "message": "Unknown job."}), 400
    with _job_lock:
        if _job["running"]:
            return jsonify({"ok": False,
                            "message": f"A {_job['kind']} is already running."})
        _job.update(running=True, kind=kind, done=False, log="", error=None)
    threading.Thread(target=_run_job, args=(kind,), daemon=True).start()
    return jsonify({"ok": True, "message": f"{kind} started."})


@app.route("/api/job")
def api_job():
    with _job_lock:
        return jsonify(dict(_job))


def main() -> int:
    (_STATIC).mkdir(exist_ok=True)
    host, port = "127.0.0.1", 8787
    print()
    print("=" * 60)
    print("  Trading operating system — starting the local web app")
    print("=" * 60)
    print(f"  Open this address in your browser:")
    print(f"      http://{host}:{port}")
    print()
    print("  It runs only on THIS computer. Press Ctrl+C here to stop.")
    print("=" * 60)
    print()
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
