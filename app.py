from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # 替換為更安全的 key

# 首頁：出題
@app.route("/")
def index():
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
        "types": [t["type"]["name"] for t in data["types"]],
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
    if user_guess == english_name:
        correct = True
    elif user_guess == chinese_name.lower():
        correct = True

    return render_template("result.html", correct=correct, answer=pokemon)


# 再來一題
@app.route("/restart")
def restart():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)