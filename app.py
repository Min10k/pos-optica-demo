import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "pos_optica_v1"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no definida")

DATABASE_URL = DATABASE_URL.strip()

def get_db():
    return psycopg.connect(DATABASE_URL)

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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

    return f"""
    <h1>Dashboard</h1>
    <p>{estado}</p>
    <a href="/abrir_caja">Abrir caja</a><br>
    <a href="/pos">POS</a><br>
    <a href="/cerrar_caja">Cerrar caja</a><br>
    <a href="/logout">Salir</a>
    """

# ======================
# ABRIR CAJA
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if request.method == "POST":
        monto = request.form.get("monto")
        if not monto:
            return "Monto inválido"

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM caja WHERE cerrada = FALSE")
        if cur.fetchone():
            cur.close()
            conn.close()
            return "Ya hay caja abierta"

        cur.execute("INSERT INTO caja (monto_inicial) VALUES (%s)", (monto,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))

    return """
    <form method="post">
        <input name="monto" type="number" required>
        <button>Abrir caja</button>
    </form>
    <a href="/dashboard">Volver</a>
    """

# ======================
# POS (ULTRA ESTABLE)
# ======================
@app.route("/pos", methods=["GET", "POST"])
def pos():
    # 🔐 asegurar carrito SIEMPRE
    if "carrito" not in session or not isinstance(session["carrito"], list):
        session["carrito"] = []

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja = cur.fetchone()
    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta<br><a href='/dashboard'>Volver</a>"

    mensaje = ""

    if request.method == "POST":
        try:
            pid = request.form.get("producto")
            cantidad = request.form.get("cantidad")

            if not pid or not cantidad:
                mensaje = "Datos incompletos"
            else:
                pid = int(pid)
                cantidad = int(cantidad)

                cur.execute(
                    "SELECT nombre, precio, stock FROM productos WHERE id=%s",
                    (pid,)
                )
                prod = cur.fetchone()

                if not prod:
                    mensaje = "Producto no encontrado"
                elif cantidad <= 0:
                    mensaje = "Cantidad inválida"
                elif cantidad > prod[2]:
                    mensaje = "Stock insuficiente"
                else:
                    session["carrito"].append({
                        "id": pid,
                        "nombre": prod[0],
                        "precio": prod[1],
                        "cantidad": cantidad
                    })
                    session.modified = True
                    return redirect(url_for("pos"))

        except Exception as e:
            mensaje = f"Error al agregar producto: {str(e)}"

    cur.execute("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    total = 0
    carrito_html = ""
    for c in session["carrito"]:
        subtotal = c["precio"] * c["cantidad"]
        total += subtotal
        carrito_html += f"<li>{c['nombre']} x {c['cantidad']} = ${subtotal}</li>"

    options = ""
    for p in productos:
        options += f"<option value='{p[0]}'>{p[1]} (${p[2]}) Stock {p[3]}</option>"

    return f"""
    <h2>POS</h2>
    <p style="color:red;">{mensaje}</p>

    <form method="post">
        <select name="producto">{options}</select>
        <input name="cantidad" type="number" min="1" required>
        <button>Agregar</button>
    </form>

    <h3>Carrito</h3>
    <ul>{carrito_html}</ul>
    <p><b>Total: ${total}</b></p>

    <a href="/pagar">PAGAR</a><br>
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
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta"

    caja_id = caja[0]
    total = sum(i["precio"] * i["cantidad"] for i in session["carrito"])

    cur.execute(
        "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s,%s,%s) RETURNING id",
        (caja_id, total, session["usuario"])
    )
    venta_id = cur.fetchone()[0]

    for i in session["carrito"]:
        cur.execute(
            "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario) VALUES (%s,%s,%s,%s)",
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
    <h2>Venta realizada</h2>
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

    cur.execute("SELECT id, monto_inicial FROM caja WHERE cerrada = FALSE LIMIT 1")
    caja = cur.fetchone()
    if not caja:
        cur.close()
        conn.close()
        return "No hay caja abierta"

    caja_id, monto = caja

    cur.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id=%s", (caja_id,))
    total = cur.fetchone()[0]

    cur.execute(
        "UPDATE caja SET total_ventas=%s, cerrada=TRUE WHERE id=%s",
        (total, caja_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return f"""
    <h2>Cierre de caja</h2>
    <p>Total en caja: ${monto + total}</p>
    <a href="/dashboard">Volver</a>
    """

if __name__ == "__main__":
    app.run()
