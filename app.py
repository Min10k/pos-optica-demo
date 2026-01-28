import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory, abort
)
from werkzeug.utils import secure_filename

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
# LOGIN (BD)
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

    links = "<ul>"
    if rol in ("admin", "caja"):
        links += "<li><a href='/abrir_caja'>Abrir caja</a></li>"
        links += "<li><a href='/cerrar_caja'>Cerrar caja</a></li>"
    if rol in ("admin", "caja", "ventas"):
        links += "<li><a href='/ventas'>Ventas</a></li>"
    if rol in ("admin", "consulta"):
        links += "<li><a href='/inventario'>Inventario</a></li>"
    if rol in ("admin",):
        links += "<li><a href='/usuarios'>Usuarios</a></li>"
    links += "<li><a href='/clientes'>Clientes</a></li>"
    links += "<li><a href='/logout'>Salir</a></li>"
    links += "</ul>"

    return f"""
    <h1>Dashboard POS Óptica</h1>
    <p>Usuario: <b>{session['usuario']}</b></p>
    <p>Rol: <b>{rol}</b></p>
    <hr>
    {links}
    """


# ======================
# USUARIOS (ADMIN)
# ======================
@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if login_required():
        return login_required()
    require_roles("admin")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute(
            """
            INSERT INTO usuarios (usuario, password, rol)
            VALUES (%s,%s,%s)
            """,
            (
                request.form["usuario"],
                request.form["password"],
                request.form["rol"]
            )
        )
        conn.commit()

    cur.execute(
        "SELECT usuario, rol, activo FROM usuarios ORDER BY usuario"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = """
    <h2>Usuarios</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required>
        <input name="password" placeholder="Password" required>
        <select name="rol">
            <option value="admin">admin</option>
            <option value="caja">caja</option>
            <option value="ventas">ventas</option>
            <option value="consulta">consulta</option>
        </select>
        <button>Agregar</button>
    </form>
    <hr>
    <ul>
    """
    for u in rows:
        html += f"<li>{u[0]} - {u[1]} - {'Activo' if u[2] else 'Inactivo'}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html


# ======================
# INVENTARIO (LECTURA)
# ======================
@app.route("/inventario")
def inventario():
    if login_required():
        return login_required()
    require_roles("admin", "consulta")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, precio, stock FROM productos ORDER BY nombre")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Inventario</h2><ul>"
    for r in rows:
        html += f"<li>{r[0]} - ${r[1]} | Stock {r[2]}</li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html


# ======================
# CLIENTES (YA FUNCIONA)
# ======================
@app.route("/clientes")
def clientes():
    if login_required():
        return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>Clientes</h2><ul>"
    for c in rows:
        html += f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
    html += "</ul><a href='/dashboard'>Volver</a>"
    return html


@app.route("/cliente/<int:cliente_id>")
def ver_cliente(cliente_id):
    if login_required():
        return login_required()

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

    html = f"<h2>{cliente[0]}</h2><ul>"
    for d in docs:
        html += f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"
    html += "</ul><a href='/clientes'>Volver</a>"
    return html


@app.route("/descargar/<int:doc_id>")
def descargar(doc_id):
    if login_required():
        return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT nombre_archivo FROM documentos_cliente WHERE id=%s",
        (doc_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
