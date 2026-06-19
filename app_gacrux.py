from flask import Flask, render_template_string, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

def conectar_bd():
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

# 🎨 DISEÑO FORMAL: GRISES, ACCENTOS ROJOS, MODELO ANTES DEL ESTAMPADO Y SIN EMOJIS
HTML_BASE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GACRUX - Panel de Almacén</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background-color: #1a1a1a; color: #e0e0e0; padding: 15px; }
        header { text-align: center; margin-bottom: 25px; padding: 15px; background-color: #262626; border-radius: 6px; border-bottom: 3px solid #e63946; }
        h2 { color: #ffffff; font-size: 1.6rem; letter-spacing: 1px; }
        
        .container { max-width: 1100px; margin: 0 auto; }
        .seccion { background-color: #262626; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h3 { margin-bottom: 15px; color: #ffffff; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input[type="text"] { width: 100%; padding: 12px; border-radius: 4px; border: 1px solid #404040; font-size: 1rem; margin-bottom: 15px; background-color: #333333; color: #ffffff; }
        input[type="text"]:focus { border-color: #e63946; outline: none; }
        
        .btn { width: 100%; padding: 14px; border-radius: 4px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; transition: 0.2s; }
        .btn-baja { background-color: #e63946; }
        .btn-baja:hover { background-color: #b91c1c; }
        #notificacion { text-align: center; margin-top: 12px; font-weight: bold; font-size: 1rem; }
        
        /* CONTENEDORES DE MODELOS */
        .contenedor-modelo { background-color: #262626; border-radius: 6px; padding: 15px; margin-bottom: 25px; border: 1px solid #404040; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        .titulo-modelo { font-size: 1.3rem; font-weight: bold; color: #e63946; margin-bottom: 12px; border-bottom: 1px solid #404040; padding-bottom: 6px; text-transform: uppercase; }
        
        /* TABLA INDUSTRIAL COMPACTA */
        .tabla-catalogo { width: 100%; border-collapse: collapse; margin-top: 5px; background-color: #1f1f1f; text-align: center; }
        .tabla-catalogo th { background-color: #333333; color: #aaaaaa; font-size: 0.85rem; font-weight: 600; padding: 8px; text-transform: uppercase; border: 1px solid #404040; }
        .tabla-catalogo td { padding: 10px; font-size: 1rem; border: 1px solid #404040; }
        .col-detalles { text-align: left; font-weight: bold; color: #ffffff; width: 45%; padding-left: 15px !important; }
        .stock-num { font-weight: bold; color: #ffffff; }
        .stock-cero { color: #555555 !important; font-weight: normal; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h2>SISTEMA GACRUX</h2>
            <p style="font-size: 0.85rem; color: #888888; margin-top: 4px;">Control de Inventario Centralizado</p>
        </header>

        <div class="seccion">
            <h3>Ajuste Rápido de Almacén</h3>
            <input type="text" id="codigo_barres" placeholder="Escanea o escribe código de barras..." autocomplete="off">
            <button class="btn btn-baja" onclick="procesarBaja()">Descontar 1 Unidad</button>
            <div id="notificacion"></div>
        </div>

        <div class="seccion">
            <h3>Existencias en Tiempo Real</h3>
            <input type="text" id="busqueda" placeholder="Filtrar por modelo, estampado o color..." onkeyup="buscarPrenda()">
            
            <div id="resultado_busqueda"></div>
        </div>
    </div>

    <script>
        document.getElementById('codigo_barres').focus();

        function procesarBaja() {
            let codigo = document.getElementById('codigo_barres').value.trim();
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
                    notif.innerText = "COINCIDENCIA: " + data.msg;
                    buscarPrenda();
                } else {
                    notif.style.color = '#e63946';
                    notif.innerText = "ERROR: " + data.msg;
                }
                document.getElementById('codigo_barres').value = '';
                document.getElementById('codigo_barres').focus();
            });
        }

        document.getElementById('codigo_barres').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') { procesarBaja(); }
        });

        function buscarPrenda() {
            let query = document.getElementById('busqueda').value;
            fetch('/api/buscar?q=' + query)
            .then(res => res.json())
            .then(data => {
                let contenedor = document.getElementById('resultado_busqueda');
                contenedor.innerHTML = '';
                
                // Agrupar los datos por MODELO (ej. SUDADERA, PLAYERA)
                let agrupado = {};
                data.forEach(p => {
                    let mod = p.modelo.toUpperCase().trim();
                    if (!agrupado[mod]) { agrupado[mod] = []; }
                    agrupado[mod].push(p);
                });
                
                // Armar las tablas agrupadas por tipo de prenda
                for (let mod in agrupado) {
                    let htmlModelo = `
                        <div class="contenedor-modelo">
                            <div class="titulo-modelo">${mod}</div>
                            <table class="tabla-catalogo">
                                <thead>
                                    <tr>
                                        <th style="text-align: left; padding-left: 15px;">Estampado / Color</th>
                                        <th style="width: 12%;">CH</th>
                                        <th style="width: 12%;">M</th>
                                        <th style="width: 12%;">G</th>
                                        <th style="width: 12%;">EG</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    agrupado[mod].forEach(p => {
                        htmlModelo += `
                            <tr>
                                <td class="col-detalles">${p.estampado} — <span style="color: #888888; font-weight: normal; font-size: 0.9rem;">${p.color}</span></td>
                                <td class="stock-num ${p.talla_ch == 0 ? 'stock-cero' : ''}">${p.talla_ch}</td>
                                <td class="stock-num ${p.talla_m == 0 ? 'stock-cero' : ''}">${p.talla_m}</td>
                                <td class="stock-num ${p.talla_g == 0 ? 'stock-cero' : ''}">${p.talla_g}</td>
                                <td class="stock-num ${p.talla_eg == 0 ? 'stock-cero' : ''}">${p.talla_eg}</td>
                            </tr>
                        `;
                    });
                    
                    htmlModelo += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    contenedor.innerHTML += htmlModelo;
                }
            });
        }
        
        buscarPrenda();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_BASE)

@app.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    db = conectar_bd()
    cursor = db.cursor(dictionary=True)
    if q:
        cursor.execute("SELECT * FROM panel_stock WHERE modelo LIKE %s OR estampado LIKE %s OR color LIKE %s ORDER BY modelo ASC, estampado ASC", (f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC")
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
            
            msg = f"{prenda['modelo']} - {prenda['estampado']} ({prenda['talla']})"
            cursor.close()
            db.close()
            return jsonify({'status': 'ok', 'msg': msg})
            
    cursor.close()
    db.close()
    return jsonify({'status': 'error', 'msg': 'Código de barras no válido.'})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
