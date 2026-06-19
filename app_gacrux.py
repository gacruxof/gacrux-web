from flask import Flask, render_template_string, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

import os

def conectar_bd():
    # Si la app detecta que está en internet (Render), usa las variables de la nube.
    # Si está en tu casa, usa tu XAMPP local por defecto.
    if "RENDER" in os.environ:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=int(os.environ.get("DB_PORT", 3306))
        )
    else:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gacrux_pos"
        )
# 🎨 DISEÑO RESPONSIVO PARA MÓVILES (HTML5 + CSS3)
HTML_BASE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GACRUX - Almacén Móvil</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Arial', sans-serif; }
        body { background-color: #1e1e24; color: #fff; padding: 15px; }
        header { text-align: center; margin-bottom: 20px; padding: 10px; background-color: #0288d1; border-radius: 8px; }
        .container { max-width: 600px; margin: 0 auto; }
        .seccion { background-color: #2b2d42; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #3d405b; }
        h3 { margin-bottom: 10px; color: #edf2f4; font-size: 1.1rem; }
        input[type="text"] { width: 100%; padding: 12px; border-radius: 6px; border: none; font-size: 1rem; margin-bottom: 10px; }
        .btn { width: 100%; padding: 12px; border-radius: 6px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; }
        .btn-baja { background-color: #e63946; }
        .btn-buscar { background-color: #2a9d8f; }
        #notificacion { text-align: center; margin-top: 10px; font-weight: bold; font-size: 0.95rem; }
        .bloque-prenda { background-color: #fff; color: #333; padding: 12px; border-radius: 6px; margin-top: 10px; border-left: 5px solid #0288d1; }
        .tabla-stock { width: 100%; margin-top: 8px; border-collapse: collapse; text-align: center; }
        .tabla-stock th { background-color: #e2e8f0; font-size: 0.85rem; padding: 4px; }
        .tabla-stock td { font-size: 1rem; font-weight: bold; padding: 6px; border: 1px solid #cbd5e1; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h2>GACRUX POS 📱</h2>
            <p style="font-size: 0.85rem;">Módulo de Ajustes de Almacén</p>
        </header>

        <div class="seccion">
            <h3>Ajuste Rápido (Pistola o Teclado)</h3>
            <input type="text" id="codigo_barras" placeholder="Escribe o escanea código..." autocomplete="off">
            <button class="btn btn-baja" onclick="procesarBaja()">📉 DESCONTAR 1 PIEZA</button>
            <div id="notificacion"></div>
        </div>

        <div class="seccion">
            <h3>Consultar Stock Real</h3>
            <input type="text" id="busqueda" placeholder="Buscar estampado..." onkeyup="buscarPrenda()">
            <div id="resultado_busqueda"></div>
        </div>
    </div>

    <script>
        document.getElementById('codigo_barras').focus();

        function procesarBaja() {
            let codigo = document.getElementById('codigo_barras').value.strip ? document.getElementById('codigo_barras').value.strip() : document.getElementById('codigo_barras').value;
            if(!codigo) return;
            
            fetch('/api/baja', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({codigo: codigo})
            })
            .then(res => res.json())
            .then(data => {
                let notif = document.getElementById('notificacion');
                if(data.status === 'ok') {
                    notif.style.color = '#4caf50';
                    notif.innerText = "✅ " + data.msg;
                    buscarPrenda();
                } else {
                    notif.style.color = '#e63946';
                    notif.innerText = "❌ " + data.msg;
                }
                document.getElementById('codigo_barras').value = '';
                document.getElementById('codigo_barras').focus();
            });
        }

        document.getElementById('codigo_barras').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') { procesarBaja(); }
        });

        function buscarPrenda() {
            let query = document.getElementById('busqueda').value;
            fetch('/api/buscar?q=' + query)
            .then(res => res.json())
            .then(data => {
                let contenedor = document.getElementById('resultado_busqueda');
                contenedor.innerHTML = '';
                data.forEach(p => {
                    contenedor.innerHTML += `
                        <div class="bloque-prenda">
                            <div style="font-weight: bold; color: #0288d1; font-size: 0.9rem;">${p.modelo.toUpperCase()} - ${p.color}</div>
                            <div style="font-size: 1rem; margin-top: 2px; font-weight: bold;">${p.estampado}</div>
                            <table class="tabla-stock">
                                <tr><th>CH</th><th>M</th><th>G</th><th>EG</th></tr>
                                <tr>
                                    <td>${p.talla_ch}</td>
                                    <td>${p.talla_m}</td>
                                    <td>${p.talla_g}</td>
                                    <td>${p.talla_eg}</td>
                                </tr>
                            </table>
                        </div>
                    `;
                });
            });
        }
        
        buscarPrenda();
    </script>
</body>
</html>
"""

# =========================================================================
# RUTAS DEL SERVIDOR WEB
# =========================================================================
@app.route('/')
def index():
    return render_template_string(HTML_BASE)

@app.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    db = conectar_bd()
    cursor = db.cursor(dictionary=True)
    if q:
        cursor.execute("SELECT * FROM panel_stock WHERE modelo LIKE %s OR estampado LIKE %s OR color LIKE %s", (f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        cursor.execute("SELECT * FROM panel_stock")
    resultados = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(resultados)

@app.route('/api/baja', methods=['POST'])
def api_baja():
    data = request.get_json()
    codigo = data.get('codigo', '').strip()
    
    db = conectar_bd()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT modelo, estampado, color, talla, precio, panel_stock_id FROM inventario WHERE codigo_barras = %s", (codigo,))
    prenda = cursor.fetchone()
    
    if prenda:
        talla_map = {'CH':'talla_ch', 'M':'talla_m', 'G':'talla_g', 'EG':'talla_eg'}
        col = talla_map.get(prenda['talla'].upper().strip())
        
        if col and prenda['panel_stock_id']:
            cursor.execute(f"SELECT {col} FROM panel_stock WHERE id = %s", (prenda['panel_stock_id'],))
            stock_actual = cursor.fetchone()[col]
            
            if stock_actual <= 0:
                cursor.close()
                db.close()
                return jsonify({'status': 'error', 'msg': f"{prenda['modelo']} ({prenda['talla']}) ya está en 0."})
                
            cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (prenda['panel_stock_id'],))
            
            import datetime
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            precio_p = float(prenda['precio'])
            sql_h = """
                INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento)
                VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'WEB ALMACEN REGISTRO')
            """
            cursor.execute(sql_h, (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual))
            db.commit()
            
            msg = f"Descontado: {prenda['modelo']} - {prenda['talla']} ({prenda['color']})"
            cursor.close()
            db.close()
            return jsonify({'status': 'ok', 'msg': msg})
            
    cursor.close()
    db.close()
    return jsonify({'status': 'error', 'msg': 'Código de barras no válido.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)