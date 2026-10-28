"""Neon Pong Arena web app. MySQL is optional; gameplay falls back to browser storage."""
from dotenv import load_dotenv

load_dotenv()
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-for-production")


def db_connection():
    try:
        import mysql.connector

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "Ahmad@786"),
            database=os.getenv("DB_NAME", "neon_pong_web"),
            connection_timeout=5,
        )

        print("✅ MySQL connected successfully!")
        return conn

    except Exception as e:
        print("❌ MySQL connection failed:", e)
        return None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    conn = db_connection()
    if not conn:
        return jsonify(ok=True, database="offline", message="Game works; progress is saved in this browser until MySQL is configured.")
    conn.close()
    return jsonify(ok=True, database="connected", message="MySQL connected")


@app.post("/api/matches")
def save_match():
    data = request.get_json(silent=True) or {}
    player = str(data.get("player", "Player"))[:40].strip() or "Player"
    level = max(1, min(12, int(data.get("level", 1))))
    won = bool(data.get("won", False))
    score = max(0, int(data.get("score", 0)))
    duration = max(0, int(data.get("duration", 0)))
    conn = db_connection()
    if not conn:
        return jsonify(ok=True, saved=False, message="MySQL is offline; the browser will keep your progress."), 200
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO web_matches (player_name, level_number, won, score, duration_seconds) VALUES (%s,%s,%s,%s,%s)", (player, level, won, score, duration))
        cur.execute("INSERT INTO web_progress (player_name, highest_level, total_wins, best_score) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE highest_level=GREATEST(highest_level, VALUES(highest_level)), total_wins=total_wins + VALUES(total_wins), best_score=GREATEST(best_score, VALUES(best_score))", (player, min(12, level + 1) if won else level, 1 if won else 0, score))
        conn.commit()
        return jsonify(ok=True, saved=True, message="Match saved to MySQL")
    except Exception as exc:
        conn.rollback()
        return jsonify(ok=False, saved=False, message="Could not save match. Check that the SQL setup was imported.", detail=str(exc)), 200
    finally:
        conn.close()


@app.get("/api/leaderboard")
def leaderboard():
    conn = db_connection()
    if not conn:
        return jsonify(ok=True, database="offline", players=[])
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT player_name AS player, total_wins AS wins, best_score AS bestScore, highest_level AS highestLevel FROM web_progress ORDER BY total_wins DESC, best_score DESC LIMIT 10")
        rows = cur.fetchall()
        return jsonify(ok=True, database="connected", players=rows)
    except Exception:
        return jsonify(ok=True, database="offline", players=[])
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
