import os
import psycopg
from flask import Flask, request, redirect, url_for, session, send_from_directory

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_v1"

DATABASE_URL = os.environ.get("DATABASE_URL")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    return psycopg.connect(DATABASE_URL, sslmode="require")

# ======================
# ESTILO
# ======================
STYLE = """
<style>
body{font-family:Arial;background:#f4f6f8;margin:0}
header{background:#1976d2;color:white;padding:15px}
nav a{color:white;margin-right:15px;text-decoration:none;font-weight:bold}
.container{padding:20px}
.card{background:white;padding:20px;border-radius:10px;
box-shadow:0 2px 6px rgba(0,0,0,.1);margin-bottom:20px}
.btn{display:inline-block;padding:10px 16px;background:#1976d2;
color:white;text-decoration:none;border-radius:6px;margin:5px 0}
.btn.green{background:#388e3c}
.btn.red{background:#d32f2f}
.btn.gray{background:#555}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #ddd}
th{background:#e3f2fd}
input,select{padding:8px;width:100%;margin-bottom:10px}
.msg{padding:10px;background:#e8f5e9;border-radius:6px;margin-bottom:10px}
.err{padding:10px;background:#ffebee;border-radius:6px;margin-bottom:10px}
</style>
"""

def layout(title, body):
    return f"""
    {STYLE}
    <header>
        <h2>👓 POS Óptica</h2>
        <nav>
            <a href="/dashboard">Dashboard</a>
            <a href="/ventas">Ventas</a>
            <a href="/inventario">Inventario</a>
            <a href="/clientes">Clientes</a>
            <a href="/logout">Salir</a>
        </nav>
    </header>
    <div class="container">
        <h3>{title}</h3>
        {body}
    </div>
    """

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT rol FROM usuarios WHERE usuario=%s AND password=%s AND activo=TRUE",
            (request.form["usuario"], request.form["password"])
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["usuario"] = request.form["usuario"]
            session["rol"] = row[0]
            return redirect(url_for("dashboard"))

        return layout("Error", "<div class='err'>Credenciales incorrectas</div>")

    return f"""
    {STYLE}
    <div class="container" style="max-width:350px;margin-top:120px">
        <div class="card">
            <h3>Ingreso</h3>
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada=FALSE LIMIT 1")
    caja = cur.fetchone()
    cur.close()
    conn.close()

    estado = "🟢 Caja abierta" if caja else "🔴 Caja cerrada"

    return layout("Dashboard", f"""
        <div class="card">
            <p><b>Usuario:</b> {session['usuario']}</p>
            <p><b>Estado de caja:</b> {estado}</p>
            <a class="btn green" href="/abrir_caja">Abrir caja</a>
            <a class="btn red" href="/cerrar_caja">Cerrar caja</a>
        </div>
    """)

# ======================
# INVENTARIO
# ======================
@app.route("/inventario")
def inventario():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,nombre,precio,stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    filas = "".join(
        f"<tr><td>{p[1]}</td><td>${p[2]}</td><td>{p[3]}</td>"
        f"<td><a class='btn gray' href='/inventario/ajustar/{p[0]}'>Ajustar</a></td></tr>"
        for p in productos
    )

    return layout("Inventario", f"""
        <div class="card">
            <table>
                <tr><th>Producto</th><th>Precio</th><th>Stock</th><th></th></tr>
                {filas}
            </table>
            <a class="btn gray" href="/dashboard">Volver</a>
        </div>
    """)

@app.route("/inventario/ajustar/<int:pid>", methods=["GET","POST"])
def ajustar_inventario(pid):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cantidad = int(request.form["cantidad"])
        precio = request.form.get("precio")

        if precio:
            cur.execute(
                "UPDATE productos SET stock = stock + %s, precio=%s WHERE id=%s",
                (cantidad, precio, pid)
            )
        else:
            cur.execute(
                "UPDATE productos SET stock = stock + %s WHERE id=%s",
                (cantidad, pid)
            )

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("inventario"))

    cur.execute("SELECT nombre,precio FROM productos WHERE id=%s",(pid,))
    prod = cur.fetchone()
    cur.close()
    conn.close()

    return layout("Ajustar inventario", f"""
        <div class="card">
            <h4>{prod[0]}</h4>
            <form method="post">
                <input name="cantidad" type="number" required placeholder="Cantidad a sumar">
                <input name="precio" type="number" step="0.01" placeholder="Nuevo precio (opcional)">
                <button class="btn green">Guardar cambios</button>
            </form>
            <a class="btn gray" href="/inventario">Volver</a>
        </div>
    """)

# ======================
# (Ventas, clientes, PDFs, caja)
# ======================
# 👉 TODO lo demás queda IGUAL y FUNCIONANDO como ya lo tienes

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
