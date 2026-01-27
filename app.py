import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "pos_optica_demo"

# ======================
# CONEXIÓN BD (NEON)
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL, sslmode="require")

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
        <input name="usuario" required placeholder="Usuario"><br><br>
        <input name="password" type="password" required placeholder="Contraseña"><br><br>
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

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM caja
        WHERE cerrada = FALSE
        ORDER BY id DESC
        LIMIT 1
    """)
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "Abierta" if caja else "Cerrada"

    return f"""
    <h2>Dashboard POS Óptica</h2>
    <p>Usuario: {session['usuario']} ({session['rol']})</p>
    <p><b>Estado de caja:</b> {estado}</p>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# ABRIR CAJA
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        monto = float(request.form["monto"])

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM caja WHERE cerrada = FALSE")
        if cur.fetchone():
            cur.close()
            conn.close()
            return "Ya hay una caja abierta"

        cur.execute("INSERT INTO caja (monto_inicial) VALUES (%s)", (monto,))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input name="monto" type="number" step="0.01" required placeholder="Monto inicial">
        <br><br>
        <button>Abrir</button>
    </form>
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

    html = "<h2>Inventario</h2><table border='1'><tr><th>Producto</th><th>Precio</th><th>Stock</th></tr>"
    for p in productos:
        html += f"<tr><td>{p[0]}</td><td>${p[1]}</td><td>{p[2]}</td></tr>"
    html += "</table><br><a href='/dashboard'>Volver</a>"

    return html

# ======================
# VENTAS (con inventario)
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM caja
        WHERE cerrada = FALSE
        ORDER BY id DESC
        LIMIT 1
    """)
    caja = cur.fetchone()

    if not caja:
        cur.close()
        conn.close()
        return "Caja cerrada"

    caja_id = caja[0]

    cur.execute("SELECT id, nombre, precio, stock FROM productos")
    productos = cur.fetchall()

    if request.method == "POST":
        prod_id = int(request.form["producto"])

        cur.execute(
            "SELECT precio, stock FROM productos WHERE id = %s",
            (prod_id,)
        )
        precio, stock = cur.fetchone()

        if stock <= 0:
            cur.close()
            conn.close()
            return "Sin stock disponible"

        # Guardar venta
        cur.execute("""
            INSERT INTO ventas (caja_id, total, usuario)
            VALUES (%s, %s, %s)
        """, (caja_id, precio, session["usuario"]))

        # Restar stock
        cur.execute("""
            UPDATE productos SET stock = stock - 1 WHERE id = %s
        """, (prod_id,))

        # Sumar a caja
        cur.execute("""
            UPDATE caja SET total_ventas = total_ventas + %s WHERE id = %s
        """, (precio, caja_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("ventas"))

    html = "<h2>Nueva venta</h2><form method='post'>"
    for p in productos:
        html += f"<input type='radio' name='producto' value='{p[0]}' required> {p[1]} (${p[2]}) - Stock: {p[3]}<br>"
    html += "<br><button>Vender</button></form><br><a href='/dashboard'>Volver</a>"

    cur.close()
    conn.close()
    return html

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE caja
        SET cerrada = TRUE,
            fecha_cierre = CURRENT_TIMESTAMP
        WHERE id = (
            SELECT id FROM caja
            WHERE cerrada = FALSE
            ORDER BY id DESC
            LIMIT 1
        )
        RETURNING monto_inicial, total_ventas
    """)

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return "No hay caja abierta"

    monto, ventas = row
    total = monto + ventas

    return f"""
    <h2>Cierre de caja</h2>
    <p>Monto inicial: ${monto}</p>
    <p>Total ventas: ${ventas}</p>
    <p><b>Total en caja: ${total}</b></p>
    <a href="/dashboard'>Volver</a>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======================
# START
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
