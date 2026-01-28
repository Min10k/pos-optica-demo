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

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p><b>Usuario:</b> {session['usuario']}</p>
    <hr>

    <a href="/clientes">👤 Clientes</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# CLIENTES (LISTA)
# ======================
@app.route("/clientes")
def clientes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, telefono, email FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Clientes</h2>"
    html += "<a href='/clientes/nuevo'>➕ Nuevo cliente</a><br><br>"
    html += "<table border='1' cellpadding='5'>"
    html += "<tr><th>Nombre</th><th>Teléfono</th><th>Email</th></tr>"

    for c in clientes:
        html += f"<tr><td>{c[1]}</td><td>{c[2]}</td><td>{c[3]}</td></tr>"

    html += "</table><br>"
    html += "<a href='/dashboard'>Volver</a>"
    return html

# ======================
# CLIENTE NUEVO
# ======================
@app.route("/clientes/nuevo", methods=["GET", "POST"])
def cliente_nuevo():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nombre, telefono, email) VALUES (%s, %s, %s)",
            (nombre, telefono, email)
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("clientes"))

    return """
    <h2>Nuevo cliente</h2>
    <form method="post">
        <input name="nombre" placeholder="Nombre" required><br><br>
        <input name="telefono" placeholder="Teléfono"><br><br>
        <input name="email" type="email" placeholder="Email"><br><br>
        <button>Guardar cliente</button>
    </form>
    <br>
    <a href="/clientes">Volver</a>
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
