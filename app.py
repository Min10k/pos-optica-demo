import os
import psycopg
from flask import Flask, request, redirect, url_for, session

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_v1"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL, sslmode="require")

# ======================
# ESTILO BASE
# ======================
STYLE = """
<style>
body{font-family:Arial;background:#f4f6f8;margin:0}
header{background:#1976d2;color:white;padding:15px}
nav a{color:white;margin-right:15px;text-decoration:none;font-weight:bold}
.container{padding:20px}
.card{background:white;padding:20px;border-radius:10px;
box-shadow:0 2px 6px rgba(0,0,0,.1);margin-bottom:20px}
.btn{display:inline-block;padding:10px 16px;background:#1976d2;
color:white;text-decoration:none;border-radius:6px;margin:5px 0}
.btn.green{background:#388e3c}
.btn.red{background:#d32f2f}
.btn.gray{background:#555}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #ddd}
th{background:#e3f2fd}
input{padding:8px;width:100%;margin-bottom:10px}
.msg{padding:10px;background:#e8f5e9;border-radius:6px;margin-bottom:10px}
.err{padding:10px;background:#ffebee;border-radius:6px;margin-bottom:10px}
</style>
"""

def layout(title, body):
    return f"""
    {STYLE}
    <header>
        <h2>👓 POS Óptica</h2>
        <nav>
            <a href="/dashboard">Dashboard</a>
            <a href="/ventas">Ventas</a>
            <a href="/inventario">Inventario</a>
            <a href="/clientes">Clientes</a>
            <a href="/logout">Salir</a>
        </nav>
    </header>
    <div class="container">
        <h3>{title}</h3>
        {body}
    </div>
    """

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rol FROM usuarios WHERE usuario=%s AND password=%s AND activo=TRUE",
            (u,p)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["usuario"] = u
            session["rol"] = row[0]
            return redirect(url_for("dashboard"))

        return layout("Error", "<div class='err'>Credenciales incorrectas</div>")

    return f"""
    {STYLE}
    <div class="container" style="max-width:350px;margin-top:120px">
        <div class="card">
            <h3>Ingreso</h3>
            <form method="post">
                <input name="usuario" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Contraseña" required>
                <button class="btn">Entrar</button>
            </form>
        </div>
    </div>
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

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada=FALSE LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja abierta" if caja else "🔴 Caja cerrada"

    body = f"""
    <div class="card">
        <p><b>Usuario:</b> {session['usuario']}</p>
        <p><b>Estado:</b> {estado}</p>
        <a class="btn green" href="/abrir_caja">Abrir caja</a><br>
        <a class="btn red" href="/cerrar_caja">Cerrar caja</a>
    </div>
    """
    return layout("Dashboard", body)

# ======================
# CLIENTES
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

    rows = ""
    for c in clientes:
        rows += f"""
        <tr>
            <td>{c[1]}</td>
            <td>{c[2] or ""}</td>
            <td>{c[3] or ""}</td>
        </tr>
        """

    body = f"""
    <div class="card">
        <a class="btn green" href="/clientes/nuevo">➕ Nuevo cliente</a>
        <table>
            <tr>
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Email</th>
            </tr>
            {rows}
        </table>
        <a class="btn gray" href="/dashboard">Volver</a>
    </div>
    """
    return layout("Clientes", body)

@app.route("/clientes/nuevo", methods=["GET","POST"])
def nuevo_cliente():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nombre, telefono, email) VALUES (%s,%s,%s)",
            (nombre, telefono, email)
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("clientes"))

    body = """
    <div class="card">
        <form method="post">
            <input name="nombre" placeholder="Nombre del cliente" required>
            <input name="telefono" placeholder="Teléfono">
            <input name="email" placeholder="Email">
            <button class="btn green">Guardar cliente</button>
        </form>
        <a class="btn gray" href="/clientes">Volver</a>
    </div>
    """
    return layout("Nuevo cliente", body)

# ======================
# POS BASE (VENTAS / INVENTARIO / CAJA)
# ======================
# ⬇️ SE ASUME QUE YA FUNCIONAN Y NO SE TOCAN ⬇️
# Usa exactamente las rutas del POS base V1 que ya confirmaste como OK

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
