from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "demo_pos_optica"

# Usuarios de prueba
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "caja": {"password": "caja123", "rol": "caja"}
}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            session["usuario"] = usuario
            session["rol"] = USUARIOS[usuario]["rol"]
            return redirect(url_for("dashboard"))
        else:
            return "Credenciales incorrectas"

    return """
        <h2>Login POS Óptica</h2>
        <form method="post">
            <input name="usuario" placeholder="Usuario"><br><br>
            <input name="password" type="password" placeholder="Contraseña"><br><br>
            <button type="submit">Entrar</button>
        </form>
    """

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return f"""
        <h2>Bienvenido {session['usuario']}</h2>
        <p>Rol: {session['rol']}</p>
        <a href='/logout'>Cerrar sesión</a>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()
