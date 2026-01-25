from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

# ======================
# USUARIOS DEMO
# ======================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}

# ======================
# INVENTARIO DEMO
# ======================
PRODUCTOS = {
    "Armazón básico": {
        "precio": 800,
        "stock": 5
    },
    "Lentes monofocales": {
        "precio": 1200,
        "stock": 10
    },
    "Lentes antirreflejantes": {
        "precio": 1600,
        "stock": 8
    }
}

# ======================
# CAJA DEMO
# ======================
CAJA = {
    "abierta": False,
    "monto_inicial": 0,
    "total_ventas": 0
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
            return redirect(url_for("dashboard"))

        return "Credenciales incorrectas"

    return """
    <h2>Login POS Óptica</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario"><br><br>
        <input name="password" type="password" placeholder="Contraseña"><br><br>
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

    estado_caja = "Abierta" if CAJA["abierta"] else "Cerrada"

    return f"""
    <h2>Bienvenido {session['usuario']}</h2>
    <p>Rol: {session['rol']}</p>
    <p>Estado de caja: {estado_caja}</p>

    <a href="/abrir_caja">🔓 Abrir caja</a><br><br>
    <a href="/ventas">🧾 Nueva venta</a><br><br>
    <a href="/cerrar_caja">🔒 Cerrar caja</a><br><br>

    <a href="/logout">Cerrar sesión</a>
    """

# ======================
# VENTAS + INVENTARIO
# ======================
@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if not CAJA["abierta"]:
        return "Caja cerrada. Debe abrir caja antes de vender."

    total = 0
    detalle = ""
    error = ""

    if request.method == "POST":
        seleccionados = request.form.getlist("producto")

        for prod in seleccionados:
            if PRODUCTOS[prod]["stock"] <= 0:
                error = f"No hay stock disponible de {prod}"
                break

            PRODUCTOS[prod]["stock"] -= 1
            precio = PRODUCTOS[prod]["precio"]
            total += precio
            detalle += f"<li>{prod} - ${precio}</li>"

        if error:
            return f"<h3 style='color:red'>{error}</h3><a href='/ventas'>Volver</a>"

        CAJA["total_ventas"] += total

        return f"""
        <h2>Venta realizada</h2>
        <ul>{detalle}</ul>
        <h3>Total: ${total}</h3>
        <a href="/dashboard">Volver</a>
        """

    checkboxes = ""
    for p, data in PRODUCTOS.items():
        checkboxes += f"""
        <input type="checkbox" name="producto" value="{p}">
        {p} - ${data['precio']} (Stock: {data['stock']})<br>
        """

    return f"""
    <h2>Nueva venta</h2>
    <form method="post">
        {checkboxes}<br>
        <button>Vender</button>
    </form>
    """

# ======================
# ABRIR CAJA
# ======================
@app.route("/abrir_caja", methods=["GET", "POST"])
def abrir_caja():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        CAJA["abierta"] = True
        CAJA["monto_inicial"] = float(request.form["monto"])
        CAJA["total_ventas"] = 0
        return redirect(url_for("dashboard"))

    return """
    <h2>Abrir caja</h2>
    <form method="post">
        <input name="monto" type="number" placeholder="Monto inicial" required>
        <br><br>
        <button>Abrir caja</button>
    </form>
    """

# ======================
# CERRAR CAJA
# ======================
@app.route("/cerrar_caja")
def cerrar_caja():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if not CAJA["abierta"]:
        return "La caja ya está cerrada"

    CAJA["abierta"] = False
    total = CAJA["monto_inicial"] + CAJA["total_ventas"]

    return f"""
    <h2>Cierre de caja</h2>
    <p>Monto inicial: ${CAJA['monto_inicial']}</p>
    <p>Total ventas: ${CAJA['total_ventas']}</p>
    <h3>Total en caja: ${total}</h3>
    <a href="/dashboard">Volver</a>
    """

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()



