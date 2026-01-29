import os
import psycopg
from flask import (
    Flask, request, redirect, url_for,
    session, abort, send_from_directory
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
# BASE STYLE (ÓPTICA)
# ======================
BASE_STYLE = """
<style>
body{margin:0;font-family:Arial;background:#f4f6f8}
header{background:#1976d2;color:white;padding:15px}
header h1{margin:0;font-size:20px}
nav a{color:white;margin-right:15px;text-decoration:none;font-weight:bold}
.container{padding:20px}
.card{background:white;padding:20px;border-radius:10px;
box-shadow:0 2px 6px rgba(0,0,0,.1);margin-bottom:20px}
.btn{display:inline-block;padding:10px 16px;background:#1976d2;
color:white;text-decoration:none;border-radius:6px;margin:4px 0}
.btn.red{background:#d32f2f}
.btn.green{background:#388e3c}
.btn.gray{background:#555}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #ddd}
th{background:#e3f2fd}
.bad{color:#d32f2f;font-weight:bold}
.ok{color:#388e3c;font-weight:bold}
input,select{padding:8px;width:100%;margin-bottom:10px}
</style>
"""

def layout(title, body):
    return f"""
    {BASE_STYLE}
    <header>
        <h1>👓 POS Óptica</h1>
        <nav>
            <a href="/dashboard">Dashboard</a>
            <a href="/ventas">Ventas</a>
            <a href="/inventario">Inventario</a>
            <a href="/clientes">Clientes</a>
            <a href="/reportes">Reportes</a>
            <a href="/logout">Salir</a>
        </nav>
    </header>
    <div class="container">
        <h2>{title}</h2>
        {body}
    </div>
    """


# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rol FROM usuarios WHERE usuario=%s AND password=%s AND activo=TRUE",
            (u, p)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["usuario"] = u
            session["rol"] = row[0]
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return f"""
    {BASE_STYLE}
    <div class="container" style="max-width:350px;margin-top:120px">
        <div class="card">
            <h2>Ingreso Óptica</h2>
            <form method="post">
                <input name="usuario" required placeholder="Usuario">
                <input name="password" type="password" required placeholder="Contraseña">
                <button class="btn">Entrar</button>
            </form>
        </div>
    </div>
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
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada=FALSE ORDER BY fecha_apertura DESC LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja ABIERTA" if caja else "🔴 Caja CERRADA"

    body = f"""
    <div class="card">
        <p><b>Usuario:</b> {session['usuario']}</p>
        <p><b>Rol:</b> {session['rol']}</p>
        <p><b>Estado:</b> {estado}</p>
    </div>

    <div class="card">
        <a class="btn green" href="/abrir_caja">Abrir caja</a>
        <a class="btn red" href="/cerrar_caja">Cerrar caja</a>
    </div>
    """
    return layout("Dashboard", body)


# ======================
# CAJA
# ======================
@app.route("/abrir_caja", methods=["GET","POST"])
def abrir_caja():
    if login_required(): return login_required()
    require_roles("admin","caja")

    if request.method == "POST":
        monto = request.form["monto"]
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM caja WHERE cerrada=FALSE")
        if cur.fetchone():
            return "Ya hay una caja abierta"

        cur.execute("INSERT INTO caja (monto_inicial) VALUES (%s)", (monto,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))

    body = """
    <div class="card">
        <form method="post">
            <label>Monto inicial</label>
            <input name="monto" type="number" required>
            <button class="btn green">Abrir caja</button>
        </form>
    </div>
    """
    return layout("Abrir caja", body)


@app.route("/cerrar_caja")
def cerrar_caja():
    if login_required(): return login_required()
    require_roles("admin","caja")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, monto_inicial FROM caja WHERE cerrada=FALSE ORDER BY fecha_apertura DESC LIMIT 1"
    )
    caja = cur.fetchone()
    if not caja:
        return "No hay caja abierta"

    caja_id, monto_inicial = caja
    cur.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id=%s",(caja_id,))
    total_ventas = cur.fetchone()[0]

    cur.execute(
        "UPDATE caja SET total_ventas=%s, cerrada=TRUE, fecha_cierre=NOW() WHERE id=%s",
        (total_ventas, caja_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    body = f"""
    <div class="card">
        <p>Monto inicial: ${monto_inicial}</p>
        <p>Total ventas: ${total_ventas}</p>
        <h3>Total en caja: ${monto_inicial + total_ventas}</h3>
        <a class="btn" href="/dashboard">Volver</a>
    </div>
    """
    return layout("Cierre de caja", body)


# ======================
# INVENTARIO + KARDEX
# ======================
@app.route("/inventario")
def inventario():
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,nombre,stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    rows = ""
    for p in productos:
        estado = "<span class='ok'>OK</span>"
        if p[2] <= 3:
            estado = "<span class='bad'>BAJO</span>"

        rows += f"""
        <tr>
            <td>{p[1]}</td>
            <td>{p[2]}</td>
            <td>{estado}</td>
            <td><a class="btn gray" href="/kardex/{p[0]}">Kardex</a></td>
        </tr>
        """

    body = f"""
    <div class="card">
        <table>
            <tr><th>Producto</th><th>Stock</th><th>Estado</th><th></th></tr>
            {rows}
        </table>
        <br>
        <a class="btn green" href="/movimiento">Entrada / Ajuste</a>
    </div>
    """
    return layout("Inventario", body)


@app.route("/movimiento", methods=["GET","POST"])
def movimiento():
    if login_required(): return login_required()
    require_roles("admin")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        prod = request.form["producto"]
        tipo = request.form["tipo"]
        cant = int(request.form["cantidad"])
        motivo = request.form["motivo"]

        if tipo == "entrada":
            cur.execute("UPDATE productos SET stock=stock+%s WHERE id=%s",(cant,prod))
        else:
            cur.execute("UPDATE productos SET stock=stock-%s WHERE id=%s",(cant,prod))

        cur.execute("""
            INSERT INTO movimientos_inventario
            (producto_id,tipo,cantidad,motivo,usuario)
            VALUES (%s,%s,%s,%s,%s)
        """,(prod,tipo,cant,motivo,session["usuario"]))
        conn.commit()
        return redirect(url_for("inventario"))

    cur.execute("SELECT id,nombre FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    opts = "".join([f"<option value='{p[0]}'>{p[1]}</option>" for p in productos])

    body = f"""
    <div class="card">
        <form method="post">
            <select name="producto">{opts}</select>
            <select name="tipo">
                <option value="entrada">Entrada</option>
                <option value="ajuste">Ajuste</option>
            </select>
            <input name="cantidad" type="number" required>
            <input name="motivo" placeholder="Motivo">
            <button class="btn green">Guardar</button>
        </form>
    </div>
    """
    return layout("Movimiento de inventario", body)


@app.route("/kardex/<int:pid>")
def kardex(pid):
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tipo,cantidad,motivo,usuario,fecha
        FROM movimientos_inventario
        WHERE producto_id=%s ORDER BY fecha DESC
    """,(pid,))
    movs = cur.fetchall()
    cur.close()
    conn.close()

    items = "".join([f"<li>{m[4]} | {m[0]} | {m[1]} | {m[2]} | {m[3]}</li>" for m in movs])

    return layout("Kardex", f"<div class='card'><ul>{items}</ul></div>")


# ======================
# CLIENTES + PDF
# ======================
@app.route("/clientes")
def clientes():
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,nombre FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    rows = "".join([f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>" for c in clientes])
    return layout("Clientes", f"<div class='card'><ul>{rows}</ul></div>")


@app.route("/cliente/<int:cid>")
def ver_cliente(cid):
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM clientes WHERE id=%s",(cid,))
    cliente = cur.fetchone()

    cur.execute(
        "SELECT id,nombre_archivo FROM documentos_cliente WHERE cliente_id=%s",(cid,)
    )
    docs = cur.fetchall()
    cur.close()
    conn.close()

    archivos = "".join(
        [f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>" for d in docs]
    )

    body = f"""
    <div class="card">
        <h3>{cliente[0]}</h3>
        <ul>{archivos}</ul>

        <form method="post" action="/subir" enctype="multipart/form-data">
            <input type="hidden" name="cliente_id" value="{cid}">
            <input type="file" name="archivo" accept="application/pdf" required>
            <button class="btn green">Subir PDF</button>
        </form>
    </div>
    """
    return layout("Cliente", body)


@app.route("/subir", methods=["POST"])
def subir():
    if login_required(): return login_required()

    cid = request.form["cliente_id"]
    archivo = request.files["archivo"]
    nombre = secure_filename(archivo.filename)
    ruta = os.path.join(UPLOAD_FOLDER, nombre)
    archivo.save(ruta)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documentos_cliente (cliente_id,nombre_archivo,ruta_archivo)
        VALUES (%s,%s,%s)
    """,(cid,nombre,ruta))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("ver_cliente", cid=cid))


@app.route("/descargar/<int:doc>")
def descargar(doc):
    if login_required(): return login_required()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre_archivo FROM documentos_cliente WHERE id=%s",(doc,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    return send_from_directory(UPLOAD_FOLDER, row[0], as_attachment=True)


# ======================
# REPORTES
# ======================
@app.route("/reportes", methods=["GET","POST"])
def reportes():
    if login_required(): return login_required()

    fecha = request.form.get("fecha", date.today())

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha,usuario,total FROM ventas
        WHERE DATE(fecha)=%s ORDER BY fecha
    """,(fecha,))
    ventas = cur.fetchall()
    cur.close()
    conn.close()

    filas = "".join([f"<li>{v[0]} | {v[1]} | ${v[2]}</li>" for v in ventas])

    body = f"""
    <div class="card">
        <form method="post">
            <input type="date" name="fecha" value="{fecha}">
            <button class="btn">Ver</button>
        </form>
        <ul>{filas}</ul>
    </div>
    """
    return layout("Reporte de ventas", body)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
