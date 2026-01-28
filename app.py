import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
from werkzeug.utils import secure_filename

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "demo_pos_optica"

DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def get_db():
    return psycopg.connect(DATABASE_URL)


# ======================
# LOGIN DEMO
# ======================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}


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


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return """
    <h1>Dashboard POS Óptica</h1>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """


# ======================
# CLIENTES
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
        html += f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html


@app.route("/cliente/<int:cliente_id>")
def ver_cliente(cliente_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT nombre, telefono, email FROM clientes WHERE id = %s",
        (cliente_id,)
    )
    cliente = cur.fetchone()

    cur.execute(
        """
        SELECT id, nombre_archivo
        FROM documentos_cliente
        WHERE cliente_id = %s
        ORDER BY fecha DESC
        """,
        (cliente_id,)
    )
    documentos = cur.fetchall()

    cur.close()
    conn.close()

    html = f"""
    <h2>Cliente: {cliente[0]}</h2>
    <p>Teléfono: {cliente[1]}</p>
    <p>Email: {cliente[2]}</p>

    <h3>Documentos</h3>
    <ul>
    """
    for d in documentos:
        html += f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"
    html += """
    </ul>

    <h3>Subir nuevo PDF</h3>
    <form method="post" action="/subir_documento" enctype="multipart/form-data">
        <input type="hidden" name="cliente_id" value="{cliente_id}">
        <input type="file" name="archivo" accept="application/pdf" required>
        <br><br>
        <button>Subir</button>
    </form>

    <br>
    <a href="/clientes">Volver a clientes</a>
    """
    return html


# ======================
# SUBIR DOCUMENTO
# ======================
@app.route("/subir_documento", methods=["POST"])
def subir_documento():
    cliente_id = request.form["cliente_id"]
    archivo = request.files["archivo"]

    if not archivo or archivo.filename == "":
        return "Archivo inválido"

    filename = secure_filename(archivo.filename)
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    archivo.save(ruta)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documentos_cliente
        (cliente_id, nombre_archivo, ruta_archivo)
        VALUES (%s, %s, %s)
        """,
        (cliente_id, filename, ruta)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("ver_cliente", cliente_id=cliente_id))


# ======================
# DESCARGAR DOCUMENTO
# ======================
@app.route("/descargar/<int:doc_id>")
def descargar(doc_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT nombre_archivo, ruta_archivo
        FROM documentos_cliente
        WHERE id = %s
        """,
        (doc_id,)
    )
    doc = cur.fetchone()
    cur.close()
    conn.close()

    if not doc:
        return "Documento no encontrado"

    nombre, ruta = doc
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        nombre,
        as_attachment=True
    )


# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
