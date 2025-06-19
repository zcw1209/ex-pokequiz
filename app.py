from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # 替換為更安全的 key

# 首頁：出題
@app.route("/")
def index():
    # 隨機選擇一隻寶可夢
    pokemon_id = random.randint(1, 366)
    api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        return "PokeAPI 請求失敗，請稍後再試。"

    data = response.json()

    pokemon_info = {
        "id": data["id"],
        "name": data["name"],
        "types": [t["type"]["name"] for t in data["types"]],
        "height": data["height"],
        "weight": data["weight"],
        "image": data["sprites"]["front_default"]
    }

    # 存入 session
    session["current_pokemon"] = pokemon_info

    return render_template("index.html", info=pokemon_info)

# 檢查答案
@app.route("/guess", methods=["POST"])
def guess():
    user_guess = request.form.get("guess", "").strip().lower()
    answer = session.get("current_pokemon", {}).get("name", "").lower()

    if user_guess == answer:
        correct = True
    else:
        correct = False

    return render_template("result.html", correct=correct, answer=session.get("current_pokemon"))

# 再來一題
@app.route("/restart")
def restart():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)