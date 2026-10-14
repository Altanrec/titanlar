import os
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deploying")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER", "") == "true"
csrf = CSRFProtect(app)

DB_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).with_name("titanlar.db")))

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT NOT NULL COLLATE NOCASE UNIQUE, 
                email TEXT NOT NULL COLLATE NOCASE UNIQUE, 
                password_hash TEXT NOT NULL, 
                avatar TEXT DEFAULT 'default.png',
                points INTEGER DEFAULT 0,
                snake_high INTEGER DEFAULT 0,
                xox_wins INTEGER DEFAULT 0,
                memory_best INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("account"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 24 or not username.replace("_", "").replace("-", "").isalnum():
            flash("Kullanıcı adı 3-24 karakter olmalı; harf, rakam, _ veya - kullan.", "error")
        elif len(email) > 254 or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Geçerli bir e-posta adresi gir.", "error")
        elif len(password) < 8:
            flash("Şifren en az 8 karakter olmalı.", "error")
        else:
            try:
                db = get_db()
                cur = db.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, generate_password_hash(password)))
                db.commit()
                session.clear()
                session["user_id"] = cur.lastrowid
                session["username"] = username
                flash("Hesabın oluşturuldu, hoş geldin!", "success")
                return redirect(url_for("account"))
            except sqlite3.IntegrityError:
                flash("Bu kullanıcı adı veya e-posta zaten kullanılıyor.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("account"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE", (identity, identity)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Tekrar hoş geldin!", "success")
            return redirect(url_for("account"))
        flash("Bilgiler hatalı. Kullanıcı adı/e-posta ve şifreni kontrol et.", "error")
    return render_template("auth.html", mode="login")

@app.route("/account", methods=["GET", "POST"])
def account():
    if not session.get("user_id"):
        flash("Önce giriş yapmalısın.", "error")
        return redirect(url_for("login"))
    
    db = get_db()
    if request.method == "POST":
        avatar = request.form.get("avatar", "default.png")
        db.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, session["user_id"]))
        db.commit()
        flash("Avatarın güncellendi!", "success")
        return redirect(url_for("account"))

    user = db.execute("SELECT username, email, avatar, points, snake_high, xox_wins, memory_best, created_at FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return redirect(url_for("login"))
    return render_template("account.html", user=user)

@app.route("/leaderboard")
def leaderboard():
    db = get_db()
    users = db.execute("SELECT username, avatar, points, snake_high, xox_wins, memory_best FROM users ORDER BY points DESC, username ASC LIMIT 50").fetchall()
    return render_template("leaderboard.html", users=users)

@app.route("/games")
def games_hub():
    return render_template("games.html")

@app.route("/games/snake")
def game_snake():
    return render_template("snake.html")

@app.route("/games/xox")
def game_xox():
    return render_template("xox.html")

@app.route("/games/memory")
def game_memory():
    return render_template("memory.html")

@app.route("/api/score", methods=["POST"])
@csrf.exempt  # JS oyunfetch istekleri için kolaylık
def update_score():
    if not session.get("user_id"):
        return jsonify({"status": "unauthorized"}), 401
    
    data = request.get_json() or {}
    game = data.get("game")
    val = int(data.get("val", 0))
    
    db = get_db()
    user_id = session["user_id"]
    user = db.execute("SELECT snake_high, xox_wins, memory_best, points FROM users WHERE id = ?", (user_id,)).fetchone()
    
    updated = False
    if game == "snake" and val > user["snake_high"]:
        diff = val - user["snake_high"]
        db.execute("UPDATE users SET snake_high = ?, points = points + ? WHERE id = ?", (val, diff * 5, user_id))
        updated = True
    elif game == "xox" and val > user["xox_wins"]:
        diff = val - user["xox_wins"]
        db.execute("UPDATE users SET xox_wins = ?, points = points + ? WHERE id = ?", (val, diff * 20, user_id))
        updated = True
    elif game == "memory" and (user["memory_best"] == 0 or val < user["memory_best"]):
        # Hafıza oyununda süre/hamle ne kadar azsa o kadar iyi, yeni rekor bonusu
        db.execute("UPDATE users SET memory_best = ?, points = points + 50 WHERE id = ?", (val, user_id))
        updated = True
        
    db.commit()
    return jsonify({"status": "success", "updated": updated})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Güvenli şekilde çıkış yaptın.", "success")
    return redirect(url_for("home"))

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
