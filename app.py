from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h2>POS Óptica Demo</h2>
    <a href="/pos">Entrar al POS</a>
    """

@app.route("/pos")
def pos():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>POS Óptica</title>

<style>
body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #F4F6F8;
}

/* ===== TOP BAR ===== */
.topbar {
    background: #1F4FD8;
    color: white;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.logo {
    font-size: 20px;
    font-weight: bold;
}

.logo span {
    font-size: 14px;
    color: #D1D5DB;
}

/* ===== LAYOUT ===== */
.container {
    display: flex;
    padding: 15px;
    gap: 15px;
}

/* LEFT */
.left {
    width: 70%;
    background: white;
    padding: 15px;
    border-radius: 8px;
}

/* RIGHT */
.right {
    width: 30%;
    background: #E5E7EB;
    padding: 15px;
    border-radius: 8px;
}

/* CLIENT */
.client-box input {
    width: 100%;
    padding: 10px;
    margin-bottom: 8px;
}

.btn {
    padding: 10px;
    border: none;
    cursor: pointer;
    border-radius: 6px;
    font-weight: bold;
}

.btn-blue { background: #1F4FD8; color: white; }
.btn-light { background: #60A5FA; color: white; }
.btn-green { background: #22C55E; color: white; }
.btn-red { background: #EF4444; color: white; }
.btn-gray { background: #D1D5DB; }

/* TABLE */
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

th, td {
    padding: 8px;
    border-bottom: 1px solid #E5E7EB;
    text-align: center;
}

/* TOTALS */
.totals {
    margin-top: 20px;
    background: #F9FAFB;
    padding: 10px;
    border-radius: 6px;
}

.totals h3 {
    margin: 5px 0;
}
</style>
</head>

<body>

<div class="topbar">
    <div class="logo">👓 ÓPTICA DEMO <span>Sistema POS</span></div>
    <div>Caja: <b>CERRADA</b></div>
</div>

<div class="container">

    <!-- LEFT PANEL -->
    <div class="left">

        <div class="client-box">
            <input placeholder="Cliente">
            <button class="btn btn-light">Buscar cliente</button>
            <button class="btn btn-blue">Agregar cliente</button>
        </div>

        <input placeholder="Buscar producto por nombre o SKU">

        <table>
            <tr>
                <th>SKU</th>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Descuento</th>
                <th>Total</th>
            </tr>
            <tr>
                <td>001</td>
                <td>Armazón básico</td>
                <td>1</td>
                <td>0%</td>
                <td>$800</td>
            </tr>
        </table>

        <div class="totals">
            <h3>Subtotal: $800</h3>
            <h3>IVA: $128</h3>
            <h2>Total: $928</h2>
        </div>

    </div>

    <!-- RIGHT PANEL -->
    <div class="right">
        <button class="btn btn-gray" style="width:100%">Agregar producto</button><br><br>
        <button class="btn btn-gray" style="width:100%">Editar producto</button><br><br>
        <button class="btn btn-gray" style="width:100%">Documentos cliente</button><br><br>
        <button class="btn btn-green" style="width:100%">Guardar venta</button><br><br>
        <button class="btn btn-red" style="width:100%">Cancelar</button>
    </div>

</div>

</body>
</html>
    """

if __name__ == "__main__":
    app.run(debug=True)
