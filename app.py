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
app.secret_key = "pos_optica_v1"

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
            session["usuario"] = u
            session["rol"] = USUARIOS[u]["rol"]
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario"><br><br>
        <input type="password" name="password" placeholder="Contraseña"><br><br>
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

    estado = "🟢 Caja abierta" if caja else "🔴 Caja cerrada"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p>Usuario: <b>{session['usuario']}</b></p>
    <p>Estado: <b>{estado}</b></p>
    <hr>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Ventas</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/pos">🖥 POS Visual</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """


# ======================
# ABRIR CAJA
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
            return "Ya hay una caja abierta <br><a href='/dashboard'>Volver</a>"

        cur.execute("INSERT INTO caja (monto_inicial) VALUES (%s)", (monto,))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input type="number" name="monto" required placeholder="Monto inicial">
        <br><br>
        <button>Abrir</button>
    </form>
    <br>
    <a href="/dashboard">Volver</a>
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
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE ORDER BY fecha_apertura DESC LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta<br><a href='/dashboard'>Volver</a>"

    caja_id = caja[0]

    if request.method == "POST":
        producto_id = request.form["producto"]
        cantidad = int(request.form["cantidad"])

        cur.execute("SELECT precio, stock FROM productos WHERE id=%s", (producto_id,))
        precio, stock = cur.fetchone()

        if cantidad > stock:
            cur.close()
            conn.close()
            return "Stock insuficiente<br><a href='/ventas'>Volver</a>"

        total = precio * cantidad

        cur.execute(
            "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s,%s,%s)",
            (caja_id, total, session["usuario"])
        )

        cur.execute(
            "UPDATE productos SET stock = stock - %s WHERE id = %s",
            (cantidad, producto_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        return "✅ Venta realizada<br><a href='/dashboard'>Volver</a>"

    cur.execute("SELECT id, nombre, precio, stock FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Nueva venta</h2><form method='post'>"
    html += "<select name='producto'>"
    for p in productos:
        html += f"<option value='{p[0]}'>{p[1]} - ${p[2]} (Stock {p[3]})</option>"
    html += "</select><br><br>"
    html += "<input type='number' name='cantidad' min='1' required><br><br>"
    html += "<button>Vender</button></form><br>"
    html += "<a href='/dashboard'>Volver</a>"
    return html


# ======================
# CLIENTES
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
def ver_cliente(cliente_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT nombre, telefono, email FROM clientes WHERE id=%s", (cliente_id,))
    cliente = cur.fetchone()

    cur.execute("""
        SELECT id, nombre_archivo
        FROM documentos_cliente
        WHERE cliente_id=%s
        ORDER BY fecha DESC
    """, (cliente_id,))
    docs = cur.fetchall()

    cur.close()
    conn.close()

    html = f"""
    <h2>{cliente[0]}</h2>
    <p>Tel: {cliente[1]}</p>
    <p>Email: {cliente[2]}</p>

    <h3>Documentos</h3>
    <ul>
    """
    for d in docs:
        html += f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"
    html += """
    </ul>

    <form method="post" action="/subir_documento" enctype="multipart/form-data">
        <input type="hidden" name="cliente_id" value="{cliente_id}">
        <input type="file" name="archivo" accept="application/pdf" required>
        <br><br>
        <button>Subir PDF</button>
    </form>
    <br>
    <a href="/clientes">Volver</a>
    """
    return html


@app.route("/subir_documento", methods=["POST"])
def subir_documento():
    cliente_id = request.form["cliente_id"]
    archivo = request.files["archivo"]

    filename = secure_filename(archivo.filename)
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    archivo.save(ruta)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documentos_cliente (cliente_id, nombre_archivo, ruta_archivo)
        VALUES (%s,%s,%s)
    """, (cliente_id, filename, ruta))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("ver_cliente", cliente_id=cliente_id))


@app.route("/descargar/<int:doc_id>")
def descargar(doc_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre_archivo FROM documentos_cliente WHERE id=%s", (doc_id,))
    nombre = cur.fetchone()[0]
    cur.close()
    conn.close()

    return send_from_directory(app.config["UPLOAD_FOLDER"], nombre, as_attachment=True)


# ======================
# POS VISUAL (UI)
# ======================
@app.route("/pos")
def pos():
    return "<h1>POS visual cargado ✔</h1><a href='/dashboard'>Volver</a>"


# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
