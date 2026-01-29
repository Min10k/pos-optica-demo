import os
import psycopg
import pandas as pd
from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory, abort,
    Response
)
from werkzeug.utils import secure_filename
from datetime import date

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_seguro"

DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
            """
            SELECT rol
            FROM usuarios
            WHERE usuario=%s AND password=%s AND activo=TRUE
            """,
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
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" required placeholder="Usuario"><br><br>
        <input name="password" type="password" required placeholder="Contraseña"><br><br>
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
    if login_required():
        return login_required()

    rol = session["rol"]
    html = f"""
    <h1>Dashboard POS Óptica</h1>
    <p>Usuario: <b>{session['usuario']}</b></p>
    <p>Rol: <b>{rol}</b></p>
    <hr>
    <ul>
    """

    if rol in ("admin", "caja"):
        html += "<li><a href='/abrir_caja'>Abrir caja</a></li>"
        html += "<li><a href='/cerrar_caja'>Cerrar caja</a></li>"
    if rol in ("admin", "caja", "ventas"):
        html += "<li><a href='/ventas'>Ventas</a></li>"
    if rol in ("admin", "consulta"):
        html += "<li><a href='/inventario'>Inventario</a></li>"
    if rol == "admin":
        html += "<li><a href='/usuarios'>Usuarios</a></li>"
    if rol in ("admin", "consulta"):
        html += "<li><a href='/reportes'>📊 Reportes</a></li>"

    html += "<li><a href='/clientes'>Clientes</a></li>"
    html += "<li><a href='/logout'>Salir</a></li>"
    html += "</ul>"
    return html


# ======================
# REPORTES
# ======================
@app.route("/reportes", methods=["GET", "POST"])
def reportes():
    if login_required():
        return login_required()
    require_roles("admin", "consulta")

    fecha = request.form.get("fecha") or date.today().isoformat()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            v.fecha,
            v.usuario,
            v.total,
            c.id AS caja_id
        FROM ventas v
        JOIN caja c ON c.id = v.caja_id
        WHERE DATE(v.fecha) = %s
        ORDER BY v.fecha
        """,
        (fecha,)
    )
    ventas = cur.fetchall()

    cur.execute(
        """
        SELECT
            usuario,
            SUM(total)
        FROM ventas
        WHERE DATE(fecha) = %s
        GROUP BY usuario
        """,
        (fecha,)
    )
    totales_usuario = cur.fetchall()

    cur.close()
    conn.close()

    html = f"""
    <h2>Reporte de ventas por día</h2>
    <form method="post">
        <input type="date" name="fecha" value="{fecha}">
        <button>Ver</button>
        <a href="/reporte_excel?fecha={fecha}">⬇️ Excel</a>
    </form>
    <hr>
    <h3>Ventas</h3>
    <ul>
    """
    for v in ventas:
        html += f"<li>{v[0]} | {v[1]} | ${v[2]} | Caja {v[3]}</li>"
    html += "</ul><hr><h3>Totales por usuario</h3><ul>"
    for t in totales_usuario:
        html += f"<li>{t[0]}: ${t[1]}</li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html


# ======================
# REPORTE EXCEL
# ======================
@app.route("/reporte_excel")
def reporte_excel():
    if login_required():
        return login_required()
    require_roles("admin", "consulta")

    fecha = request.args.get("fecha")

    conn = get_db()
    df = pd.read_sql(
        """
        SELECT
            v.fecha,
            v.usuario,
            v.total,
            c.id AS caja_id
        FROM ventas v
        JOIN caja c ON c.id = v.caja_id
        WHERE DATE(v.fecha) = %s
        ORDER BY v.fecha
        """,
        conn,
        params=(fecha,)
    )
    conn.close()

    output = pd.ExcelWriter("reporte.xlsx", engine="xlsxwriter")
    df.to_excel(output, index=False, sheet_name="Ventas")
    output.close()

    return send_from_directory(
        ".", "reporte.xlsx", as_attachment=True
    )


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
