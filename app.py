import os
import psycopg
from flask import (
    Flask, session, redirect, url_for,
    request
)

# ======================
# CONFIG
# ======================
app = Flask(__name__)
app.secret_key = "pos_optica_demo"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL)

# ======================
# LOGIN DEMO
# ======================
USUARIOS = {
    "admin": "admin123",
    "caja": "caja123"
}

# ======================
# LOGIN
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["usuario"]
        p = request.form["password"]

        if u in USUARIOS and USUARIOS[u] == p:
            session["usuario"] = u
            return redirect(url_for("pos"))

        return "<h3>Credenciales incorrectas</h3>"

    return """
    <style>
        body{font-family:Arial;background:#F4F6F8;display:flex;justify-content:center;align-items:center;height:100vh}
        .box{background:white;padding:30px;border-radius:8px;width:300px}
        input,button{width:100%;padding:10px;margin-top:10px}
        button{background:#1F4FD8;color:white;border:none}
    </style>

    <div class="box">
        <h2>👓 Óptica Demo</h2>
        <form method="post">
            <input name="usuario" placeholder="Usuario">
            <input name="password" type="password" placeholder="Contraseña">
            <button>Entrar</button>
        </form>
    </div>
    """

# ======================
# POS + VENTA
# ======================
@app.route("/pos", methods=["GET", "POST"])
def pos():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, precio FROM productos ORDER BY nombre")
    productos = cur.fetchall()

    mensaje = ""

    if request.method == "POST":
        total = 0

        for p in productos:
            cantidad = request.form.get(f"prod_{p[0]}")
            if cantidad:
                cantidad = int(cantidad)
                if cantidad > 0:
                    subtotal = cantidad * float(p[2])
                    total += subtotal

        if total > 0:
            cur.execute(
                "INSERT INTO ventas (total, usuario) VALUES (%s, %s)",
                (total, session["usuario"])
            )
            conn.commit()
            mensaje = f"<h3 style='color:green'>Venta realizada — Total ${total}</h3>"
        else:
            mensaje = "<h3 style='color:red'>No se seleccionaron productos</h3>"

    filas = ""
    for p in productos:
        filas += f"""
        <tr>
            <td>{p[1]}</td>
            <td>${p[2]}</td>
            <td>
                <input type="number" name="prod_{p[0]}" min="0" value="0" style="width:70px">
            </td>
        </tr>
        """

    cur.close()
    conn.close()

    return f"""
    <style>
        body{{font-family:Arial;background:#F4F6F8;margin:0}}
        header{{background:#1F4FD8;color:white;padding:15px}}
        main{{padding:20px}}
        table{{width:100%;border-collapse:collapse;background:white}}
        th,td{{padding:10px;border-bottom:1px solid #ddd}}
        th{{background:#E5E7EB}}
        .btn{{padding:10px 15px;border:none;border-radius:5px}}
        .btn-green{{background:#22C55E;color:white}}
        footer{{margin-top:20px;text-align:right}}
    </style>

    <header>
        <h2>👓 ÓPTICA DEMO — POS</h2>
        <small>Usuario: {session['usuario']}</small>
    </header>

    <main>
        {mensaje}

        <form method="post">
            <table>
                <tr>
                    <th>Producto</th>
                    <th>Precio</th>
                    <th>Cantidad</th>
                </tr>
                {filas}
            </table>

            <footer>
                <button class="btn btn-green">Cobrar</button>
            </footer>
        </form>
    </main>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
