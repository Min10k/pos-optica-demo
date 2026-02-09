import os
import psycopg
from flask import Flask, session, redirect, url_for

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
    from flask import request

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
# POS (SOLO LECTURA)
# ======================
@app.route("/pos")
def pos():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, precio, stock FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    filas = ""
    for p in productos:
        filas += f"""
        <tr>
            <td>{p[0]}</td>
            <td>${p[1]}</td>
            <td>{p[2]}</td>
            <td><input type="number" value="1" min="1" style="width:60px"></td>
        </tr>
        """

    return f"""
    <style>
        body{{font-family:Arial;background:#F4F6F8;margin:0}}
        header{{background:#1F4FD8;color:white;padding:15px}}
        main{{padding:20px}}
        table{{width:100%;border-collapse:collapse;background:white}}
        th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}
        th{{background:#E5E7EB}}
        .right{{text-align:right}}
        .btn{{padding:10px 15px;border:none;border-radius:5px}}
        .btn-green{{background:#22C55E;color:white}}
        .btn-red{{background:#EF4444;color:white}}
        footer{{margin-top:20px;text-align:right}}
    </style>

    <header>
        <h2>👓 ÓPTICA DEMO — POS</h2>
        <small>Usuario: {session['usuario']}</small>
    </header>

    <main>
        <h3>Productos</h3>

        <table>
            <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Cantidad</th>
            </tr>
            {filas}
        </table>

        <footer>
            <button class="btn btn-green">Pagar (demo)</button>
            <button class="btn btn-red">Cancelar</button>
        </footer>
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
