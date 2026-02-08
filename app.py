import os
import psycopg
from flask import Flask, request, redirect, url_for, session

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_v1"

DATABASE_URL = os.environ.get("DATABASE_URL").strip()

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

        return "Credenciales incorrectas<br><a href='/'>Volver</a>"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" required><br><br>
        <input type="password" name="password" required><br><br>
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
    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p>{estado}</p>
    <hr>
    <a href="/abrir_caja">Abrir caja</a><br><br>
    <a href="/pos">Ir al POS</a><br><br>
    <a href="/cerrar_caja">Cerrar caja</a><br><br>
    <a href="/logout">Salir</a>
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
        <input name="monto" type="number" required>
        <button>Abrir</button>
    </form>
    <a href="/dashboard">Volver</a>
    """

# ======================
# POS + CARRITO
# ======================
@app.route("/pos", methods=["GET", "POST"])
def pos():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta<br><a href='/dashboard'>Volver</a>"

    if request.method == "POST":
        pid = int(request.form["producto"])
        cantidad = int(request.form["cantidad"])

        cur.execute(
            "SELECT nombre, precio, stock FROM productos WHERE id = %s",
            (pid,)
        )
        prod = cur.fetchone()

        if cantidad > prod[2]:
            cur.close()
            conn.close()
            return "Stock insuficiente<br><a href='/pos'>Volver</a>"

        session["carrito"].append({
            "id": pid,
            "nombre": prod[0],
            "precio": prod[1],
            "cantidad": cantidad
        })
        session.modified = True

    cur.execute("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    carrito_html = ""
    total = 0
    for c in session["carrito"]:
        subtotal = c["precio"] * c["cantidad"]
        total += subtotal
        carrito_html += f"<li>{c['nombre']} x {c['cantidad']} = ${subtotal}</li>"

    options = ""
    for p in productos:
        options += f"<option value='{p[0]}'>{p[1]} (${p[2]}) Stock {p[3]}</option>"

    return f"""
    <h2>POS</h2>

    <form method="post">
        <select name="producto">{options}</select>
        <input name="cantidad" type="number" min="1" required>
        <button>Agregar</button>
    </form>

    <h3>Carrito</h3>
    <ul>{carrito_html}</ul>
    <p><b>Total: ${total}</b></p>

    <a href="/pagar">PAGAR</a><br><br>
    <a href="/dashboard">Salir</a>
    """

# ======================
# PAGAR
# ======================
@app.route("/pagar")
def pagar():
    if not session.get("carrito"):
        return "Carrito vacío<br><a href='/pos'>Volver</a>"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja_id = cur.fetchone()[0]

    total = sum(i["precio"] * i["cantidad"] for i in session["carrito"])

    cur.execute(
        "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s, %s, %s) RETURNING id",
        (caja_id, total, session["usuario"])
    )
    venta_id = cur.fetchone()[0]

    for i in session["carrito"]:
        cur.execute(
            """
            INSERT INTO detalle_ventas
            (venta_id, producto_id, cantidad, precio_unitario)
            VALUES (%s, %s, %s, %s)
            """,
            (venta_id, i["id"], i["cantidad"], i["precio"])
        )
        cur.execute(
            "UPDATE productos SET stock = stock - %s WHERE id = %s",
            (i["cantidad"], i["id"])
        )

    conn.commit()
    cur.close()
    conn.close()

    session["carrito"] = []

    return f"""
    <h2>Venta realizada con éxito</h2>
    <p>Total: ${total}</p>
    <a href="/pos">Nueva venta</a><br>
    <a href="/dashboard">Dashboard</a>
    """

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, monto_inicial FROM caja WHERE cerrada = FALSE LIMIT 1"
    )
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta"

    caja_id, monto = caja

    cur.execute(
        "SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id = %s",
        (caja_id,)
    )
    total_ventas = cur.fetchone()[0]

    cur.execute(
        """
        UPDATE caja
        SET total_ventas=%s, cerrada=TRUE, fecha_cierre=CURRENT_TIMESTAMP
        WHERE id=%s
        """,
        (total_ventas, caja_id)
    )

    conn.commit()
    cur.close()
    conn.close()

    return f"""
    <h2>Cierre de caja</h2>
    <p>Monto inicial: ${monto}</p>
    <p>Total ventas: ${total_ventas}</p>
    <p><b>Total en caja: ${monto + total_ventas}</b></p>
    <a href="/dashboard">Volver</a>
    """

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
