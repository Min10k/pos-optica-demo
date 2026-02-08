import os
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "pos_optica_v1"

# ======================
# LOGIN DEMO
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
        <input name="usuario" placeholder="Usuario"><br><br>
        <input name="password" type="password" placeholder="Contraseña"><br><br>
        <button>Entrar</button>
    </form>
    """

# ======================
# LOGOUT
# ======================
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
# POS VISUAL (SOLO DISEÑO)
# ======================
@app.route("/pos")
def pos():
    if "usuario" not in session:
        return redirect(url_for("login"))

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
    grid-template-columns: 65% 35%;
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

button {{
    padding: 10px;
    width: 100%;
    margin: 5px 0;
    font-size: 14px;
}}

.btn-green {{ background: #2a9d8f; color: white; }}
.btn-red {{ background: #e63946; color: white; }}
.btn-gray {{ background: #adb5bd; }}

footer {{
    background: #dee2e6;
    padding: 10px;
    display: flex;
    justify-content: space-between;
}}
</style>
</head>

<body>

<header>
    <div>🕶️ POS Óptica</div>
    <div>Usuario: {session['usuario']}</div>
</header>

<div class="container">
    <div class="left">
        <div class="box">
            <b>Cliente</b><br>
            <input placeholder="Buscar cliente..." style="width:100%; padding:8px;">
        </div>

        <div class="box">
            <b>Venta</b>
            <table>
                <tr>
                    <th>Producto</th>
                    <th>Cant</th>
                    <th>Total</th>
                </tr>
                <tr>
                    <td>Lentes</td>
                    <td>1</td>
                    <td>$1200</td>
                </tr>
                <tr>
                    <td>Armazón</td>
                    <td>1</td>
                    <td>$800</td>
                </tr>
            </table>
        </div>
    </div>

    <div class="right">
        <div class="box">
            <button class="btn-gray">Lentes</button>
            <button class="btn-gray">Armazones</button>
            <button class="btn-gray">Accesorios</button>
        </div>

        <div class="box">
            <button class="btn-gray">Agregar cliente</button>
            <button class="btn-gray">Guardar venta</button>
        </div>
    </div>
</div>

<footer>
    <div><b>Total:</b> $2000</div>
    <div>
        <button class="btn-green">PAGAR</button>
        <button class="btn-red" onclick="window.location='/dashboard'">SALIR</button>
    </div>
</footer>

</body>
</html>
    """

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
