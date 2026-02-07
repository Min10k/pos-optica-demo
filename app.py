import os
import psycopg
from flask import Flask

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida")

DATABASE_URL = DATABASE_URL.strip()  # 🔒 elimina espacios invisibles

def get_db():
    return psycopg.connect(DATABASE_URL)


@app.route("/")
def test():
    try:
        conn = psycopg.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return "✅ Conexión a DB OK"
    except Exception as e:
        return f"❌ Error DB: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
