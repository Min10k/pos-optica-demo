import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
from werkzeug.utils import secure_filename

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "demo_pos_optica"

DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
            session.clear()
            session["usuario"] = u
            session["rol"] = USUARIOS[u]["rol"]
            session["carrito"] = []
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
    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE ORDER BY fecha_apertura DESC LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

    return f"""
    <h1>POS Óptica</h1>
    <p><b>Usuario:</b> {session['usuario']}</p>
    <p><b>Estado:</b> {estado}</p>
    <hr>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/pos">🧾 POS / Ventas</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>

    <a href="/logout">Salir</a>
    """


# ======================
# CAJA
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if request.method == "POST":
        monto = request.form["monto"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM caja WHERE cerrada = FALSE")
        if cur.fetchone():
            cur.close()
            conn.close()
            return "Ya hay una caja abierta"

        cur.execute(
            "INSERT INTO caja (monto_inicial) VALUES (%s)",
            (monto,)
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input name="monto" type="number" required placeholder="Monto inicial">
        <br><br>
        <button>Abrir</button>
    </form>
    <br>
    <a href="/dashboard">Volver</a>
    """


@app.route("/cerrar_caja")
def cerrar_caja():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, monto_inicial
        FROM caja
        WHERE cerrada = FALSE
        ORDER BY fecha_apertura DESC
        LIMIT 1
    """)
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta"

    caja_id, monto_inicial = caja

    cur.execute(
        "SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id = %s",
        (caja_id,)
    )
    total_ventas = cur.fetchone()[0]

    cur.execute("""
        UPDATE caja
        SET total_ventas = %s,
            cerrada = TRUE,
            fecha_cierre = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (total_ventas, caja_id))

    conn.commit()
    cur.close()
    conn.close()

    total = float(monto_inicial) + float(total_ventas)

    return f"""
    <h2>Cierre de caja</h2>
    <p>Monto inicial: ${monto_inicial}</p>
    <p>Total ventas: ${total_ventas}</p>
    <h3>Total en caja: ${total}</h3>
    <br>
    <a href="/dashboard">Volver</a>
    """


# ======================
# POS / VENTAS
# ======================
@app.route("/pos", methods=["GET", "POST"])
def pos():
    if "carrito" not in session:
        session["carrito"] = []

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE ORDER BY fecha_apertura DESC LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta"

    if request.method == "POST":
        pid = request.form["producto"]
        cantidad = int(request.form["cantidad"])

        cur.execute(
            "SELECT nombre, precio, stock FROM productos WHERE id = %s",
            (pid,)
        )
        prod = cur.fetchone()

        if not prod:
            return "Producto no encontrado"

        if cantidad > prod[2]:
            return "Stock insuficiente"

        session["carrito"].append({
            "id": pid,
            "nombre": prod[0],
            "precio": float(prod[1]),
            "cantidad": cantidad
        })
        session.modified = True

        return redirect(url_for("pos"))

    cur.execute("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    total = 0
    items = ""
    for c in session["carrito"]:
        subtotal = c["precio"] * c["cantidad"]
        total += subtotal
        items += f"<li>{c['nombre']} x {c['cantidad']} = ${subtotal}</li>"

    html = "<h2>POS</h2>"
    html += "<ul>" + items + "</ul>"
    html += f"<h3>Total: ${total}</h3>"

    html += "<form method='post'>"
    html += "<select name='producto'>"
    for p in productos:
        html += f"<option value='{p[0]}'>{p[1]} - ${p[2]} (Stock {p[3]})</option>"
    html += "</select><br><br>"
    html += "<input name='cantidad' type='number' min='1' required><br><br>"
    html += "<button>Agregar</button></form><br>"

    html += "<a href='/pagar'>💳 Pagar</a><br><br>"
    html += "<a href='/dashboard'>Volver</a>"
    return html


@app.route("/pagar")
def pagar():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE ORDER BY fecha_apertura DESC LIMIT 1")
    caja_id = cur.fetchone()[0]

    total = 0
    for c in session["carrito"]:
        total += c["precio"] * c["cantidad"]

    cur.execute(
        "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s, %s, %s)",
        (caja_id, total, session["usuario"])
    )

    for c in session["carrito"]:
        cur.execute(
            "UPDATE productos SET stock = stock - %s WHERE id = %s",
            (c["cantidad"], c["id"])
        )

    conn.commit()
    cur.close()
    conn.close()

    session["carrito"] = []
    session.modified = True

    return """
    <h2>Venta realizada</h2>
    <a href="/pos">Nueva venta</a><br><br>
    <a href="/dashboard">Dashboard</a>
    """


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
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html


# ======================
# CLIENTES + PDFs
# ======================
@app.route("/clientes")
def clientes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Clientes</h2><ul>"
    for c in clientes:
        html += f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html


@app.route("/cliente/<int:cliente_id>")
def cliente(cliente_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT nombre, telefono, email FROM clientes WHERE id=%s", (cliente_id,))
    cli = cur.fetchone()

    cur.execute("""
        SELECT id, nombre_archivo
        FROM documentos_cliente
        WHERE cliente_id=%s
        ORDER BY fecha DESC
    """, (cliente_id
