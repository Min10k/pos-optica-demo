from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "POS Óptica funcionando 🚀👓"

if __name__ == "__main__":
    app.run()
