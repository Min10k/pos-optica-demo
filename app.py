import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

# ======================
# CONEXIÓN BD (NEON)
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(
        DATABASE_URL,
        sslmode="require"
    )

# ======================
# USUARIOS DEMO
# ======================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]

        if u in USUARIOS and USUARIOS[u]["password"] == p:
            session["usuario"] = u
            session["rol"] = USUARIOS[u]["rol"]
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required><br><br>
        <input name="password" type="password" placeholder="Contraseña" required><br><br>
        <button>Entrar</button>
    </form>
    """

# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    estado = "🔴 Caja CERRADA"

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id 
            FROM caja 
            WHERE cerrada = FALSE 
            ORDER BY fecha_apertura DESC 
            LIMIT 1
        """)
        caja = cur.fetchone()
        cur.close()
        conn.close()

        if caja:
            estado = "🟢 Caja ABIERTA"
    except:
        estado = "⚠️ Error consultando caja"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p><b>Usuario:</b> {session['usuario']}</p>
    <p><b>Estado:</b> {estado}</p>
    <hr>

    <a href="/abrir_caja">Abrir caja</a><br><br>
    <a href="/ventas">Nueva venta</a><br><br>
    <a href="/inventario">Inventario</a><br><br>
    <a href="/clientes">Clientes</a><br><br>
    <a href="/cerrar_caja">Cerrar caja</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
