from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # 替換為更安全的 key

#避免某些瀏覽器 session 不保存
@app.before_request
def make_session_permanent():
    session.permanent = True



# 首頁：出題
@app.route("/")
def index():

   # 每次進入新一題才重設
    if "current_pokemon" not in session or request.args.get("new") == "1":
        session["guess_count"] = 0

    type_translation = {
        "normal": "一般",
        "fire": "火",
        "water": "水",
        "electric": "電",
        "grass": "草",
        "ice": "冰",
        "fighting": "格鬥",
        "poison": "毒",
        "ground": "地面",
        "flying": "飛行",
        "psychic": "超能力",
        "bug": "蟲",
        "rock": "岩石",
        "ghost": "幽靈",
        "dragon": "龍",
        "dark": "惡",
        "steel": "鋼",
        "fairy": "妖精"
    }


    # 隨機選擇一隻寶可夢
    pokemon_id = random.randint(1, 152)
    api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        return "PokeAPI 請求失敗，請稍後再試。"

    data = response.json()

    # 加在取得 data 後面
    species_url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
    species_res = requests.get(species_url)

    chinese_name = ""
    if species_res.status_code == 200:
        species_data = species_res.json()
        for name_info in species_data["names"]:
            if name_info["language"]["name"] == "zh-Hant":
                chinese_name = name_info["name"]
                break


    pokemon_info = {
        "id": data["id"],
        "name": data["name"],
        "types": [
            {
                "en": t["type"]["name"],
                "zh": type_translation.get(t["type"]["name"], t["type"]["name"])
            }
            for t in data["types"]
        ],
        "height": data["height"],
        "weight": data["weight"],
        "image": data["sprites"]["front_default"],
        "chinese_name": chinese_name
    }


    # 存入 session
    session["current_pokemon"] = pokemon_info

    return render_template("index.html", info=pokemon_info)

# 檢查答案
@app.route("/guess", methods=["POST"])
def guess():
    user_guess = request.form.get("guess", "").strip().lower()
    pokemon = session.get("current_pokemon", {})
    english_name = pokemon.get("name", "").lower()
    chinese_name = pokemon.get("chinese_name", "").strip()

    correct = False
    guess_count = session.get("guess_count", 0)

    if user_guess == english_name or user_guess == chinese_name.lower():
        correct = True
        total_guesses = guess_count + 1
    else:
        session["guess_count"] = guess_count + 1
        total_guesses = session["guess_count"]

    return render_template("result.html",
                           correct=correct,
                           answer=pokemon,
                           guess_count=session.get("guess_count", 0),
                           total_guesses=total_guesses)




# 再來一題
@app.route("/restart")
def restart():
    session["guess_count"] = 0
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)