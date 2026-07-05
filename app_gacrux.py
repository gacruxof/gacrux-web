import os
import datetime
import io
import base64
import json
import math
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

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
        password=os.environ.get("DB_PASSWORD", "AVNS_lJSsblo1fLuMi6cA-yW"), 
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
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto FROM usuarios_gacrux WHERE id = %s", (user_id,))
        res = cursor.fetchone()
        cursor.close(); db.close()
        if res: return UsuarioWeb(res['id'], res['usuario'], res['nombre_real'], res['rol_puesto'])
    except: pass
    return None

# ==============================================================================
# HTML WEB (7 TALLAS)
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
            --bg-body: #11111b; --bg-card: #1e1e2e; --bg-block: #181825; --bg-table: #1e1e2e;
            --bg-th: #313244; --text-main: #cdd6f4; --text-muted: #a6adc8; --border-color: #313244;
            --input-bg: #11111b; --input-border: #45475a; --primary: #1e3a8a; --danger: #e63946;
        }
        [data-theme="light"] {
            --bg-body: #f4f6f9; --bg-card: #ffffff; --bg-block: #f8f9fa; --bg-table: #ffffff;
            --bg-th: #e2e8f0; --text-main: #11111b; --text-muted: #555555; --border-color: #cbd5e1;
            --input-bg: #f8f9fa; --input-border: #cbd5e1; --primary: #1d4ed8; --danger: #dc2626;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; transition: background 0.3s, color 0.3s; }
        body { background-color: var(--bg-body); color: var(--text-main); padding: 10px 15px; padding-top: 75px;}
        header { position: fixed; top: 0; left: 0; right: 0; height: 60px; background-color: var(--bg-card); display: flex; justify-content: space-between; align-items: center; padding: 0 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); z-index: 1000; border-bottom: 2px solid var(--primary); }
        .logo-title { font-size: 1.4rem; font-weight: 900; color: var(--primary); letter-spacing: 1px;}
        .profile-menu { position: relative; display: inline-block; }
        .profile-btn { background: var(--bg-block); color: var(--text-main); font-size: 1.2rem; border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .dropdown-content { display: none; position: absolute; right: 0; top: 50px; background-color: var(--bg-card); min-width: 220px; border-radius: 8px; box-shadow: 0 8px 20px rgba(0,0,0,0.5); border: 1px solid var(--border-color); overflow: hidden; }
        .dropdown-content.show { display: block; }
        .dropdown-header { padding: 15px; background: var(--bg-block); border-bottom: 1px solid var(--border-color); text-align: left; }
        .dropdown-header strong { display: block; font-size: 1rem; color: var(--text-main); }
        .dropdown-header span { font-size: 0.8rem; color: var(--primary); font-weight: bold; text-transform: uppercase;}
        .dropdown-content button, .dropdown-content a { width: 100%; padding: 12px 15px; text-decoration: none; display: block; text-align: left; background: none; border: none; font-size: 1rem; color: var(--text-main); font-weight: bold; cursor: pointer; }
        .dropdown-content button:active, .dropdown-content a:active { background-color: var(--bg-block); }
        .logout-btn { color: var(--danger) !important; border-top: 1px solid var(--border-color) !important; }
        .container { max-width: 1000px; margin: 0 auto; }
        .seccion { background-color: var(--bg-card); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid var(--border-color);}
        h3 { margin-bottom: 15px; color: var(--text-main); font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        input[type="text"] { width: 100%; padding: 14px; border-radius: 6px; border: 2px solid var(--input-border); font-size: 1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-main); }
        input[type="text"]:focus { border-color: var(--primary); outline: none; }
        .btn { padding: 14px; border-radius: 6px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; box-shadow: 0 4px 0 rgba(0,0,0,0.2); }
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
                for (let est_k in estructura[mod]) { 
                    estructura[mod][est_k].forEach(p => { 
                        totalLote += (p.talla_t12||0) + (p.talla_t16||0) + (p.talla_ex_ch||0) + (p.talla_ch||0) + (p.talla_m||0) + (p.talla_g||0) + (p.talla_ex_g||0); 
                    }); 
                }
                
                let claseColor = esAzul ? 'mod-azul' : 'mod-rojo';
                htmlFinal += `<div class="contenedor-modelo ${claseColor}"><div class="header-modelo-flex"><div class="titulo-modelo">${mod}</div><div class="total-modelo-top">${totalLote} PZAS</div></div>`;
                
                for (let est in estructura[mod]) {
                    let sT12 = 0, sT16 = 0, sEXCH = 0, sCH = 0, sM = 0, sG = 0, sEXG = 0;
                    estructura[mod][est].forEach(p => { 
                        sT12 += p.talla_t12 || 0; sT16 += p.talla_t16 || 0; sEXCH += p.talla_ex_ch || 0;
                        sCH += p.talla_ch || 0; sM += p.talla_m || 0; sG += p.talla_g || 0; sEXG += p.talla_ex_g || 0; 
                    });
                    
                    htmlFinal += `<div class="bloque-estampado"><div class="titulo-estampado">${est}</div><table class="tabla-catalogo"><thead><tr><th class="col-color">COLOR</th>
                                        ${sT12 > 0 ? '<th style="width: 10%;">T12</th>' : ''}
                                        ${sT16 > 0 ? '<th style="width: 10%;">T16</th>' : ''}
                                        ${sEXCH > 0 ? '<th style="width: 12%;">EX CH</th>' : ''}
                                        ${sCH > 0 ? '<th style="width: 10%;">CH</th>' : ''}
                                        ${sM > 0 ? '<th style="width: 10%;">M</th>' : ''}
                                        ${sG > 0 ? '<th style="width: 10%;">G</th>' : ''}
                                        ${sEXG > 0 ? '<th style="width: 12%;">EX G</th>' : ''}
                                        </tr></thead><tbody>`;
                    
                    estructura[mod][est].forEach(p => {
                        let claseEditable = esAdmin ? 'editable' : '';
                        htmlFinal += `<tr><td class="col-color">${p.color.toUpperCase()}</td>
                                ${sT12 > 0 ? `<td class="${claseEditable} ${(p.talla_t12||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_t12')">${p.talla_t12||0}</td>` : ''}
                                ${sT16 > 0 ? `<td class="${claseEditable} ${(p.talla_t16||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_t16')">${p.talla_t16||0}</td>` : ''}
                                ${sEXCH > 0 ? `<td class="${claseEditable} ${(p.talla_ex_ch||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_ex_ch')">${p.talla_ex_ch||0}</td>` : ''}
                                ${sCH > 0 ? `<td class="${claseEditable} ${(p.talla_ch||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_ch')">${p.talla_ch||0}</td>` : ''}
                                ${sM > 0 ? `<td class="${claseEditable} ${(p.talla_m||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_m')">${p.talla_m||0}</td>` : ''}
                                ${sG > 0 ? `<td class="${claseEditable} ${(p.talla_g||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_g')">${p.talla_g||0}</td>` : ''}
                                ${sEXG > 0 ? `<td class="${claseEditable} ${(p.talla_ex_g||0) == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_ex_g')">${p.talla_ex_g||0}</td>` : ''}
                                </tr>`;
                    });
                    
                    let sumaTotalTabla = sT12 + sT16 + sEXCH + sCH + sM + sG + sEXG;
                    htmlFinal += `</tbody></table><div class="fila-totales-excel"><div>TOTAL ESTAMPADO:</div><div>${sumaTotalTabla}</div></div></div>`;
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
# RUTAS WEB PRINCIPALES
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
            cursor.close()
            db.close()
            if usuario_bd and usuario_bd['password'] == pass_input:
                user_obj = UsuarioWeb(usuario_bd['id'], usuario_bd['usuario'], usuario_bd['nombre_real'], usuario_bd['rol_puesto'])
                login_user(user_obj)
                return redirect(url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos')
        except Exception as e:
            flash(f'Error de conexión: {e}')
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
    cursor.close()
    db.close()
    return jsonify(resultados)

@app.route('/api/guardar_stock_web', methods=['POST'])
@login_required
def api_guardar_stock_web():
    if current_user.usuario != "alberto": 
        return jsonify({'status': 'error', 'msg': 'Privilegios insuficientes.'})
    
    data = request.get_json()
    db_id = data.get('id')
    columna_sql = data.get('columna', '').strip()
    nuevo_valor = data.get('valor')
    
    columnas_permitidas = ['talla_t12', 'talla_t16', 'talla_ex_ch', 'talla_ch', 'talla_m', 'talla_g', 'talla_ex_g', 'talla_eg']
    if columna_sql not in columnas_permitidas or nuevo_valor < 0: 
        return jsonify({'status': 'error', 'msg': 'Parámetros no válidos.'})
        
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
            db.commit()
            cursor.close()
            db.close()
            return jsonify({'status': 'ok'})
        cursor.close()
        db.close()
        return jsonify({'status': 'error', 'msg': 'Fila no encontrada.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

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
        talla_map = {
            'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch',
            'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 
            'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'
        }
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
                    if res_stock[col] <= 0:
                        cursor.close(); db.close()
                        return jsonify({'status': 'error', 'msg': f"{prenda['modelo']} ({prenda['talla']}) ya está en 0."})
                        
                    cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (p_id,))
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
# RUTAS DE LA APP MÓVIL Y ADMIN
# ==============================================================================

def generar_codigo_13_nube(cursor, modelo, estampado, color, talla):
    cursor.execute("SELECT SUBSTRING(codigo_barras, 1, 5) AS mod_id FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo,))
    res_mod = cursor.fetchone()
    if res_mod and res_mod['mod_id'] and res_mod['mod_id'].isdigit(): 
        mod_str = res_mod['mod_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 1, 5) AS UNSIGNED)) AS max_mod FROM inventario WHERE LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'")
        res_max_mod = cursor.fetchone()
        mod_str = f"{ (res_max_mod['max_mod'] if res_max_mod and res_max_mod['max_mod'] else 0) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 6, 5) AS est_id FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado))
    res_est = cursor.fetchone()
    if res_est and res_est['est_id'] and res_est['est_id'].isdigit(): 
        est_str = res_est['est_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 6, 5) AS UNSIGNED)) AS max_est FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo,))
        res_max_est = cursor.fetchone()
        est_str = f"{(res_max_est['max_est'] if res_max_est and res_max_est['max_est'] else 0) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 11, 2) AS col_id FROM inventario WHERE modelo = %s AND estampado = %s AND color = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado, color))
    res_col = cursor.fetchone()
    if res_col and res_col['col_id'] and res_col['col_id'].isdigit(): 
        col_str = res_col['col_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 11, 2) AS UNSIGNED)) AS max_col FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo, estampado))
        res_max_col = cursor.fetchone()
        col_str = f"{(res_max_col['max_col'] if res_max_col and res_max_col['max_col'] else 0) + 1:02d}"

    talla_id = {'CH': 1, 'M': 2, 'G': 3, 'XG': 4, 'EX G': 4, 'T-12': 5, 'T-16': 6, 'EG': 4}.get(talla.upper(), 9)
    return f"{mod_str}{est_str}{col_str}{talla_id:01d}"

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
        cursor.close()
        db.close()
        
        if usuario_bd and usuario_bd['password'] == pass_input:
            token_sencillo = f"gacrux-auth-{usuario_bd['id']}"
            return jsonify({
                'token': token_sencillo,
                'nombre_real': usuario_bd['nombre_real'],
                'rol_puesto': usuario_bd['rol_puesto']
            }), 200
        else:
            return jsonify({'error': 'Credenciales incorrectas'}), 401
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventario/descontar', methods=['POST'])
def api_descontar():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): 
        return jsonify({'error': 'Acceso no autorizado a la API'}), 401

    data = request.get_json()
    codigo = data.get('codigo_barras', '').strip()
    realizado_por = data.get('realizado_por', 'App Nativa Flutter').strip()
    
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT modelo, estampado, color, talla, precio, panel_stock_id FROM inventario WHERE codigo_barras = %s", (codigo,))
        prenda = cursor.fetchone()
        
        if prenda:
            talla_map = {
                'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch',
                'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 
                'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'
            }
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
                    
                    if res_stock and res_stock[col] > 0:
                        cursor.execute(f"UPDATE panel_stock SET {col} = {col} - 1 WHERE id = %s", (p_id,))
                        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        precio_p = float(prenda['precio'])
                        
                        sql_h = """
                            INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por)
                            VALUES (%s, %s, %s, %s, 1, %s, %s, %s, 'BAJA APP MOVIL', %s)
                        """
                        cursor.execute(sql_h, (prenda['modelo'], prenda['estampado'], prenda['color'], prenda['talla'], precio_p, precio_p, fecha_actual, realizado_por))
                        db.commit()
                        cursor.close()
                        db.close()
                        
                        nombre_prenda = f"{prenda['modelo']} {prenda['estampado']} {prenda['color']} {prenda['talla']}"
                        return jsonify({'status': 'ok', 'msg': nombre_prenda})
        
        cursor.close()
        db.close()
        return jsonify({'error': 'CÓDIGO INVÁLIDO O SIN STOCK'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/app/inventario', methods=['GET'])
def api_app_inventario():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'Acceso no autorizado'}), 401
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
        resultados = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(resultados)
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

@app.route('/api/pos/enviar', methods=['POST'])
def api_pos_enviar():
    auth_header = request.headers.get('Authorization')
    if not auth_header: return jsonify({'error': 'No autorizado'}), 401
    codigo = request.get_json().get('codigo', '').strip()
    if not codigo: return jsonify({'error': 'Sin código'}), 400
    try:
        db = conectar_bd()
        cursor = db.cursor()
        cursor.execute("INSERT INTO cola_escaneos (codigo_barras, procesado) VALUES (%s, 0)", (codigo,))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'status': 'ok'})
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

@app.route('/api/app/bases', methods=['GET'])
def api_app_bases():
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM modelos_base")
        modelos = cursor.fetchall()
        cursor.execute("SELECT * FROM colores_base")
        colores = cursor.fetchall()
        cursor.close()
        db.close()
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
    realizado_por = data.get('realizado_por', 'App Móvil').strip()
    
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
                SET talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s,
                    genero=%s, estilo=%s, tipo_prenda=%s
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
        
        codigos_generados = []
        total_ingresado = 0
        
        for talla_str, cantidad in tallas_ingresadas:
            cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo, estampado, color, talla_str))
            ex = cursor.fetchone()
            if ex:
                codigo_final = ex['codigo_barras']
                cursor.execute("UPDATE inventario SET genero=%s, estilo=%s, tipo_prenda=%s WHERE codigo_barras=%s", (genero, estilo, tipo_prenda, codigo_final))
            else:
                codigo_final = generar_codigo_13_nube(cursor, modelo, estampado, color, talla_str)
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
        cursor.close()
        db.close()
        return jsonify({'status': 'ok', 'codigos': codigos_generados, 'total': total_ingresado})
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

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
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'status': 'ok'})
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

@app.route('/api/app/mapa_codigos', methods=['GET'])
def api_mapa_codigos():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.codigo_barras, i.talla, 
                   COALESCE(p.talla_t12, 0) as talla_t12, 
                   COALESCE(p.talla_t16, 0) as talla_t16, 
                   COALESCE(p.talla_ex_ch, 0) as talla_ex_ch, 
                   COALESCE(p.talla_ch, 0) as talla_ch, 
                   COALESCE(p.talla_m, 0) as talla_m, 
                   COALESCE(p.talla_g, 0) as talla_g, 
                   COALESCE(p.talla_ex_g, 0) as talla_ex_g,
                   COALESCE(p.talla_eg, 0) as talla_eg
            FROM inventario i
            LEFT JOIN panel_stock p ON 
                (i.panel_stock_id = p.id) OR 
                (i.panel_stock_id IS NULL AND i.modelo = p.modelo AND i.estampado = p.estampado AND i.color = p.color)
        """)
        res = cursor.fetchall()
        cursor.close()
        db.close()
        
        mapa = {}
        t_map = {
            'T-12': 'talla_t12', 'T-16': 'talla_t16', 'EX CH': 'talla_ex_ch',
            'CH': 'talla_ch', 'M': 'talla_m', 'G': 'talla_g', 
            'EG': 'talla_ex_g', 'XG': 'talla_ex_g', 'EX G': 'talla_ex_g'
        }
        for r in res:
            columna = t_map.get(str(r['talla']).upper(), 'talla_ex_g')
            if columna in r:
                mapa[r['codigo_barras']] = r[columna]
            else:
                mapa[r['codigo_barras']] = r.get('talla_eg', 0)
            
        return jsonify(mapa)
    except Exception as e: 
        return jsonify({'error': str(e)}), 500

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

        db.commit()
        cursor.close()
        db.close()
        return f"<h1>Migración Gacrux Completada</h1><p>{'<br>'.join(mensajes)}</p>"
    except Exception as e: return f"<h1>Error Crítico</h1><p>{str(e)}</p>"

# ==============================================================================
# 🔥 MOTOR DE HOJA MADRE MÓVIL Y GESTOR DE RECETAS EN NUBE 🔥
# ==============================================================================
@app.route('/api/app/receta/<modelo>', methods=['GET'])
def api_get_receta(modelo):
    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recetas_madre WHERE modelo = %s", (modelo,))
        res = cursor.fetchone()
        cursor.close()
        db.close()
        if res: return jsonify(res)
        return jsonify({})
    except Exception as e:
        return jsonify({})

@app.route('/api/app/magia_madre', methods=['POST'])
def api_magia_madre():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): 
        return jsonify({'error': 'No autorizado'}), 401
    
    req = request.get_json()
    modelo = req.get('modelo', '').strip().upper()
    estampados = req.get('estampados', [])
    colores = req.get('colores', [])
    cuerpos_actuales = req.get('cuerpos_actuales', {})
    tallas_usadas = req.get('tallas_usadas', [])
    datos_lienzo_color = req.get('datos_lienzo_color', {})
    folios_a_usar = req.get('folios_a_usar', [])
    
    fecha_txt = datetime.datetime.now().strftime("%d/%m/%y")
    str_folios = ", ".join([str(f).zfill(2) for f in folios_a_usar])

    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)
        
        # 🔥 CONSULTAR IMAGEN Y CUERPOS POR ID 🔥
        cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
        row_img = cursor.fetchone()
        imagen_blob = row_img['imagen_dibujo'] if row_img else None
        formato_img = row_img['formato_img'] if row_img else "1500x1900 (Frente)"

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
                    if row['id'] == id_g:
                        cuerpos_del_modelo.append(row)
                        break
        if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]

        datos_corte = []
        for c in colores:
            lienzos = int(datos_lienzo_color.get(c, 0))
            fila = {"color": c, "lienzos": lienzos, "totales_talla": {t: 0 for t in tallas_usadas}, "gran_total": 0}
            for t in tallas_usadas: 
                prendas = lienzos * int(cuerpos_actuales.get(t, 0))
                fila["totales_talla"][t] = prendas
                fila["gran_total"] += prendas
            datos_corte.append(fila)

        datos_corte.sort(key=lambda x: x["gran_total"], reverse=True)

        num_folios = len(folios_a_usar)
        est_por_folio = [estampados[i:i + 4] for i in range(0, len(estampados), 4)]
        datos_inventario_global = []

        total_ingresado = 0
        mapa_bd = {
            "T-12": "talla_t12", "T-16": "talla_t16", "EX CH": "talla_ex_ch",
            "CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX G": "talla_ex_g"
        }

        for i_f, folio_actual in enumerate(folios_a_usar):
            estampados_del_folio = est_por_folio[i_f] if i_f < len(est_por_folio) else []
            estampados_data = [{"nombre": est, "filas": []} for est in estampados_del_folio]
            modelo_folio_nube = f"{modelo} {str(folio_actual).zfill(2)}"
            
            for fila_corte in datos_corte:
                c = fila_corte["color"]
                reparto_por_talla = {t: [] for t in tallas_usadas}
                for t in tallas_usadas:
                    total_corte = fila_corte["totales_talla"][t]
                    total_folio = total_corte // num_folios
                    base = total_folio // 4
                    sobra = total_folio % 4
                    for i_e in range(4):
                        asignado = base + 1 if i_e < sobra else base
                        reparto_por_talla[t].append(asignado)

                for i_e, est_dict in enumerate(estampados_data):
                    fila_inv = {"color": c, "tallas": {}}
                    for t in tallas_usadas:
                        fila_inv["tallas"][t] = reparto_por_talla[t][i_e]
                    est_dict["filas"].append(fila_inv)

            datos_inventario_global.append({"folio": str(folio_actual).zfill(2), "estampados": estampados_data})
            
            for est_item in estampados_data:
                est_nombre = est_item["nombre"]
                for fila in est_item["filas"]:
                    c = fila["color"]
                    cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est_nombre, c))
                    res = cursor.fetchone()
                    
                    v_stock = {"talla_t12": 0, "talla_t16": 0, "talla_ex_ch": 0, "talla_ch": 0, "talla_m": 0, "talla_g": 0, "talla_ex_g": 0}
                    for t in tallas_usadas:
                        cant = fila["tallas"][t]
                        if cant > 0:
                            col_sql = mapa_bd.get(t, "talla_ex_g")
                            v_stock[col_sql] += cant
                            total_ingresado += cant

                    if res:
                        cursor.execute("""
                            UPDATE panel_stock 
                            SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, 
                                talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s 
                            WHERE id=%s
                        """, (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                        panel_id = res['id']
                    else:
                        cursor.execute("""
                            INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')
                        """, (modelo_folio_nube, est_nombre, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
                        panel_id = cursor.lastrowid

                    for t in tallas_usadas:
                        if fila["tallas"][t] > 0:
                            cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo_folio_nube, est_nombre, c, t))
                            if not cursor.fetchone():
                                cod = generar_codigo_13_nube(cursor, modelo_folio_nube, est_nombre, c, t)
                                cursor.execute("INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, 250.0, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                               (cod, modelo_folio_nube, est_nombre, c, t, panel_id))
                                               
        if total_ingresado > 0:
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'HOJA MADRE APP', 'SISTEMA')", 
                           (modelo_folio_nube, total_ingresado, fecha_txt))

        siguiente_folio = folios_a_usar[-1] + 1
        cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (siguiente_folio, modelo))
        db.commit()
        cursor.close()
        db.close()

        # 🔥 CONSTRUCCIÓN DEL PDF (ESTILO IDÉNTICO A LA PC) 🔥
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=40, bottomMargin=15)
        elementos = []
        estilos = getSampleStyleSheet()
        estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)
        
        if imagen_blob:
            b_io = io.BytesIO(imagen_blob)
            w_img = 220 if "2500" in formato_img else 130
            logo = RLImage(b_io, width=w_img, height=130, kind='proportional')
        else: logo = ""
        
        t_header_corte = Table([
            [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", estilos['Normal']), 
             Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
             Paragraph(f"<font color='red'><b>FOLIO:</b> {str_folios}</font>", ParagraphStyle(name='hr', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=12))],
            [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
        ], colWidths=[185, 185, 185], rowHeights=[20, 135]) 
        t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
        
        elementos.append(t_header_corte)
        elementos.append(Spacer(1, 10)) 

        tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
        data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
        
        for c_dict in cuerpos_del_modelo:
            nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
            if 'x2' in tipo_mult:
                txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
            elif 'A/B' in tipo_mult:
                txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
            else:
                txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""

            fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
            for t in tallas_todas: fila.append(f_calc(int(cuerpos_actuales.get(t, 0))))
            data_t1.append(fila)

        t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60])
        t1.setStyle(TableStyle([
            ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
            ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#f8fafc")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ]))

        data_t2 = [["N° ROLLO\n(Marcado)", "COLOR", "N° LIENZO"] + tallas_todas + ["TOTAL"]]
        marcados = []; current_marcado = []; current_sum = 0
        for d in datos_corte:
            if current_sum + d["lienzos"] > 80 and current_sum > 0:
                marcados.append(current_marcado); current_marcado = [d]; current_sum = d["lienzos"]
            else:
                current_marcado.append(d); current_sum += d["lienzos"]
        if current_marcado: marcados.append(current_marcado)

        suma_lienzos = 0; suma_tallas = {t: 0 for t in tallas_todas}; gran_total = 0
        row_idx = 1
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
                    val = d["totales_talla"].get(t, 0)
                    fila.append(str(val) if val > 0 else "")
                    suma_tallas[t] += val
                fila.append(str(d["gran_total"]))
                gran_total += d["gran_total"]
                data_t2.append(fila)
                row_idx += 1
            if len(marcado_data) > 1: estilos_tabla2.append(('SPAN', (0, start_row), (0, row_idx - 1)))

        fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
        for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
        fila_final.append(str(gran_total))
        data_t2.append(fila_final)
        estilos_tabla2.extend([
            ('SPAN', (0, row_idx), (1, row_idx)), ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#e2e8f0")), 
            ('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black), ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
        ])
        t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45])
        t2.setStyle(TableStyle(estilos_tabla2))

        tablas_encogibles = KeepInFrame(
            maxWidth=540, maxHeight=500, 
            content=[t1, Spacer(1, 15), Paragraph("<b>FECHA:</b> _________________", estilos['Normal']), Spacer(1, 10), t2], 
            mode='shrink', vAlign='TOP'
        )
        elementos.append(tablas_encogibles)
        elementos.append(PageBreak())

        # 🔥 INVENTARIOS (COMPRIMIBLES Y ESTÁTICOS) 🔥
        t_title = ParagraphStyle('titulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
        MAX_COLORS = 10
        color_chunks = [colores[i:i + MAX_COLORS] for i in range(0, len(colores), MAX_COLORS)]

        for i_f, data_folio in enumerate(datos_inventario_global):
            folio = data_folio["folio"]; estampados_data = data_folio["estampados"]

            t_header_inv = Table([
                [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                 Paragraph(f"<b>FOLIO:</b> {folio}<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
            ], colWidths=[285, 285])

            for i_e, est_item in enumerate(estampados_data):
                for chunk_idx, color_chunk in enumerate(color_chunks):
                    
                    est_nombre = est_item["nombre"]; filas_colores = est_item["filas"]
                    
                    title_text = f"<font color='#3b82f6'>▐</font> <b>ESTAMPADO {i_e + 1}: {est_nombre}</b>"
                    if len(color_chunks) > 1: title_text += f" (Parte {chunk_idx + 1})"
                    title = Paragraph(title_text, t_title)
                    
                    num_colors_chunk = len(color_chunk)
                    if num_colors_chunk <= 6: f_size = 8; pad = 4
                    elif num_colors_chunk <= 10: f_size = 7.5; pad = 3
                    else: f_size = 6.5; pad = 1
                    
                    style_color_inv_dyn = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                    
                    w_color = 65; w_talla = 22; espacio_total_tabla = 285 
                    w_vacio = max(15, (espacio_total_tabla - w_color - (w_talla * len(tallas_usadas))) / 2.0) 
                    anchos_columnas = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_usadas)
                    
                    data_t = [["COLOR", "", ""] + tallas_usadas]
                    totales_tallas = {t: 0 for t in tallas_usadas}

                    for c in color_chunk:
                        row_data = next((r for r in filas_colores if r["color"] == c), None)
                        if row_data:
                            r_row = [Paragraph(c, style_color_inv_dyn), "", ""]
                            for t in tallas_usadas:
                                cant = row_data["tallas"].get(t, 0)
                                r_row.append(str(cant) if cant > 0 else "")
                                totales_tallas[t] += cant
                            data_t.append(r_row)

                    f_tot = ["TOTAL", "", ""]
                    for t in tallas_usadas: f_tot.append(str(totales_tallas[t]))
                    data_t.append(f_tot)

                    t_inv = Table(data_t, colWidths=anchos_columnas)
                    t_inv.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                        ('SPAN', (0, -1), (2, -1)), ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), f_size), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")), 
                        ('BOTTOMPADDING', (0,0), (-1,-1), pad), ('TOPPADDING', (0,0), (-1,-1), pad),
                    ]))
                    
                    wrapper_table = Table([[title], [Spacer(1, 4)], [t_inv]], colWidths=[285])
                    wrapper_table.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0)]))
                    
                    grid_data = [[wrapper_table, ""], [Spacer(1, 15), Spacer(1, 15)], ["", ""]]
                    t_grid = Table(grid_data, colWidths=[291, 291])
                    t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                    
                    firmas_data = [
                        [" ", " "], [" ", " "], [" ", " "],
                        ["___________________________________", "___________________________________"],
                        ["DOBLADO", "ALMACÉN"],
                        ["JACQUELINE TLATELPA XOLALTENCO", "DULCE EVELIN POTRERO RODRIGUEZ"]
                    ]
                    t_firmas = Table(firmas_data, colWidths=[291, 291])
                    t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                    
                    t_master = Table([[t_header_inv], [t_grid], [t_firmas]], colWidths=[582], rowHeights=[60, 490, 130]) 
                    t_master.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,2), (0,2), 'BOTTOM'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                    ]))
                    elementos.append(t_master)
                    if chunk_idx < len(color_chunks) - 1 or i_e < len(estampados_data) - 1 or i_f < len(datos_inventario_global) - 1:
                        elementos.append(PageBreak())

        doc.build(elementos)
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Produccion_{str_folios}.pdf"})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==============================================================================
# HOJA MADRE PEDIDOS (OPTIMIZADA)
# ==============================================================================
@app.route('/api/app/magia_pedido', methods=['POST'])
def api_magia_pedido():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    
    req = request.get_json()
    modelo = req.get('modelo', '').strip().upper()
    estampados = req.get('estampados', [])
    if not estampados: estampados = ["SIN ESTAMPADO"]
    pedidos_app = req.get('pedidos', {}) 
    folio_arranque = int(req.get('folio_arranque', 1))
    
    fecha_txt = datetime.datetime.now().strftime("%d/%m/%y")

    try:
        db = conectar_bd()
        cursor = db.cursor(dictionary=True)

        tallas_activas = set(); colores_activos = set()
        for c, t_data in pedidos_app.items():
            for t, cant in t_data.items():
                if cant > 0: tallas_activas.add(t); colores_activos.add(c)
        tallas_activas = list(tallas_activas); colores_activos = list(colores_activos)
        orden_tallas = {"T-12":1, "T-16":2, "EX CH":3, "CH":4, "M":5, "G":6, "EX G":7}
        tallas_activas.sort(key=lambda x: orden_tallas.get(x, 99))

        def total_pedido_grupo(grupo):
            return sum(t_data.get(t, 0) for c, t_data in pedidos_app.items() for t in grupo)

        def calcular_desperdicio(grupo_tallas):
            best_waste = float('inf'); best_lienzos_total = float('inf')
            best_cuerpos = {}; best_lienzos_color = {}
            def get_combos(n, current_sum=0):
                if n == 1: return [[i] for i in range(1, 7 - current_sum)]
                combos = []
                for i in range(1, 7 - current_sum - (n-1) + 1):
                    for rest in get_combos(n-1, current_sum + i): combos.append([i] + rest)
                return combos
                
            for combo in get_combos(len(grupo_tallas)):
                cuerpos = {grupo_tallas[i]: combo[i] for i in range(len(grupo_tallas))}
                lienzos_color = {}; waste = 0; tot_l = 0
                for c, peds in pedidos_app.items():
                    req_lienzos = max((math.ceil(peds.get(t, 0) / cuerpos[t]) for t in grupo_tallas if peds.get(t, 0) > 0), default=0)
                    lienzos_color[c] = req_lienzos; tot_l += req_lienzos
                    for t in grupo_tallas: waste += (req_lienzos * cuerpos[t]) - peds.get(t, 0)
                if tot_l < best_lienzos_total or (tot_l == best_lienzos_total and waste < best_waste):
                    best_lienzos_total = tot_l; best_waste = waste; best_cuerpos = cuerpos; best_lienzos_color = lienzos_color
            return best_waste, best_lienzos_total, best_cuerpos, best_lienzos_color

        def evaluar_grupo_de_3(grupo_3):
            w_all, l_all, c_all, lc_all = calcular_desperdicio(grupo_3)
            tot_ped = total_pedido_grupo(grupo_3)
            if tot_ped <= 30: return [(grupo_3, c_all, lc_all)]
            if w_all > (tot_ped * 0.50):
                best_split_lienzos = float('inf'); best_split_waste = float('inf'); best_split = None
                for i in range(3):
                    single = [grupo_3[i]]; pair = [grupo_3[j] for j in range(3) if j != i]
                    ws, ls, cs, lcs = calcular_desperdicio(single)
                    wp, lp, cp, lcp = calcular_desperdicio(pair)
                    if (ls + lp) < best_split_lienzos or ((ls + lp) == best_split_lienzos and (ws + wp) < best_split_waste):
                        best_split_lienzos = ls + lp; best_split_waste = ws + wp; best_split = [(single, cs, lcs), (pair, cp, lcp)]
                if best_split_lienzos < l_all or (best_split_lienzos == l_all and best_split_waste < w_all): return best_split
            return [(grupo_3, c_all, lc_all)]

        particiones = []; n_tallas = len(tallas_activas)
        if n_tallas <= 2: w, tl, c, l = calcular_desperdicio(tallas_activas); particiones.append((tallas_activas, c, l))
        elif n_tallas == 3: particiones.extend(evaluar_grupo_de_3(tallas_activas))
        elif n_tallas == 4:
            g1, g2 = tallas_activas[0:2], tallas_activas[2:4]
            w1, tl1, c1, l1 = calcular_desperdicio(g1); particiones.append((g1, c1, l1))
            w2, tl2, c2, l2 = calcular_desperdicio(g2); particiones.append((g2, c2, l2))
        elif n_tallas == 5:
            particiones.extend(evaluar_grupo_de_3(tallas_activas[0:3]))
            w2, tl2, c2, l2 = calcular_desperdicio(tallas_activas[3:5]); particiones.append((tallas_activas[3:5], c2, l2))
        elif n_tallas == 6:
            for i in range(0, 6, 2): g = tallas_activas[i:i+2]; w, tl, c, l = calcular_desperdicio(g); particiones.append((g, c, l))
        elif n_tallas == 7:
            particiones.extend(evaluar_grupo_de_3(tallas_activas[0:3]))
            for i in range(3, 7, 2): g = tallas_activas[i:i+2]; w, tl, c, l = calcular_desperdicio(g); particiones.append((g, c, l))

        # 🔥 CARGAR IMÁGENES Y CUERPOS POR ID 🔥
        cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
        row_img = cursor.fetchone()
        imagen_blob = row_img['imagen_dibujo'] if row_img else None
        formato_img = row_img['formato_img'] if row_img else "1500x1900 (Frente)"

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
                    if row['id'] == id_g:
                        cuerpos_del_modelo.append(row)
                        break
        if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=40, bottomMargin=15)
        elementos = []
        estilos = getSampleStyleSheet()
        estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)

        if imagen_blob:
            b_io = io.BytesIO(imagen_blob)
            w_img = 220 if "2500" in formato_img else 130
            logo = RLImage(b_io, width=w_img, height=130, kind='proportional')
        else: logo = ""

        folio_actual = folio_arranque 
        talla_a_folio = {}

        # 1. DIBUJAR HOJAS DE CORTE
        for particion in particiones:
            grupo_tallas, cuerpos_dict, lienzos = particion
            for t in grupo_tallas: talla_a_folio[t] = str(folio_actual).zfill(2)
            
            t_header_corte = Table([
                [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", estilos['Normal']), 
                 Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
                 Paragraph(f"<font color='red'><b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)</font>", ParagraphStyle(name='hr', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=12))],
                [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
            ], colWidths=[185, 185, 185], rowHeights=[20, 135])
            t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
            
            tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
            data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
            
            for c_dict in cuerpos_del_modelo:
                nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
                if 'x2' in tipo_mult:
                    txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
                elif 'A/B' in tipo_mult:
                    txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
                else:
                    txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""

                fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
                for t in tallas_todas: fila.append(f_calc(cuerpos_dict.get(t, 0)))
                data_t1.append(fila)

            t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60])
            t1.setStyle(TableStyle([
                ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
                ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#fef3c7")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ]))

            data_t2 = [["N° ROLLO\n(Marcado)", "COLOR", "N° LIENZO"] + tallas_todas + ["TOTAL"]]
            suma_lienzos = 0; suma_tallas = {t: 0 for t in tallas_todas}; gran_total = 0; idx_color = 0
            for c, l_cant in lienzos.items():
                if l_cant == 0: continue
                fila = ["Marcado\n1" if idx_color == 0 else "", Paragraph(c, estilo_wrap), str(l_cant)]; suma_lienzos += l_cant
                for t in tallas_todas:
                    prod = l_cant * cuerpos_dict.get(t, 0)
                    fila.append(str(prod) if prod > 0 else ""); suma_tallas[t] += prod
                tot_fila = sum(l_cant * cuerpos_dict.get(tx, 0) for tx in grupo_tallas)
                fila.append(str(tot_fila)); gran_total += tot_fila; data_t2.append(fila); idx_color += 1

            fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
            for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
            fila_final.append(str(gran_total)); data_t2.append(fila_final)
            
            t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45])
            t2.setStyle(TableStyle([
                ('SPAN', (0, 1), (0, max(1, idx_color))), ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fef3c7")), 
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9), ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('SPAN', (0, -1), (1, -1)), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#fde68a")), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            ]))
            
            tablas_encogibles = KeepInFrame(
                maxWidth=540, maxHeight=500, 
                content=[t1, Spacer(1, 15), Paragraph("<b>FECHA:</b> _________________", estilos['Normal']), Spacer(1, 10), t2], 
                mode='shrink', vAlign='TOP'
            )
            elementos.append(t_header_corte)
            elementos.append(Spacer(1, 10))
            elementos.append(tablas_encogibles)
            elementos.append(PageBreak())

        # 2. CALCULAR INVENTARIO UNIFICADO
        total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
        for particion in particiones:
            grupo_tallas, cuerpos_dict, lienzos = particion
            for c, l_cant in lienzos.items():
                for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos_dict.get(t, 0)

        # 3. DIBUJAR INVENTARIOS UNIFICADOS (CHUNKING)
        t_title = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
        
        num_est = len(estampados)
        total_ingresado_nube = 0
        mapa_bd = {"CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX CH": "talla_ex_ch", "XG": "talla_ex_g", "EX G": "talla_ex_g", "T-12": "talla_t12", "T-16": "talla_t16"}

        MAX_COLORS = 10
        color_chunks = [colores_activos[i:i + MAX_COLORS] for i in range(0, len(colores_activos), MAX_COLORS)]

        for i_e, est in enumerate(estampados):
            for chunk_idx, color_chunk in enumerate(color_chunks):
                
                t_header_inv = Table([
                    [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                     Paragraph(f"<b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
                ], colWidths=[285, 285])
                
                title_text = f"<font color='#d97706'>▐</font> <b>ESTAMPADO {i_e + 1}: {est}</b>"
                if len(color_chunks) > 1: title_text += f" (Parte {chunk_idx + 1})"
                title = Paragraph(title_text, ParagraphStyle('titulo_grande', fontSize=10, fontName='Helvetica-Bold'))
                
                num_colors_chunk = len(color_chunk)
                if num_colors_chunk <= 6: f_size = 8; pad = 4
                elif num_colors_chunk <= 10: f_size = 7.5; pad = 3
                else: f_size = 6.5; pad = 1
                    
                style_color_inv = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                
                w_color = 65; w_talla = 22; espacio_total_tabla = 285 
                w_vacio = max(15, (espacio_total_tabla - w_color - (w_talla * len(tallas_activas))) / 2.0) 
                anchos = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_activas)
                
                data_tot = [["COLOR", "", ""] + tallas_activas]; sum_tot = {t: 0 for t in tallas_activas}
                data_ped = [["COLOR", "", ""] + tallas_activas]; sum_ped = {t: 0 for t in tallas_activas}
                data_sob = [["COLOR", "", ""] + tallas_activas]; sum_sob = {t: 0 for t in tallas_activas}
                
                for c in color_chunk:
                    r_tot = [Paragraph(c, style_color_inv), "", ""]; r_ped = [Paragraph(c, style_color_inv), "", ""]; r_sob = [Paragraph(c, style_color_inv), "", ""]
                    for t in tallas_activas:
                        prod = total_prod[c][t]
                        ped = pedidos_app.get(c, {}).get(t, 0)
                        
                        base_prod = prod // num_est; sobra_prod = prod % num_est
                        prod_est = base_prod + 1 if i_e < sobra_prod else base_prod
                        
                        base_ped = ped // num_est; sobra_ped = ped % num_est
                        ped_est = base_ped + 1 if i_e < sobra_ped else base_ped
                        
                        sob_est = max(0, prod_est - ped_est)
                        
                        r_tot.append(str(prod_est) if prod_est>0 else "-")
                        r_ped.append(str(ped_est) if ped_est>0 else "-")
                        r_sob.append(str(sob_est) if sob_est>0 else "-")
                        
                        sum_tot[t] += prod_est; sum_ped[t] += ped_est; sum_sob[t] += sob_est
                        
                        # INYECCIÓN A LA NUBE (SOLO SOBRANTES)
                        if sob_est > 0:
                            modelo_folio_nube = f"{modelo} {str(folio_arranque).zfill(2)}" 
                            col_sql = mapa_bd.get(t, "talla_ex_g")
                            
                            cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est, c))
                            res = cursor.fetchone()
                            
                            v_stock = {"talla_t12":0, "talla_t16":0, "talla_ex_ch":0, "talla_ch":0, "talla_m":0, "talla_g":0, "talla_ex_g":0}
                            v_stock[col_sql] = sob_est
                            
                            if res:
                                cursor.execute("""
                                    UPDATE panel_stock 
                                    SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, 
                                        talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s 
                                    WHERE id=%s
                                """, (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                                panel_id = res['id']
                            else:
                                cursor.execute("""
                                    INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')
                                """, (modelo_folio_nube, est, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
                                panel_id = cursor.lastrowid

                            cursor.execute("SELECT codigo_barras FROM inventario WHERE modelo=%s AND estampado=%s AND color=%s AND talla=%s LIMIT 1", (modelo_folio_nube, est, c, t))
                            if not cursor.fetchone():
                                cod = generar_codigo_13_nube(cursor, modelo_folio_nube, est, c, t)
                                cursor.execute("INSERT INTO inventario (codigo_barras, modelo, estampado, color, talla, precio, panel_stock_id, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, 250.0, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                               (cod, modelo_folio_nube, est, c, t, panel_id))
                            total_ingresado_nube += sob_est
                    
                    data_tot.append(r_tot); data_ped.append(r_ped); data_sob.append(r_sob)
                
                data_tot.append(["SUMA", "", ""] + [str(sum_tot[t]) for t in tallas_activas])
                data_ped.append(["SUMA", "", ""] + [str(sum_ped[t]) for t in tallas_activas])
                data_sob.append(["SUMA", "", ""] + [str(sum_sob[t]) for t in tallas_activas])

                style_tabla_3 = TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                    ('SPAN', (0, -1), (2, -1)), ('SPAN', (0, 0), (2, 0)),
                    ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), f_size), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
                    ('BOTTOMPADDING', (0,0), (-1,-1), pad), ('TOPPADDING', (0,0), (-1,-1), pad),
                ])
                t_tot = Table(data_tot, colWidths=anchos); t_tot.setStyle(style_tabla_3)
                t_ped = Table(data_ped, colWidths=anchos); t_ped.setStyle(style_tabla_3)
                t_sob = Table(data_sob, colWidths=anchos); t_sob.setStyle(style_tabla_3)

                wrap_tot = Table([[Paragraph("<font color='#3b82f6'>1. TOTAL PRODUCIDO</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_tot]])
                wrap_ped = Table([[Paragraph("<font color='#16a34a'>2. PEDIDO CLIENTE</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_ped]])
                wrap_sob = Table([[Paragraph("<font color='#e63946'>3. A NUBE (SOBRANTE)</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_sob]])

                grid_data = [
                    [wrap_tot, wrap_ped],
                    [Spacer(1, 15), Spacer(1, 15)],
                    [wrap_sob, ""]
                ]
                t_grid = Table(grid_data, colWidths=[291, 291])
                t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                
                firmas_data = [
                    [" ", " "], [" ", " "], [" ", " "],
                    ["___________________________________", "___________________________________"],
                    ["DOBLADO", "ALMACÉN"],
                    ["JACQUELINE TLATELPA XOLALTENCO", "DULCE EVELIN POTRERO RODRIGUEZ"]
                ]
                t_firmas = Table(firmas_data, colWidths=[291, 291])
                t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                
                wrap_t_grid = KeepInFrame(maxWidth=582, maxHeight=490, content=[title, Spacer(1,8), t_grid], mode='shrink', vAlign='TOP')
                t_master = Table([[t_header_inv], [wrap_t_grid], [t_firmas]], colWidths=[582], rowHeights=[60, 490, 130]) 
                t_master.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,2), (0,2), 'BOTTOM'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                ]))
                elementos.append(t_master)
                if chunk_idx < len(color_chunks) - 1 or i_e < len(estampados) - 1:
                    elementos.append(PageBreak())

        if total_ingresado_nube > 0:
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE (SOBRANTES)', 'SISTEMA')", 
                           (modelo, total_ingresado_nube, fecha_txt))
                           
        cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folio_arranque + 1, modelo))
        db.commit()
        cursor.close()
        db.close()

        doc.build(elementos)
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Pedido_{str(folio_arranque).zfill(2)}.pdf", 'siguiente_folio': folio_arranque + 1})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
