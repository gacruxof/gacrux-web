import os
import datetime
import io
import base64
import json
import math
import traceback
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

# Werkzeug para atrapar errores nativos del servidor
from werkzeug.exceptions import HTTPException

from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.barcode import code128

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('JWT_SECRET', os.environ.get('SECRET_KEY', 'CLAVE_SECRETA_GACRUX_ALBERTO_2026'))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

# 🔥 ATRAPA-TODO GLOBAL PARA FORZAR RESPUESTAS JSON (EVITA HTML DE RENDER) 🔥
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    error_exacto = traceback.format_exc()
    print("💥 ERROR GLOBAL DEL SERVIDOR:", error_exacto)
    return jsonify({'error': f"💥 Falla Interna (Posible falta de Memoria en Render):\n{error_exacto}"}), 500

def safe_int(val):
    try: return int(val)
    except: return 0

def conectar_bd():
    try:
        db = mysql.connector.connect(
            host=os.environ.get("DB_HOST", "mysql-292462b-gacrux-of.a.aivencloud.com"),
            user=os.environ.get("DB_USER", "avnadmin"),
            password=os.environ.get("DB_PASSWORD", "AVNS_lJSsblo1fLuMi6cA-yW"), 
            database=os.environ.get("DB_NAME", "defaultdb"),
            port=safe_int(os.environ.get("DB_PORT", 19257)),
            connect_timeout=8
        )
        db.ping(reconnect=True, attempts=3, delay=1)
        return db
    except Exception as e:
        raise Exception("Aiven DB no responde: " + str(e))

class UsuarioWeb(UserMixin):
    def __init__(self, id_user, usuario, nombre_real, rol_puesto):
        self.id = id_user; self.usuario = usuario; self.nombre_real = nombre_real; self.rol_puesto = rol_puesto

@login_manager.user_loader
def load_user(user_id):
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto FROM usuarios_gacrux WHERE id = %s", (user_id,))
        res = cursor.fetchone()
        if res: return UsuarioWeb(res['id'], res['usuario'], res['nombre_real'], res['rol_puesto'])
    except Exception: pass
    finally:
        if cursor: cursor.close()
        if db: db.close()
    return None

# ==============================================================================
# 🔥 FUNCIÓN GENERADORA DE CÓDIGOS INDUSTRIALES 🔥
# ==============================================================================
def generar_codigo_13_nube(cursor, modelo, estampado, color, talla):
    cursor.execute("SELECT SUBSTRING(codigo_barras, 1, 5) AS mod_id FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo,))
    res_mod = cursor.fetchone()
    if res_mod and res_mod.get('mod_id') and str(res_mod['mod_id']).isdigit(): 
        mod_str = str(res_mod['mod_id'])
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 1, 5) AS UNSIGNED)) AS max_mod FROM inventario WHERE LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'")
        res_max_mod = cursor.fetchone()
        max_m = res_max_mod.get('max_mod') if res_max_mod and res_max_mod.get('max_mod') else 0
        mod_str = f"{int(max_m) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 6, 5) AS est_id FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado))
    res_est = cursor.fetchone()
    if res_est and res_est.get('est_id') and str(res_est['est_id']).isdigit(): 
        est_str = str(res_est['est_id'])
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 6, 5) AS UNSIGNED)) AS max_est FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo,))
        res_max_est = cursor.fetchone()
        max_e = res_max_est.get('max_est') if res_max_est and res_max_est.get('max_est') else 0
        est_str = f"{int(max_e) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 11, 2) AS col_id FROM inventario WHERE modelo = %s AND estampado = %s AND color = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado, color))
    res_col = cursor.fetchone()
    if res_col and res_col.get('col_id') and str(res_col['col_id']).isdigit(): 
        col_str = str(res_col['col_id'])
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 11, 2) AS UNSIGNED)) AS max_col FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo, estampado))
        res_max_col = cursor.fetchone()
        max_c = res_max_col.get('max_col') if res_max_col and res_max_col.get('max_col') else 0
        col_str = f"{int(max_c) + 1:02d}"

    talla_id = {'CH': 1, 'M': 2, 'G': 3, 'XG': 4, 'EX G': 4, 'T-12': 5, 'T-16': 6, 'EG': 4}.get(talla.upper(), 9)
    return f"{mod_str}{est_str}{col_str}{talla_id:01d}"

# ==============================================================================
# HTML WEB (PUENTE LIGERO PARA ESCANEO DE ALMACÉN Y POS)
# ==============================================================================
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>GACRUX - Iniciar Sesión</title>
    <style>
        body { background-color: #121214; color: white; font-family: 'Segoe UI', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #1e1e24; padding: 35px 30px; border-radius: 12px; width: 90%; max-width: 360px; text-align: center; box-shadow: 0 8px 25px rgba(0,0,0,0.6); border-bottom: 4px solid #1e3a8a; }
        h2 { font-size: 1.6rem; margin-bottom: 5px; letter-spacing: 1px; color: #89b4fa;}
        p { color: #a6adc8; font-size: 0.95rem; margin-bottom: 25px; }
        .input-group { position: relative; width: 100%; margin: 12px 0; }
        input { width: 100%; padding: 14px; border: 1px solid #313244; background: #181825; color: white; border-radius: 6px; box-sizing: border-box; font-size: 1rem; transition: border 0.3s;}
        input:focus { border-color: #89b4fa; outline: none; }
        .input-group input { padding-right: 45px; }
        .btn-ojo { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #888; cursor: pointer; font-size: 1.2rem; padding: 5px; }
        button[type="submit"] { width: 100%; padding: 14px; background: #1e3a8a; border: none; color: white; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 15px; font-size: 1.1rem; text-transform: uppercase; box-shadow: 0 4px 0 #11111b; transition: 0.2s;}
        button[type="submit"]:active { transform: translateY(4px); box-shadow: 0 0 0 #11111b; }
        .error { color: #f38ba8; font-size: 0.9rem; margin-top: 15px; font-weight: bold; background: rgba(243, 139, 168, 0.1); padding: 10px; border-radius: 6px;}
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🚀 GACRUX</h2>
        <p>Control de Almacén Móvil</p>
        <form method="POST">
            <div class="input-group">
                <input type="text" name="usuario" placeholder="Usuario" required autocomplete="off">
            </div>
            <div class="input-group">
                <input type="password" id="password" name="password" placeholder="Contraseña" required>
                <button type="button" class="btn-ojo" onclick="toggleOjoWeb()">👁️</button>
            </div>
            <button type="submit">ENTRAR</button>
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for msg in messages %}
              <div class="error">⚠️ {{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
    </div>
    <script>
        function toggleOjoWeb() {
            const labelPass = document.getElementById('password');
            const btnOjo = document.querySelector('.btn-ojo');
            if (labelPass.type === 'password') { labelPass.type = 'text'; btnOjo.style.color = '#89b4fa'; } 
            else { labelPass.type = 'password'; btnOjo.style.color = '#888'; }
        }
    </script>
</body>
</html>
"""

HTML_BASE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>GACRUX - Escáner Puente</title>
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <style>
        :root {
            --bg-body: #11111b; --bg-card: #1e1e2e; --bg-block: #181825; 
            --text-main: #cdd6f4; --text-muted: #a6adc8; --border-color: #313244;
            --input-bg: #11111b; --input-border: #45475a; --primary: #1e3a8a; --danger: #e63946; --success: #16a34a;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background-color: var(--bg-body); color: var(--text-main); padding: 10px 15px; padding-top: 80px;}
        header { position: fixed; top: 0; left: 0; right: 0; height: 65px; background-color: var(--bg-card); display: flex; justify-content: space-between; align-items: center; padding: 0 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); z-index: 1000; border-bottom: 2px solid var(--primary); }
        .logo-title { font-size: 1.5rem; font-weight: 900; color: var(--primary); letter-spacing: 1px;}
        .profile-btn { background: var(--bg-block); color: var(--text-main); font-size: 1.2rem; border: 1px solid var(--border-color); border-radius: 50%; width: 42px; height: 42px; display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .container { max-width: 600px; margin: 0 auto; }
        .seccion { background-color: var(--bg-card); padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border: 1px solid var(--border-color); text-align: center;}
        
        .modo-switch { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 25px; }
        .btn-modo { flex: 1; padding: 15px 10px; font-size: 1rem; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; color: white; transition: 0.2s; }
        .modo-inactivo { background-color: var(--bg-block); color: var(--text-muted); border: 1px solid var(--border-color); }
        
        .modo-baja-activo { background-color: var(--danger); box-shadow: 0 0 12px rgba(230, 57, 70, 0.5); }
        .modo-pos-activo { background-color: var(--success); box-shadow: 0 0 12px rgba(22, 163, 74, 0.5); }

        input[type="text"] { width: 100%; padding: 18px; border-radius: 8px; border: 2px solid var(--input-border); font-size: 1.1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-main); text-align: center; }
        input[type="text"]:focus { border-color: var(--primary); outline: none; }
        
        .btn-accion { width: 100%; padding: 18px; border-radius: 8px; border: none; font-size: 1.1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; box-shadow: 0 4px 0 rgba(0,0,0,0.3); transition: 0.2s; margin-bottom: 10px;}
        .btn-accion:active { transform: translateY(4px); box-shadow: 0 0 0 rgba(0,0,0,0); }
        
        .btn-camara { background-color: var(--primary); display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 1.2rem;}
        
        #contenedor-lector { position: relative; width: 100%; margin: 0 auto 20px auto; display: none; }
        #reader { width: 100%; border-radius: 12px; overflow: hidden; border: 3px solid var(--primary); background: black;}
        .contador-escaner { position: absolute; top: 10px; right: 10px; background-color: var(--danger); color: white; padding: 6px 15px; border-radius: 20px; font-weight: 900; font-size: 1.5rem; display: none; z-index: 999; box-shadow: 0 4px 10px rgba(0,0,0,0.6); border: 2px solid white; transition: transform 0.15s ease-out; }
        
        #controles-camara { display: none; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .btn-cerrar-cam { background-color: var(--bg-block); color: white; border: 1px solid var(--border-color); width: 30%; }
        .btn-disparar { background-color: #2e7d32; flex-grow: 1; }
        
        #notificacion { text-align: center; margin-top: 20px; font-weight: bold; font-size: 1.1rem; padding: 10px; border-radius: 8px; min-height: 45px;}
    </style>
</head>
<body>
    <header>
        <div class="logo-title">⭐ GACRUX</div>
        <div onclick="window.location.href='/logout'" class="profile-btn" title="Cerrar Sesión">👤</div>
    </header>

    <div class="container">
        <div class="seccion">
            
            <div class="modo-switch">
                <button id="btn-modo-baja" class="btn-modo modo-baja-activo" onclick="setModo('baja')">🔻 MODO ALMACÉN</button>
                <button id="btn-modo-pos" class="btn-modo modo-inactivo" onclick="setModo('pos')">🛒 MODO POS</button>
            </div>

            <button class="btn-accion btn-camara" id="btn-encender-cam" onclick="encenderScanner()"><span>📷</span> INICIAR CÁMARA</button>
            
            <div id="contenedor-lector">
                <div id="reader"></div>
                <div id="badge-contador" class="contador-escaner">x1</div>
            </div>
            
            <div id="controles-camara">
                <button class="btn-accion btn-cerrar-cam" onclick="apagarScanner()">CERRAR</button>
                <button class="btn-accion btn-disparar" id="btn-disparar" onclick="activarDisparo()">🎯 LEER CÓDIGO</button>
            </div>

            <input type="text" id="codigo_barras" placeholder="Escribe el código manualmente..." autocomplete="off">
            <button class="btn-accion" id="btn-procesar-manual" style="background-color: var(--bg-block); border: 1px solid var(--border-color); color: var(--text-main);" onclick="procesarEscaneo()">EJECUTAR MANUAL</button>
            
            <div id="notificacion"></div>
        </div>
    </div>

    <script>
        let modoActual = 'baja';
        let html5QrCode = null;
        let scannerActivoParaLeer = false; 
        let ultimoCodigoEscaneado = "";
        let contadorMismoCodigo = 0;

        function setModo(modo) {
            modoActual = modo;
            const btnBaja = document.getElementById('btn-modo-baja');
            const btnPos = document.getElementById('btn-modo-pos');
            
            if (modo === 'baja') {
                btnBaja.className = 'btn-modo modo-baja-activo';
                btnPos.className = 'btn-modo modo-inactivo';
            } else {
                btnPos.className = 'btn-modo modo-pos-activo';
                btnBaja.className = 'btn-modo modo-inactivo';
            }
            document.getElementById('notificacion').innerText = "";
        }

        function hacerBeep() {
            try {
                let AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return; 
                let ctx = new AudioContext();
                let osc = ctx.createOscillator(); let gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = "square"; osc.frequency.setValueAtTime(850, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                osc.start(); osc.stop(ctx.currentTime + 0.15); 
            } catch(e) {}
        }

        function encenderScanner() {
            document.getElementById('codigo_barras').setAttribute('readonly', 'true');
            document.getElementById('contenedor-lector').style.display = 'block'; 
            document.getElementById('btn-encender-cam').style.display = 'none';
            document.getElementById('controles-camara').style.display = 'flex';
            
            html5QrCode = new Html5Qrcode("reader");
            const config = { fps: 10, qrbox: { width: 250, height: 120 } };

            Html5Qrcode.getCameras().then(devices => {
                if (devices && devices.length) {
                    let cameraId = devices[0].id;
                    for (let i = 0; i < devices.length; i++) {
                        let lbl = devices[i].label.toLowerCase();
                        if (lbl.includes("back") || lbl.includes("trasera") || lbl.includes("environment")) {
                            cameraId = devices[i].id;
                        }
                    }
                    if (cameraId === devices[0].id && devices.length > 1) {
                        cameraId = devices[devices.length - 1].id;
                    }
                    iniciarLecturaConId(cameraId, config);
                } else {
                    iniciarLecturaConId({ facingMode: "environment" }, config);
                }
            }).catch(err => {
                iniciarLecturaConId({ facingMode: "environment" }, config);
            });
        }

        function iniciarLecturaConId(idCamara, config) {
            html5QrCode.start(idCamara, config, 
                (textoDecodificado) => {
                    if (scannerActivoParaLeer) {
                        scannerActivoParaLeer = false; hacerBeep(); 
                        if (textoDecodificado === ultimoCodigoEscaneado) { contadorMismoCodigo++; } 
                        else { ultimoCodigoEscaneado = textoDecodificado; contadorMismoCodigo = 1; }
                        
                        const badge = document.getElementById('badge-contador');
                        badge.style.display = 'block'; badge.innerText = "x" + contadorMismoCodigo;
                        badge.style.transform = "scale(1.3)"; setTimeout(() => { badge.style.transform = "scale(1)"; }, 150);
                        
                        document.getElementById('codigo_barras').value = textoDecodificado;
                        const btnDisparar = document.getElementById('btn-disparar');
                        btnDisparar.innerHTML = "🎯 LEER CÓDIGO"; btnDisparar.style.backgroundColor = "#2e7d32";
                        procesarEscaneo();
                    }
                }, (errorMensaje) => {}
            ).catch(err => {
                if(idCamara !== { facingMode: "environment" }) {
                    html5QrCode.start({ facingMode: "environment" }, config, () => {}, () => {}).catch(e => {
                        alert("Error al iniciar la cámara. Verifica permisos del navegador.");
                        apagarScanner();
                    });
                } else {
                    alert("Error al iniciar la cámara. Verifica permisos del navegador.");
                    apagarScanner();
                }
            });
        }

        function activarDisparo() {
            if (!html5QrCode) return;
            scannerActivoParaLeer = true; 
            const btnDisparar = document.getElementById('btn-disparar');
            btnDisparar.innerHTML = "👀 ENFOCA EL CÓDIGO..."; btnDisparar.style.backgroundColor = "#d97706"; 
        }

        function apagarScanner() {
            document.getElementById('codigo_barras').removeAttribute('readonly');
            if (html5QrCode) {
                html5QrCode.stop().then(() => {
                    document.getElementById('contenedor-lector').style.display = 'none'; 
                    document.getElementById('controles-camara').style.display = 'none'; 
                    document.getElementById('btn-encender-cam').style.display = 'flex';
                }).catch(err => {});
            }
        }

        function procesarEscaneo() {
            let codigo = document.getElementById('codigo_barras').value.trim();
            if(!codigo) return;
            
            let url = modoActual === 'baja' ? '/api/baja' : '/api/pos/enviar';
            
            fetch(url, {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({codigo: codigo})
            }).then(res => res.json()).then(data => {
                let notif = document.getElementById('notificacion');
                if(data.status === 'ok') {
                    notif.style.backgroundColor = 'rgba(22, 163, 74, 0.2)';
                    notif.style.color = 'var(--success)'; 
                    notif.innerText = modoActual === 'baja' ? ("✅ DESCONTADO: " + (data.msg || '')) : "🛒 ENVIADO A POS";
                } else {
                    notif.style.backgroundColor = 'rgba(230, 57, 70, 0.2)';
                    notif.style.color = 'var(--danger)'; 
                    notif.innerText = "❌ ERROR: " + (data.msg || data.error);
                }
                document.getElementById('codigo_barras').value = '';
            }).catch(err => {
                let notif = document.getElementById('notificacion');
                notif.style.backgroundColor = 'rgba(230, 57, 70, 0.2)';
                notif.style.color = 'var(--danger)'; 
                notif.innerText = "❌ Error de red con el servidor.";
            });
        }
        
        document.getElementById('codigo_barras').addEventListener('keypress', function(e) { 
            if (e.key === 'Enter') procesarEscaneo(); 
        });
    </script>
</body>
</html>
"""

@app.route('/api/ping', methods=['GET'])
def api_ping(): return jsonify({'status': 'despierto'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('usuario', '').strip().lower()
        pass_input = request.form.get('password', '').strip()
        db = None; cursor = None
        try:
            db = conectar_bd(); cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id, usuario, nombre_real, rol_puesto, password FROM usuarios_gacrux WHERE usuario = %s", (user_input,))
            usuario_bd = cursor.fetchone()
            if usuario_bd and usuario_bd['password'] == pass_input:
                user_obj = UsuarioWeb(usuario_bd['id'], usuario_bd['usuario'], usuario_bd['nombre_real'], usuario_bd['rol_puesto'])
                login_user(user_obj); return redirect(url_for('index'))
            else: flash('Usuario o contraseña incorrectos')
        except Exception as e: flash(f'Error de conexión: {e}')
        finally:
            if cursor: cursor.close()
            if db: db.close()
    return render_template_string(HTML_LOGIN)

@app.route('/')
@login_required
def index():
    return render_template_string(HTML_BASE)

@app.route('/api/login', methods=['POST'])
def api_login_movil():
    datos = request.get_json(); user_input = datos.get('usuario', '').strip().lower(); pass_input = datos.get('password', '').strip()
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto, password FROM usuarios_gacrux WHERE usuario = %s", (user_input,))
        usuario_bd = cursor.fetchone()
        if usuario_bd and usuario_bd['password'] == pass_input:
            return jsonify({'token': f"gacrux-auth-{usuario_bd['id']}", 'nombre_real': usuario_bd['nombre_real'], 'rol_puesto': usuario_bd['rol_puesto']}), 200
        else: return jsonify({'error': 'Credenciales incorrectas'}), 401
    except Exception as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/bases', methods=['GET'])
def api_app_bases():
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM modelos_base ORDER BY nombre ASC")
        modelos = cursor.fetchall()
        cursor.execute("SELECT id, nombre FROM colores_base ORDER BY nombre ASC")
        colores = cursor.fetchall()
        return jsonify({'modelos': modelos, 'colores': colores})
    except Exception as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/receta/<modelo>', methods=['GET'])
def api_get_receta(modelo):
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recetas_madre WHERE modelo = %s", (modelo,))
        res = cursor.fetchone()
        if res: return jsonify(res)
        return jsonify({})
    except Exception: return jsonify({})
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/baja', methods=['POST'])
@login_required
def api_baja_web():
    data = request.get_json(); codigo = data.get('codigo', '').strip()
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT modelo, estampado, color, talla, precio, panel_stock_id FROM inventario WHERE codigo_barras = %s", (codigo,))
        prenda = cursor.fetchone()
        if prenda:
            talla_map = {'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch', 'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'}
            col = talla_map.get(prenda['talla'].upper().strip())
            if col:
                p_id = prenda['panel_stock_id']
                if not p_id:
                    cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s LIMIT 1", (prenda['modelo'], prenda['estampado'], prenda['color']))
                    res_p = cursor.fetchone()
                    if res_p: p_id = res_p['id']
                if p_id:
                    cursor.execute("SHOW COLUMNS FROM panel_stock LIKE %s", (col,))
                    if not cursor.fetchone() and col == 'talla_ex_g': col = 'talla_eg'
                    
                    cursor.execute(f"SELECT {col} FROM panel_stock WHERE id = %s", (p_id,))
                    res_stock = cursor.fetchone()
                    if res_stock:
                        if safe_int(res_stock[col]) <= 0: return jsonify({'status': 'error', 'msg': f"{prenda['modelo']} ({prenda['talla']}) ya está en 0."})
                        cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (p_id,))
                        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        precio_p = float(prenda['precio'])
                        cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'WEB ALMACEN REGISTRO', %s)", 
                                       (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, current_user.nombre_real))
                        db.commit()
                        return jsonify({'status': 'ok', 'msg': f"{prenda['modelo']} - {prenda['estampado']} ({prenda['talla']})"})
                    else: return jsonify({'status': 'error', 'msg': 'Borrada del Catálogo Maestro.'})
        return jsonify({'status': 'error', 'msg': 'Código de barras no válido o desconectado.'})
    except Exception as e:
        if db: db.rollback()
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/inventario/descontar', methods=['POST'])
def api_descontar():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'Acceso no autorizado a la API'}), 401
    data = request.get_json(); codigo = data.get('codigo_barras', '').strip(); realizado_por = data.get('realizado_por', 'App Nativa Flutter').strip()
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT modelo, estampado, color, talla, precio, panel_stock_id FROM inventario WHERE codigo_barras = %s", (codigo,))
        prenda = cursor.fetchone()
        if prenda:
            talla_map = {'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch', 'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'}
            col = talla_map.get(prenda['talla'].upper().strip())
            if col:
                p_id = prenda['panel_stock_id']
                if not p_id:
                    cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s LIMIT 1", (prenda['modelo'], prenda['estampado'], prenda['color']))
                    res_p = cursor.fetchone()
                    if res_p: p_id = res_p['id']
                if p_id:
                    cursor.execute("SHOW COLUMNS FROM panel_stock LIKE %s", (col,))
                    if not cursor.fetchone() and col == 'talla_ex_g': col = 'talla_eg'
                    
                    cursor.execute(f"SELECT {col} FROM panel_stock WHERE id = %s", (p_id,))
                    res_stock = cursor.fetchone()
                    if res_stock and safe_int(res_stock[col]) > 0:
                        cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (p_id,))
                        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        precio_p = float(prenda['precio'])
                        cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'BAJA APP MOVIL', %s)", 
                                       (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, realizado_por))
                        db.commit()
                        return jsonify({'status': 'ok', 'msg': f"{prenda['modelo']} {prenda['estampado']} {prenda['color']} {prenda['talla']}"})
        return jsonify({'error': 'CÓDIGO INVÁLIDO O SIN STOCK'}), 400
    except Exception as e:
        if db: db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/pos/enviar', methods=['POST'])
def api_pos_enviar():
    es_web = current_user.is_authenticated
    es_app = False
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("Bearer gacrux-auth-"): es_app = True
    
    if not es_web and not es_app: return jsonify({'error': 'No autorizado'}), 401
    
    codigo = request.get_json().get('codigo', '').strip()
    if not codigo: return jsonify({'error': 'Sin código'}), 400
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor()
        cursor.execute("INSERT INTO cola_escaneos (codigo_barras, procesado) VALUES (%s, 0)", (codigo,))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e: 
        if db: db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/inventario', methods=['GET'])
def api_app_inventario():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'Acceso no autorizado'}), 401
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
        resultados = cursor.fetchall()
        return jsonify(resultados)
    except Exception as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/subir_lote', methods=['POST'])
def api_subir_lote():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(); modelo = data.get('modelo', '').strip().upper(); estampado = data.get('estampado', '').strip().upper()
    color = data.get('color', '').strip().upper(); precio = float(data.get('precio', 250.0))
    tallas = data.get('tallas', {}); realizado_por = data.get('realizado_por', 'App Móvil').strip()
    genero = data.get('genero', 'TODO').strip().upper(); estilo = data.get('estilo', 'NORMAL').strip().upper(); tipo_prenda = data.get('tipo_prenda', 'SUDADERA').strip().upper()
    
    if not modelo or not estampado or not color: return jsonify({'error': 'Faltan datos'}), 400
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo, estampado, color))
        res = cursor.fetchone()
        
        ch = safe_int(tallas.get('CH', 0)); m = safe_int(tallas.get('M', 0)); g = safe_int(tallas.get('G', 0))
        talla_extra_nombre = tallas.get('EXTRA_NAME', 'EG').upper(); talla_extra_cant = safe_int(tallas.get('EXTRA_CANT', 0))
        
        if res:
            cursor.execute("""
                UPDATE panel_stock 
                SET talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s, genero=%s, estilo=%s, tipo_prenda=%s
                WHERE id=%s
            """, (ch, m, g, talla_extra_cant, genero, estilo, tipo_prenda, res['id']))
            panel_id = res['id']
        else:
            cursor.execute("""
                INSERT INTO panel_stock (modelo, estampado, color, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (modelo, estampado, color, ch, m, g, talla_extra_cant, genero, estilo, tipo_prenda))
            panel_id = cursor.lastrowid
            
        tallas_ingresadas = []
        if ch > 0: tallas_ingresadas.append(('CH', ch))
        if m > 0: tallas_ingresadas.append(('M', m))
        if g > 0: tallas_ingresadas.append(('G', g))
        if talla_extra_cant > 0: tallas_ingresadas.append((talla_extra_nombre, talla_extra_cant))
        
        codigos_generados = []; total_ingresado = 0
        for talla_str, cantidad in tallas_ingresadas:
            cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo, estampado, color, talla_str))
            ex = cursor.fetchone()
            if ex:
                codigo_final = ex['codigo_barras']
                cursor.execute("UPDATE inventario SET genero=%s, estilo=%s, tipo_prenda=%s WHERE codigo_barras=%s", (genero, estilo, tipo_prenda, codigo_final))
            else:
                codigo_final = generar_codigo_13_nube(cursor, modelo, estampado, color, talla_str)
                cursor.execute("INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                               (codigo_final, modelo, estampado, color, talla_str, precio, panel_id, genero, estilo, tipo_prenda))
            codigos_generados.append({"talla": talla_str, "codigo": codigo_final, "cantidad": cantidad})
            total_ingresado += cantidad
            
        if total_ingresado > 0:
            fecha_a = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE', %s)", 
                           (modelo, total_ingresado, fecha_a, realizado_por))
        db.commit()
        return jsonify({'status': 'ok', 'codigos': codigos_generados, 'total': total_ingresado})
    except Exception as e: 
        if db: db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/actualizar_filtros', methods=['POST'])
def api_actualizar_filtros():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(); modelo = data.get('modelo', '').strip().upper(); genero = data.get('genero', '').strip().upper()
    estilo = data.get('estilo', '').strip().upper(); tipo_prenda = data.get('tipo_prenda', '').strip().upper()
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor()
        cursor.execute("UPDATE panel_stock SET genero=%s, estilo=%s, tipo_prenda=%s WHERE modelo=%s", (genero, estilo, tipo_prenda, modelo))
        cursor.execute("UPDATE inventario SET genero=%s, estilo=%s, tipo_prenda=%s WHERE modelo=%s", (genero, estilo, tipo_prenda, modelo))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e: 
        if db: db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/api/app/mapa_codigos', methods=['GET'])
def api_mapa_codigos():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.codigo_barras, i.talla, COALESCE(p.talla_t12, 0) as talla_t12, COALESCE(p.talla_t16, 0) as talla_t16, COALESCE(p.talla_ex_ch, 0) as talla_ex_ch, 
                   COALESCE(p.talla_ch, 0) as talla_ch, COALESCE(p.talla_m, 0) as talla_m, COALESCE(p.talla_g, 0) as talla_g, COALESCE(p.talla_ex_g, 0) as talla_ex_g, COALESCE(p.talla_eg, 0) as talla_eg
            FROM inventario i
            LEFT JOIN panel_stock p ON (i.panel_stock_id = p.id) OR (i.panel_stock_id IS NULL AND i.modelo = p.modelo AND i.estampado = p.estampado AND i.color = p.color)
        """)
        res = cursor.fetchall()
        mapa = {}
        t_map = {'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch', 'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'}
        for r in res:
            columna = t_map.get(str(r['talla']).upper(), 'talla_ex_g')
            if columna in r: mapa[r['codigo_barras']] = r[columna]
            else: mapa[r['codigo_barras']] = r.get('talla_eg', 0)
        return jsonify(mapa)
    except Exception as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if db: db.close()

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/api/migrar_bd')
def api_migrar_bd():
    db = None; cursor = None
    try:
        db = conectar_bd(); cursor = db.cursor()
        mensajes = []
        cursor.execute("SHOW COLUMNS FROM panel_stock LIKE 'genero'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE panel_stock ADD COLUMN genero VARCHAR(50) DEFAULT 'TODO'")
            cursor.execute("ALTER TABLE panel_stock ADD COLUMN estilo VARCHAR(50) DEFAULT 'NORMAL'")
            cursor.execute("ALTER TABLE panel_stock ADD COLUMN tipo_prenda VARCHAR(50) DEFAULT 'SUDADERA'")
            mensajes.append("✅ Filtros añadidos a panel_stock.")
        cursor.execute("SHOW COLUMNS FROM inventario LIKE 'genero'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE inventario ADD COLUMN genero VARCHAR(50) DEFAULT 'TODO'")
            cursor.execute("ALTER TABLE inventario ADD COLUMN estilo VARCHAR(50) DEFAULT 'NORMAL'")
            cursor.execute("ALTER TABLE inventario ADD COLUMN tipo_prenda VARCHAR(50) DEFAULT 'SUDADERA'")
            mensajes.append("✅ Filtros añadidos a inventario.")
        cursor.execute("CREATE TABLE IF NOT EXISTS modelos_base (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) UNIQUE, genero VARCHAR(50), estilo VARCHAR(50), tipo_prenda VARCHAR(50))")
        cursor.execute("CREATE TABLE IF NOT EXISTS colores_base (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS recetas_madre (modelo VARCHAR(100) PRIMARY KEY, folio INT DEFAULT 1, colores TEXT, cuerpos TEXT, cuerpos_ids TEXT)")
        mensajes.append("✅ Tablas de Autocompletado Creadas.")
        db.commit()
        return f"<h1>Migración Gacrux Completada</h1><p>{'<br>'.join(mensajes)}</p>"
    except Exception as e: 
        if db: db.rollback()
        return f"<h1>Error Crítico</h1><p>{str(e)}</p>"
    finally:
        if cursor: cursor.close()
        if db: db.close()

# ==============================================================================
# 🔥 MOTOR DE HOJA MADRE MÓVIL BLINDADO Y OPTIMIZADO 🔥
# ==============================================================================
@app.route('/api/app/magia_madre', methods=['POST'])
def api_magia_madre():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
        
        req = request.get_json()
        step = req.get('step', 'all')
        modelo = req.get('modelo', '').strip().upper()
        
        # 🔥 RESTRICCIÓN DE IMAGEN OBLIGATORIA DESDE EL INICIO 🔥
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
        row_img = cursor.fetchone()
        if not row_img or not row_img.get('imagen_dibujo'):
            cursor.close(); db.close()
            return jsonify({'error': f'⛔ IMAGEN OBLIGATORIA: Por favor, sube el dibujo del modelo {modelo} en la sección de Reglas de Producción antes de generar.'}), 400
        
        imagen_blob = row_img['imagen_dibujo']
        formato_img = row_img.get('formato_img', '1500x1900 (Frente)')

        cursor.execute("SELECT cuerpos_ids FROM recetas_madre WHERE modelo = %s", (modelo,))
        row_ids = cursor.fetchone()
        ids_guardados = json.loads(row_ids['cuerpos_ids']) if row_ids and row_ids.get('cuerpos_ids') else []
        cuerpos_del_modelo = []
        if ids_guardados:
            placeholders = ','.join(['%s']*len(ids_guardados))
            cursor.execute(f"SELECT id, nombre, tipo_multiplicador FROM cuerpos_base WHERE id IN ({placeholders})", tuple(ids_guardados))
            res_cuerpos = cursor.fetchall()
            for id_g in ids_guardados:
                for row in res_cuerpos:
                    if row['id'] == id_g: cuerpos_del_modelo.append(row); break
        if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]
        cursor.close(); db.close()

        raw_estampados = req.get('estampados', [])
        estampados_por_folio = int(req.get('estampados_por_folio', 4))
        colores = req.get('colores', [])
        cuerpos_actuales = req.get('cuerpos_actuales', {})
        tallas_usadas = req.get('tallas_usadas', [])
        datos_lienzo_color = req.get('datos_lienzo_color', {})
        folios_a_usar = req.get('folios_a_usar', [])
        fecha_txt = datetime.datetime.now().strftime("%d/%m/%y")
        str_folios = ", ".join([str(f).zfill(2) for f in folios_a_usar])

        datos_inventario_global = []; datos_corte = []

        for c in colores:
            lienzos = safe_int(datos_lienzo_color.get(c, 0))
            fila = {"color": c, "lienzos": lienzos, "totales_talla": {t: 0 for t in tallas_usadas}, "gran_total": 0}
            for t in tallas_usadas: 
                prendas = lienzos * safe_int(cuerpos_actuales.get(t, 0))
                fila["totales_talla"][t] = prendas; fila["gran_total"] += prendas
            datos_corte.append(fila)
        datos_corte.sort(key=lambda x: x["gran_total"], reverse=True)
        num_folios = len(folios_a_usar)
        
        est_por_folio_raw = [raw_estampados[i:i + estampados_por_folio] for i in range(0, len(raw_estampados), estampados_por_folio)]
        est_por_folio = []; estampados = []
        for chunk in est_por_folio_raw:
            clean_chunk = [e for e in chunk if e.strip()]
            if not clean_chunk: clean_chunk = ["SIN ESTAMPADO"]
            est_por_folio.append(clean_chunk); estampados.extend(clean_chunk)
        if not estampados: estampados = ["SIN ESTAMPADO"]; est_por_folio = [["SIN ESTAMPADO"]]
        while len(est_por_folio) < num_folios: est_por_folio.append(["SIN ESTAMPADO"])

        total_ingresado_nube = 0; current_global_idx = 1
        mapa_bd = {"T-12": "talla_t12", "T-16": "talla_t16", "EX CH": "talla_ex_ch", "CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX G": "talla_ex_g"}

        for i_f, folio_actual in enumerate(folios_a_usar):
            estampados_del_folio = est_por_folio[i_f]; estampados_data = []
            for est_name in estampados_del_folio:
                estampados_data.append({"nombre": est_name, "filas": [], "global_idx": current_global_idx}); current_global_idx += 1
                
            modelo_folio_nube = f"{modelo} {str(folio_actual).zfill(2)}"
            for fila_corte in datos_corte:
                c = fila_corte["color"]; reparto_por_talla = {t: [] for t in tallas_usadas}
                for t in tallas_usadas:
                    total_corte = fila_corte["totales_talla"][t]; total_folio = total_corte // num_folios
                    num_est_folio = len(estampados_data)
                    if num_est_folio > 0:
                        base = total_folio // num_est_folio; sobra = total_folio % num_est_folio
                        for i_e in range(num_est_folio):
                            asignado = base + 1 if i_e < sobra else base
                            reparto_por_talla[t].append(asignado)
                for i_e, est_dict in enumerate(estampados_data):
                    fila_inv = {"color": c, "tallas": {}}
                    for t in tallas_usadas: fila_inv["tallas"][t] = reparto_por_talla[t][i_e]
                    est_dict["filas"].append(fila_inv)

            datos_inventario_global.append({"folio": str(folio_actual).zfill(2), "estampados": estampados_data})
            
            # 🔥 PASO 1: BASE DE DATOS 🔥
            if step in ['db', 'all']:
                db = conectar_bd(); cursor = db.cursor(dictionary=True)
                try:
                    for est_item in estampados_data:
                        est_nombre = est_item["nombre"]
                        for fila in est_item["filas"]:
                            c = fila["color"]
                            cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est_nombre, c))
                            res = cursor.fetchone()
                            v_stock = {"talla_t12": 0, "talla_t16": 0, "talla_ex_ch": 0, "talla_ch": 0, "talla_m": 0, "talla_g": 0, "talla_ex_g": 0}
                            for t in tallas_usadas:
                                cant = fila["tallas"][t]
                                if cant > 0: col_sql = mapa_bd.get(t, "talla_ex_g"); v_stock[col_sql] += cant; total_ingresado_nube += cant

                            if res:
                                cursor.execute("""UPDATE panel_stock SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s WHERE id=%s""", 
                                               (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                                panel_id = res['id']
                            else:
                                cursor.execute("""INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')""", 
                                               (modelo_folio_nube, est_nombre, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
                                panel_id = cursor.lastrowid

                            for t in tallas_usadas:
                                if fila["tallas"][t] > 0:
                                    cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo_folio_nube, est_nombre, c, t))
                                    if not cursor.fetchone():
                                        cod = generar_codigo_13_nube(cursor, modelo_folio_nube, est_nombre, c, t)
                                        cursor.execute("INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, 250.0, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                                       (cod, modelo_folio_nube, est_nombre, c, t, panel_id))
                    
                    if total_ingresado_nube > 0:
                        cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE', 'SISTEMA')", 
                                       (modelo, total_ingresado_nube, fecha_txt))
                    cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folios_a_usar[-1] + 1, modelo))
                    db.commit()
                except Exception as e:
                    db.rollback(); raise e
                finally:
                    cursor.close(); db.close()

        if step == 'db': return jsonify({'status': 'ok'})

        # 🔥 PASO 2: DIBUJO DEL PDF 🔥
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=80, bottomMargin=15)
        elementos = []; estilos = getSampleStyleSheet()
        estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)
        style_header_corte = ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)

        try:
            img = PILImage.open(io.BytesIO(imagen_blob))
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                alpha = img.convert('RGBA').split()[-1]
                bg = PILImage.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=alpha)
                img = bg
            elif img.mode != 'RGB': 
                img = img.convert('RGB')
            img.thumbnail((300, 300))
            temp_io = io.BytesIO()
            img.save(temp_io, format='PNG')
            temp_io_bytes = temp_io.getvalue()
            w_img = 220 if "2500" in formato_img else 130
        except Exception as e:
            return jsonify({'error': f'⛔ IMAGEN CORRUPTA: No se pudo procesar el dibujo de {modelo}. Vuelve a subirlo en Reglas de Producción.'}), 400

        # 1. DIBUJAR HOJA DE CORTE (UNA SOLA VEZ)
        try: logo = RLImage(io.BytesIO(temp_io_bytes), width=w_img, height=130, kind='proportional')
        except: logo = ""

        t_header_corte = Table([
            [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", style_header_corte), 
             Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
             Paragraph(f"<font color='red'><b>FOLIO:</b> {str_folios}</font>", ParagraphStyle(name='hr', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=12))],
            [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
        ], colWidths=[194, 194, 194], rowHeights=[None, 135], hAlign='CENTER')
        t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
        elementos.append(t_header_corte); elementos.append(Spacer(1, 10))

        # 🔥 FIX: TALLAS FIJAS SIEMPRE 🔥
        tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
        w_talla_corte = 432 / len(tallas_todas)
        
        data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS"] + [""] * (len(tallas_todas) - 1), ["", ""] + tallas_todas]
        for c_dict in cuerpos_del_modelo:
            nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
            if 'x2' in tipo_mult: txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
            elif 'A/B' in tipo_mult: txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
            else: txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""
            fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
            for t in tallas_todas: fila.append(f_calc(safe_int(cuerpos_actuales.get(t, 0))))
            data_t1.append(fila)

        t1 = Table(data_t1, colWidths=[80, 70] + [w_talla_corte] * len(tallas_todas), hAlign='CENTER')
        t1.setStyle(TableStyle([
            ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
            # 🔥 FIX: COLOR AZUL CLARO PARA PRODUCCIÓN NORMAL 🔥
            ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#e0f2fe")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ]))

        data_t2 = [["N° ROLLO\n(Marcado)", "COLOR", "N° LIENZO"] + tallas_todas + ["TOTAL"]]
        marcados = []; current_marcado = []; current_sum = 0
        for d in datos_corte:
            if current_sum + d["lienzos"] > 80 and current_sum > 0:
                marcados.append(current_marcado); current_marcado = [d]; current_sum = d["lienzos"]
            else: current_marcado.append(d); current_sum += d["lienzos"]
        if current_marcado: marcados.append(current_marcado)

        suma_lienzos = 0; suma_tallas = {t: 0 for t in tallas_todas}; gran_total = 0; row_idx = 1
        estilos_tabla2 = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9), ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ]
        for num_m, marcado_data in enumerate(marcados):
            start_row = row_idx
            for i, d in enumerate(marcado_data):
                fila = [f"Marcado\n{num_m + 1}" if i == 0 else "", Paragraph(d["color"], estilo_wrap), str(d["lienzos"])]
                suma_lienzos += d["lienzos"]
                for t in tallas_todas:
                    val = d["totales_talla"].get(t, 0); fila.append(str(val) if val > 0 else ""); suma_tallas[t] += val
                fila.append(str(d["gran_total"])); gran_total += d["gran_total"]; data_t2.append(fila); row_idx += 1
            if len(marcado_data) > 1: estilos_tabla2.append(('SPAN', (0, start_row), (0, row_idx - 1)))

        fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
        for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
        fila_final.append(str(gran_total)); data_t2.append(fila_final)
        estilos_tabla2.extend([
            ('SPAN', (0, row_idx), (1, row_idx)), ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#e2e8f0")), 
            ('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black), ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
        ])
        
        w_talla_rollo = 337 / len(tallas_todas)
        t2 = Table(data_t2, colWidths=[55, 90, 50] + [w_talla_rollo] * len(tallas_todas) + [50], hAlign='CENTER')
        t2.setStyle(TableStyle(estilos_tabla2))

        tablas_encogibles = KeepInFrame(
            maxWidth=582, maxHeight=500, 
            content=[t1, Spacer(1, 15), Paragraph("<b>FECHA:</b> _________________", estilos['Normal']), Spacer(1, 10), t2], 
            mode='shrink', vAlign='TOP', hAlign='CENTER'
        )
        elementos.append(tablas_encogibles); elementos.append(PageBreak())

# 2. DIBUJAR INVENTARIOS UNIFICADOS
        t_title = ParagraphStyle('titulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
        
        # 🔥 FIX: TODOS LOS COLORES EN UNA HOJA Y AUTO-COMPRESIÓN 🔥
        color_chunks = [colores]

        for i_f, data_folio in enumerate(datos_inventario_global):
            folio = data_folio["folio"]; estampados_data = data_folio["estampados"]

            for chunk_idx, color_chunk in enumerate(color_chunks):
                estampados_por_hoja = [estampados_data[i:i + estampados_por_folio] for i in range(0, len(estampados_data), estampados_por_folio)]
                if not estampados_por_hoja: estampados_por_hoja = [[]]
                
                for lote_idx, lote_estampados in enumerate(estampados_por_hoja):
                    t_header_inv = Table([
                        [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                         Paragraph(f"<b>FOLIO:</b> {folio}<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
                    ], colWidths=[291, 291], hAlign='CENTER')

                    tablas_estampados = []
                    for est_item in lote_estampados:
                        est_nombre = est_item["nombre"]; filas_colores = est_item["filas"]; global_idx = est_item["global_idx"]
                        title_text = f"<font color='#3b82f6'>▐</font> <b>ESTAMPADO {global_idx}: {est_nombre}</b>"
                        title = Paragraph(title_text, t_title)
                        
                        num_colors = len(color_chunk)
                        if num_colors <= 6: f_size = 8; pad = 4
                        elif num_colors <= 10: f_size = 7; pad = 3
                        elif num_colors <= 14: f_size = 6; pad = 2
                        else: f_size = 5; pad = 1
                            
                        style_color_inv_dyn = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                        w_color = 65; w_talla = 20; espacio_total_tabla = 286
                        w_vacio = max(10, (espacio_total_tabla - w_color - (w_talla * len(tallas_usadas))) / 2.0) 
                        anchos_columnas = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_usadas)
                        
                        data_t = [["COLOR", "", ""] + tallas_usadas]; totales_tallas = {t: 0 for t in tallas_usadas}

                        for c in color_chunk:
                            row_data = next((r for r in filas_colores if r["color"] == c), None)
                            if row_data:
                                r_row = [Paragraph(c, style_color_inv_dyn), "", ""]
                                for t in tallas_usadas:
                                    cant = row_data["tallas"].get(t, 0); r_row.append(str(cant) if cant > 0 else ""); totales_tallas[t] += cant
                                data_t.append(r_row)

                        f_tot = ["TOTAL", "", ""]
                        for t in tallas_usadas: f_tot.append(str(totales_tallas[t]))
                        data_t.append(f_tot)

                        t_inv = Table(data_t, colWidths=anchos_columnas, hAlign='CENTER')
                        t_inv.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                            ('SPAN', (0, -1), (2, -1)), ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,-1), f_size), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")), 
                            ('BOTTOMPADDING', (0,0), (-1,-1), pad), ('TOPPADDING', (0,0), (-1,-1), pad),
                        ]))
                        
                        wrapper_table = Table([[title], [Spacer(1, 4)], [t_inv]], colWidths=[286], hAlign='CENTER')
                        wrapper_table.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0)]))
                        tablas_estampados.append(wrapper_table)

                    while len(tablas_estampados) < 4: tablas_estampados.append("")

                    # 🔥 FIX: SEPARACIÓN DE 10 PUNTOS 🔥
                    grid_data = [
                        [tablas_estampados[0], "", tablas_estampados[1]], 
                        [Spacer(1, 15), "", Spacer(1, 15)], 
                        [tablas_estampados[2], "", tablas_estampados[3]]
                    ]
                    t_grid = Table(grid_data, colWidths=[286, 10, 286], hAlign='CENTER')
                    t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                    
                    firmas_data = [
                        [" ", "", " "], [" ", "", " "], [" ", "", " "],
                        ["___________________________________", "", "___________________________________"],
                        ["DOBLADO", "", "ALMACÉN"],
                        ["JACQUELINE TLATELPA XOLALTENCO", "", "DULCE EVELIN POTRERO RODRIGUEZ"]
                    ]
                    t_firmas = Table(firmas_data, colWidths=[286, 10, 286], hAlign='CENTER')
                    t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                    
                    wrap_t_grid = KeepInFrame(maxWidth=582, maxHeight=490, content=[t_header_inv, Spacer(1,15), t_grid], mode='shrink', vAlign='TOP', hAlign='CENTER')
                    t_master = Table([[wrap_t_grid], [t_firmas]], colWidths=[582], rowHeights=[550, 110], hAlign='CENTER') 
                    t_master.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,1), (0,1), 'BOTTOM'),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                    ]))
                    elementos.append(t_master)
                    if not (i_f == len(datos_inventario_global) - 1 and lote_idx == len(estampados_por_hoja) - 1):
                        elementos.append(PageBreak())
        
        if not elementos:
            elementos.append(Paragraph("NO SE GENERARON DATOS. REVISA LAS TALLAS.", estilos['Normal']))

        doc.build(elementos) 
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        # =================================================================
        # 🔥 3. FABRICAR EL LIBRO DE CÓDIGOS DE BARRAS EN MEMORIA 🔥
        # =================================================================
        buffer_codigos = io.BytesIO()
            # Margen izquierdo de 50 para poder engargolar/perforar como libro
            doc_codigos = SimpleDocTemplate(buffer_codigos, pagesize=letter, leftMargin=50, rightMargin=15, topMargin=40, bottomMargin=15)
            elementos_codigos = []
            
            style_bc_text = ParagraphStyle(name='bc', alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=8, leading=10)
            style_bc_title = ParagraphStyle(name='bct', alignment=TA_LEFT, fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor("#1e3a8a"))

            db_bc = conectar_bd()
            cursor_bc = db_bc.cursor(dictionary=True)
            
            try:
                for f_val in folios_a_usar:
                    mod_folio_nube = f"{modelo} {str(f_val).zfill(2)}"
                    cursor_bc.execute("SELECT codigo_barras, color, talla, estampado FROM inventario WHERE modelo = %s ORDER BY estampado, talla, color", (mod_folio_nube,))
                    cods_bd = cursor_bc.fetchall()
                    
                    if not cods_bd: continue
                    
                    estampados_unicos = list(dict.fromkeys([r['estampado'] for r in cods_bd]))
                    
                    for est in estampados_unicos:
                        elementos_codigos.append(Paragraph(f"MODELO: {modelo} &nbsp;&nbsp;&nbsp;&nbsp; ESTAMPADO: {est}", style_bc_title))
                        elementos_codigos.append(Spacer(1, 20))
                        
                        cods_est = [r for r in cods_bd if r['estampado'] == est]
                        colores_unicos = list(dict.fromkeys([r['color'] for r in cods_est]))
                        
                        # 🔥 COLUMNAS = TALLAS, FILAS = COLORES 🔥
                        cols_num = len(tallas_usadas) if tallas_usadas else 1
                        w_col = 547 / cols_num
                        
                        # Auto-ajuste del ancho de la barra para que nunca se encimen si son muchas tallas
                        bar_w = 1.2
                        if cols_num >= 7: bar_w = 0.4
                        elif cols_num == 6: bar_w = 0.5
                        elif cols_num == 5: bar_w = 0.6
                        elif cols_num == 4: bar_w = 0.8
                        elif cols_num == 3: bar_w = 1.0
                        elif cols_num == 2: bar_w = 1.3

                        filas_bc = []
                        
                        for c in colores_unicos:
                            fila = []
                            for t in tallas_usadas:
                                item = next((r for r in cods_est if r['color'] == c and r['talla'] == t), None)
                                if item:
                                    bc = code128.Code128(item['codigo_barras'], barHeight=35, barWidth=bar_w)
                                    txt = Paragraph(f"{item['codigo_barras']}<br/>Talla: <b>{t}</b><br/>Color: {item['color']}", style_bc_text)
                                    celda = Table([[bc], [Spacer(1,4)], [txt]], hAlign='CENTER')
                                    fila.append(celda)
                                else:
                                    fila.append("") # Celda vacía si este color no tiene esta talla
                            filas_bc.append(fila)
                            
                        t_bc = Table(filas_bc, colWidths=[w_col]*cols_num, hAlign='LEFT')
                        t_bc.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                            ('BOTTOMPADDING', (0,0), (-1,-1), 15)
                        ]))
                        
                        elementos_codigos.append(t_bc)
                        elementos_codigos.append(PageBreak()) 
            except Exception as e:
                print("Error Códigos Madre:", e)
            finally:
                cursor_bc.close()
                db_bc.close()
                
            if not elementos_codigos:
                elementos_codigos.append(Paragraph("Sin códigos generados.", estilos['Normal']))
                
            doc_codigos.build(elementos_codigos)
            pdf_codigos_base64 = base64.b64encode(buffer_codigos.getvalue()).decode('utf-8')
            buffer_codigos.close()

            return jsonify({
                'status': 'ok', 
                'pdf_base64': pdf_base64, 
                'filename': f"Gacrux_{modelo}_Produccion_{str_folios}.pdf",
                'pdf_codigos_base64': pdf_codigos_base64,
                'filename_codigos': f"Gacrux_{modelo}_Codigos_Produccion_{str_folios}.pdf"
            })

@app.route('/api/app/magia_pedido', methods=['POST'])
def api_magia_pedido():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
        
        req = request.get_json()
        step = req.get('step', 'all')
        modelo = req.get('modelo', '').strip().upper()
        
        # 🔥 RESTRICCIÓN DE IMAGEN OBLIGATORIA DESDE EL INICIO 🔥
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
        row_img = cursor.fetchone()
        if not row_img or not row_img.get('imagen_dibujo'):
            cursor.close(); db.close()
            return jsonify({'error': f'⛔ IMAGEN OBLIGATORIA: Por favor, sube el dibujo del modelo {modelo} en la sección de Reglas de Producción antes de generar.'}), 400
        
        imagen_blob = row_img['imagen_dibujo']
        formato_img = row_img.get('formato_img', '1500x1900 (Frente)')

        cursor.execute("SELECT cuerpos_ids FROM recetas_madre WHERE modelo = %s", (modelo,))
        row_ids = cursor.fetchone()
        ids_guardados = json.loads(row_ids['cuerpos_ids']) if row_ids and row_ids.get('cuerpos_ids') else []
        cuerpos_del_modelo = []
        if ids_guardados:
            placeholders = ','.join(['%s']*len(ids_guardados))
            cursor.execute(f"SELECT id, nombre, tipo_multiplicador FROM cuerpos_base WHERE id IN ({placeholders})", tuple(ids_guardados))
            res_cuerpos = cursor.fetchall()
            for id_g in ids_guardados:
                for row in res_cuerpos:
                    if row['id'] == id_g: cuerpos_del_modelo.append(row); break
        if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]
        cursor.close(); db.close()

        raw_estampados = req.get('estampados', [])
        estampados_por_folio = int(req.get('estampados_por_folio', 4))
        pedidos_app = req.get('pedidos', {}) 
        folio_arranque = safe_int(req.get('folio_arranque', 1))
        fecha_txt = datetime.datetime.now().strftime("%d/%m/%y")

        tallas_activas = set(); colores_activos = set()
        for c, t_data in pedidos_app.items():
            for t, cant in t_data.items():
                if safe_int(cant) > 0: tallas_activas.add(t); colores_activos.add(c)
        tallas_activas = list(tallas_activas); colores_activos = list(colores_activos)
        orden_tallas = {"T-12":1, "T-16":2, "EX CH":3, "CH":4, "M":5, "G":6, "EX G":7}
        tallas_activas.sort(key=lambda x: orden_tallas.get(x, 99))

        def total_pedido_grupo(grupo): 
            return sum(safe_int(t_data.get(t, 0)) for c, t_data in pedidos_app.items() for t in grupo)

        # 🔥 LA NUEVA IA MATEMÁTICA: CREA COMBINACIONES 100% SEGURAS (LÍMITE EXACTO DE 6 CUERPOS) 🔥
        def get_combos(n):
            combos = []
            def search(path, current_sum):
                if len(path) == n:
                    if current_sum <= 6:
                        combos.append(path)
                    return
                min_needed_for_rest = n - 1 - len(path)
                max_val = 6 - current_sum - min_needed_for_rest
                if max_val < 1:
                    return
                for i in range(1, max_val + 1):
                    search(path + [i], current_sum + i)
            search([], 0)
            return combos

        def calcular_desperdicio(grupo_tallas):
            best_waste = float('inf'); best_lienzos_total = float('inf'); best_cuerpos = {}; best_lienzos_color = {}
            
            combos = get_combos(len(grupo_tallas))
            if not combos: 
                return float('inf'), float('inf'), {}, {}
            
            for combo in combos:
                cuerpos = {grupo_tallas[i]: combo[i] for i in range(len(grupo_tallas))}
                lienzos_color = {}; waste = 0; tot_l = 0
                for c, peds in pedidos_app.items():
                    req_lienzos = max((math.ceil(safe_int(peds.get(t, 0)) / cuerpos[t]) for t in grupo_tallas if safe_int(peds.get(t, 0)) > 0), default=0)
                    lienzos_color[c] = req_lienzos; tot_l += req_lienzos
                    for t in grupo_tallas: waste += (req_lienzos * cuerpos[t]) - safe_int(peds.get(t, 0))
                
                if tot_l < best_lienzos_total or (tot_l == best_lienzos_total and waste < best_waste):
                    best_lienzos_total = tot_l; best_waste = waste; best_cuerpos = cuerpos; best_lienzos_color = lienzos_color
            return best_waste, best_lienzos_total, best_cuerpos, best_lienzos_color

        # 🔥 LA NUEVA IA: DECIDE CÓMO PARTIR LAS TALLAS EN HOJAS DE CORTE 🔥
        def particionar_tallas(grupo):
            n = len(grupo)
            if n <= 3:
                # 1 a 3 tallas: Obliga a buscar la mejor combinación en 1 sola hoja.
                w, tl, c, l = calcular_desperdicio(grupo)
                return [(grupo, c, l)]
            elif n == 4:
                # 4 tallas: Intenta en 1 hoja. Si el desperdicio supera el 50%, parte en 2 y 2.
                w1, tl1, c1, l1 = calcular_desperdicio(grupo)
                tot_ped = total_pedido_grupo(grupo)
                if tot_ped > 0 and w1 <= (tot_ped * 0.50):
                    return [(grupo, c1, l1)]
                else:
                    return particionar_tallas(grupo[:2]) + particionar_tallas(grupo[2:])
            elif n == 5:
                # 5 tallas: Siempre fuerza la división en 3 y 2.
                return particionar_tallas(grupo[:3]) + particionar_tallas(grupo[3:])
            else:
                # 6+ tallas: Parte a la mitad (ej. 3 y 3)
                mid = n // 2
                return particionar_tallas(grupo[:mid]) + particionar_tallas(grupo[mid:])

        particiones = particionar_tallas(tallas_activas)

        est_por_folio_raw = [raw_estampados[i:i + estampados_por_folio] for i in range(0, len(raw_estampados), estampados_por_folio)]
        est_por_folio = []; estampados = []
        for chunk in est_por_folio_raw:
            clean_chunk = [e for e in chunk if e.strip()]
            if clean_chunk: est_por_folio.append(clean_chunk); estampados.extend(clean_chunk)
        if not estampados: estampados = ["SIN ESTAMPADO"]; est_por_folio = [["SIN ESTAMPADO"]]

        # 🔥 FIX: SACAR ESTA VARIABLE AFUERA PARA QUE EL PASO 2 (PDF) LA PUEDA LEER 🔥
        num_est = len(estampados)

        # 🔥 PASO 1: BASE DE DATOS 🔥
        if step in ['db', 'all']:
            db = conectar_bd(); cursor = db.cursor(dictionary=True)
            try:
                total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
                for particion in particiones:
                    grupo_tallas, cuerpos_dict, lienzos = particion
                    for c, l_cant in lienzos.items():
                        for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos_dict.get(t, 0)

                total_ingresado_nube = 0
                mapa_bd = {"CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX CH": "talla_ex_ch", "XG": "talla_ex_g", "EX G": "talla_ex_g", "T-12": "talla_t12", "T-16": "talla_t16"}

                for i_e, est in enumerate(estampados):
                    for c in colores_activos:
                        for t in tallas_activas:
                            prod = total_prod[c][t]; ped = safe_int(pedidos_app.get(c, {}).get(t, 0))
                            base_prod = prod // num_est; sobra_prod = prod % num_est
                            prod_est = base_prod + 1 if i_e < sobra_prod else base_prod
                            base_ped = ped // num_est; sobra_ped = ped % num_est
                            ped_est = base_ped + 1 if i_e < sobra_ped else base_ped
                            sob_est = max(0, prod_est - ped_est)
                            
                            # SOLAMENTE LOS SOBRANTES SE VAN A LA NUBE:
                            if sob_est > 0:
                                modelo_folio_nube = f"{modelo} {str(folio_arranque).zfill(2)}" 
                                col_sql = mapa_bd.get(t, "talla_ex_g")
                                cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est, c))
                                res = cursor.fetchone()
                                v_stock = {"talla_t12":0, "talla_t16":0, "talla_ex_ch":0, "talla_ch":0, "talla_m":0, "talla_g":0, "talla_ex_g":0}
                                v_stock[col_sql] = sob_est
                                
                                if res:
                                    cursor.execute("""UPDATE panel_stock SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s WHERE id=%s""", 
                                                   (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                                    panel_id = res['id']
                                else:
                                    cursor.execute("""INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')""", 
                                                   (modelo_folio_nube, est, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
                                    panel_id = cursor.lastrowid

                                cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo_folio_nube, est, c, t))
                                if not cursor.fetchone():
                                    cod = generar_codigo_13_nube(cursor, modelo_folio_nube, est, c, t)
                                    cursor.execute("INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, 250.0, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                                   (cod, modelo_folio_nube, est, c, t, panel_id))
                                total_ingresado_nube += sob_est

                if total_ingresado_nube > 0:
                    cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE (SOBRANTES)', 'SISTEMA')", 
                                   (modelo, total_ingresado_nube, fecha_txt))
                                   
                cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folio_arranque + 1, modelo))
                db.commit()
            except Exception as e:
                db.rollback(); raise e
            finally:
                cursor.close(); db.close()

            if step == 'db': return jsonify({'status': 'ok'})

        # 🔥 PASO 2: DIBUJAR PDF 🔥
        if step in ['pdf', 'all']:
            total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
            for particion in particiones:
                grupo_tallas, cuerpos_dict, lienzos = particion
                for c, l_cant in lienzos.items():
                    for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos_dict.get(t, 0)

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=80, bottomMargin=15)
            elementos = []; estilos = getSampleStyleSheet()
            estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)
            style_header_corte = ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)

            try:
                img = PILImage.open(io.BytesIO(imagen_blob))
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    alpha = img.convert('RGBA').split()[-1]
                    bg = PILImage.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=alpha)
                    img = bg
                elif img.mode != 'RGB': 
                    img = img.convert('RGB')
                img.thumbnail((300, 300))
                temp_io = io.BytesIO()
                img.save(temp_io, format='PNG')
                temp_io_bytes = temp_io.getvalue()
                w_img = 220 if "2500" in formato_img else 130
            except Exception as e:
                return jsonify({'error': f'⛔ IMAGEN CORRUPTA: No se pudo procesar el dibujo de {modelo}. Vuelve a subirlo en Reglas de Producción.'}), 400

            # 1. DIBUJAR HOJAS DE CORTE (SEPARADAS POR PARTICIÓN SI LA IA LO DECIDIÓ)
            try: logo = RLImage(io.BytesIO(temp_io_bytes), width=w_img, height=130, kind='proportional')
            except: logo = ""

            tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
            w_talla_corte = 432 / len(tallas_todas)
            w_talla_rollo = 337 / len(tallas_todas)

            # Iteramos sobre cada partición para crear una hoja separada si la IA decidió dividir
            for idx_part, particion in enumerate(particiones):
                grupo_tallas, cuerpos, lienzos = particion
                
                # Indicador de parte si se dividió en varias hojas (Ej: PARTE 1, PARTE 2)
                str_parte = f" (PARTE {idx_part + 1})" if len(particiones) > 1 else ""

                t_header_corte = Table([
                    [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", style_header_corte), 
                     Paragraph(f"<b>HOJA DE ORDEN DEL ÁREA DE CORTE{str_parte}</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
                     Paragraph(f"<font color='red'><b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)</font>", ParagraphStyle(name='hr', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=12))],
                    [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
                ], colWidths=[194, 194, 194], rowHeights=[None, 135], hAlign='CENTER')
                t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
                
                elementos.append(t_header_corte); elementos.append(Spacer(1, 10))
                
                data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS"] + [""] * (len(tallas_todas) - 1), ["", ""] + tallas_todas]
                
                for c_dict in cuerpos_del_modelo:
                    nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
                    if 'x2' in tipo_mult: txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
                    elif 'A/B' in tipo_mult: txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
                    else: txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""

                    fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
                    # Solo imprimimos los cuerpos si la talla pertenece a ESTA partición
                    for t in tallas_todas: fila.append(f_calc(safe_int(cuerpos.get(t, 0))))
                    data_t1.append(fila)

                t1 = Table(data_t1, colWidths=[80, 70] + [w_talla_corte] * len(tallas_todas), hAlign='CENTER')
                t1.setStyle(TableStyle([
                    ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
                    ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#fef3c7")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ]))

                data_t2 = [["N° ROLLO\n(Marcado)", "COLOR", "N° LIENZO"] + tallas_todas + ["TOTAL"]]
                marcados = []; current_marcado = []; current_sum = 0
                
                # Solo procesamos los colores que tienen lienzos en ESTA partición
                for c in colores_activos:
                    l_cant = lienzos.get(c, 0)
                    if l_cant > 0:
                        totales_t = {t: l_cant * cuerpos.get(t, 0) for t in tallas_todas}
                        g_tot = sum(totales_t.values())
                        d = {"color": c, "lienzos": l_cant, "totales_talla": totales_t, "gran_total": g_tot}
                        if current_sum + l_cant > 80 and current_sum > 0:
                            marcados.append(current_marcado); current_marcado = [d]; current_sum = l_cant
                        else:
                            current_marcado.append(d); current_sum += l_cant
                if current_marcado: marcados.append(current_marcado)

                # 🔥 AUTO-COMPRESIÓN: Si meten más de 10 colores, la letra se hace chiquita para caber 🔥
                total_filas_color = sum(len(m) for m in marcados)
                if total_filas_color > 10:
                    estilo_color = ParagraphStyle(name='Compreso', alignment=TA_CENTER, fontName='Helvetica', fontSize=7, leading=8)
                    t2_font_size = 7
                else:
                    estilo_color = estilo_wrap
                    t2_font_size = 9

                suma_lienzos = 0; suma_tallas = {t: 0 for t in tallas_todas}; gran_total = 0; row_idx = 1
                estilos_tabla2 = [
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), t2_font_size), ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ]
                for num_m, marcado_data in enumerate(marcados):
                    start_row = row_idx
                    for i, d in enumerate(marcado_data):
                        fila = [f"Marcado\n{num_m + 1}" if i == 0 else "", Paragraph(d["color"], estilo_color), str(d["lienzos"])]
                        suma_lienzos += d["lienzos"]
                        for t in tallas_todas:
                            val = d["totales_talla"].get(t, 0); fila.append(str(val) if val > 0 else ""); suma_tallas[t] += val
                        fila.append(str(d["gran_total"])); gran_total += d["gran_total"]; data_t2.append(fila); row_idx += 1
                    if len(marcado_data) > 1: estilos_tabla2.append(('SPAN', (0, start_row), (0, row_idx - 1)))

                fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
                for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
                fila_final.append(str(gran_total)); data_t2.append(fila_final)
                estilos_tabla2.extend([
                    ('SPAN', (0, row_idx), (1, row_idx)), ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#e2e8f0")), 
                    ('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black), ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
                ])
                
                t2 = Table(data_t2, colWidths=[55, 90, 50] + [w_talla_rollo] * len(tallas_todas) + [50], hAlign='CENTER')
                t2.setStyle(TableStyle(estilos_tabla2))

                tablas_encogibles = KeepInFrame(
                    maxWidth=582, maxHeight=500, 
                    content=[t1, Spacer(1, 15), Paragraph("<b>FECHA:</b> _________________", estilos['Normal']), Spacer(1, 10), t2], 
                    mode='shrink', vAlign='TOP', hAlign='CENTER'
                )
                elementos.append(tablas_encogibles); elementos.append(PageBreak())

            # 2. DIBUJAR INVENTARIOS UNIFICADOS
            t_title = ParagraphStyle('titulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
            
            # 🔥 FIX: TODOS LOS COLORES EN UNA HOJA Y AUTO-COMPRESIÓN 🔥
            color_chunks = [colores_activos]

            for lote_idx, lote_estampados in enumerate(est_por_folio):
                for chunk_idx, color_chunk in enumerate(color_chunks):
                    
                    t_header_inv = Table([
                        [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                         Paragraph(f"<b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
                    ], colWidths=[291, 291], hAlign='CENTER')

                    tablas_estampados = []
                    for i_e, est_item in enumerate(lote_estampados):
                        original_idx = lote_idx * estampados_por_folio + i_e
                        title_text = f"<font color='#d97706'>▐</font> <b>ESTAMPADO {original_idx + 1}: {est_item}</b>"
                        title = Paragraph(title_text, t_title)
                        
                        num_colors = len(color_chunk)
                        if num_colors <= 6: f_size = 8; pad = 4
                        elif num_colors <= 10: f_size = 7; pad = 3
                        elif num_colors <= 14: f_size = 6; pad = 2
                        else: f_size = 5; pad = 1
                            
                        style_color_inv_dyn = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                        w_color = 65; w_talla = 20; espacio_total_tabla = 286 
                        w_vacio = max(10, (espacio_total_tabla - w_color - (w_talla * len(tallas_activas))) / 2.0) 
                        anchos_columnas = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_activas)
                        
                        data_tot = [["COLOR", "", ""] + tallas_activas]; sum_tot = {t: 0 for t in tallas_activas}
                        data_ped = [["COLOR", "", ""] + tallas_activas]; sum_ped = {t: 0 for t in tallas_activas}
                        data_sob = [["COLOR", "", ""] + tallas_activas]; sum_sob = {t: 0 for t in tallas_activas}

                        for c in color_chunk:
                            r_tot = [Paragraph(c, style_color_inv_dyn), "", ""]
                            r_ped = [Paragraph(c, style_color_inv_dyn), "", ""]
                            r_sob = [Paragraph(c, style_color_inv_dyn), "", ""]
                            
                            for t in tallas_activas:
                                prod = total_prod[c][t]
                                ped = safe_int(pedidos_app.get(c, {}).get(t, 0))
                                
                                base_prod = prod // num_est; sobra_prod = prod % num_est
                                prod_est = base_prod + 1 if original_idx < sobra_prod else base_prod
                                
                                base_ped = ped // num_est; sobra_ped = ped % num_est
                                ped_est = base_ped + 1 if original_idx < sobra_ped else base_ped
                                
                                sob_est = max(0, prod_est - ped_est)
                                
                                r_tot.append(str(prod_est) if prod_est>0 else "-")
                                r_ped.append(str(ped_est) if ped_est>0 else "-")
                                r_sob.append(str(sob_est) if sob_est>0 else "-")
                                
                                sum_tot[t] += prod_est; sum_ped[t] += ped_est; sum_sob[t] += sob_est

                            data_tot.append(r_tot); data_ped.append(r_ped); data_sob.append(r_sob)
                        
                        data_tot.append(["SUMA", "", ""] + [str(sum_tot[t]) for t in tallas_activas])
                        data_ped.append(["SUMA", "", ""] + [str(sum_ped[t]) for t in tallas_activas])
                        data_sob.append(["SUMA", "", ""] + [str(sum_sob[t]) for t in tallas_activas])

                        style_tabla_3 = TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                            ('SPAN', (0, -1), (2, -1)), ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,-1), f_size), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")), 
                            ('BOTTOMPADDING', (0,0), (-1,-1), pad), ('TOPPADDING', (0,0), (-1,-1), pad),
                        ])
                        
                        t_tot = Table(data_tot, colWidths=anchos_columnas, hAlign='CENTER'); t_tot.setStyle(style_tabla_3)
                        t_ped = Table(data_ped, colWidths=anchos_columnas, hAlign='CENTER'); t_ped.setStyle(style_tabla_3)
                        t_sob = Table(data_sob, colWidths=anchos_columnas, hAlign='CENTER'); t_sob.setStyle(style_tabla_3)

                        wrap_tot = Table([[Paragraph("<font color='#3b82f6'>1. TOTAL PRODUCIDO</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_tot]], hAlign='CENTER')
                        wrap_ped = Table([[Paragraph("<font color='#16a34a'>2. PEDIDO CLIENTE</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_ped]], hAlign='CENTER')
                        wrap_sob = Table([[Paragraph("<font color='#e63946'>3. A NUBE (SOBRANTE)</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_sob]], hAlign='CENTER')

                        tablas_estampados.append(Table(
                            [[wrap_tot, "", wrap_ped], 
                             [Spacer(1, 15), "", Spacer(1, 15)], 
                             [wrap_sob, "", ""]], 
                            colWidths=[286, 10, 286], 
                            style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)], 
                            hAlign='CENTER'
                        ))
                        tablas_estampados.append(title)

                    elementos_hoja = [t_header_inv, Spacer(1, 15)]
                    for i in range(0, len(tablas_estampados), 2):
                        tabla_est = tablas_estampados[i]
                        titulo_est = tablas_estampados[i+1]
                        elementos_hoja.append(titulo_est)
                        elementos_hoja.append(Spacer(1, 8))
                        elementos_hoja.append(tabla_est)
                        elementos_hoja.append(Spacer(1, 15))

                    firmas_data = [
                        [" ", "", " "], [" ", "", " "], [" ", "", " "],
                        ["___________________________________", "", "___________________________________"],
                        ["DOBLADO", "", "ALMACÉN"],
                        ["JACQUELINE TLATELPA XOLALTENCO", "", "DULCE EVELIN POTRERO RODRIGUEZ"]
                    ]
                    t_firmas = Table(firmas_data, colWidths=[286, 10, 286], hAlign='CENTER')
                    t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                    
                    wrap_elementos = KeepInFrame(maxWidth=582, maxHeight=490, content=elementos_hoja, mode='shrink', vAlign='TOP', hAlign='CENTER')
                    t_master = Table([[wrap_elementos], [t_firmas]], colWidths=[582], rowHeights=[550, 110], hAlign='CENTER') 
                    t_master.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,1), (0,1), 'BOTTOM'),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                    ]))
                    elementos.append(t_master)
                    if not (lote_idx == len(est_por_folio) - 1 and chunk_idx == len(color_chunks) - 1):
                        elementos.append(PageBreak())
        
                    if not elementos:
                        elementos.append(Paragraph("NO SE GENERARON DATOS. REVISA LAS TALLAS.", estilos['Normal']))

                    doc.build(elementos) 
                    pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    buffer.close()

            # =================================================================
            # 🔥 3. FABRICAR EL LIBRO DE CÓDIGOS DE BARRAS EN MEMORIA 🔥
            # =================================================================
            buffer_codigos = io.BytesIO()
            doc_codigos = SimpleDocTemplate(buffer_codigos, pagesize=letter, leftMargin=50, rightMargin=15, topMargin=40, bottomMargin=15)
            elementos_codigos = []
            
            style_bc_text = ParagraphStyle(name='bc', alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=8, leading=10)
            style_bc_title = ParagraphStyle(name='bct', alignment=TA_LEFT, fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor("#1e3a8a"))

            db_bc = conectar_bd()
            cursor_bc = db_bc.cursor(dictionary=True)
            
            try:
                for f_val in [folio_arranque]:
                    mod_folio_nube = f"{modelo} {str(f_val).zfill(2)}"
                    cursor_bc.execute("SELECT codigo_barras, color, talla, estampado FROM inventario WHERE modelo = %s ORDER BY estampado, talla, color", (mod_folio_nube,))
                    cods_bd = cursor_bc.fetchall()
                    
                    if not cods_bd: continue
                    
                    estampados_unicos = list(dict.fromkeys([r['estampado'] for r in cods_bd]))
                    
                    for est in estampados_unicos:
                        elementos_codigos.append(Paragraph(f"MODELO: {modelo} &nbsp;&nbsp;&nbsp;&nbsp; ESTAMPADO: {est}", style_bc_title))
                        elementos_codigos.append(Spacer(1, 20))
                        
                        cods_est = [r for r in cods_bd if r['estampado'] == est]
                        colores_unicos = list(dict.fromkeys([r['color'] for r in cods_est]))
                        
                        # 🔥 COLUMNAS = TALLAS, FILAS = COLORES 🔥
                        cols_num = len(tallas_activas) if tallas_activas else 1
                        w_col = 547 / cols_num
                        
                        # Auto-ajuste del ancho de la barra
                        bar_w = 1.2
                        if cols_num >= 7: bar_w = 0.4
                        elif cols_num == 6: bar_w = 0.5
                        elif cols_num == 5: bar_w = 0.6
                        elif cols_num == 4: bar_w = 0.8
                        elif cols_num == 3: bar_w = 1.0
                        elif cols_num == 2: bar_w = 1.3

                        filas_bc = []
                        
                        for c in colores_unicos:
                            fila = []
                            for t in tallas_activas:
                                item = next((r for r in cods_est if r['color'] == c and r['talla'] == t), None)
                                if item:
                                    bc = code128.Code128(item['codigo_barras'], barHeight=35, barWidth=bar_w)
                                    txt = Paragraph(f"{item['codigo_barras']}<br/>Talla: <b>{t}</b><br/>Color: {item['color']}", style_bc_text)
                                    celda = Table([[bc], [Spacer(1,4)], [txt]], hAlign='CENTER')
                                    fila.append(celda)
                                else:
                                    fila.append("") # Celda vacía si no pidieron esa talla en ese color
                            filas_bc.append(fila)
                            
                        t_bc = Table(filas_bc, colWidths=[w_col]*cols_num, hAlign='LEFT')
                        t_bc.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                            ('BOTTOMPADDING', (0,0), (-1,-1), 15)
                        ]))
                        
                        elementos_codigos.append(t_bc)
                        elementos_codigos.append(PageBreak()) 
            except Exception as e:
                print("Error Códigos Pedido:", e)
            finally:
                cursor_bc.close()
                db_bc.close()
                
            if not elementos_codigos:
                elementos_codigos.append(Paragraph("Sin códigos.", estilos['Normal']))
                
            doc_codigos.build(elementos_codigos)
            pdf_codigos_base64 = base64.b64encode(buffer_codigos.getvalue()).decode('utf-8')
            buffer_codigos.close()

            return jsonify({
                'status': 'ok', 
                'pdf_base64': pdf_base64, 
                'filename': f"Gacrux_{modelo}_Pedido_{str(folio_arranque).zfill(2)}.pdf",
                'pdf_codigos_base64': pdf_codigos_base64,
                'filename_codigos': f"Gacrux_{modelo}_Codigos_Pedido_{str(folio_arranque).zfill(2)}.pdf",
                'siguiente_folio': folio_arranque + 1
            })

    except Exception as e:
        error_exacto = traceback.format_exc()
        print("ERROR CRÍTICO PEDIDO:", error_exacto)
        return jsonify({'error': f"💥 Falla Interna (Posible falta de Memoria en Render):\n{error_exacto}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
