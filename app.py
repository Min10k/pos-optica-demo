import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, abort
)
from datetime import datetime

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_seguro"

DATABASE_URL = os.environ.get("DATABASE_URL")

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
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rol FROM usuarios WHERE usuario=%s AND password=%s AND activo=TRUE",
            (usuario, password)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["usuario"] = usuario
            session["rol"] = row[0]
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return """
    <style>
    body{font-family:Arial;background:#f4f6f8}
    .box{width:300px;margin:120px auto;padding:20px;background:#fff;border-radius:8px}
    </style>
    <div class="box">
    <h2>POS Óptica</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required><br><br>
        <input name="password" type="password" placeholder="Contraseña" required><br><br>
        <button>Entrar</button>
    </form>
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

    return f"""
    <style>
    body{{font-family:Arial;background:#eef1f5}}
    a{{display:block;padding:10px;margin:6px;background:#1e88e5;color:white;
      text-decoration:none;border-radius:6px;width:250px}}
    </style>

    <h2>Dashboard</h2>
    <p>Usuario: <b>{session['usuario']}</b> ({session['rol']})</p>

    <a href="/inventario">📦 Inventario</a>
    <a href="/movimiento">➕ Entrada / Ajuste</a>
    <a href="/logout">Salir</a>
    """

# ======================
# INVENTARIO (ALERTAS)
# ======================
@app.route("/inventario")
def inventario():
    if login_required(): return login_required()
    require_roles("admin", "consulta")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nombre, stock FROM productos ORDER BY nombre"
    )
    productos = cur.fetchall()
    cur.close()
    conn.close()

    html = """
    <h2>Inventario</h2>
    <table border=1 cellpadding=6>
    <tr><th>Producto</th><th>Stock</th><th>Estado</th><th>Kardex</th></tr>
    """
    for p in productos:
        estado = "🟢 OK"
        if p[2] <= 3:
            estado = "🔴 BAJO"

        html += f"""
        <tr>
            <td>{p[1]}</td>
            <td>{p[2]}</td>
            <td>{estado}</td>
            <td><a href="/kardex/{p[0]}">Ver</a></td>
        </tr>
        """
    html += "</table><br><a href='/dashboard'>Volver</a>"
    return html

# ======================
# ENTRADA / AJUSTE
# ======================
@app.route("/movimiento", methods=["GET", "POST"])
def movimiento():
    if login_required(): return login_required()
    require_roles("admin")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        producto = request.form["producto"]
        tipo = request.form["tipo"]
        cantidad = int(request.form["cantidad"])
        motivo = request.form["motivo"]

        if tipo == "entrada":
            cur.execute("UPDATE productos SET stock = stock + %s WHERE id=%s", (cantidad, producto))
        else:
            cur.execute("UPDATE productos SET stock = stock - %s WHERE id=%s", (cantidad, producto))

        cur.execute(
            """
            INSERT INTO movimientos_inventario
            (producto_id, tipo, cantidad, motivo, usuario)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (producto, tipo, cantidad, motivo, session["usuario"])
        )
        conn.commit()
        return redirect(url_for("inventario"))

    cur.execute("SELECT id, nombre FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    html = """
    <h2>Movimiento de inventario</h2>
    <form method="post">
    <select name="producto">
    """
    for p in productos:
        html += f"<option value='{p[0]}'>{p[1]}</option>"
    html += """
    </select><br><br>

    <select name="tipo">
        <option value="entrada">Entrada</option>
        <option value="ajuste">Ajuste</option>
    </select><br><br>

    <input type="number" name="cantidad" required><br><br>
    <input name="motivo" placeholder="Motivo"><br><br>
    <button>Guardar</button>
    </form>
    <br><a href="/dashboard">Volver</a>
    """
    return html

# ======================
# KARDEX
# ======================
@app.route("/kardex/<int:producto_id>")
def kardex(producto_id):
    if login_required(): return login_required()
    require_roles("admin", "consulta")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tipo, cantidad, motivo, usuario, fecha
        FROM movimientos_inventario
        WHERE producto_id=%s
        ORDER BY fecha DESC
        """,
        (producto_id,)
    )
    movs = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Kardex</h2><ul>"
    for m in movs:
        html += f"<li>{m[4]} | {m[0]} | {m[1]} | {m[2]} | {m[3]}</li>"
    html += "</ul><a href='/inventario'>Volver</a>"
    return html

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
