from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import os
import datetime

app = Flask(__name__)
app.secret_key = 'CLAVE_SECRETA_GACRUX_ALBERTO_2026' # 🔑 Llave para encriptar las sesiones en los celulares

# Configuración del sistema de seguridad de accesos
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirige aquí si intentan espiar sin iniciar sesión

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

# Clase de usuario para que Flask rastree quién está navegando en el celular
class UsuarioWeb(UserMixin):
    def __init__(self, id_user, usuario, nombre_real):
        self.id = id_user
        self.usuario = usuario
        self.nombre_real = nombre_real

@login_manager.user_loader
def load_user(user_id):
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real FROM usuarios_gacrux WHERE id = %s", (user_id,))
        res = cursor.fetchone()
        cursor.close()
        db.close()
        if res:
            return UsuarioWeb(res['id'], res['usuario'], res['nombre_real'])
    except:
        pass
    return None

# 🔒 PANTALLA DE INICIO DE SESIÓN WEB AMIGABLE PARA CELULARES
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GACRUX - Iniciar Sesión</title>
    <style>
        body { background-color: #121214; color: white; font-family: 'Segoe UI', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #1e1e24; padding: 35px 30px; border-radius: 8px; width: 90%; max-width: 360px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border-bottom: 3px solid #1e3a8a; }
        h2 { font-size: 1.5rem; margin-bottom: 5px; letter-spacing: 1px; }
        p { color: #888; font-size: 0.9rem; margin-bottom: 25px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #333; background: #26262b; color: white; border-radius: 4px; box-sizing: border-box; font-size: 1rem; }
        input:focus { border-color: #1e3a8a; outline: none; }
        button { width: 100%; padding: 12px; background: #1e3a8a; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; margin-top: 15px; font-size: 1rem; text-transform: uppercase; }
        button:hover { background: #1d4ed8; }
        .error { color: #ff4a4a; font-size: 0.9rem; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>SISTEMA GACRUX</h2>
        <p>Control de Almacén en Línea</p>
        <form method="POST">
            <input type="text" name="usuario" placeholder="Usuario" required autocomplete="off">
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">ENTRAR 🔓</button>
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for msg in messages %}
              <div class="error">⚠️ {{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
    </div>
</body>
</html>
"""

# 🎨 DISEÑO WEB ADAPTATIVO INTELIGENTE (TU INTERFAZ ORIGINAL CON RASTREO)
HTML_BASE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GACRUX - Panel de Almacén</title>
    <style id="theme-style">
        /* 🌙 MODO OSCURO (POR DEFECTO) */
        :root {
            --bg-body: #1a1a1a;
            --bg-card: #262626;
            --bg-block: #1f1f1f;
            --bg-table: #161616;
            --bg-th: #282828;
            --text-color: #ffffff;
            --subtext-color: #777777;
            --border-color: #333333;
            --input-bg: #333333;
            --input-border: #404040;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; transition: background 0.2s, color 0.2s; }
        body { background-color: var(--bg-body); color: var(--text-color); padding: 15px; }
        
        header { position: relative; text-align: center; margin-bottom: 25px; padding: 15px; background-color: var(--bg-card); border-radius: 6px; border-bottom: 3px solid #444444; }
        h2 { color: #ffffff; font-size: 1.6rem; letter-spacing: 1px; }
        
        .theme-toggle { position: absolute; top: 15px; right: 15px; padding: 8px 12px; font-size: 0.85rem; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; background-color: #444444; color: white; }
        
        .container { max-width: 1100px; margin: 0 auto; }
        .seccion { background-color: var(--bg-card); padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h3 { margin-bottom: 15px; color: #ffffff; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input[type="text"] { width: 100%; padding: 12px; border-radius: 4px; border: 1px solid var(--input-border); font-size: 1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-color); }
        input[type="text"]:focus { border-color: #888888; outline: none; }
        
        .btn { width: 100%; padding: 14px; border-radius: 4px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; }
        .btn-baja { background-color: #444444; border: 1px solid #555555; }
        #notificacion { text-align: center; margin-top: 12px; font-weight: bold; font-size: 1rem; }
        
        .contenedor-modelo { background-color: var(--bg-card); border-radius: 6px; padding: 20px; margin-bottom: 35px; border: 1px solid var(--input-border); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        
        .header-modelo-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding: 10px 15px; border-radius: 4px; color: #ffffff; }
        .mod-azul .header-modelo-flex { background-color: #1e3a8a; }
        .mod-rojo .header-modelo-flex { background-color: #7f1d1d; }
        .titulo-modelo { font-size: 1.3rem; font-weight: bold; text-transform: uppercase; }
        .total-modelo-top { font-size: 1.1rem; font-weight: bold; }
        
        .bloque-estampado { margin-bottom: 25px; background-color: var(--bg-block); padding: 15px; border-radius: 4px; }
        .mod-azul .bloque-estampado { border-left: 5px solid #1e3a8a; }
        .mod-rojo .bloque-estampado { border-left: 5px solid #7f1d1d; }
        
        .titulo-estampado { font-size: 1.2rem; font-weight: bold; color: var(--text-color); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .tabla-catalogo { width: 100%; border-collapse: collapse; text-align: center; background-color: var(--bg-table); }
        .tabla-catalogo th { background-color: var(--bg-th); color: #999999; font-size: 0.85rem; font-weight: 600; padding: 8px; text-transform: uppercase; border: 1px solid var(--border-color); }
        .tabla-catalogo td { padding: 8px 10px; font-size: 1rem; border: 1px solid var(--border-color); }
        
        .col-color { text-align: left; font-weight: bold; color: var(--text-color); padding-left: 15px !important; }
        .stock-num { font-weight: bold; color: var(--text-color); }
        .stock-cero { color: #3d3d3d !important; font-weight: normal; }
        
        .fila-totales-excel { width: 100%; padding: 8px 15px; background-color: var(--bg-block); font-size: 0.9rem; font-weight: bold; color: #e63946; border-top: 1px dashed #e63946; display: flex; justify-content: space-between; flex-wrap: wrap; }
        
        .user-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; font-size: 0.85rem; color: var(--subtext-color); border-top: 1px solid var(--border-color); padding-top: 12px; }
        .logout-link { color: #e63946; font-weight: bold; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h2>SISTEMA GACRUX</h2>
            <p style="font-size: 0.85rem; color: var(--subtext-color); margin-top: 4px;">Control de Inventario Centralizado</p>
            <button class="theme-toggle" onclick="alternarTemaWeb()">CAMBIAR TEMA ☀️</button>
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
            
            <div class="user-footer">
                <div>👤 Sesión activa: <strong>{{ empleado }}</strong></div>
                <div><a class="logout-link" href="/logout">CERRAR SESIÓN 🚪</a></div>
            </div>
        </div>
    </div>

    <script>
        let modoOscuroActivo = true;

        function alternarTemaWeb() {
            modoOscuroActivo = !modoOscuroActivo;
            const root = document.documentElement;
            const btn = document.querySelector('.theme-toggle');
            
            if (modoOscuroActivo) {
                btn.innerText = "CAMBIAR TEMA ☀️";
                root.style.setProperty('--bg-body', '#1a1a1a');
                root.style.setProperty('--bg-card', '#262626');
                root.style.setProperty('--bg-block', '#1f1f1f');
                root.style.setProperty('--bg-table', '#161616');
                root.style.setProperty('--bg-th', '#282828');
                root.style.setProperty('--text-color', '#ffffff');
                root.style.setProperty('--subtext-color', '#777777');
                root.style.setProperty('--border-color', '#333333');
                root.style.setProperty('--input-bg', '#333333');
                root.style.setProperty('--input-border', '#404040');
            } else {
                btn.innerText = "CAMBIAR TEMA 🌙";
                root.style.setProperty('--bg-body', '#f4f6f9');
                root.style.setProperty('--bg-card', '#ffffff');
                root.style.setProperty('--bg-block', '#f8f9fa');
                root.style.setProperty('--bg-table', '#ffffff');
                root.style.setProperty('--bg-th', '#e2e8f0');
                root.style.setProperty('--text-color', '#000000');
                root.style.setProperty('--subtext-color', '#555555');
                root.style.setProperty('--border-color', '#cbd5e1');
                root.style.setProperty('--input-bg', '#ffffff');
                root.style.setProperty('--input-border', '#cbd5e1');
            }
        }

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
                    let est = p.estampado.trim();
                    
                    if (!estructura[mod]) { estructura[mod] = {}; }
                    if (!estructura[mod][est]) { estructura[mod][est] = []; }
                    
                    estructura[mod][est].push(p);
                });
                
                let esAzul = true;
                
                for (let mod in estructura) {
                    let totalLoteAcumulado = 0;
                    for (let est_k in estructura[mod]) {
                        estructura[mod][est_k].forEach(p => {
                            totalLoteAcumulado += (p.talla_ch + p.talla_m + p.talla_g + p.talla_eg);
                        });
                    }

                    let claseColor = esAzul ? 'mod-azul' : 'mod-rojo';
                    let htmlBlock = `
                        <div class="contenedor-modelo ${claseColor}">
                            <div class="header-modelo-flex">
                                <div class="titulo-modelo">MODELO: ${mod}</div>
                                <div class="total-modelo-top">TOTAL LOTE: ${totalLoteAcumulado} pzas</div>
                            </div>
                    `;
                    
                    for (let est in estructura[mod]) {
                        let sumCH = 0, sumM = 0, sumG = 0, sumEG = 0;
                        estructura[mod][est].forEach(p => {
                            sumCH += p.talla_ch;
                            sumM += p.talla_m;
                            sumG += p.talla_g;
                            sumEG += p.talla_eg;
                        });

                        htmlBlock += `
                            <div class="bloque-estampado">
                                <div class="titulo-estampado">${est.toUpperCase()}</div>
                                <table class="tabla-catalogo">
                                    <thead>
                                        <tr>
                                            <th style="text-align: left; padding-left: 15px;">Color</th>
                                            ${sumCH > 0 ? '<th style="width: 13%;">CH</th>' : ''}
                                            ${sumM > 0 ? '<th style="width: 13%;">M</th>' : ''}
                                            ${sumG > 0 ? '<th style="width: 13%;">G</th>' : ''}
                                            ${sumEG > 0 ? '<th style="width: 13%;">EG</th>' : ''}
                                        </tr>
                                    </thead>
                                    <tbody>
                        `;
                        
                        estructura[mod][est].forEach(p => {
                            htmlBlock += `
                                <tr>
                                    <td class="col-color">${p.color.toUpperCase()}</td>
                                    ${sumCH > 0 ? `<td class="stock-num ${p.talla_ch == 0 ? 'stock-cero' : ''}">${p.talla_ch}</td>` : ''}
                                    ${sumM > 0 ? `<td class="stock-num ${p.talla_m == 0 ? 'stock-cero' : ''}">${p.talla_m}</td>` : ''}
                                    ${sumG > 0 ? `<td class="stock-num ${p.talla_g == 0 ? 'stock-cero' : ''}">${p.talla_g}</td>` : ''}
                                    ${sumEG > 0 ? `<td class="stock-num ${p.talla_eg == 0 ? 'stock-cero' : ''}">${p.talla_eg}</td>` : ''}
                                </tr>
                            `;
                        });
                        
                        let sumaTotalTabla = sumCH + sumM + sumG + sumEG;

                        let partesTotales = [];
                        if (sumCH > 0) partesTotales.push(`CH: ${sumCH}`);
                        if (sumM > 0) partesTotales.push(`M: ${sumM}`);
                        if (sumG > 0) partesTotales.push(`G: ${sumG}`);
                        if (sumEG > 0) partesTotales.push(`EG: ${sumEG}`);

                        htmlBlock += `
                                    </tbody>
                                </table>
                                <div class="fila-totales-excel">
                                    <div>${partesTotales.join(' &nbsp;|&nbsp; ')}</div>
                                    <div>SUMA TOTAL: ${sumaTotalTabla}</div>
                                </div>
                            </div>
                        `;
                    }
                    
                    htmlBlock += `</div>`;
                    contenedor.innerHTML += htmlBlock;
                    esAzul = !esAzul;
                }
            });
        }
        
        buscarPrenda();
        setInterval(function() {
            if(document.getElementById('busqueda').value.trim()) { return; }
            buscarPrenda();
        }, 3000);
    </script>
</body>
</html>
"""

# 🔑 ACCESO AL LOGIN DESDE EL NAVEGADOR
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('usuario', '').strip().lower()
        pass_input = request.form.get('password', '').strip()
        
        try:
            db = conectar_bd()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id, usuario, nombre_real FROM usuarios_gacrux WHERE usuario = %s AND password = %s", (user_input, pass_input))
            validado = cursor.fetchone()
            cursor.close()
            db.close()
            
            if validado:
                user_obj = UsuarioWeb(validado['id'], validado['usuario'], validado['nombre_real'])
                login_user(user_obj)
                return redirect(url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos')
        except Exception as e:
            flash(f'Error de conexión: {e}')
            
    return render_template_string(HTML_LOGIN)

# 👑 RUTA PRINCIPAL PROTEGIDA CON CONTRASEÑA
@app.route('/')
@login_required
def index():
    return render_template_string(HTML_BASE, empleado=current_user.nombre_real)

@app.route('/api/buscar')
@login_required
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
@login_required
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
            
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            precio_p = float(prenda['precio'])
            
            # 📝 SE AUDITA AUTOMÁTICAMENTE EL EMPLEADO QUE DESTRABÓ LA SESIÓN WEB
            sql_h = """
                INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por)
                VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'WEB ALMACEN REGISTRO', %s)
            """
            cursor.execute(sql_h, (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, current_user.nombre_real))
            db.commit()
            
            msg = f"{prenda['modelo']} - {prenda['estampado']} ({prenda['talla']})"
            cursor.close()
            db.close()
            return jsonify({'status': 'ok', 'msg': msg})
            
    cursor.close()
    db.close()
    return jsonify({'status': 'error', 'msg': 'Código de barras no válido.'})

# 🚪 RUTA PARA SALIR DE LA SESIÓN WEB
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
