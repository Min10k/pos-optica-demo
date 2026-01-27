import os
import psycopg
from flask import Flask, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "pos_optica_demo"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ======================
# CONEXIÓN BD
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

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Ventas</a><br><br>
    <a href="/inventario">📦 Inventario</a><br><br>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# CLIENTES
# ======================
@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        cur.execute("""
            INSERT INTO clientes (nombre, telefono, email)
            VALUES (%s, %s, %s)
        """, (nombre, telefono, email))
        conn.commit()

    cur.execute("SELECT id, nombre, telefono, email FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()

    cur.close()
    conn.close()

    html = """
    <h2>Clientes</h2>
    <form method="post">
        <input name="nombre" required placeholder="Nombre"><br>
        <input name="telefono" placeholder="Teléfono"><br>
        <input name="email" placeholder="Email"><br><br>
        <button>Agregar cliente</button>
    </form>
    <hr>
    """

    for c in clientes:
        html += f"""
        <p>
            <b>{c[1]}</b> ({c[2] or ''})
            <br>
            <a href="/cliente/{c[0]}">Ver cliente</a>
        </p>
        """

    html += "<br><a href='/dashboard'>Volver</a>"
    return html

# ======================
# CLIENTE + DOCUMENTOS
# ======================
@app.route("/cliente/<int:cliente_id>", methods=["GET", "POST"])
def cliente(cliente_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT nombre FROM clientes WHERE id = %s", (cliente_id,))
    cliente = cur.fetchone()

    if not cliente:
        cur.close()
        conn.close()
        return "Cliente no encontrado"

    if request.method == "POST":
        archivo = request.files["archivo"]
        if archivo:
            filename = secure_filename(archivo.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            archivo.save(path)

            cur.execute("""
                INSERT INTO documentos_cliente (cliente_id, nombre_archivo, ruta_archivo)
                VALUES (%s, %s, %s)
            """, (cliente_id, filename, path))
            conn.commit()

    cur.execute("""
        SELECT nombre_archivo FROM documentos_cliente
        WHERE cliente_id = %s
    """, (cliente_id,))
    docs = cur.fetchall()

    cur.close()
    conn.close()

    html = f"<h2>Cliente: {cliente[0]}</h2>"
    html += """
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="archivo" accept="application/pdf" required>
        <br><br>
        <button>Subir PDF</button>
    </form>
    <hr>
    <h3>Documentos</h3>
    """

    for d in docs:
        html += f"<p>{d[0]}</p>"

    html += "<br><a href='/clientes'>Volver</a>"
    return html

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
