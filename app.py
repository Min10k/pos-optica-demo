import os
import psycopg
import pandas as pd
from flask import Flask, request, redirect, session, send_file
from io import BytesIO

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada")
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
            return redirect("/dashboard")

        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" required><br><br>
        <input name="password" type="password" required><br><br>
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
    <h1>Dashboard POS Óptica</h1>
    <a href="/clientes">Clientes</a><br><br>
    <a href="/reporte_ventas">Reporte de ventas (Excel)</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# CLIENTES (LISTA SIMPLE)
# ======================
@app.route("/clientes")
def clientes():
    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    data = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Clientes</h2><ul>"
    for c in data:
        html += f"<li>{c[1]}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html

# ======================
# REPORTE VENTAS (FORM)
# ======================
@app.route("/reporte_ventas", methods=["GET", "POST"])
def reporte_ventas():
    if "usuario" not in session:
        return redirect("/")

    if request.method == "POST":
        fecha = request.form["fecha"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                v.fecha,
                v.usuario,
                v.total,
                v.caja_id
            FROM ventas v
            WHERE DATE(v.fecha) = %s
            ORDER BY v.fecha
        """, (fecha,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Crear Excel
        df = pd.DataFrame(rows, columns=[
            "Fecha/Hora",
            "Usuario",
            "Total",
            "Caja ID"
        ])

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Ventas")

        output.seek(0)

        return send_file(
            output,
            download_name=f"ventas_{fecha}.xlsx",
            as_attachment=True
        )

    return """
    <h2>Reporte de ventas</h2>
    <form method="post">
        <label>Fecha:</label><br>
        <input type="date" name="fecha" required><br><br>
        <button>Descargar Excel</button>
    </form>
    <br>
    <a href="/dashboard">Volver</a>
    """

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
