import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

# ======================
# CONEXIÓN A BD (NEON)
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(
        DATABASE_URL,
        sslmode="require"
    )

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

    estado_caja = "🔴 Caja CERRADA"

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id 
            FROM caja 
            WHERE cerrada = FALSE 
            ORDER BY fecha_apertura DESC 
            LIMIT 1
        """)
        caja = cur.fetchone()
        cur.close()
        conn.close()

        if caja:
            estado_caja = f"🟢 Caja ABIERTA (ID {caja[0]})"
    except Exception as e:
        estado_caja = "⚠️ Error al consultar estado de caja"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p><b>Usuario:</b> {session['usuario']}</p>
    <p><b>Estado de caja:</b> {estado_caja}</p>
    <hr>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/clientes">👤 Clientes</a><br><br>
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
        <button>Abrir caja</button>
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
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html

# ======================
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id 
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

    caja_id = caja[0]

    if request.method == "POST":
        producto_id = request.form["producto"]
        cantidad = int(request.form["cantidad"])

        cur.execute("SELECT precio, stock FROM productos WHERE id = %s", (producto_id,))
        precio, stock = cur.fetchone()

        if cantidad > stock:
            cur.close()
            conn.close()
            return "Stock insuficiente"

        total = precio * cantidad

        cur.execute(
            "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s, %s, %s)",
            (caja_id, total, session["usuario"])
        )

        cur.execute(
            "UPDATE productos SET stock = stock - %s WHERE id = %s",
            (cantidad, producto_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    cur.execute("SELECT id, nombre, precio, stock FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Nueva venta</h2><form method='post'>"
    html += "<select name='producto'>"
    for p in productos:
        html += f"<option value='{p[0]}'>{p[1]} - ${p[2]} (Stock {p[3]})</option>"
    html += "</select><br><br>"
    html += "<input name='cantidad' type='number' min='1' required><br><br>"
    html += "<button>Vender</button></form><br>"
    html += "<a href='/dashboard'>Volver</a>"
    return html

# ======================
# CLIENTES (solo ver)
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
        html += f"<li>{c[1]}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html

# ======================
# CERRAR CAJA
# ======================
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

    cur.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id = %s", (caja_id,))
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

    total_caja = monto_inicial + total_ventas

    return f"""
    <h2>Cierre de caja</h2>
    <p>Monto inicial: ${monto_inicial}</p>
    <p>Total ventas: ${total_ventas}</p>
    <p><b>Total en caja: ${total_caja}</b></p>
    <br>
    <a href="/dashboard">Volver</a>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
