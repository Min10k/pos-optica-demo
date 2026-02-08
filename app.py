import os
import psycopg
from flask import Flask, request, redirect, url_for, session

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_v1"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no definida")

DATABASE_URL = DATABASE_URL.strip()

def get_db():
    return psycopg.connect(DATABASE_URL)

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

        return "Credenciales incorrectas<br><a href='/'>Volver</a>"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required><br><br>
        <input type="password" name="password" placeholder="Contraseña" required><br><br>
        <button>Entrar</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p>Usuario: <b>{session['usuario']}</b></p>
    <hr>
    <a href="/pos">🧾 Ir al POS</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# POS VISUAL + PRODUCTOS REALES
# ======================
@app.route("/pos")
def pos():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    filas = ""
    for p in productos:
        filas += f"""
        <tr>
            <td>{p[0]}</td>
            <td>${p[1]}</td>
            <td>{p[2]}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>POS Óptica</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f2f2f2;
    margin: 0;
}}

header {{
    background: #2f3e46;
    color: white;
    padding: 15px;
    display: flex;
    justify-content: space-between;
}}

.container {{
    display: grid;
    grid-template-columns: 70% 30%;
    height: calc(100vh - 70px);
}}

.left, .right {{
    padding: 15px;
}}

.box {{
    background: white;
    padding: 10px;
    margin-bottom: 10px;
    border-radius: 5px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th, td {{
    border-bottom: 1px solid #ddd;
    padding: 8px;
    text-align: center;
}}

th {{
    background: #e9ecef;
}}

button {{
    padding: 12px;
    width: 100%;
    margin: 6px 0;
    font-size: 14px;
}}

.btn-green {{ background: #2a9d8f; color: white; }}
.btn-red {{ background: #e63946; color: white; }}
.btn-gray {{ background: #adb5bd; }}
</style>
</head>

<body>

<header>
    <div>🕶️ POS Óptica</div>
    <div>Usuario: {session['usuario']}</div>
</header>

<div class="container">

    <!-- IZQUIERDA -->
    <div class="left">
        <div class="box">
            <b>Productos disponibles</b>
            <table>
                <tr>
                    <th>Producto</th>
                    <th>Precio</th>
                    <th>Stock</th>
                </tr>
                {filas}
            </table>
        </div>
    </div>

    <!-- DERECHA -->
    <div class="right">
        <div class="box">
            <button class="btn-gray">Buscar cliente</button>
            <button class="btn-gray">Agregar cliente</button>
            <button class="btn-gray">Agregar producto</button>
            <button class="btn-gray">Descuento</button>
            <button class="btn-gray">Pago efectivo</button>
            <button class="btn-gray">Pago tarjeta</button>
        </div>

        <div class="box">
            <button class="btn-green">PAGAR</button>
            <button class="btn-red" onclick="window.location='/dashboard'">SALIR</button>
        </div>
    </div>

</div>

</body>
</html>
    """

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
