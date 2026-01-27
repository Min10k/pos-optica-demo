import os
import psycopg
import csv
from io import StringIO
from datetime import date
from flask import Flask, request, redirect, url_for, session, Response

app = Flask(__name__)
app.secret_key = "pos_optica_demo"

# ======================
# BD
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

    return """
    <h2>Dashboard POS Óptica</h2>
    <a href="/reporte_ventas">📊 Ventas por día</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# REPORTE VENTAS
# ======================
@app.route("/reporte_ventas", methods=["GET", "POST"])
def reporte_ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    fecha = request.form.get("fecha", str(date.today()))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.fecha::date,
            v.fecha::time,
            v.usuario,
            v.total,
            c.fecha_cierre::time
        FROM ventas v
        JOIN caja c ON v.caja_id = c.id
        WHERE v.fecha::date = %s
        ORDER BY v.fecha
    """, (fecha,))

    ventas = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <h2>Ventas del día {fecha}</h2>
    <form method="post">
        <input type="date" name="fecha" value="{fecha}">
        <button>Buscar</button>
    </form>
    <br>
    <a href="/reporte_ventas_excel?fecha={fecha}">⬇ Descargar Excel</a>
    <br><br>
    <table border="1">
        <tr>
            <th>Fecha</th>
            <th>Hora venta</th>
            <th>Usuario</th>
            <th>Total</th>
            <th>Hora cierre caja</th>
        </tr>
    """

    for v in ventas:
        html += f"""
        <tr>
            <td>{v[0]}</td>
            <td>{v[1]}</td>
            <td>{v[2]}</td>
            <td>${v[3]}</td>
            <td>{v[4] or ""}</td>
        </tr>
        """

    html += "</table><br><a href='/dashboard'>Volver</a>"
    return html

# ======================
# DESCARGAR EXCEL (CSV)
# ======================
@app.route("/reporte_ventas_excel")
def reporte_ventas_excel():
    if "usuario" not in session:
        return redirect(url_for("login"))

    fecha = request.args.get("fecha")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.fecha::date AS fecha,
            v.fecha::time AS hora_venta,
            v.usuario,
            v.total,
            c.fecha_cierre::time AS hora_corte
        FROM ventas v
        JOIN caja c ON v.caja_id = c.id
        WHERE v.fecha::date = %s
        ORDER BY v.fecha
    """, (fecha,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    # Encabezados
    writer.writerow([
        "Fecha",
        "Hora venta",
        "Usuario",
        "Total",
        "Hora cierre caja"
    ])

    for r in rows:
        writer.writerow(r)

    output.seek(0)

    filename = f"ventas_{fecha}.csv"

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

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
