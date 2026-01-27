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
    return psycopg.connect(DATABASE_URL, sslmode="require")

# ======================
# USUARIOS DEMO
# ======================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}

# ======================
# PRODUCTOS
# ======================
PRODUCTOS = {
    "Armazón básico": 800,
    "Lentes monofocales": 1200,
    "Lentes antirreflejantes": 1600
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
        <input name="password" type="password" placeholder="Contraseña"><br><br>
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
        SELECT cerrada
        FROM caja
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()

    estado = "Cerrada"
    if row and row[0] is False:
        estado = "Abierta"

    return f"""
    <h2>Bienvenido {session['usuario']}</h2>
    <p>Rol: {session['rol']}</p>
    <p>Estado de caja: {estado}</p>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# ABRIR CAJA
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if request.method == "POST":
        monto = float(request.form["monto"])

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO caja (monto_inicial, total_ventas, cerrada)
            VALUES (%s, 0, FALSE)
        """, (monto,))
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
    """

# ======================
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if not CAJA_ABIERTA:
        return "Caja cerrada"

    conn = get_db()
    cur = conn.cursor()

    # obtener caja abierta
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
        return "No hay caja abierta"

    caja_id = caja[0]

    if request.method == "POST":
        total = 0
        seleccionados = request.form.getlist("producto")

        for p in seleccionados:
            total += PRODUCTOS[p]

        # guardar venta con caja_id
        cur.execute(
            "INSERT INTO ventas (usuario, total, caja_id) VALUES (%s, %s, %s)",
            (session["usuario"], total, caja_id)
        )

        # sumar venta a la caja
        cur.execute(
            "UPDATE caja SET total_ventas = total_ventas + %s WHERE id = %s",
            (total, caja_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        return f"""
        <h2>Venta realizada</h2>
        <p>Total: ${total}</p>
        <a href="/dashboard">Volver</a>
        """

    html = "<h2>Nueva venta</h2><form method='post'>"
    for p, precio in PRODUCTOS.items():
        html += f"<input type='checkbox' name='producto' value='{p}'> {p} - ${precio}<br>"
    html += "<br><button>Vender</button></form>"
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
        SET cerrada = TRUE
        WHERE id = (
            SELECT id FROM caja
            WHERE cerrada = FALSE
            ORDER BY id DESC
            LIMIT 1
        )
        RETURNING total_ventas
    """)

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    total = row[0] if row else 0

    return f"""
    <h2>Cierre de caja</h2>
    <p>Total ventas: ${total}</p>
    <a href="/dashboard">Volver</a>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
