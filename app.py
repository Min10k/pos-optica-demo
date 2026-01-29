import os
import psycopg
from flask import Flask, request, redirect, url_for, session, abort

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_seguro"

DATABASE_URL = os.environ.get("DATABASE_URL")

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
body{
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:#f4f6f8;
    color:#333;
}
header{
    background:#1976d2;
    color:white;
    padding:15px;
}
header h1{margin:0;font-size:20px}
nav a{
    color:white;
    margin-right:15px;
    text-decoration:none;
    font-weight:bold;
}
.container{
    padding:20px;
}
.card{
    background:white;
    padding:20px;
    border-radius:10px;
    box-shadow:0 2px 6px rgba(0,0,0,.1);
    margin-bottom:20px;
}
.btn{
    display:inline-block;
    padding:10px 16px;
    background:#1976d2;
    color:white;
    text-decoration:none;
    border-radius:6px;
    margin:5px 0;
}
.btn.gray{background:#555}
.btn.red{background:#d32f2f}
.btn.green{background:#388e3c}
table{
    width:100%;
    border-collapse:collapse;
}
th,td{
    padding:10px;
    border-bottom:1px solid #ddd;
}
th{
    background:#e3f2fd;
}
.bad{color:#d32f2f;font-weight:bold}
.ok{color:#388e3c;font-weight:bold}
input,select{
    padding:8px;
    width:100%;
    margin-bottom:10px;
}
</style>
"""

def layout(title, body):
    return f"""
    {BASE_STYLE}
    <header>
        <h1>👓 POS Óptica</h1>
        <nav>
            <a href="/dashboard">Dashboard</a>
            <a href="/inventario">Inventario</a>
            <a href="/movimiento">Movimientos</a>
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
            (u,p)
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
                <input name="usuario" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Contraseña" required>
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

    body = f"""
    <div class="card">
        <p><b>Usuario:</b> {session['usuario']}</p>
        <p><b>Rol:</b> {session['rol']}</p>
    </div>

    <div class="card">
        <a class="btn" href="/inventario">📦 Ver inventario</a><br>
        <a class="btn green" href="/movimiento">➕ Entrada / Ajuste</a>
    </div>
    """
    return layout("Dashboard", body)

# ======================
# INVENTARIO
# ======================
@app.route("/inventario")
def inventario():
    if login_required(): return login_required()
    require_roles("admin","consulta")

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
            estado = "<span class='bad'>STOCK BAJO</span>"

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
            <tr>
                <th>Producto</th>
                <th>Stock</th>
                <th>Estado</th>
                <th>Historial</th>
            </tr>
            {rows}
        </table>
    </div>
    """
    return layout("Inventario", body)

# ======================
# MOVIMIENTOS
# ======================
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
            cur.execute("UPDATE productos SET stock = stock + %s WHERE id=%s",(cant,prod))
        else:
            cur.execute("UPDATE productos SET stock = stock - %s WHERE id=%s",(cant,prod))

        cur.execute("""
            INSERT INTO movimientos_inventario
            (producto_id,tipo,cantidad,motivo,usuario)
            VALUES (%s,%s,%s,%s,%s)
        """,(prod,tipo,cant,motivo,session["usuario"]))
        conn.commit()
        return redirect(url_for("inventario"))

    cur.execute("SELECT id,nombre FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    options = "".join([f"<option value='{p[0]}'>{p[1]}</option>" for p in productos])

    body = f"""
    <div class="card">
        <form method="post">
            <label>Producto</label>
            <select name="producto">{options}</select>

            <label>Tipo</label>
            <select name="tipo">
                <option value="entrada">Entrada</option>
                <option value="ajuste">Ajuste</option>
            </select>

            <label>Cantidad</label>
            <input type="number" name="cantidad" required>

            <label>Motivo</label>
            <input name="motivo">

            <button class="btn green">Guardar</button>
        </form>
    </div>
    """
    return layout("Movimiento de inventario", body)

# ======================
# KARDEX
# ======================
@app.route("/kardex/<int:pid>")
def kardex(pid):
    if login_required(): return login_required()
    require_roles("admin","consulta")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tipo,cantidad,motivo,usuario,fecha
        FROM movimientos_inventario
        WHERE producto_id=%s
        ORDER BY fecha DESC
    """,(pid,))
    movs = cur.fetchall()
    cur.close()
    conn.close()

    items = ""
    for m in movs:
        items += f"<li>{m[4]} | {m[0]} | {m[1]} | {m[2]} | {m[3]}</li>"

    body = f"""
    <div class="card">
        <ul>{items}</ul>
        <a class="btn gray" href="/inventario">Volver</a>
    </div>
    """
    return layout("Kardex del producto", body)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
