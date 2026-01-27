import os
import psycopg
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "pos_optica_demo"

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
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            session["usuario"] = usuario
            session["rol"] = USUARIOS[usuario]["rol"]
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

        # No permitir dos cajas abiertas
        cur.execute("SELECT id FROM caja WHERE cerrada = FALSE")
        if cur.fetchone():
            cur.close()
            conn.close()
            return "Ya hay una caja abierta"

        cur.execute("""
            INSERT INTO caja (monto_inicial)
            VALUES (%s)
        """, (monto,))

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
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    # Buscar caja abierta
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
        return "<h3>No hay caja abierta</h3><a href='/dashboard'>Volver</a>"

    caja_id = caja[0]

    if request.method == "POST":
        total = float(request.form["total"])

        # Guardar venta
        cur.execute("""
            INSERT INTO ventas (caja_id, total, usuario)
            VALUES (%s, %s, %s)
        """, (caja_id, total, session["usuario"]))

        # Sumar venta a la caja
        cur.execute("""
            UPDATE caja
            SET total_ventas = total_ventas + %s
            WHERE id = %s
        """, (total, caja_id))

        conn.commit()
        cur.close()
        conn.close()

        return f"""
        <h2>Venta registrada</h2>
        <p>Total: ${total}</p>
        <a href="/dashboard">Volver</a>
        """

    cur.close()
    conn.close()

    return """
    <h2>Nueva venta</h2>
    <form method="post">
        <input name="total" type="number" step="0.01" required placeholder="Total de la venta">
        <br><br>
        <button>Registrar venta</button>
    </form>
    """

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    if "usuario" not in session:
        return redirect(url_for("login"))

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

    monto, total = row

    return f"""
    <h2>Caja cerrada</h2>
    <p>Monto inicial: ${monto}</p>
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

# ======================
# START (RENDER)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
