from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import os
import datetime

app = Flask(__name__)
app.secret_key = 'CLAVE_SECRETA_GACRUX_ALBERTO_2026'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

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
            host="mysql-292462b-gacrux-of.a.aivencloud.com", 
            port=19257,
            user="avnadmin",
            password="AVNS_lJSsblo1fLuMi6cA-yW",
            database="defaultdb"
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
        .input-group { position: relative; width: 100%; margin: 8px 0; }
        input { width: 100%; padding: 12px; border: 1px solid #333; background: #26262b; color: white; border-radius: 4px; box-sizing: border-box; font-size: 1rem; }
        input:focus { border-color: #1e3a8a; outline: none; }
        .input-group input { padding-right: 45px; }
        .btn-ojo { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #888; cursor: pointer; font-size: 1.1rem; padding: 5px; }
        button[type="submit"] { width: 100%; padding: 12px; background: #1e3a8a; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; margin-top: 15px; font-size: 1rem; text-transform: uppercase; }
        button[type="submit"]:hover { background: #1d4ed8; }
        .error { color: #ff4a4a; font-size: 0.9rem; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>SISTEMA GACRUX</h2>
        <p>Control de Almacén en Línea</p>
        <form method="POST">
            <div class="input-group">
                <input type="text" name="usuario" placeholder="Usuario" required autocomplete="off">
            </div>
            <div class="input-group">
                <input type="password" id="password" name="password" placeholder="Contraseña" required>
                <button type="button" class="btn-ojo" onclick="toggleOjoWeb()">👁️</button>
            </div>
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
    <script>
        function toggleOjoWeb() {
            const labelPass = document.getElementById('password');
            const btnOjo = document.querySelector('.btn-ojo');
            if (labelPass.type === 'password') { labelPass.type = 'text'; btnOjo.style.color = '#1e3a8a'; } 
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GACRUX - Panel de Almacén</title>
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <style id="theme-style">
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
        
        header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 25px; padding: 15px 20px; background-color: var(--bg-card); border-radius: 6px; border-bottom: 3px solid #444444; gap: 15px; }
        .header-info { text-align: left; }
        .header-actions { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
        h2 { color: #ffffff; font-size: 1.6rem; letter-spacing: 1px; margin-bottom: 4px;}
        
        .theme-toggle { padding: 8px 12px; font-size: 0.85rem; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; background-color: #444444; color: white; width: 100%;}
        .logout-link { background-color: transparent; color: #ef233c; font-weight: bold; text-decoration: none; border: 1px solid #ef233c; padding: 6px 12px; border-radius: 4px; text-transform: uppercase; font-size: 0.85rem; text-align: center; width: 100%; display: block;}
        .logout-link:hover { background-color: #ef233c; color: white; }
        
        .container { max-width: 1100px; margin: 0 auto; }
        .seccion { background-color: var(--bg-card); padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h3 { margin-bottom: 15px; color: #ffffff; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input[type="text"] { width: 100%; padding: 12px; border-radius: 4px; border: 1px solid var(--input-border); font-size: 1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-color); }
        input[type="text"]:focus { border-color: #888888; outline: none; }
        
        .btn { padding: 14px; border-radius: 4px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; text-transform: uppercase; }
        .btn-full { width: 100%; }
        .btn-baja { background-color: #444444; border: 1px solid #555555; }
        .btn-camara { background-color: #1e3a8a; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 8px;}
        
        #contenedor-lector { position: relative; width: 100%; max-width: 500px; margin: 0 auto 15px auto; display: none; }
        #reader { width: 100%; border-radius: 8px; overflow: hidden; border: 2px solid #1e3a8a; background: black;}
        .contador-escaner { position: absolute; top: 10px; right: 10px; background-color: #ef233c; color: white; padding: 6px 15px; border-radius: 20px; font-weight: 900; font-size: 1.5rem; display: none; z-index: 999; box-shadow: 0 4px 10px rgba(0,0,0,0.6); border: 2px solid white; transition: transform 0.15s ease-out; }
        
        #controles-camara { display: none; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .btn-disparar { background-color: #2e7d32; flex-grow: 1; font-size: 1.1rem; }
        .btn-cerrar-cam { background-color: #7f1d1d; width: 35%; min-width: 120px; }
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
        .editable { cursor: pointer; background-color: rgba(30, 58, 138, 0.1); border-radius: 3px; position: relative; }
        .editable:hover { background-color: rgba(30, 58, 138, 0.3); color: #4ea8de; }
        .input-inline-edit { width: 50px; text-align: center; background: #333; color: white; border: 1px solid #1e3a8a; border-radius: 3px; font-weight: bold; font-size: 1rem; padding: 2px 0; }
        .stock-cero { color: #3d3d3d !important; font-weight: normal; }
        .fila-totales-excel { width: 100%; padding: 8px 15px; background-color: var(--bg-block); font-size: 0.9rem; font-weight: bold; color: #e63946; border-top: 1px dashed #e63946; display: flex; justify-content: space-between; flex-wrap: wrap; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-info">
                <h2>SISTEMA GACRUX</h2>
                <p style="font-size: 0.85rem; color: var(--subtext-color);">Control de Inventario Centralizado</p>
                <div style="margin-top: 10px; font-size: 0.85rem;">
                    👤 SESIÓN: <strong>{{ empleado }}</strong><br>
                    🛡️ PUESTO: <span style="color: #4ea8de; font-weight: bold;">{{ puesto }}</span>
                </div>
            </div>
            <div class="header-actions">
                <button class="theme-toggle" onclick="alternarTemaWeb()">CAMBIAR TEMA ☀️</button>
                <a class="logout-link" href="/logout">CERRAR SESIÓN 🚪</a>
            </div>
        </header>

        <div class="seccion">
            <h3>Ajuste Rápido de Almacén</h3>
            <button class="btn btn-full btn-camara" id="btn-encender-cam" onclick="encenderScanner()"><span>📷</span> ENCENDER VISOR DE CÁMARA</button>
            
            <div id="contenedor-lector">
                <div id="reader"></div>
                <div id="badge-contador" class="contador-escaner">x1</div>
            </div>
            
            <div id="controles-camara">
                <button class="btn btn-cerrar-cam" onclick="apagarScanner()">🔴 CERRAR</button>
                <button class="btn btn-disparar" id="btn-disparar" onclick="activarDisparo()">🎯 DISPARAR (LEER CÓDIGO)</button>
            </div>

            <input type="text" id="codigo_barras" placeholder="O escribe el código de barras manualmente..." autocomplete="off">
            <button class="btn btn-full btn-baja" onclick="procesarBaja()">Descontar 1 Unidad</button>
            <div id="notificacion"></div>
        </div>

        <div class="seccion">
            <h3>Existencias en Tiempo Real</h3>
            <input type="text" id="busqueda" placeholder="🔍 Filtrar por modelo, estampado o color..." onkeyup="buscarPrenda()">
            <div id="resultado_busqueda"></div>
        </div>
    </div>

    <script>
        let modoOscuroActivo = true;
        const esAdmin = "{{ es_admin }}" === "True"; 
        let html5QrCode = null;
        let scannerActivoParaLeer = false; 
        let ultimoCodigoEscaneado = "";
        let contadorMismoCodigo = 0;
        let motorAudioGlobal = null;

        function hacerBeep() {
            try {
                let AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return; 
                if (!motorAudioGlobal) { motorAudioGlobal = new AudioContext(); }
                if (motorAudioGlobal.state === 'suspended') { motorAudioGlobal.resume(); }
                let osc = motorAudioGlobal.createOscillator();
                let gain = motorAudioGlobal.createGain();
                osc.connect(gain); gain.connect(motorAudioGlobal.destination);
                osc.type = "square"; osc.frequency.setValueAtTime(850, motorAudioGlobal.currentTime);
                gain.gain.setValueAtTime(0.1, motorAudioGlobal.currentTime);
                osc.start(); osc.stop(motorAudioGlobal.currentTime + 0.15); 
            } catch(e) {}
        }

        function encenderScanner() {
            const contenedorLector = document.getElementById('contenedor-lector');
            const btnEncender = document.getElementById('btn-encender-cam');
            const controlesCam = document.getElementById('controles-camara');
            const inputCodigo = document.getElementById('codigo_barras');
            
            inputCodigo.setAttribute('readonly', 'true');
            document.activeElement.blur(); 
            contenedorLector.style.display = 'block'; 
            btnEncender.style.display = 'none';
            controlesCam.style.display = 'flex';
            
            ultimoCodigoEscaneado = ""; contadorMismoCodigo = 0;
            document.getElementById('badge-contador').style.display = 'none';
            
            html5QrCode = new Html5Qrcode("reader");
            const config = { fps: 15, qrbox: { width: 250, height: 120 } }; 
            
            html5QrCode.start({ facingMode: "environment" }, config, 
                (textoDecodificado) => {
                    if (scannerActivoParaLeer) {
                        scannerActivoParaLeer = false; 
                        hacerBeep(); 
                        if (textoDecodificado === ultimoCodigoEscaneado) { contadorMismoCodigo++; } 
                        else { ultimoCodigoEscaneado = textoDecodificado; contadorMismoCodigo = 1; }
                        
                        const badge = document.getElementById('badge-contador');
                        badge.style.display = 'block'; badge.innerText = "x" + contadorMismoCodigo;
                        badge.style.transform = "scale(1.3)"; setTimeout(() => { badge.style.transform = "scale(1)"; }, 150);
                        
                        inputCodigo.value = textoDecodificado;
                        const btnDisparar = document.getElementById('btn-disparar');
                        btnDisparar.innerHTML = "🎯 DISPARAR (LEER CÓDIGO)"; btnDisparar.style.backgroundColor = "#2e7d32";
                        procesarBaja();
                    }
                },
                (errorMensaje) => {}
            ).catch(err => {
                alert("Error al iniciar la cámara. Verifica permisos.");
                apagarScanner();
            });
        }

        function activarDisparo() {
            if (!html5QrCode) return;
            scannerActivoParaLeer = true; 
            const btnDisparar = document.getElementById('btn-disparar');
            btnDisparar.innerHTML = "👀 ENFOCA EL CÓDIGO AHORA..."; btnDisparar.style.backgroundColor = "#d08c00"; 
        }

        function apagarScanner() {
            const contenedorLector = document.getElementById('contenedor-lector');
            const btnEncender = document.getElementById('btn-encender-cam');
            const controlesCam = document.getElementById('controles-camara');
            const inputCodigo = document.getElementById('codigo_barras');
            inputCodigo.removeAttribute('readonly');
            
            if (html5QrCode) {
                html5QrCode.stop().then(() => {
                    contenedorLector.style.display = 'none'; controlesCam.style.display = 'none'; btnEncender.style.display = 'flex';
                    scannerActivoParaLeer = false; ultimoCodigoEscaneado = ""; contadorMismoCodigo = 0;
                    document.getElementById('badge-contador').style.display = 'none';
                    const btnDisparar = document.getElementById('btn-disparar');
                    btnDisparar.innerHTML = "🎯 DISPARAR (LEER CÓDIGO)"; btnDisparar.style.backgroundColor = "#2e7d32";
                }).catch(err => {});
            }
        }

        function alternarTemaWeb() {
            modoOscuroActivo = !modoOscuroActivo;
            const root = document.documentElement;
            const btn = document.querySelector('.theme-toggle');
            if (modoOscuroActivo) {
                btn.innerText = "CAMBIAR TEMA ☀️";
                root.style.setProperty('--bg-body', '#1a1a1a'); root.style.setProperty('--bg-card', '#262626');
                root.style.setProperty('--bg-block', '#1f1f1f'); root.style.setProperty('--bg-table', '#161616');
                root.style.setProperty('--bg-th', '#282828'); root.style.setProperty('--text-color', '#ffffff');
                root.style.setProperty('--subtext-color', '#777777'); root.style.setProperty('--border-color', '#333333');
                root.style.setProperty('--input-bg', '#333333'); root.style.setProperty('--input-border', '#404040');
            } else {
                btn.innerText = "CAMBIAR TEMA 🌙";
                root.style.setProperty('--bg-body', '#f4f6f9'); root.style.setProperty('--bg-card', '#ffffff');
                root.style.setProperty('--bg-block', '#f8f9fa'); root.style.setProperty('--bg-table', '#ffffff');
                root.style.setProperty('--bg-th', '#e2e8f0'); root.style.setProperty('--text-color', '#000000');
                root.style.setProperty('--subtext-color', '#555555'); root.style.setProperty('--border-color', '#cbd5e1');
                root.style.setProperty('--input-bg', '#ffffff'); root.style.setProperty('--input-border', '#cbd5e1');
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
                    notif.style.color = '#4caf50'; notif.innerText = "COINCIDENCIA: " + data.msg;
                    buscarPrenda();
                } else {
                    notif.style.color = '#e63946'; notif.innerText = "ERROR: " + data.msg;
                }
                document.getElementById('codigo_barras').value = '';
                if (document.getElementById('contenedor-lector').style.display !== 'block') { document.getElementById('codigo_barras').focus(); }
            });
        }

        document.getElementById('codigo_barras').addEventListener('keypress', function(e) { if (e.key === 'Enter') { procesarBaja(); } });

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
                    if (data.status === 'ok') { buscarPrenda(); } 
                    else { alert("Error al inyectar cambio: " + data.msg); elemento.innerHTML = valorActual; }
                });
            }
            input.addEventListener('keypress', function(e) { if (e.key === 'Enter') { guardarCambioInmediato(); } });
            input.addEventListener('focusout', guardarCambioInmediato);
        }

        function buscarPrenda() {
            if (document.querySelector('.input-inline-edit')) return; 
            let query = document.getElementById('busqueda').value;
            fetch('/api/buscar?q=' + query)
            .then(res => res.json()).then(data => {
                let contenedor = document.getElementById('resultado_busqueda'); contenedor.innerHTML = '';
                let estructura = {};
                data.forEach(p => {
                    let mod = p.modelo.toUpperCase().trim(); let est = p.estampado.toUpperCase().trim(); 
                    if (!estructura[mod]) { estructura[mod] = {}; }
                    if (!estructura[mod][est]) { estructura[mod][est] = []; }
                    estructura[mod][est].push(p);
                });
                
                let esAzul = true;
                for (let mod in estructura) {
                    let totalLoteAcumulado = 0;
                    for (let est_k in estructura[mod]) { estructura[mod][est_k].forEach(p => { totalLoteAcumulado += (p.talla_ch + p.talla_m + p.talla_g + p.talla_eg); }); }
                    let claseColor = esAzul ? 'mod-azul' : 'mod-rojo';
                    let htmlBlock = `<div class="contenedor-modelo ${claseColor}"><div class="header-modelo-flex"><div class="titulo-modelo">MODELO: ${mod}</div><div class="total-modelo-top">TOTAL LOTE: ${totalLoteAcumulado} pzas</div></div>`;
                    
                    for (let est in estructura[mod]) {
                        let sumCH = 0, sumM = 0, sumG = 0, sumEG = 0;
                        estructura[mod][est].forEach(p => { sumCH += p.talla_ch; sumM += p.talla_m; sumG += p.talla_g; sumEG += p.talla_eg; });
                        htmlBlock += `<div class="bloque-estampado"><div class="titulo-estampado">${est}</div><table class="tabla-catalogo"><thead><tr><th style="text-align: left; padding-left: 15px;">Color</th>
                                            ${sumCH > 0 ? '<th style="width: 13%;">CH</th>' : ''}${sumM > 0 ? '<th style="width: 13%;">M</th>' : ''}
                                            ${sumG > 0 ? '<th style="width: 13%;">G</th>' : ''}${sumEG > 0 ? '<th style="width: 13%;">EG</th>' : ''}</tr></thead><tbody>`;
                        
                        estructura[mod][est].forEach(p => {
                            let claseEditable = esAdmin ? 'editable' : '';
                            htmlBlock += `<tr><td class="col-color">${p.color.toUpperCase()}</td>
                                    ${sumCH > 0 ? `<td class="stock-num ${claseEditable} ${p.talla_ch == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_ch')">${p.talla_ch}</td>` : ''}
                                    ${sumM > 0 ? `<td class="stock-num ${claseEditable} ${p.talla_m == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_m')">${p.talla_m}</td>` : ''}
                                    ${sumG > 0 ? `<td class="stock-num ${claseEditable} ${p.talla_g == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_g')">${p.talla_g}</td>` : ''}
                                    ${sumEG > 0 ? `<td class="stock-num ${claseEditable} ${p.talla_eg == 0 ? 'stock-cero' : ''}" onclick="activarEdicionCelda(this, ${p.id}, 'talla_eg')">${p.talla_eg}</td>` : ''}</tr>`;
                        });
                        
                        let sumaTotalTabla = sumCH + sumM + sumG + sumEG;
                        let partesTotales = [];
                        if (sumCH > 0) partesTotales.push(`CH: ${sumCH}`); if (sumM > 0) partesTotales.push(`M: ${sumM}`);
                        if (sumG > 0) partesTotales.push(`G: ${sumG}`); if (sumEG > 0) partesTotales.push(`EG: ${sumEG}`);
                        htmlBlock += `</tbody></table><div class="fila-totales-excel"><div>${partesTotales.join(' &nbsp;|&nbsp; ')}</div><div>SUMA TOTAL: ${sumaTotalTabla}</div></div></div>`;
                    }
                    htmlBlock += `</div>`; contenedor.innerHTML += htmlBlock; esAzul = !esAzul;
                }
            });
        }
        
        buscarPrenda();
        setInterval(function() { if(document.querySelector('.input-inline-edit')) { return; } buscarPrenda(); }, 2000);
    </script>
</body>
</html>
"""

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
            
            # Validación CASE-SENSITIVE en Python
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
    q = request.args.get('q', '').strip()
    db = conectar_bd()
    cursor = db.cursor(dictionary=True)
    if q: cursor.execute("SELECT * FROM panel_stock WHERE modelo LIKE %s OR estampado LIKE %s OR color LIKE %s ORDER BY modelo ASC, estampado ASC, color ASC", (f"%{q}%", f"%{q}%", f"%{q}%"))
    else: cursor.execute("SELECT * FROM panel_stock ORDER BY modelo ASC, estampado ASC, color ASC")
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
        
        # 🚀 RESTAURANDO LÓGICA CON ID INTERMEDIARIO:
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
                return jsonify({'status': 'error', 'msg': 'La prenda existe en inventario pero fue borrada del Catálogo Maestro.'})
                
    cursor.close(); db.close()
    return jsonify({'status': 'error', 'msg': 'Código de barras no válido o desconectado.'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
