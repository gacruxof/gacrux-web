import os
import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

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

def conectar_bd():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql-292462b-gacrux-of.a.aivencloud.com"),
        user=os.environ.get("DB_USER", "avnadmin"),
        password=os.environ.get("DB_PASSWORD"), 
        database=os.environ.get("DB_NAME", "defaultdb"),
        port=int(os.environ.get("DB_PORT", 19257))
    )

class UsuarioWeb(UserMixin):
    def __init__(self, id_user, usuario, nombre_real, rol_puesto):
        self.id = id_user
        self.usuario = usuario
        self.nombre_real = nombre_real
        self.rol_puesto = rol_puesto

@login_manager.user_loader
def load_user(user_id):
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto FROM usuarios_gacrux WHERE id = %s", (user_id,))
        res = cursor.fetchone()
        cursor.close()
        db.close()
        if res:
            return UsuarioWeb(res['id'], res['usuario'], res['nombre_real'], res['rol_puesto'])
    except:
        pass
    return None

# ==============================================================================
# HTML WEB (INTACTO)
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
    <title>GACRUX - Panel Móvil</title>
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <style>
        :root {
            --bg-body: #11111b;
            --bg-card: #1e1e2e;
            --bg-block: #181825;
            --bg-table: #1e1e2e;
            --bg-th: #313244;
            --text-main: #cdd6f4;
            --text-muted: #a6adc8;
            --border-color: #313244;
            --input-bg: #11111b;
            --input-border: #45475a;
            --primary: #1e3a8a;
            --danger: #e63946;
        }
        
        [data-theme="light"] {
            --bg-body: #f4f6f9;
            --bg-card: #ffffff;
            --bg-block: #f8f9fa;
            --bg-table: #ffffff;
            --bg-th: #e2e8f0;
            --text-main: #11111b;
            --text-muted: #555555;
            --border-color: #cbd5e1;
            --input-bg: #f8f9fa;
            --input-border: #cbd5e1;
            --primary: #1d4ed8;
            --danger: #dc2626;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; transition: background 0.3s, color 0.3s; }
        body { background-color: var(--bg-body); color: var(--text-main); padding: 10px 15px; padding-top: 75px;}
        
        header { 
            position: fixed; top: 0; left: 0; right: 0; height: 60px;
            background-color: var(--bg-card); display: flex; justify-content: space-between; align-items: center; 
            padding: 0 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); z-index: 1000; border-bottom: 2px solid var(--primary);
        }
        .logo-title { font-size: 1.4rem; font-weight: 900; color: var(--primary); letter-spacing: 1px;}
        
        .profile-menu { position: relative; display: inline-block; }
        .profile-btn { 
            background: var(--bg-block); color: var(--text-main); font-size: 1.2rem; 
            border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; 
            display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .dropdown-content { 
            display: none; position: absolute; right: 0; top: 50px; 
            background-color: var(--bg-card); min-width: 220px; border-radius: 8px; 
            box-shadow: 0 8px 20px rgba(0,0,0,0.5); border: 1px solid var(--border-color); overflow: hidden;
        }
        .dropdown-content.show { display: block; }
        .dropdown-header { padding: 15px; background: var(--bg-block); border-bottom: 1px solid var(--border-color); text-align: left; }
        .dropdown-header strong { display: block; font-size: 1rem; color: var(--text-main); }
        .dropdown-header span { font-size: 0.8rem; color: var(--primary); font-weight: bold; text-transform: uppercase;}
        
        .dropdown-content button, .dropdown-content a { 
            width: 100%; padding: 12px 15px; text-decoration: none; display: block; 
            text-align: left; background: none; border: none; font-size: 1rem; color: var(--text-main); font-weight: bold; cursor: pointer;
        }
        .dropdown-content button:active, .dropdown-content a:active { background-color: var(--bg-block); }
        .logout-btn { color: var(--danger) !important; border-top: 1px solid var(--border-color) !important; }

        .container { max-width: 1000px; margin: 0 auto; }
        .seccion { background-color: var(--bg-card); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid var(--border-color);}
        h3 { margin-bottom: 15px; color: var(--text-main); font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input[type="text"] { width: 100%; padding: 14px; border-radius: 6px; border: 2px solid var(--input-border); font-size: 1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-main); }
        input[type="text"]:focus { border-color: var(--primary); outline: none; }
        
        .btn { padding: 14px; border-radius: 6px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; box-shadow: 0 4px 0 rgba(0,0,0,0.2); }
        .btn:active { transform: translateY(4px); box-shadow: 0 0 0 rgba(0,0,0,0); }
        .btn-full { width: 100%; }
        .btn-baja { background-color: var(--bg-block); border: 1px solid var(--border-color); color: var(--text-main);}
        .btn-camara { background-color: var(--primary); margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 8px;}
        
        #contenedor-lector { position: relative; width: 100%; max-width: 500px; margin: 0 auto 15px auto; display: none; }
        #reader { width: 100%; border-radius: 8px; overflow: hidden; border: 2px solid var(--primary); background: black;}
        .contador-escaner { position: absolute; top: 10px; right: 10px; background-color: var(--danger); color: white; padding: 6px 15px; border-radius: 20px; font-weight: 900; font-size: 1.5rem; display: none; z-index: 999; box-shadow: 0 4px 10px rgba(0,0,0,0.6); border: 2px solid white; transition: transform 0.15s ease-out; }
        
        #controles-camara { display: none; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .btn-disparar { background-color: #2e7d32; flex-grow: 1; font-size: 1.1rem; }
        .btn-cerrar-cam { background-color: var(--danger); width: 35%; min-width: 120px; }
        #notificacion { text-align: center; margin-top: 12px; font-weight: bold; font-size: 1rem; }
        
        .contenedor-modelo { background-color: var(--bg-card); border-radius: 8px; padding: 15px; margin-bottom: 30px; border: 1px solid var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .header-modelo-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 12px 15px; border-radius: 6px; color: #ffffff !important; }
        .mod-azul .header-modelo-flex { background-color: #1e3a8a; }
        .mod-rojo .header-modelo-flex { background-color: #7f1d1d; }
        .titulo-modelo { font-size: 1.2rem; font-weight: 900; letter-spacing: 0.5px;}
        .total-modelo-top { font-size: 1rem; font-weight: bold; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;}
        
        .bloque-estampado { margin-bottom: 20px; background-color: var(--bg-block); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);}
        .mod-azul .bloque-estampado { border-left: 5px solid #1e3a8a; }
        .mod-rojo .bloque-estampado { border-left: 5px solid #7f1d1d; }
        .titulo-estampado { font-size: 1.1rem; font-weight: 900; color: var(--text-main); margin-bottom: 10px; text-transform: uppercase; }
        
        .tabla-catalogo { width: 100%; border-collapse: collapse; text-align: center; background-color: var(--bg-table); border-radius: 6px; overflow: hidden;}
        .tabla-catalogo th { background-color: var(--bg-th); color: var(--text-muted); font-size: 0.8rem; font-weight: bold; padding: 10px 5px; text-transform: uppercase; border-bottom: 2px solid var(--border-color); }
        .tabla-catalogo td { padding: 10px 5px; font-size: 1rem; border-bottom: 1px solid var(--border-color); color: var(--text-main); font-weight: 600;}
        .col-color { text-align: left; padding-left: 15px !important; }
        
        .editable { cursor: pointer; position: relative; }
        .editable:active { background-color: rgba(30, 58, 138, 0.2); }
        .input-inline-edit { width: 45px; text-align: center; background: var(--input-bg); color: var(--text-main); border: 2px solid var(--primary); border-radius: 4px; font-weight: bold; font-size: 1rem; padding: 4px 0; outline: none;}
        .stock-cero { color: var(--text-muted) !important; font-weight: normal; opacity: 0.5;}
        
        .fila-totales-excel { width: 100%; padding: 10px 15px; background-color: var(--bg-card); font-size: 0.9rem; font-weight: bold; color: var(--danger); border-top: 1px dashed var(--danger); display: flex; justify-content: space-between; flex-wrap: wrap; margin-top: 5px; border-radius: 4px;}
        
        .sticky-search { position: sticky; top: 60px; z-index: 100; background: var(--bg-body); padding: 10px 0; margin-bottom: 10px;}
    </style>
</head>
<body>
    <header>
        <div class="logo-title">🚀 GACRUX</div>
        <div class="profile-menu">
            <div class="profile-btn" onclick="toggleMenu()">👤</div>
            <div class="dropdown-content" id="menuDropdown">
                <div class="dropdown-header">
                    <strong>{{ empleado }}</strong>
                    <span>{{ puesto }}</span>
                </div>
                <button onclick="alternarTemaWeb()">🌗 Alternar Tema</button>
                <a href="/logout" class="logout-btn">🚪 Cerrar Sesión</a>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="seccion">
            <h3>Ajuste Rápido de Almacén</h3>
            <button class="btn btn-full btn-camara" id="btn-encender-cam" onclick="encenderScanner()"><span>📷</span> INICIAR CÁMARA ESCÁNER</button>
            
            <div id="contenedor-lector">
                <div id="reader"></div>
                <div id="badge-contador" class="contador-escaner">x1</div>
            </div>
            
            <div id="controles-camara">
                <button class="btn btn-cerrar-cam" onclick="apagarScanner()">🔴 CERRAR</button>
                <button class="btn btn-disparar" id="btn-disparar" onclick="activarDisparo()">🎯 DISPARAR (LEER CÓDIGO)</button>
            </div>

            <input type="text" id="codigo_barras" placeholder="O escribe el código manualmente..." autocomplete="off">
            <button class="btn btn-full btn-baja" onclick="procesarBaja()">Descontar 1 Unidad</button>
            <div id="notificacion"></div>
        </div>

        <div class="seccion">
            <h3>Catálogo de Existencias</h3>
            <div class="sticky-search">
                <input type="text" id="busqueda" placeholder="🔍 Filtrar por modelo, color o estampado..." autocomplete="off">
            </div>
            <div id="resultado_busqueda"></div>
        </div>
    </div>

    <script>
        function toggleMenu() { document.getElementById("menuDropdown").classList.toggle("show"); }
        window.onclick = function(event) {
            if (!event.target.matches('.profile-btn')) {
                var dropdowns = document.getElementsByClassName("dropdown-content");
                for (var i = 0; i < dropdowns.length; i++) {
                    if (dropdowns[i].classList.contains('show')) dropdowns[i].classList.remove('show');
                }
            }
        }

        function alternarTemaWeb() {
            const root = document.documentElement;
            if (root.getAttribute('data-theme') === 'light') {
                root.removeAttribute('data-theme');
                localStorage.setItem('gacrux_theme', 'dark');
            } else {
                root.setAttribute('data-theme', 'light');
                localStorage.setItem('gacrux_theme', 'light');
            }
        }
        if(localStorage.getItem('gacrux_theme') === 'light') document.documentElement.setAttribute('data-theme', 'light');

        const esAdmin = "{{ es_admin }}" === "True"; 
        let html5QrCode = null;
        let scannerActivoParaLeer = false; 
        let ultimoCodigoEscaneado = "";
        let contadorMismoCodigo = 0;

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
                        btnDisparar.innerHTML = "🎯 DISPARAR (LEER CÓDIGO)"; btnDisparar.style.backgroundColor = "#2e7d32";
                        procesarBaja();
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
            btnDisparar.innerHTML = "👀 ENFOCA EL CÓDIGO AHORA..."; btnDisparar.style.backgroundColor = "#d08c00"; 
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

        function procesarBaja() {
            let codigo = document.getElementById('codigo_barras').value.trim();
            if(!codigo) return;
            
            fetch('/api/baja', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({codigo: codigo})
            }).then(res => res.json()).then(data => {
                let notif = document.getElementById('notificacion');
                if(data.status === 'ok') {
                    notif.style.color = 'var(--success)'; notif.innerText = "COINCIDENCIA: " + data.msg;
                    fetchCatalogo(); 
                } else {
                    notif.style.color = 'var(--danger)'; notif.innerText = "ERROR: " + data.msg;
                }
                document.getElementById('codigo_barras').value = '';
            });
        }
        document.getElementById('codigo_barras').addEventListener('keypress', function(e) { if (e.key === 'Enter') procesarBaja(); });

        let dataGlobalCatalogo = [];
        let textoBusquedaActual = "";

        async function fetchCatalogo() {
            if (document.querySelector('.input-inline-edit')) return; 
            try {
                let res = await fetch('/api/buscar');
                dataGlobalCatalogo = await res.json();
                renderizarCatalogo();
            } catch(e) {}
        }

        function renderizarCatalogo() {
            if (document.querySelector('.input-inline-edit')) return;
            let contenedor = document.getElementById('resultado_busqueda');
            
            let datosFiltrados = dataGlobalCatalogo.filter(p => {
                if (!textoBusquedaActual) return true;
                let q = textoBusquedaActual.toLowerCase();
                return p.modelo.toLowerCase().includes(q) || 
                       p.estampado.toLowerCase().includes(q) || 
                       p.color.toLowerCase().includes(q);
            });

            if (datosFiltrados.length === 0) {
                contenedor.innerHTML = "<p style='text-align:center; color: var(--text-muted); margin-top: 20px;'>No se encontraron resultados.</p>";
                return;
            }

            let estructura = {};
            datosFiltrados.forEach(p => {
                let mod = p.modelo.toUpperCase().trim(); 
                let est = p.estampado.toUpperCase().trim(); 
                if (!estructura[mod]) estructura[mod] = {};
                if (!estructura[mod][est]) estructura[mod][est] = [];
                estructura[mod][est].push(p);
            });
            
            let htmlFinal = "";
            let esAzul = true;
            for (let mod in estructura) {
                let totalLote = 0;
                for (let est_k in estructura[mod]) { estructura[mod][est_k].forEach(p => { totalLote += (p.talla_ch + p.talla_m + p.talla_g + p.talla_eg); }); }
                
                let claseColor = esAzul ? 'mod-azul' : 'mod-rojo';
                htmlFinal += `<div class="contenedor-modelo ${claseColor}"><div class="header-modelo-flex"><div class="titulo-modelo">${mod}</div><div class="total-modelo-top">${totalLote} PZAS</div></div>`;
                
                for (let est in estructura[mod]) {
                    let sumCH = 0, sumM = 0, sumG = 0, sumEG = 0;
                    estructura[mod][est].forEach(p => { sumCH += p.talla_ch; sumM += p.talla_m; sumG += p.talla_g; sumEG += p.talla_eg; });
                    
                    htmlFinal += `<div class="bloque-estampado"><div class="titulo-estampado">${est}</div><table class="tabla-catalogo"><thead><tr><th class="col-color">COLOR</th>
                                        ${sumCH > 0 ? '<th style="width: 15%;">CH</th>' : ''}${sumM > 0 ? '<th style="width: 15%;">M</th>' : ''}
                                        ${sumG > 0 ? '<th style="width: 15%;">G</th>' : ''}${sumEG > 0 ? '<th style="width: 15%;">EG</th>' : ''}</tr></thead><tbody>`;
                    
                    estructura[mod][est].forEach(p => {
                        let claseEditable = esAdmin ? 'editable' : '';
                        htmlFinal += `<tr><td class="col-color">${p.color.toUpperCase()}</td>
                                ${sumCH > 0 ? `<td class="${claseEditable} ${p.talla_ch == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_ch')">${p.talla_ch}</td>` : ''}
                                ${sumM > 0 ? `<td class="${claseEditable} ${p.talla_m == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_m')">${p.talla_m}</td>` : ''}
                                ${sumG > 0 ? `<td class="${claseEditable} ${p.talla_g == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_g')">${p.talla_g}</td>` : ''}
                                ${sumEG > 0 ? `<td class="${claseEditable} ${p.talla_eg == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_eg')">${p.talla_eg}</td>` : ''}</tr>`;
                    });
                    
                    let sumaTotalTabla = sumCH + sumM + sumG + sumEG;
                    let partesTotales = [];
                    if (sumCH > 0) partesTotales.push(`CH: ${sumCH}`); if (sumM > 0) partesTotales.push(`M: ${sumM}`);
                    if (sumG > 0) partesTotales.push(`G: ${sumG}`); if (sumEG > 0) partesTotales.push(`EG: ${sumEG}`);
                    htmlFinal += `</tbody></table><div class="fila-totales-excel"><div>${partesTotales.join(' &nbsp;|&nbsp; ')}</div><div>TOTAL: ${sumaTotalTabla}</div></div></div>`;
                }
                htmlFinal += `</div>`; esAzul = !esAzul;
            }
            contenedor.innerHTML = htmlFinal;
        }

        document.getElementById('busqueda').addEventListener('input', function(e) {
            textoBusquedaActual = e.target.value.trim();
            renderizarCatalogo();
        });

        function activarEdicionCelda(elemento, dbId, columnaSql) {
            if (!esAdmin || elemento.querySelector('input')) return; 
            let valorActual = elemento.innerText.trim();
            elemento.innerHTML = `<input type="number" class="input-inline-edit" value="${valorActual}" min="0">`;
            let input = elemento.querySelector('input'); input.focus(); input.select();
            
            function guardarCambioInmediato() {
                let nuevoValor = input.value.trim();
                if (nuevoValor === "" || isNaN(nuevoValor) || parseInt(nuevoValor) < 0) { elemento.innerHTML = valorActual; return; }
                if (parseInt(nuevoValor) === parseInt(valorActual)) { elemento.innerHTML = nuevoValor; return; }
                elemento.innerHTML = "...";
                fetch('/api/guardar_stock_web', {
                    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: dbId, columna: columnaSql, valor: parseInt(nuevoValor)})
                }).then(res => res.json()).then(data => {
                    if (data.status === 'ok') { fetchCatalogo(); } 
                    else { alert("Error al guardar: " + data.msg); elemento.innerHTML = valorActual; }
                });
            }
            input.addEventListener('keypress', function(e) { if (e.key === 'Enter') guardarCambioInmediato(); });
            input.addEventListener('focusout', guardarCambioInmediato);
        }
        
        setInterval(fetchCatalogo, 4000);
        fetchCatalogo(); 
    </script>
</body>
</html>
"""

# ==============================================================================
# RUTAS WEB PRINCIPALES (INTACTAS)
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('usuario', '').strip().lower()
        pass_input = request.form.get('password', '').strip()
        try:
            db = conectar_bd()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id, usuario, nombre_real, rol_puesto, password FROM usuarios_gacrux WHERE usuario = %s", (user_input,))
            usuario_bd = cursor.fetchone()
            cursor.close(); db.close()
            
            if usuario_bd and usuario_bd['password'] == pass_input:
                user_obj = UsuarioWeb(usuario_bd['id'], usuario_bd['usuario'], usuario_bd['nombre_real'], usuario_bd['rol_puesto'])
                login_user(user_obj)
                return redirect(url_for('index'))
            else: flash('Usuario o contraseña incorrectos')
        except Exception as e: flash(f'Error de conexión: {e}')
    return render_template_string(HTML_LOGIN)

@app.route('/')
@login_required
def index():
    es_jefe = (current_user.usuario == "alberto")
    return render_template_string(HTML_BASE, empleado=current_user.nombre_real.upper(), puesto=current_user.rol_puesto.upper(), es_admin=es_jefe)

@app.route('/api/buscar')
@login_required
def api_buscar():
    db = conectar_bd()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
    resultados = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify(resultados)

@app.route('/api/guardar_stock_web', methods=['POST'])
@login_required
def api_guardar_stock_web():
    if current_user.usuario != "alberto": return jsonify({'status': 'error', 'msg': 'Privilegios insuficientes.'})
    data = request.get_json(); db_id = data.get('id'); columna_sql = data.get('columna', '').strip(); nuevo_valor = data.get('valor')
    if columna_sql not in ['talla_ch', 'talla_m', 'talla_g', 'talla_eg'] or nuevo_valor < 0: return jsonify({'status': 'error', 'msg': 'Parámetros no válidos.'})
        
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT modelo, estampado, color FROM panel_stock WHERE id = %s", (db_id,))
        info = cursor.fetchone()
        if info:
            cursor.execute(f"UPDATE panel_stock SET {columna_sql} = %s WHERE id = %s", (nuevo_valor, db_id))
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            talla_legible = columna_sql.replace('talla_', '').upper()
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, %s, %s, %s, 0, 0.00, 0.00, %s, 'EDICION MANUAL WEB', %s)", 
                           (info['modelo'], info['estampado'], info['color'], talla_legible, fecha_actual, f"{current_user.nombre_real} (Móvil)"))
            db.commit(); cursor.close(); db.close()
            return jsonify({'status': 'ok'})
        cursor.close(); db.close()
        return jsonify({'status': 'error', 'msg': 'Fila no encontrada.'})
    except Exception as e: return jsonify({'status': 'error', 'msg': str(e)})

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
            res_stock = cursor.fetchone()
            
            if res_stock:
                if res_stock[col] <= 0:
                    cursor.close(); db.close()
                    return jsonify({'status': 'error', 'msg': f"{prenda['modelo']} ({prenda['talla']}) ya está en 0."})
                    
                cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (prenda['panel_stock_id'],))
                fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                precio_p = float(prenda['precio'])
                
                sql_h = """
                    INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por)
                    VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'WEB ALMACEN REGISTRO', %s)
                """
                cursor.execute(sql_h, (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, current_user.nombre_real))
                db.commit()
                
                msg = f"{prenda['modelo']} - {prenda['estampado']} ({prenda['talla']})"
                cursor.close(); db.close()
                return jsonify({'status': 'ok', 'msg': msg})
            else:
                cursor.close(); db.close()
                return jsonify({'status': 'error', 'msg': 'Borrada del Catálogo Maestro.'})
                
    cursor.close(); db.close()
    return jsonify({'status': 'error', 'msg': 'Código de barras no válido o desconectado.'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==============================================================================
# RUTAS DE LA APP MÓVIL Y NUEVO MODO DESARROLLADOR
# ==============================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    datos = request.get_json()
    user_input = datos.get('usuario', '').strip().lower()
    pass_input = datos.get('password', '').strip()
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto, password FROM usuarios_gacrux WHERE usuario = %s", (user_input,))
        usuario_bd = cursor.fetchone()
        cursor.close(); db.close()
        
        if usuario_bd and usuario_bd['password'] == pass_input:
            token_sencillo = f"gacrux-auth-{usuario_bd['id']}"
            return jsonify({
                'token': token_sencillo,
                'nombre_real': usuario_bd['nombre_real'],
                'rol_puesto': usuario_bd['rol_puesto']
            }), 200
        else:
            return jsonify({'error': 'Credenciales incorrectas'}), 401
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/inventario/descontar', methods=['POST'])
def api_descontar():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'Acceso no autorizado a la API'}), 401

    data = request.get_json()
    codigo = data.get('codigo_barras', '').strip()
    realizado_por = data.get('realizado_por', 'App Nativa Flutter').strip() # <- AQUÍ ATRAPAMOS EL NOMBRE
    
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT modelo, estampado, color, talla, precio, panel_stock_id FROM inventario WHERE codigo_barras = %s", (codigo,))
        prenda = cursor.fetchone()
        
        if prenda:
            talla_map = {'CH':'talla_ch', 'M':'talla_m', 'G':'talla_g', 'EG':'talla_eg'}
            col = talla_map.get(prenda['talla'].upper().strip())
            
            if col and prenda['panel_stock_id']:
                cursor.execute(f"SELECT {col} FROM panel_stock WHERE id = %s", (prenda['panel_stock_id'],))
                res_stock = cursor.fetchone()
                
                if res_stock and res_stock[col] > 0:
                    cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (prenda['panel_stock_id'],))
                    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    precio_p = float(prenda['precio'])
                    
                    sql_h = """
                        INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por)
                        VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'BAJA APP MOVIL', %s)
                    """
                    cursor.execute(sql_h, (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, realizado_por))
                    db.commit()
                    cursor.close(); db.close()
                    return jsonify({'status': 'ok', 'msg': 'Descontado exitosamente'})
        
        cursor.close(); db.close()
        return jsonify({'error': 'Código inválido o sin stock'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/app/inventario', methods=['GET'])
def api_app_inventario():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'Acceso no autorizado'}), 401
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        # Traerá también las nuevas columnas automáticamente
        cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
        resultados = cursor.fetchall()
        cursor.close(); db.close()
        return jsonify(resultados)
    except Exception as e: return jsonify({'error': str(e)}), 500

# ==============================================================================
# RUTAS DE ADMINISTRADOR (NUEVAS Y AUTOCOMPLETADO)
# ==============================================================================
def generar_codigo_13_digitos(cursor, modelo, estampado, color, talla):
    cursor.execute("SELECT SUBSTRING(codigo_barras, 1, 5) AS mod_id FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo,))
    res_mod = cursor.fetchone()
    if res_mod and res_mod['mod_id'] and res_mod['mod_id'].isdigit(): mod_str = res_mod['mod_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 1, 5) AS UNSIGNED)) AS max_mod FROM inventario WHERE LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'")
        res_max_mod = cursor.fetchone()
        max_m = res_max_mod['max_mod'] if res_max_mod and res_max_mod['max_mod'] else 0
        mod_str = f"{max_m + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 6, 5) AS est_id FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado))
    res_est = cursor.fetchone()
    if res_est and res_est['est_id'] and res_est['est_id'].isdigit(): est_str = res_est['est_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 6, 5) AS UNSIGNED)) AS max_est FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo,))
        res_max_est = cursor.fetchone()
        max_e = res_max_est['max_est'] if res_max_est and res_max_est['max_est'] else 0
        est_str = f"{max_e + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 11, 2) AS col_id FROM inventario WHERE modelo = %s AND estampado = %s AND color = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado, color))
    res_col = cursor.fetchone()
    if res_col and res_col['col_id'] and res_col['col_id'].isdigit(): col_str = res_col['col_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 11, 2) AS UNSIGNED)) AS max_col FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo, estampado))
        res_max_col = cursor.fetchone()
        max_c = res_max_col['max_col'] if res_max_col and res_max_col['max_col'] else 0
        col_str = f"{max_c + 1:02d}"

    # Asignamos ID de talla dinámico
    mapa_tallas = {'CH': 1, 'M': 2, 'G': 3, 'XG': 4, 'T-12': 5, 'T-16': 6, 'EG': 4}
    talla_id = mapa_tallas.get(talla.upper(), 9)
    return f"{mod_str}{est_str}{col_str}{talla_id:01d}"

@app.route('/api/app/bases', methods=['GET'])
def api_app_bases():
    """Descarga los modelos y colores base para el autocompletado en Flutter"""
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM modelos_base")
        modelos = cursor.fetchall()
        cursor.execute("SELECT * FROM colores_base")
        colores = cursor.fetchall()
        cursor.close(); db.close()
        return jsonify({'modelos': modelos, 'colores': colores})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/app/subir_lote', methods=['POST'])
def api_subir_lote():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
        
    data = request.get_json()
    modelo = data.get('modelo', '').strip().upper()
    estampado = data.get('estampado', '').strip().upper()
    color = data.get('color', '').strip().upper()
    precio = float(data.get('precio', 250.0))
    tallas = data.get('tallas', {})
    realizado_por = data.get('realizado_por', 'App Móvil').strip() # <- AQUÍ ATRAPAMOS EL NOMBRE
    
    genero = data.get('genero', 'TODO').strip().upper()
    estilo = data.get('estilo', 'NORMAL').strip().upper()
    tipo_prenda = data.get('tipo_prenda', 'SUDADERA').strip().upper()
    
    if not modelo or not estampado or not color: return jsonify({'error': 'Faltan datos'}), 400
        
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo, estampado, color))
        res = cursor.fetchone()
        
        ch = tallas.get('CH', 0)
        m = tallas.get('M', 0)
        g = tallas.get('G', 0)
        talla_extra_nombre = tallas.get('EXTRA_NAME', 'EG').upper()
        talla_extra_cant = tallas.get('EXTRA_CANT', 0)
        
        if res:
            cursor.execute("""
                UPDATE panel_stock 
                SET talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_eg=talla_eg+%s,
                    genero=%s, estilo=%s, tipo_prenda=%s
                WHERE id=%s
            """, (ch, m, g, talla_extra_cant, genero, estilo, tipo_prenda, res['id']))
            panel_id = res['id']
        else:
            cursor.execute("""
                INSERT INTO panel_stock (modelo, estampado, color, talla_ch, talla_m, talla_g, talla_eg, genero, estilo, tipo_prenda) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (modelo, estampado, color, ch, m, g, talla_extra_cant, genero, estilo, tipo_prenda))
            panel_id = cursor.lastrowid
            
        tallas_ingresadas = []
        if ch > 0: tallas_ingresadas.append(('CH', ch))
        if m > 0: tallas_ingresadas.append(('M', m))
        if g > 0: tallas_ingresadas.append(('G', g))
        if talla_extra_cant > 0: tallas_ingresadas.append((talla_extra_nombre, talla_extra_cant))
        
        codigos_generados = []
        total_ingresado = 0
        
        for talla_str, cantidad in tallas_ingresadas:
            cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo, estampado, color, talla_str))
            ex = cursor.fetchone()
            if ex:
                codigo_final = ex['codigo_barras']
                cursor.execute("UPDATE inventario SET genero=%s, estilo=%s, tipo_prenda=%s WHERE codigo_barras=%s", (genero, estilo, tipo_prenda, codigo_final))
            else:
                codigo_final = generar_codigo_13_digitos(cursor, modelo, estampado, color, talla_str)
                cursor.execute("""
                    INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (codigo_final, modelo, estampado, color, talla_str, precio, panel_id, genero, estilo, tipo_prenda))
            
            codigos_generados.append({"talla": talla_str, "codigo": codigo_final, "cantidad": cantidad})
            total_ingresado += cantidad
            
        if total_ingresado > 0:
            fecha_a = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, %s, %s, %s, %s, 0, 0, %s, 'INGRESO APP LOTE', %s)", 
                           (modelo, estampado, color, "MÚLTIPLE", total_ingresado, fecha_a, realizado_por))
            
        db.commit()
        cursor.close(); db.close()
        return jsonify({'status': 'ok', 'codigos': codigos_generados, 'total': total_ingresado})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/app/actualizar_filtros', methods=['POST'])
def api_actualizar_filtros():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    modelo = data.get('modelo', '').strip().upper()
    genero = data.get('genero', '').strip().upper()
    estilo = data.get('estilo', '').strip().upper()
    tipo_prenda = data.get('tipo_prenda', '').strip().upper()
    try:
        db = conectar_bd()
        cursor = db.cursor()
        cursor.execute("UPDATE panel_stock SET genero=%s, estilo=%s, tipo_prenda=%s WHERE modelo=%s", (genero, estilo, tipo_prenda, modelo))
        cursor.execute("UPDATE inventario SET genero=%s, estilo=%s, tipo_prenda=%s WHERE modelo=%s", (genero, estilo, tipo_prenda, modelo))
        db.commit(); cursor.close(); db.close()
        return jsonify({'status': 'ok'})
    except Exception as e: return jsonify({'error': str(e)}), 500

# ==============================================================================
# MIGRACIÓN (Ya incluye las bases)
# ==============================================================================
@app.route('/api/migrar_bd')
def api_migrar_bd():
    try:
        db = conectar_bd()
        cursor = db.cursor()
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
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modelos_base (
                id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) UNIQUE,
                genero VARCHAR(50), estilo VARCHAR(50), tipo_prenda VARCHAR(50)
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS colores_base (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) UNIQUE)")
        mensajes.append("✅ Tablas de Autocompletado Creadas.")

        db.commit(); cursor.close(); db.close()
        return f"<h1>Migración Gacrux Completada</h1><p>{'<br>'.join(mensajes)}</p>"
    except Exception as e: return f"<h1>Error Crítico</h1><p>{str(e)}</p>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
