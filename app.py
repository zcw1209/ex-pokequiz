from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
import pymysql
import requests
import random

import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)

# 判斷要載入哪一份環境檔案
mode = os.getenv("APP_MODE", "dev")  # 預設是 dev
if mode == "prod":
    load_dotenv(".env.prod")
else:
    load_dotenv(".env.dev")

# MySQL 設定
db = pymysql.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

@app.before_request
def make_session_permanent():
    session.permanent = True

# 首頁
@app.route("/")
def index():
    # 沒有寶可夢資料或是點了新題目就重設
    if "current_pokemon" not in session or request.args.get("new") == "1":
        session["guess_count"] = 0

        pokemon_id = random.randint(1, 152)
        api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        res = requests.get(api_url)
        if res.status_code != 200:
            return "取得寶可夢資料失敗"

        data = res.json()
        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
        species_res = requests.get(species_url)
        chinese_name = ""
        if species_res.status_code == 200:
            species_data = species_res.json()
            for name_info in species_data["names"]:
                if name_info["language"]["name"] == "zh-Hant":
                    chinese_name = name_info["name"]
                    break

        type_translation = {
            "normal": "一般", "fire": "火", "water": "水", "electric": "電",
            "grass": "草", "ice": "冰", "fighting": "格鬥", "poison": "毒",
            "ground": "地面", "flying": "飛行", "psychic": "超能力", "bug": "蟲",
            "rock": "岩石", "ghost": "幽靈", "dragon": "龍", "dark": "惡",
            "steel": "鋼", "fairy": "妖精"
        }

        pokemon_info = {
            "id": data["id"],
            "name": data["name"],
            "types": [{"en": t["type"]["name"], "zh": type_translation.get(t["type"]["name"], t["type"]["name"])} for t in data["types"]],
            "height": data["height"],
            "weight": data["weight"],
            "image": data["sprites"]["front_default"],
            "chinese_name": chinese_name
        }

        session["current_pokemon"] = pokemon_info

    return render_template("index.html", info=session["current_pokemon"])


# 猜寶可夢
@app.route("/guess", methods=["POST"])
def guess():
    user_guess = request.form.get("guess", "").strip().lower()
    pokemon = session.get("current_pokemon", {})
    english_name = pokemon.get("name", "").lower()
    chinese_name = pokemon.get("chinese_name", "").strip()
    guess_count = session.get("guess_count", 0)

    correct = False
    if user_guess == english_name or user_guess == chinese_name.lower():
        correct = True
        total_guesses = guess_count + 1

        if "username" in session:
            with db.cursor() as cursor:
                # 找出使用者 ID
                cursor.execute("SELECT id FROM users WHERE username=%s", (session["username"],))
                user = cursor.fetchone()
                if user:
                    user_id = user["id"]

                    # ✅ 1. 先寫入 pokedex 表（若尚未存在）
                    insert_pokedex = """
                    INSERT INTO pokedex (id, name_en, name_zh, image_url)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name_en=VALUES(name_en)
                    """
                    cursor.execute(insert_pokedex, (
                        pokemon["id"],
                        pokemon["name"],
                        pokemon["chinese_name"],
                        pokemon["image"]
                    ))

                    # ✅ 2. 再寫入 user_pokedex 關聯（避免重複）
                    insert_user_pokedex = """
                    INSERT IGNORE INTO user_pokedex (user_id, pokemon_id)
                    VALUES (%s, %s)
                    """
                    cursor.execute(insert_user_pokedex, (user_id, pokemon["id"]))

                    db.commit()
    else:
        session["guess_count"] = guess_count + 1
        total_guesses = session["guess_count"]

    return render_template("result.html",
                           correct=correct,
                           answer=pokemon,
                           guess_count=session.get("guess_count", 0),
                           total_guesses=total_guesses)



# 註冊
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        if not username or not password or not name or not email or not phone:
            flash("請填寫完整資訊")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            with db.cursor() as cursor:
                sql = "INSERT INTO users (username, password, name, email, phone) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(sql, (username, hashed_password, name, email, phone))
                db.commit()
                flash("註冊成功，請登入")
                return redirect(url_for("login"))
        except pymysql.err.IntegrityError:
            flash("使用者名稱已存在")
            return redirect(url_for("register"))

    return render_template("register.html")


# 登入
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        session["temp_username"] = username

        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user["password"], password):
                session["username"] = user["username"]
                session.pop("temp_username", None)
                flash("登入成功！", "success")
                return redirect(url_for("index"))
            else:
                flash("帳號或密碼錯誤", "error")
                return redirect(url_for("login"))

    return render_template("login.html", temp_username=session.get("temp_username", ""))


# 登出
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("您已登出")
    return redirect(url_for("login"))


# 我的圖鑑
@app.route("/my_pokedex")
def my_pokedex():
    if "username" not in session:
        flash("請先登入以查看你的圖鑑")
        return redirect(url_for("login"))

    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE username=%s", (session["username"],))
        user = cursor.fetchone()
        user_id = user["id"]

        sql = """
        SELECT p.id, p.name_en, p.name_zh, p.image_url
        FROM user_pokedex up
        JOIN pokedex p ON up.pokemon_id = p.id
        WHERE up.user_id = %s
        """
        cursor.execute(sql, (user_id,))
        pokemons = cursor.fetchall()

    return render_template("my_pokedex.html", pokemons=pokemons)


if __name__ == "__main__":
    app.run(debug=True)
