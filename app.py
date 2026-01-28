import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
from werkzeug.utils import secure_filename

# ======================
# CONFIGURACIÓN
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_seguro"

DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def get_db():
    # Neon requiere SSL
    return psycopg.connect(DATABASE_URL, sslmode="require")


# ======================
# LOGIN (DEMO)
# ======================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}


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
    <ul>
        <li><a href="/clientes">👤 Clientes</a></li>
        <li><a href="/logout">Cerrar sesión</a></li>
    </ul>
    """


# ======================
# CLIENTES (LISTA)
# ======================
@app.route("/clientes")
def clientes():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return f"Error al cargar clientes: {e}"

    html = "<h2>Clientes</h2><ul>"
    for c in rows:
        html += f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html


# ======================
# VER CLIENTE + DOCUMENTOS
# ======================
@app.route("/cliente/<int:cliente_id>")
def ver_cliente(cliente_id):
    try:
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
    except Exception as e:
        return f"Error al cargar cliente: {e}"

    html = f"""
    <h2>Cliente: {cliente[0]}</h2>
    <p>Teléfono: {cliente[1]}</p>
    <p>Email: {cliente[2]}</p>

    <h3>Documentos</h3>
    <ul>
    """
    for d in documentos:
        html += f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"
    html += f"""
    </ul>

    <h3>Subir PDF</h3>
    <form method="post" action="/subir_documento" enctype="multipart/form-data">
        <input type="hidden" name="cliente_id" value="{cliente_id}">
        <input type="file" name="archivo" accept="application/pdf" required>
        <br><br>
        <button>Subir</button>
    </form>

    <br>
    <a href="/clientes">Volver</a>
    """
    return html


# ======================
# SUBIR DOCUMENTO
# ======================
@app.route("/subir_documento", methods=["POST"])
def subir_documento():
    cliente_id = request.form["cliente_id"]
    archivo = request.files.get("archivo")

    if not archivo or archivo.filename == "":
        return "Archivo inválido"

    nombre = secure_filename(archivo.filename)
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre)
    archivo.save(ruta)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO documentos_cliente
            (cliente_id, nombre_archivo, ruta_archivo)
            VALUES (%s, %s, %s)
            """,
            (cliente_id, nombre, ruta)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return f"Error al guardar documento: {e}"

    return redirect(url_for("ver_cliente", cliente_id=cliente_id))


# ======================
# DESCARGAR DOCUMENTO
# ======================
@app.route("/descargar/<int:doc_id>")
def descargar(doc_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT nombre_archivo FROM documentos_cliente WHERE id = %s",
            (doc_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return f"Error al descargar: {e}"

    if not row:
        return "Documento no encontrado"

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        row[0],
        as_attachment=True
    )


# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
