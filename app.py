from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

# Usuarios demo
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}

# Productos demo
PRODUCTOS = {
    "Armazón básico": 800,
    "Lentes monofocales": 1200,
    "Lentes antirreflejantes": 1600
}

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

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return f"""
        <h2>Bienvenido {session['usuario']}</h2>
        <p>Rol: {session['rol']}</p>

        <a href='/ventas'>🧾 Nueva venta</a><br><br>

        <a href='/logout'>Cerrar sesión</a>
    """


@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    total = 0
    detalle = ""

    if request.method == "POST":
        seleccionados = request.form.getlist("producto")
        for prod in seleccionados:
            total += PRODUCTOS[prod]
            detalle += f"<li>{prod} - ${PRODUCTOS[prod]}</li>"

        return f"""
        <h2>Venta realizada</h2>
        <ul>{detalle}</ul>
        <h3>Total: ${total}</h3>
        <a href='/dashboard'>Volver</a>
        """

    checkboxes = ""
    for p, precio in PRODUCTOS.items():
        checkboxes += f"""
        <input type='checkbox' name='producto' value='{p}'>
        {p} - ${precio}<br>
        """

    return f"""
    <h2>Nueva venta</h2>
    <form method="post">
        {checkboxes}<br>
        <button>Calcular total</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()

