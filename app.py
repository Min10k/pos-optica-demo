import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, abort, send_from_directory
)
from werkzeug.utils import secure_filename

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_seguro"

DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def get_db():
    return psycopg.connect(DATABASE_URL, sslmode="require")


# ======================
# HELPERS
# ======================
def login_required():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return None


def require_roles(*roles):
    if session.get("rol") not in roles:
        abort(403)


# ======================
# ESTILO BASE (ÓPTICA)
# ======================
BASE_STYLE = """
<style>
body{margin:0;font-family:Arial;background:#f4f6f8}
header{background:#1976d2;color:white;padding:15px}
header h1{margin:0;font-size:20px}
nav a{color:white;margin-right:15px;text-decoration:none;font-weight:bold}
.container{padding:20px}
.card{background:white;padding:20px;border-radius:10px;
box-shadow:0 2px 6px rgba(0,0,0,.1);margin-bottom:20px}
.btn{display:inline-block;padding:10px 16px;background:#1976d2;
color:white;text-decoration:none;border-radius:6px;margin:4px 0}
.btn.red{background:#d32f2f}
.btn.green{background:#388e3c}
.btn.gray{background:#555}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #ddd}
th{background:#e3f2fd}
.bad{color:#d32f2f;font-weight:bold}
.ok{color:#388e3c;font-weight:bold}
input,select{padding:8px;width:100%;margin-bottom:10px}
</style>
"""

def layout(title, body):
    return f"""
    {BASE_STYLE}
    <header>
        <h1>👓 POS Óptica</h1>
        <nav>
            <a href="/dashboard">🏠 Dashboard</a>
            <a href="/ventas">🧾 Ventas</a>
            <a href="/inventario">📦 Inventario</a>
            <a href="/clientes">👤 Clientes</a>
            <a href="/logout">🚪 Salir</a>
        </nav>
    </header>
    <div class="container">
        <h2>{title}</h2>
        {body}
    </div>
    """

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rol FROM usuarios WHERE usuario=%s AND password=%s AND activo=TRUE",
            (u, p)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["usuario"] = u
            session["rol"] = row[0]
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return f"""
    {BASE_STYLE}
    <div class="container" style="max-width:350px;margin-top:120px">
        <div class="card">
            <h2>Ingreso Óptica</h2>
            <form method="post">
                <input name="usuario" required placeholder="Usuario">
                <input name="password" type="password" required placeholder="Contraseña">
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
    if login_required(): return login_required()

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
        <p><b>Estado caja:</b> {estado}</p>
        <a class="btn green" href="/abrir_caja">Abrir caja</a>
        <a class="btn red" href="/cerrar_caja">Cerrar caja</a>
    </div>
    """
    return layout("Dashboard", body)


# ======================
# VENTAS (ESTABILIZADAS)
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada=FALSE LIMIT 1")
    caja = cur.fetchone()
    if not caja:
        return layout("Ventas", "<div class='card'>❌ No puedes vender sin caja abierta.<br><a class='btn' href='/dashboard'>Volver</a></div>")

    caja_id = caja[0]

    if request.method == "POST":
        prod_id = request.form["producto"]
        cantidad = int(request.form["cantidad"])

        cur.execute("SELECT precio, stock FROM productos WHERE id=%s",(prod_id,))
        precio, stock = cur.fetchone()

        if cantidad > stock:
            return layout("Error", "<div class='card'>❌ Stock insuficiente.<br><a class='btn' href='/ventas'>Volver</a></div>")

        total = precio * cantidad

        cur.execute(
            "INSERT INTO ventas (caja_id,total,usuario) VALUES (%s,%s,%s)",
            (caja_id,total,session["usuario"])
        )
        cur.execute(
            "UPDATE productos SET stock=stock-%s WHERE id=%s",
            (cantidad,prod_id)
        )
        conn.commit()
        return redirect(url_for("ventas"))

    cur.execute("SELECT id,nombre,precio,stock FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    options = "".join([
        f"<option value='{p[0]}'>{p[1]} - ${p[2]} (Stock {p[3]})</option>"
        for p in productos
    ])

    body = f"""
    <div class="card">
        <form method="post">
            <select name="producto">{options}</select>
            <input name="cantidad" type="number" min="1" required>
            <button class="btn green">Vender</button>
        </form>
        <a class="btn gray" href="/dashboard">⬅ Volver</a>
    </div>
    """
    return layout("Ventas", body)


# ======================
# CLIENTES (ALTA + VER)
# ======================
@app.route("/clientes")
def clientes():
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,nombre FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    rows = "".join([f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>" for c in clientes])

    body = f"""
    <div class="card">
        <a class="btn green" href="/nuevo_cliente">➕ Nuevo cliente</a>
        <ul>{rows}</ul>
        <a class="btn gray" href="/dashboard">⬅ Volver</a>
    </div>
    """
    return layout("Clientes", body)


@app.route("/nuevo_cliente", methods=["GET","POST"])
def nuevo_cliente():
    if login_required(): return login_required()

    if request.method == "POST":
        nombre = request.form["nombre"]
        tel = request.form["telefono"]
        email = request.form["email"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nombre,telefono,email) VALUES (%s,%s,%s)",
            (nombre,tel,email)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("clientes"))

    body = """
    <div class="card">
        <form method="post">
            <input name="nombre" placeholder="Nombre" required>
            <input name="telefono" placeholder="Teléfono">
            <input name="email" placeholder="Email">
            <button class="btn green">Guardar</button>
        </form>
        <a class="btn gray" href="/clientes">⬅ Volver</a>
    </div>
    """
    return layout("Nuevo cliente", body)
