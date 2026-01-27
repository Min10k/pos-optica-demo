import os
import psycopg
import csv
from io import StringIO
from datetime import date
from flask import Flask, request, redirect, url_for, session, Response

app = Flask(__name__)
app.secret_key = "pos_optica_final"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL, sslmode="require")

# ======================
# USUARIOS
# ======================
USUARIOS = {
    "admin": "admin123",
    "caja": "caja123"
}

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]
        if u in USUARIOS and USUARIOS[u] == p:
            session["usuario"] = u
            return redirect("/dashboard")
        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" required><br><br>
        <input type="password" name="password" required><br><br>
        <button>Entrar</button>
    </form>
    """

# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/")

    return """
    <h2>Dashboard POS Óptica</h2>
    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/reporte_ventas">📊 Ventas por día (Excel)</a><br><br>
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
        cur.execute(
            "INSERT INTO caja (monto_inicial) VALUES (%s)",
            (monto,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/dashboard")

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input type="number" name="monto" required>
        <button>Abrir</button>
    </form>
    <br><a href="/dashboard">Volver</a>
    """

# ======================
# VENTAS
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM caja WHERE cerrada = FALSE ORDER BY id DESC LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        return "No hay caja abierta"

    caja_id = caja[0]

    if request.method == "POST":
        total = request.form["total"]
        usuario = session["usuario"]
        cur.execute(
            "INSERT INTO ventas (caja_id, total, usuario) VALUES (%s, %s, %s)",
            (caja_id, total, usuario)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/dashboard")

    return """
    <h2>Nueva venta</h2>
    <form method="post">
        <input type="number" name="total" required>
        <button>Vender</button>
    </form>
    <br><a href="/dashboard">Volver</a>
    """

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, monto_inicial FROM caja WHERE cerrada = FALSE ORDER BY id DESC LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        return "No hay caja abierta"

    caja_id, monto = caja

    cur.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id=%s", (caja_id,))
    total_ventas = cur.fetchone()[0]

    cur.execute("""
        UPDATE caja
        SET cerrada=TRUE, fecha_cierre=NOW(), total_ventas=%s
        WHERE id=%s
    """, (total_ventas, caja_id))

    conn.commit()
    cur.close()
    conn.close()

    return f"""
    <h2>Cierre de caja</h2>
    Monto inicial: ${monto}<br>
    Total ventas: ${total_ventas}<br>
    Total en caja: ${monto + total_ventas}<br><br>
    <a href="/dashboard">Volver</a>
    """

# ======================
# REPORTE + EXCEL
# ======================
@app.route("/reporte_ventas", methods=["GET", "POST"])
def reporte_ventas():
    fecha = request.form.get("fecha", str(date.today()))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.fecha, v.usuario, v.total
        FROM ventas v
        WHERE v.fecha::date=%s
    """, (fecha,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <h2>Ventas {fecha}</h2>
    <form method="post">
        <input type="date" name="fecha" value="{fecha}">
        <button>Buscar</button>
    </form>
    <br>
    <a href="/reporte_excel?fecha={fecha}">⬇ Descargar Excel</a>
    <br><br>
    """

    for r in rows:
        html += f"{r[0]} | {r[1]} | ${r[2]}<br>"

    html += "<br><a href='/dashboard'>Volver</a>"
    return html

@app.route("/reporte_excel")
def reporte_excel():
    fecha = request.args.get("fecha")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha, usuario, total
        FROM ventas
        WHERE fecha::date=%s
    """, (fecha,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Usuario", "Total"])
    for r in rows:
        writer.writerow(r)

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ventas_{fecha}.csv"}
    )

# ======================
# PLACEHOLDERS
# ======================
@app.route("/inventario")
def inventario():
    return "<h2>Inventario (fase siguiente)</h2><a href='/dashboard'>Volver</a>"

@app.route("/clientes")
def clientes():
    return "<h2>Clientes (fase siguiente)</h2><a href='/dashboard'>Volver</a>"

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
