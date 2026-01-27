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
    return psycopg.connect(DATABASE_URL)

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

    return f"""
    <h2>Bienvenido {session['usuario']}</h2>
    <p>Rol: {session['rol']}</p>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# 🔓 ABRIR CAJA (FIX DEFINITIVO)
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if request.method == "POST":
        try:
            monto = float(request.form["monto"])

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO caja (monto_inicial, total_ventas)
                        VALUES (%s, %s)
                        """,
                        (monto, 0)
                    )
                conn.commit()

            return redirect(url_for("dashboard"))

        except Exception as e:
            return f"<h3>Error al abrir caja</h3><pre>{e}</pre>"

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input name="monto" type="number" step="0.01" required>
        <button>Abrir</button>
    </form>
    """

# ======================
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if request.method == "POST":
        total = 0
        seleccionados = request.form.getlist("producto")

        for p in seleccionados:
            total += PRODUCTOS[p]

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ventas (usuario, total) VALUES (%s, %s)",
                    (session["usuario"], total)
                )
            conn.commit()

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
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(total), 0) FROM ventas")
            total = cur.fetchone()[0]

            cur.execute(
                """
                UPDATE caja
                SET total_ventas = %s
                WHERE id = (SELECT id FROM caja ORDER BY fecha DESC LIMIT 1)
                """,
                (total,)
            )
        conn.commit()

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

# ======================
# START (Render)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
