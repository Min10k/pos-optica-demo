import os
import psycopg
from flask import Flask, request, redirect, url_for, session, send_from_directory

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

DATABASE_URL = os.environ.get("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM caja
        WHERE cerrada = FALSE
        ORDER BY fecha_apertura DESC
        LIMIT 1
    """)
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p><b>Usuario:</b> {session['usuario']}</p>
    <p><b>Estado:</b> {estado}</p>
    <hr>
    <a href="/clientes">👤 Clientes</a><br><br>
    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# CLIENTES (LISTA)
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
        html += f"<li><a href='/cliente/{c[0]}'>{c[1]}</a></li>"
    html += "</ul><br><a href='/dashboard'>Volver</a>"
    return html

# ======================
# DETALLE CLIENTE + PDFs
# ======================
@app.route("/cliente/<int:cliente_id>", methods=["GET", "POST"])
def cliente_detalle(cliente_id):
    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # Nombre cliente
    cur.execute("SELECT nombre FROM clientes WHERE id = %s", (cliente_id,))
    cliente = cur.fetchone()
    if not cliente:
        cur.close()
        conn.close()
        return "Cliente no encontrado"

    # Subir PDF
    if request.method == "POST":
        archivo = request.files["archivo"]
        if archivo and archivo.filename.lower().endswith(".pdf"):
            ruta_cliente = os.path.join(UPLOAD_FOLDER, str(cliente_id))
            os.makedirs(ruta_cliente, exist_ok=True)

            ruta = os.path.join(ruta_cliente, archivo.filename)
            archivo.save(ruta)

            cur.execute("""
                INSERT INTO documentos_cliente (cliente_id, nombre_archivo, ruta_archivo)
                VALUES (%s, %s, %s)
            """, (cliente_id, archivo.filename, ruta))
            conn.commit()

    # Listar PDFs
    cur.execute("""
        SELECT id, nombre_archivo
        FROM documentos_cliente
        WHERE cliente_id = %s
        ORDER BY fecha DESC
    """, (cliente_id,))
    docs = cur.fetchall()

    cur.close()
    conn.close()

    html = f"<h2>Cliente: {cliente[0]}</h2>"
    html += """
    <h3>Subir PDF</h3>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="archivo" accept="application/pdf" required>
        <button>Subir</button>
    </form>
    <hr>
    <h3>Documentos</h3>
    <ul>
    """
    for d in docs:
        html += f"<li><a href='/descargar/{d[0]}'>{d[1]}</a></li>"
    html += "</ul><br><a href='/clientes'>Volver</a>"
    return html

# ======================
# DESCARGAR PDF
# ======================
@app.route("/descargar/<int:doc_id>")
def descargar_pdf(doc_id):
    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT nombre_archivo, ruta_archivo
        FROM documentos_cliente
        WHERE id = %s
    """, (doc_id,))
    doc = cur.fetchone()
    cur.close()
    conn.close()

    if not doc:
        return "Archivo no encontrado"

    ruta = os.path.dirname(doc[1])
    return send_from_directory(ruta, doc[0], as_attachment=True)

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
