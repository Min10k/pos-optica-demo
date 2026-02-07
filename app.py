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
# ABRIR CAJA
# ======================
@app.route("/abrir_caja", methods=["GET","POST"])
def abrir_caja():
    if request.method == "POST":
        monto = request.form["monto"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM caja WHERE cerrada=FALSE")
        if cur.fetchone():
            return layout("Caja", "<div class='err'>Ya hay una caja abierta</div>")

        cur.execute("INSERT INTO caja (monto_inicial) VALUES (%s)", (monto,))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return layout("Abrir caja", """
        <div class="card">
            <form method="post">
                <input name="monto" type="number" required placeholder="Monto inicial">
                <button class="btn green">Abrir caja</button>
            </form>
            <a class="btn gray" href="/dashboard">Volver</a>
        </div>
    """)

# ======================
# VENTAS
# ======================
@app.route("/ventas", methods=["GET","POST"])
def ventas():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM caja WHERE cerrada=FALSE LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        return layout("Ventas", "<div class='err'>No hay caja abierta</div>")

    mensaje = ""

    if request.method == "POST":
        pid = request.form["producto"]
        cantidad = int(request.form["cantidad"])

        cur.execute("SELECT precio,stock FROM productos WHERE id=%s",(pid,))
        precio, stock = cur.fetchone()

        if cantidad > stock:
            mensaje = "<div class='err'>Stock insuficiente</div>"
        else:
            total = precio * cantidad
            cur.execute(
                "INSERT INTO ventas (caja_id,total,usuario) VALUES (%s,%s,%s)",
                (caja[0], total, session["usuario"])
            )
            cur.execute(
                "UPDATE productos SET stock = stock - %s WHERE id=%s",
                (cantidad, pid)
            )
            conn.commit()
            mensaje = f"<div class='msg'>Venta realizada – Total ${total}</div>"

    cur.execute("SELECT id,nombre,precio,stock FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    opciones = "".join(
        f"<option value='{p[0]}'>{p[1]} - ${p[2]} (Stock {p[3]})</option>"
        for p in productos
    )

    return layout("Ventas", f"""
        {mensaje}
        <div class="card">
            <form method="post">
                <select name="producto">{opciones}</select>
                <input name="cantidad" type="number" min="1" required>
                <button class="btn green">Vender</button>
            </form>
            <a class="btn gray" href="/dashboard">Volver</a>
        </div>
    """)

# ======================
# INVENTARIO + AJUSTE
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
        cur.execute(
            "UPDATE productos SET stock = stock + %s, precio = %s WHERE id = %s",
            (int(request.form["cantidad"]), request.form["precio"], pid)
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
                <input name="precio" type="number" step="0.01" value="{prod[1]}" required>
                <button class="btn green">Guardar</button>
            </form>
            <a class="btn gray" href="/inventario">Volver</a>
        </div>
    """)

# ======================
# CLIENTES + PDF
# ======================
@app.route("/clientes")
def clientes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,nombre FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    lista = "".join(
        f"<li>{c[1]} - <a href='/cliente/{c[0]}'>Ver</a></li>"
        for c in clientes
    )

    return layout("Clientes", f"""
        <div class="card">
            <a class="btn green" href="/clientes/nuevo">➕ Nuevo cliente</a>
            <ul>{lista}</ul>
            <a class="btn gray" href="/dashboard">Volver</a>
        </div>
    """)

@app.route("/clientes/nuevo", methods=["GET","POST"])
def nuevo_cliente():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nombre,telefono,email) VALUES (%s,%s,%s)",
            (request.form["nombre"], request.form["telefono"], request.form["email"])
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("clientes"))

    return layout("Nuevo cliente", """
        <div class="card">
            <form method="post">
                <input name="nombre" required placeholder="Nombre">
                <input name="telefono" placeholder="Teléfono">
                <input name="email" placeholder="Correo">
                <button class="btn green">Guardar</button>
            </form>
            <a class="btn gray" href="/clientes">Volver</a>
        </div>
    """)

@app.route("/cliente/<int:cid>")
def ver_cliente(cid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre,telefono,email FROM clientes WHERE id=%s",(cid,))
    cliente = cur.fetchone()

    cur.execute(
        "SELECT id,nombre_archivo FROM documentos_cliente WHERE cliente_id=%s",
        (cid,)
    )
    docs = cur.fetchall()
    cur.close()
    conn.close()

    archivos = "".join(
        f"<li>{d[1]} - <a href='/descargar/{d[0]}'>Descargar</a></li>"
        for d in docs
    )

    return layout("Cliente", f"""
        <div class="card">
            <h4>{cliente[0]}</h4>
            <p>📞 {cliente[1] or '-'}</p>
            <p>📧 {cliente[2] or '-'}</p>

            <h4>Documentos</h4>
            <ul>{archivos}</ul>

            <form method="post" action="/subir_pdf" enctype="multipart/form-data">
                <input type="hidden" name="cliente_id" value="{cid}">
                <input type="file" name="archivo" accept="application/pdf" required>
                <button class="btn green">Subir PDF</button>
            </form>

            <a class="btn gray" href="/clientes">Volver</a>
        </div>
    """)

@app.route("/subir_pdf", methods=["POST"])
def subir_pdf():
    archivo = request.files["archivo"]
    cid = request.form["cliente_id"]

    ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
    archivo.save(ruta)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documentos_cliente (cliente_id,nombre_archivo,ruta_archivo) VALUES (%s,%s,%s)",
        (cid, archivo.filename, ruta)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("ver_cliente", cid=cid))

@app.route("/descargar/<int:doc>")
def descargar(doc):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre_archivo FROM documentos_cliente WHERE id=%s",(doc,))
    nombre = cur.fetchone()[0]
    cur.close()
    conn.close()

    return send_from_directory(UPLOAD_FOLDER, nombre, as_attachment=True)

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,monto_inicial FROM caja WHERE cerrada=FALSE LIMIT 1")
    caja = cur.fetchone()

    if not caja:
        return layout("Caja", "<div class='err'>No hay caja abierta</div>")

    cur.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE caja_id=%s",(caja[0],))
    total = cur.fetchone()[0]

    cur.execute(
        "UPDATE caja SET total_ventas=%s, cerrada=TRUE WHERE id=%s",
        (total, caja[0])
    )
    conn.commit()
    cur.close()
    conn.close()

    return layout("Caja cerrada", f"""
        <div class="card">
            <p>Monto inicial: ${caja[1]}</p>
            <p>Total ventas: ${total}</p>
            <h3>Total en caja: ${caja[1] + total}</h3>
            <a class="btn gray" href="/dashboard">Volver</a>
        </div>
    """)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))

    @app.route("/pos")
def pos_ui():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>POS Óptica</title>
<style>
body{
    margin:0;
    font-family:Arial;
    background:#e5e5e5;
}
header{
    background:#2f3b45;
    color:white;
    padding:10px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
header button{
    background:#d32f2f;
    color:white;
    border:none;
    padding:10px 15px;
    font-size:16px;
}
.main{
    display:flex;
    height:calc(100vh - 50px);
}
.left{
    flex:3;
    background:white;
    padding:15px;
}
.right{
    flex:2;
    background:#f4f4f4;
    padding:10px;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
}
.box{
    border:1px solid #ccc;
    padding:10px;
    margin-bottom:10px;
}
.table{
    width:100%;
    border-collapse:collapse;
}
.table th,.table td{
    border-bottom:1px solid #ddd;
    padding:8px;
    text-align:left;
}
.btn{
    background:#9e9e9e;
    border:none;
    padding:15px;
    font-size:14px;
    cursor:pointer;
}
.btn.green{background:#4caf50;color:white}
.btn.blue{background:#1976d2;color:white}
.btn.orange{background:#f9a825}
.footer{
    display:flex;
    justify-content:space-between;
    padding:10px;
    background:#ddd;
}
.footer button{
    padding:15px;
    font-size:16px;
}
</style>
</head>

<body>

<header>
    <div><b>POS Óptica</b></div>
    <div>
        <button>Cerrar (F9)</button>
    </div>
</header>

<div class="main">

    <!-- IZQUIERDA -->
    <div class="left">

        <div class="box">
            <b>Cliente</b><br>
            <input style="width:100%;padding:8px" placeholder="Buscar cliente">
            <br><br>
            <button class="btn orange">Buscar cliente</button>
            <button class="btn blue">Agregar cliente</button>
        </div>

        <div class="box">
            <b>Buscar producto</b><br>
            <input style="width:100%;padding:8px" placeholder="Nombre o SKU">
            <button class="btn orange" style="margin-top:5px">Buscar</button>
        </div>

        <table class="table">
            <tr>
                <th>Producto</th>
                <th>Cant</th>
                <th>Total</th>
            </tr>
            <tr>
                <td>Lentes monofocales</td>
                <td>1</td>
                <td>$1200</td>
            </tr>
            <tr>
                <td>Armazón</td>
                <td>1</td>
                <td>$800</td>
            </tr>
        </table>

        <div class="footer">
            <div>
                <b>Total:</b> $2000
            </div>
            <button class="btn green">Pagar (F2)</button>
        </div>

    </div>

    <!-- DERECHA -->
    <div class="right">
        <button class="btn">Agregar producto</button>
        <button class="btn">Editar producto</button>
        <button class="btn">Guardar venta</button>
        <button class="btn">Ventas pendientes</button>
        <button class="btn">Editar cliente</button>
        <button class="btn">Abrir cajón</button>
        <button class="btn">Descuento</button>
        <button class="btn">Imprimir</button>
        <button class="btn">Pago efectivo</button>
        <button class="btn">Pago tarjeta</button>
        <button class="btn">Pantalla completa</button>
        <button class="btn">Reporte X</button>
    </div>

</div>

</body>
</html>
"""

