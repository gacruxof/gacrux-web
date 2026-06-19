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

# 🎨 DISEÑO FORMAL Y ACTUALIZACIÓN EN TIEMPO REAL AUTOMÁTICA
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
        header { text-align: center; margin-bottom: 25px; padding: 15px; background-color: #262626; border-radius: 6px; border-bottom: 3px solid #444444; }
        h2 { color: #ffffff; font-size: 1.6rem; letter-spacing: 1px; }
        
        .container { max-width: 1100px; margin: 0 auto; }
        .seccion { background-color: #262626; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h3 { margin-bottom: 15px; color: #ffffff; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input[type="text"] { width: 100%; padding: 12px; border-radius: 4px; border: 1px solid #404040; font-size: 1rem; margin-bottom: 15px; background-color: #333333; color: #ffffff; }
        input[type="text"]:focus { border-color: #888888; outline: none; }
        
        .btn { width: 100%; padding: 14px; border-radius: 4px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; transition: 0.2s; }
        .btn-baja { background-color: #444444; border: 1px solid #555555; }
        .btn-baja:hover { background-color: #333333; }
        #notificacion { text-align: center; margin-top: 12px; font-weight: bold; font-size: 1rem; }
        
        /* BLOQUES INTERCALADOS */
        .contenedor-modelo { background-color: #262626; border-radius: 6px; padding: 20px; margin-bottom: 35px; border: 1px solid #404040; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .titulo-modelo { font-size: 1.6rem; font-weight: bold; margin-bottom: 20px; padding-bottom: 6px; text-transform: uppercase; border-bottom: 2px solid #404040; }
        
        .mod-azul .titulo-modelo { color: #1e3a8a; } 
        .mod-rojo .titulo-modelo { color: #7f1d1d; } 
        
        .bloque-estampado { margin-bottom: 25px; background-color: #1f1f1f; padding: 15px; border-radius: 4px; }
        .mod-azul .bloque-estampado { border-left: 5px solid #1e3a8a; }
        .mod-rojo .bloque-estampado { border-left: 5px solid #7f1d1d; }
        
        .titulo-estampado { font-size: 1.2rem; font-weight: bold; color: #ffffff; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .tabla-catalogo { width: 100%; border-collapse: collapse; text-align: center; background-color: #161616; }
        .tabla-catalogo th { background-color: #282828; color: #999999; font-size: 0.85rem; font-weight: 600; padding: 8px; text-transform: uppercase; border: 1px solid #333333; }
        .tabla-catalogo td { padding: 8px 10px; font-size: 1rem; border: 1px solid #333333; }
        
        .col-color { text-align: left; font-weight: bold; color: #dddddd; padding-left: 15px !important; width: 45%; }
        .stock-num { font-weight: bold; color: #ffffff; }
        .stock-cero { color: #3d3d3d !important; font-weight: normal; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h2>SISTEMA GACRUX</h2>
            <p style="font-size: 0.85rem; color: #777777; margin-top: 4px;">Control de Inventario Centralizado</p>
        </header>

        <div class="seccion">
            <h3>Ajuste Rápido de Almacén</h3>
            <input type="text" id="codigo_barras" placeholder="Escanea o escribe código de barras..." autocomplete="off">
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
        document.getElementById('codigo_barras').focus();

        function procesarBaja() {
            let codigo = document.getElementById('codigo_barras').value.trim();
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
                
                let estructura = {};
                data.forEach(p => {
                    let mod = p.modelo.toUpperCase().trim();
                    let est = p.estampado.toUpperCase().trim();
                    
                    if (!estructura[mod]) { estructura[mod] = {}; }
                    if (!estructura[mod][est]) { estructura[mod][est] = []; }
                    
                    estructura[mod][est].push(p);
                });
                
                let esAzul = true;
                
                for (let mod in estructura) {
                    let claseColor = esAzul ? 'mod-azul' : 'mod-rojo';
                    let htmlBlock = `<div class="contenedor-modelo ${claseColor}"><div class="titulo-modelo">${mod}</div>`;
                    
                    for (let est in estructura[mod]) {
                        htmlBlock += `
                            <div class="bloque-estampado">
                                <div class="titulo-estampado">${est}</div>
                                <table class="tabla-catalogo">
                                    <thead>
                                        <tr>
                                            <th style="text-align: left; padding-left: 15px;">Color</th>
                                            <th style="width: 12%;">CH</th>
                                            <th style="width: 12%;">M</th>
                                            <th style="width: 12%;">G</th>
                                            <th style="width: 12%;">EG</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                        `;
                        
                        estructura[mod][est].forEach(p => {
                            htmlBlock += `
                                <tr>
                                    <td class="col-color">${p.color.toUpperCase()}</td>
                                    <td class="stock-num ${p.talla_ch == 0 ? 'stock-cero' : ''}">${p.talla_ch}</td>
                                    <td class="stock-num ${p.talla_m == 0 ? 'stock-cero' : ''}">${p.talla_m}</td>
                                    <td class="stock-num ${p.talla_g == 0 ? 'stock-cero' : ''}">${p.talla_g}</td>
                                    <td class="stock-num ${p.talla_eg == 0 ? 'stock-cero' : ''}">${p.talla_eg}</td>
                                </tr>
                            `;
                        });
                        
                        htmlBlock += `
                                    </tbody>
                                </table>
                            </div>
                        `;
                    }
                    
                    htmlBlock += `</div>`;
                    contenedor.innerHTML += htmlBlock;
                    esAzul = !esAzul;
                }
            });
        }
        
        // 🔄 AUTOMATIZACIÓN: Ejecuta la búsqueda inicial y luego repite cada 3 segundos en silencio
        buscarPrenda();
        setInterval(buscarPrenda, 3000);
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
        cursor.execute("SELECT * FROM panel_stock WHERE modelo LIKE %s OR estampado LIKE %s OR color LIKE %s ORDER BY modelo ASC, estampado ASC, color ASC", (f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
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
