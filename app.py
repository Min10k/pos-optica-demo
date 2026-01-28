import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no está definida")
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
        u = request.form.get("usuario")
        p = request.form.get("password")

        if u in USUARIOS and USUARIOS[u]["password"] == p:
            session["usuario"] = u
            session["rol"] = USUARIOS[u]["rol"]
            return redirect("/dashboard")

        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" required><br><br>
        <input name="password" type="password" required><br><br>
        <button>Entrar</button>
    </form>
    """

# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM caja
        WHERE cerrada = FALSE
        ORDER BY fecha_apertura DESC
        LIMIT 1
    """)
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

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
# CLIENTES
# ======================
@app.route("/clientes")
def clientes():
    if "usuario" not in session:
        return redirect("/")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nombre, telefono, email
            FROM clientes
            ORDER BY nombre
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return f"Error al cargar clientes: {e}"

    html = "<h2>Clientes</h2><ul>"
    for c in data:
        html += f"<li>{c[1]} - {c[2]} - {c[3]}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html

# ======================
# INVENTARIO
# ======================
@app.route("/inventario")
def inventario():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Inventario</h2><ul>"
    for p in productos:
        html += f"<li>{p[0]} - ${p[1]} | Stock: {p[2]}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
