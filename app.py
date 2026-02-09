import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, Response
)
from werkzeug.utils import secure_filename

# ======================
# CONFIGURACIÓN
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_demo"

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
        <input name="usuario" placeholder="Usuario"><br><br>
        <input name="password" type="password" placeholder="Contraseña"><br><br>
        <button>Entrar</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/")

    return """
    <h1>Dashboard POS Óptica</h1>
    <ul>
        <li><a href="/clientes">👤 Clientes</a></li>
        <li><a href="/logout">Salir</a></li>
    </ul>
    """

# ======================
# CLIENTES
# ======================
@app.route("/clientes")
def clientes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    data = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Clientes</h2><ul>"
    for c in data:
        html += f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html

# ======================
# VER CLIENTE
# ======================
@app.route("/cliente/<int:cliente_id>")
def cliente(cliente_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT nombre, telefono, email FROM clientes WHERE id=%s",
        (cliente_id,)
    )
    cliente = cur.fetchone()

    cur.execute(
        """
        SELECT id, nombre_archivo
        FROM documentos_cliente
        WHERE cliente_id=%s
        ORDER BY fecha DESC
        """,
        (cliente_id,)
    )
    docs = cur.fetchall()

    cur.close()
    conn.close()

    html = f"""
    <h2>{cliente[0]}</h2>
    <p>Teléfono: {cliente[1]}</p>
    <p>Email: {cliente[2]}</p>

    <h3>Documentos</h3>
    <ul>
    """

    for d in docs:
        html += f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"

    html += f"""
    </ul>

    <h3>Subir PDF</h3>
    <form method="post" action="/subir_pdf" enctype="multipart/form-data">
        <input type="hidden" name="cliente_id" value="{cliente_id}">
        <input type="file" name="archivo" accept="application/pdf" required>
        <br><br>
        <button>Subir</button>
    </form>

    <br><a href="/clientes">Volver</a>
    """

    return html

# ======================
# SUBIR PDF (A BD)
# ======================
@app.route("/subir_pdf", methods=["POST"])
def subir_pdf():
    cliente_id = request.form["cliente_id"]
    archivo = request.files["archivo"]

    if not archivo or archivo.filename == "":
        return "Archivo inválido"

    nombre = secure_filename(archivo.filename)
    data = archivo.read()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documentos_cliente
        (cliente_id, nombre_archivo, archivo)
        VALUES (%s,%s,%s)
        """,
        (cliente_id, nombre, data)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(f"/cliente/{cliente_id}")

# ======================
# DESCARGAR PDF
# ======================
@app.route("/descargar/<int:doc_id>")
def descargar(doc_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT nombre_archivo, archivo FROM documentos_cliente WHERE id=%s",
        (doc_id,)
    )
    doc = cur.fetchone()
    cur.close()
    conn.close()

    if not doc:
        return "Documento no encontrado"

    nombre, data = doc

    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nombre}"
        }
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
