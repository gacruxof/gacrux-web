import os
import datetime
import io
import base64
import json
import math
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Flowable
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
        password=os.environ.get("DB_PASSWORD"), 
        database=os.environ.get("DB_NAME", "defaultdb"),
        port=int(os.environ.get("DB_PORT", 19257))
    )

class UsuarioWeb(UserMixin):
    def __init__(self, id_user, usuario, nombre_real, rol_puesto):
        self.id = id_user; self.usuario = usuario; self.nombre_real = nombre_real; self.rol_puesto = rol_puesto

@login_manager.user_loader
def load_user(user_id):
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_real, rol_puesto FROM usuarios_gacrux WHERE id = %s", (user_id,))
        res = cursor.fetchone(); cursor.close(); db.close()
        if res: return UsuarioWeb(res['id'], res['usuario'], res['nombre_real'], res['rol_puesto'])
    except: pass
    return None

# ==============================================================================
# HTML WEB (PANEL DE ALMACÉN ACTUALIZADO A 7 TALLAS)
# ==============================================================================
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>GACRUX - Iniciar Sesión</title><style>
body { background-color: #121214; color: white; font-family: 'Segoe UI', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
.login-box { background: #1e1e24; padding: 35px 30px; border-radius: 12px; width: 90%; max-width: 360px; text-align: center; box-shadow: 0 8px 25px rgba(0,0,0,0.6); border-bottom: 4px solid #1e3a8a; }
h2 { font-size: 1.6rem; margin-bottom: 5px; letter-spacing: 1px; color: #89b4fa;} p { color: #a6adc8; font-size: 0.95rem; margin-bottom: 25px; }
.input-group { position: relative; width: 100%; margin: 12px 0; } input { width: 100%; padding: 14px; border: 1px solid #313244; background: #181825; color: white; border-radius: 6px; box-sizing: border-box; font-size: 1rem; }
input:focus { border-color: #89b4fa; outline: none; } .btn-ojo { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #888; cursor: pointer; font-size: 1.2rem; padding: 5px; }
button[type="submit"] { width: 100%; padding: 14px; background: #1e3a8a; border: none; color: white; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 15px; font-size: 1.1rem;}
.error { color: #f38ba8; font-size: 0.9rem; margin-top: 15px; font-weight: bold; background: rgba(243, 139, 168, 0.1); padding: 10px; border-radius: 6px;}
</style></head><body><div class="login-box"><h2>🚀 GACRUX</h2><p>Control de Almacén</p>
<form method="POST"><div class="input-group"><input type="text" name="usuario" placeholder="Usuario" required></div>
<div class="input-group"><input type="password" id="password" name="password" placeholder="Contraseña" required><button type="button" class="btn-ojo" onclick="t()">👁️</button></div>
<button type="submit">ENTRAR</button></form>
{% with messages = get_flashed_messages() %}{% if messages %}{% for msg in messages %}<div class="error">⚠️ {{ msg }}</div>{% endfor %}{% endif %}{% endwith %}
</div><script>function t() { const l = document.getElementById('password'); l.type = l.type === 'password' ? 'text' : 'password'; }</script></body></html>
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
        :root { --bg-body: #11111b; --bg-card: #1e1e2e; --bg-block: #181825; --bg-table: #1e1e2e; --bg-th: #313244; --text-main: #cdd6f4; --text-muted: #a6adc8; --border-color: #313244; --input-bg: #11111b; --input-border: #45475a; --primary: #1e3a8a; --danger: #e63946; }
        [data-theme="light"] { --bg-body: #f4f6f9; --bg-card: #ffffff; --bg-block: #f8f9fa; --bg-table: #ffffff; --bg-th: #e2e8f0; --text-main: #11111b; --text-muted: #555555; --border-color: #cbd5e1; --input-bg: #f8f9fa; --input-border: #cbd5e1; --primary: #1d4ed8; --danger: #dc2626; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; transition: background 0.3s, color 0.3s; }
        body { background-color: var(--bg-body); color: var(--text-main); padding: 10px 15px; padding-top: 75px;}
        header { position: fixed; top: 0; left: 0; right: 0; height: 60px; background-color: var(--bg-card); display: flex; justify-content: space-between; align-items: center; padding: 0 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); z-index: 1000; border-bottom: 2px solid var(--primary); }
        .logo-title { font-size: 1.4rem; font-weight: 900; color: var(--primary); letter-spacing: 1px;}
        .profile-menu { position: relative; display: inline-block; }
        .profile-btn { background: var(--bg-block); color: var(--text-main); font-size: 1.2rem; border: 1px solid var(--border-color); border-radius: 50%; width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; cursor: pointer; }
        .dropdown-content { display: none; position: absolute; right: 0; top: 50px; background-color: var(--bg-card); min-width: 220px; border-radius: 8px; box-shadow: 0 8px 20px rgba(0,0,0,0.5); border: 1px solid var(--border-color); overflow: hidden; }
        .dropdown-content.show { display: block; } .dropdown-header { padding: 15px; background: var(--bg-block); border-bottom: 1px solid var(--border-color); }
        .dropdown-content button, .dropdown-content a { width: 100%; padding: 12px 15px; text-decoration: none; display: block; text-align: left; background: none; border: none; font-size: 1rem; color: var(--text-main); font-weight: bold; cursor: pointer; }
        .logout-btn { color: var(--danger) !important; border-top: 1px solid var(--border-color) !important; }
        .container { max-width: 1000px; margin: 0 auto; } .seccion { background-color: var(--bg-card); padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid var(--border-color);}
        input[type="text"] { width: 100%; padding: 14px; border-radius: 6px; border: 2px solid var(--input-border); font-size: 1rem; margin-bottom: 15px; background-color: var(--input-bg); color: var(--text-main); }
        .btn { padding: 14px; border-radius: 6px; border: none; font-size: 1rem; font-weight: bold; cursor: pointer; color: white; width: 100%;}
        .btn-baja { background-color: var(--bg-block); border: 1px solid var(--border-color); color: var(--text-main);} .btn-camara { background-color: var(--primary); margin-bottom: 15px;}
        #contenedor-lector { display: none; margin-bottom: 15px; } #controles-camara { display: none; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .btn-disparar { background-color: #2e7d32; flex-grow: 1; } .btn-cerrar-cam { background-color: var(--danger); width: 35%; }
        .contenedor-modelo { background-color: var(--bg-card); border-radius: 8px; padding: 15px; margin-bottom: 30px; border: 1px solid var(--border-color); }
        .header-modelo-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 12px 15px; border-radius: 6px; color: #ffffff !important; }
        .mod-azul .header-modelo-flex { background-color: #1e3a8a; } .mod-rojo .header-modelo-flex { background-color: #7f1d1d; }
        .titulo-modelo { font-size: 1.2rem; font-weight: 900;} .total-modelo-top { font-size: 1rem; font-weight: bold; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;}
        .bloque-estampado { margin-bottom: 20px; background-color: var(--bg-block); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);}
        .titulo-estampado { font-size: 1.1rem; font-weight: 900; color: var(--text-main); margin-bottom: 10px; }
        .tabla-catalogo { width: 100%; border-collapse: collapse; text-align: center; background-color: var(--bg-table); border-radius: 6px; overflow: hidden;}
        .tabla-catalogo th { background-color: var(--bg-th); color: var(--text-muted); font-size: 0.8rem; font-weight: bold; padding: 8px 3px; border-bottom: 2px solid var(--border-color); }
        .tabla-catalogo td { padding: 8px 3px; font-size: 0.95rem; border-bottom: 1px solid var(--border-color); color: var(--text-main); font-weight: 600;}
        .col-color { text-align: left; padding-left: 10px !important; }
        .editable { cursor: pointer; position: relative; } .input-inline-edit { width: 35px; text-align: center; background: var(--input-bg); color: var(--text-main); border: 2px solid var(--primary); border-radius: 4px; font-weight: bold; padding: 4px 0;}
        .stock-cero { color: var(--text-muted) !important; font-weight: normal; opacity: 0.5;}
        .fila-totales-excel { width: 100%; padding: 10px; background-color: var(--bg-card); font-size: 0.9rem; font-weight: bold; color: var(--danger); border-top: 1px dashed var(--danger); display: flex; justify-content: space-between; flex-wrap: wrap; margin-top: 5px; border-radius: 4px;}
        .sticky-search { position: sticky; top: 60px; z-index: 100; background: var(--bg-body); padding: 10px 0; margin-bottom: 10px;}
    </style>
</head>
<body>
    <header>
        <div class="logo-title">🚀 GACRUX</div>
        <div class="profile-menu">
            <div class="profile-btn" onclick="toggleMenu()">👤</div>
            <div class="dropdown-content" id="menuDropdown">
                <div class="dropdown-header"><strong>{{ empleado }}</strong><span>{{ puesto }}</span></div>
                <button onclick="alternarTemaWeb()">🌗 Alternar Tema</button><a href="/logout" class="logout-btn">🚪 Cerrar Sesión</a>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="seccion">
            <h3>Ajuste Rápido de Almacén</h3>
            <button class="btn btn-camara" id="btn-encender-cam" onclick="encenderScanner()"><span>📷</span> INICIAR CÁMARA</button>
            <div id="contenedor-lector"><div id="reader"></div></div>
            <div id="controles-camara"><button class="btn btn-cerrar-cam" onclick="apagarScanner()">🔴 CERRAR</button><button class="btn btn-disparar" id="btn-disparar" onclick="activarDisparo()">🎯 DISPARAR</button></div>
            <input type="text" id="codigo_barras" placeholder="O escribe el código manualmente..." autocomplete="off">
            <button class="btn btn-baja" onclick="procesarBaja()">Descontar 1 Unidad</button>
            <div id="notificacion" style="text-align:center; font-weight:bold; margin-top:10px;"></div>
        </div>

        <div class="seccion">
            <h3>Catálogo de Existencias</h3>
            <div class="sticky-search"><input type="text" id="busqueda" placeholder="🔍 Filtrar por modelo o color..." autocomplete="off"></div>
            <div id="resultado_busqueda"></div>
        </div>
    </div>

    <script>
        function toggleMenu() { document.getElementById("menuDropdown").classList.toggle("show"); }
        function alternarTemaWeb() {
            const root = document.documentElement;
            if (root.getAttribute('data-theme') === 'light') { root.removeAttribute('data-theme'); localStorage.setItem('gacrux_theme', 'dark'); } 
            else { root.setAttribute('data-theme', 'light'); localStorage.setItem('gacrux_theme', 'light'); }
        }
        if(localStorage.getItem('gacrux_theme') === 'light') document.documentElement.setAttribute('data-theme', 'light');

        const esAdmin = "{{ es_admin }}" === "True"; 
        let html5QrCode = null; let scannerActivo = false; 

        function encenderScanner() {
            document.getElementById('contenedor-lector').style.display = 'block'; document.getElementById('btn-encender-cam').style.display = 'none'; document.getElementById('controles-camara').style.display = 'flex';
            html5QrCode = new Html5Qrcode("reader");
            html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 250, height: 120 } }, 
                (txt) => { if (scannerActivo) { scannerActivo = false; document.getElementById('codigo_barras').value = txt; document.getElementById('btn-disparar').style.backgroundColor = "#2e7d32"; procesarBaja(); } }
            ).catch(err => alert("Error al iniciar cámara."));
        }
        function activarDisparo() { if (!html5QrCode) return; scannerActivo = true; document.getElementById('btn-disparar').style.backgroundColor = "#d08c00"; }
        function apagarScanner() { if (html5QrCode) { html5QrCode.stop().then(() => { document.getElementById('contenedor-lector').style.display = 'none'; document.getElementById('controles-camara').style.display = 'none'; document.getElementById('btn-encender-cam').style.display = 'block'; }); } }
        function procesarBaja() {
            let codigo = document.getElementById('codigo_barras').value.trim(); if(!codigo) return;
            fetch('/api/baja', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({codigo: codigo}) })
            .then(res => res.json()).then(data => {
                let notif = document.getElementById('notificacion');
                if(data.status === 'ok') { notif.style.color = '#a6e3a1'; notif.innerText = "BAJA EXITOSA: " + data.msg; fetchCatalogo(); } 
                else { notif.style.color = '#f38ba8'; notif.innerText = "ERROR: " + data.msg; }
                document.getElementById('codigo_barras').value = '';
            });
        }

        let dataGlobal = []; let textoBusqueda = "";
        async function fetchCatalogo() { if (document.querySelector('.input-inline-edit')) return; try { let res = await fetch('/api/buscar'); dataGlobal = await res.json(); render(); } catch(e) {} }

        function render() {
            if (document.querySelector('.input-inline-edit')) return;
            let contenedor = document.getElementById('resultado_busqueda');
            let filtrados = dataGlobal.filter(p => !textoBusqueda || p.modelo.toLowerCase().includes(textoBusqueda.toLowerCase()) || p.color.toLowerCase().includes(textoBusqueda.toLowerCase()));
            if (filtrados.length === 0) { contenedor.innerHTML = "<p>No hay resultados.</p>"; return; }

            let ext = {};
            filtrados.forEach(p => {
                let m = p.modelo.toUpperCase().trim(); let e = p.estampado.toUpperCase().trim(); 
                if (!ext[m]) ext[m] = {}; if (!ext[m][e]) ext[m][e] = []; ext[m][e].push(p);
            });
            
            let html = ""; let esAzul = true;
            for (let mod in ext) {
                let totalMod = 0;
                for (let est_k in ext[mod]) { ext[mod][est_k].forEach(p => { totalMod += (p.talla_t12||0)+(p.talla_t16||0)+(p.talla_ex_ch||0)+(p.talla_ch||0)+(p.talla_m||0)+(p.talla_g||0)+(p.talla_ex_g||0); }); }
                html += `<div class="contenedor-modelo ${esAzul ? 'mod-azul' : 'mod-rojo'}"><div class="header-modelo-flex"><div class="titulo-modelo">${mod}</div><div class="total-modelo-top">${totalMod} PZAS</div></div>`;
                
                for (let est in ext[mod]) {
                    let sT12=0, sT16=0, sEXCH=0, sCH=0, sM=0, sG=0, sEXG=0;
                    ext[mod][est].forEach(p => { sT12+=p.talla_t12||0; sT16+=p.talla_t16||0; sEXCH+=p.talla_ex_ch||0; sCH+=p.talla_ch||0; sM+=p.talla_m||0; sG+=p.talla_g||0; sEXG+=p.talla_ex_g||0; });
                    
                    html += `<div class="bloque-estampado"><div class="titulo-estampado">${est}</div><table class="tabla-catalogo"><thead><tr><th class="col-color">COLOR</th>
                            ${sT12 > 0 ? '<th>T12</th>' : ''}${sT16 > 0 ? '<th>T16</th>' : ''}${sEXCH > 0 ? '<th>EX-CH</th>' : ''}
                            ${sCH > 0 ? '<th>CH</th>' : ''}${sM > 0 ? '<th>M</th>' : ''}${sG > 0 ? '<th>G</th>' : ''}${sEXG > 0 ? '<th>EX-G</th>' : ''}</tr></thead><tbody>`;
                    
                    ext[mod][est].forEach(p => {
                        let ce = esAdmin ? 'editable' : '';
                        html += `<tr><td class="col-color">${p.color.toUpperCase()}</td>
                            ${sT12 > 0 ? `<td class="${ce} ${(p.talla_t12||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_t12')">${p.talla_t12||0}</td>` : ''}
                            ${sT16 > 0 ? `<td class="${ce} ${(p.talla_t16||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_t16')">${p.talla_t16||0}</td>` : ''}
                            ${sEXCH > 0 ? `<td class="${ce} ${(p.talla_ex_ch||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_ex_ch')">${p.talla_ex_ch||0}</td>` : ''}
                            ${sCH > 0 ? `<td class="${ce} ${(p.talla_ch||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_ch')">${p.talla_ch||0}</td>` : ''}
                            ${sM > 0 ? `<td class="${ce} ${(p.talla_m||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_m')">${p.talla_m||0}</td>` : ''}
                            ${sG > 0 ? `<td class="${ce} ${(p.talla_g||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_g')">${p.talla_g||0}</td>` : ''}
                            ${sEXG > 0 ? `<td class="${ce} ${(p.talla_ex_g||0)==0 ? 'stock-cero':''}" onclick="ed(this,${p.id},'talla_ex_g')">${p.talla_ex_g||0}</td>` : ''}</tr>`;
                    });
                    let sumT = sT12+sT16+sEXCH+sCH+sM+sG+sEXG;
                    html += `</tbody></table><div class="fila-totales-excel"><div>TOTAL ESTAMPADO</div><div>${sumT}</div></div></div>`;
                }
                html += `</div>`; esAzul = !esAzul;
            }
            contenedor.innerHTML = html;
        }

        document.getElementById('busqueda').addEventListener('input', e => { textoBusqueda = e.target.value; render(); });

        function ed(el, id, col) {
            if (!esAdmin || el.querySelector('input')) return; 
            let val = el.innerText.trim(); el.innerHTML = `<input type="number" class="input-inline-edit" value="${val}" min="0">`;
            let input = el.querySelector('input'); input.focus(); input.select();
            function save() {
                let n = input.value.trim(); if(n==="" || isNaN(n) || parseInt(n)<0){ el.innerHTML = val; return; }
                if(parseInt(n) === parseInt(val)){ el.innerHTML = n; return; }
                fetch('/api/guardar_stock_web', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id, columna:col, valor:parseInt(n)}) })
                .then(r => r.json()).then(d => { if(d.status==='ok') fetchCatalogo(); else { alert("Error"); el.innerHTML=val; } });
            }
            input.addEventListener('keypress', e => { if(e.key==='Enter') save(); }); input.addEventListener('focusout', save);
        }
        setInterval(fetchCatalogo, 4000); fetchCatalogo(); 
    </script>
</body>
</html>
"""

class FirmasAbsolutas(Flowable):
    def wrap(self, availWidth, availHeight): return 0, 0
    def draw(self):
        self.canv.saveState()
        self.canv.translate(0, -self.canv._currentMatrix[5]) 
        self.canv.setFont("Helvetica-Bold", 9)
        self.canv.setFillColor(colors.black)
        self.canv.drawCentredString(180, 50, "___________________________________")
        self.canv.drawCentredString(180, 35, "DOBLADO")
        self.canv.drawCentredString(180, 20, "JACQUELINE TLATELPA XOLALTENCO")
        self.canv.drawCentredString(430, 50, "___________________________________")
        self.canv.drawCentredString(430, 35, "ALMACÉN")
        self.canv.drawCentredString(430, 20, "DULCE EVELIN POTRERO RODRIGUEZ")
        self.canv.restoreState()

def generar_codigo_13_nube(cursor, modelo, estampado, color, talla):
    cursor.execute("SELECT SUBSTRING(codigo_barras, 1, 5) AS mod_id FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo,))
    res_mod = cursor.fetchone()
    if res_mod and res_mod['mod_id'] and res_mod['mod_id'].isdigit(): mod_str = res_mod['mod_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 1, 5) AS UNSIGNED)) AS max_mod FROM inventario WHERE LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'")
        res_max_mod = cursor.fetchone()
        mod_str = f"{ (res_max_mod['max_mod'] if res_max_mod and res_max_mod['max_mod'] else 0) + 1:05d}"
    cursor.execute("SELECT SUBSTRING(codigo_barras, 6, 5) AS est_id FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado))
    res_est = cursor.fetchone()
    if res_est and res_est['est_id'] and res_est['est_id'].isdigit(): est_str = res_est['est_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 6, 5) AS UNSIGNED)) AS max_est FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo,))
        res_max_est = cursor.fetchone()
        est_str = f"{(res_max_est['max_est'] if res_max_est and res_max_est['max_est'] else 0) + 1:05d}"
    cursor.execute("SELECT SUBSTRING(codigo_barras, 11, 2) AS col_id FROM inventario WHERE modelo = %s AND estampado = %s AND color = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado, color))
    res_col = cursor.fetchone()
    if res_col and res_col['col_id'] and res_col['col_id'].isdigit(): col_str = res_col['col_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 11, 2) AS UNSIGNED)) AS max_col FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo, estampado))
        res_max_col = cursor.fetchone()
        col_str = f"{(res_max_col['max_col'] if res_max_col and res_max_col['max_col'] else 0) + 1:02d}"
    talla_id = {'CH': 1, 'M': 2, 'G': 3, 'XG': 4, 'EX G': 4, 'T-12': 5, 'T-16': 6, 'EG': 4}.get(talla.upper(), 9)
    return f"{mod_str}{est_str}{col_str}{talla_id:01d}"

@app.route('/api/app/receta/<modelo>', methods=['GET'])
def api_get_receta(modelo):
    try:
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        cursor.execute("CREATE TABLE IF NOT EXISTS recetas_madre (modelo VARCHAR(100) PRIMARY KEY, folio INT DEFAULT 1, colores TEXT, cuerpos TEXT)")
        cursor.execute("SELECT * FROM recetas_madre WHERE modelo = %s", (modelo,))
        res = cursor.fetchone(); cursor.close(); db.close()
        if res: return jsonify(res)
        return jsonify({})
    except: return jsonify({})

# ==============================================================================
# HOJA MADRE NORMAL
# ==============================================================================
@app.route('/api/app/magia_madre', methods=['POST'])
def api_magia_madre():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
    
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
        db = conectar_bd(); cursor = db.cursor(dictionary=True)
        datos_corte = []
        for c in colores:
            lienzos = int(datos_lienzo_color.get(c, 0))
            fila = {"color": c, "lienzos": lienzos, "totales_talla": {t: 0 for t in tallas_usadas}, "gran_total": 0}
            for t in tallas_usadas: 
                prendas = lienzos * int(cuerpos_actuales.get(t, 0))
                fila["totales_talla"][t] = prendas; fila["gran_total"] += prendas
            datos_corte.append(fila)
        datos_corte.sort(key=lambda x: x["gran_total"], reverse=True)

        num_folios = len(folios_a_usar)
        est_por_folio = [estampados[i:i + 4] for i in range(0, len(estampados), 4)]
        datos_inventario_global = []; total_ingresado = 0
        
        # 🔥 MAPA DE TALLAS ACTUALIZADO PARA INYECTAR CORRECTAMENTE 🔥
        mapa_bd = {"CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX CH": "talla_ex_ch", "XG": "talla_ex_g", "EX G": "talla_ex_g", "T-12": "talla_t12", "T-16": "talla_t16"}

        for i_f, folio_actual in enumerate(folios_a_usar):
            estampados_del_folio = est_por_folio[i_f] if i_f < len(est_por_folio) else []
            estampados_data = [{"nombre": est, "filas": []} for est in estampados_del_folio]
            modelo_folio_nube = f"{modelo} {str(folio_actual).zfill(2)}"
            
            for fila_corte in datos_corte:
                c = fila_corte["color"]
                reparto_por_talla = {t: [] for t in tallas_usadas}
                for t in tallas_usadas:
                    total_corte = fila_corte["totales_talla"][t]; total_folio = total_corte // num_folios
                    base = total_folio // 4; sobra = total_folio % 4
                    for i_e in range(4):
                        asignado = base + 1 if i_e < sobra else base
                        reparto_por_talla[t].append(asignado)

                for i_e, est_dict in enumerate(estampados_data):
                    fila_inv = {"color": c, "tallas": {}}
                    for t in tallas_usadas: fila_inv["tallas"][t] = reparto_por_talla[t][i_e]
                    est_dict["filas"].append(fila_inv)

            datos_inventario_global.append({"folio": str(folio_actual).zfill(2), "estampados": estampados_data})
            
            for est_item in estampados_data:
                est_nombre = est_item["nombre"]
                for fila in est_item["filas"]:
                    c = fila["color"]
                    cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est_nombre, c))
                    res = cursor.fetchone()
                    
                    v_stock = {"talla_t12":0, "talla_t16":0, "talla_ex_ch":0, "talla_ch":0, "talla_m":0, "talla_g":0, "talla_ex_g":0}
                    for t in tallas_usadas:
                        cant = fila["tallas"][t]
                        if cant > 0:
                            col_sql = mapa_bd.get(t, "talla_ex_g"); v_stock[col_sql] += cant; total_ingresado += cant

                    if res:
                        cursor.execute("UPDATE panel_stock SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s WHERE id=%s", 
                                       (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                        panel_id = res['id']
                    else:
                        cursor.execute("INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                       (modelo_folio_nube, est_nombre, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
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
        db.commit(); cursor.close(); db.close()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=20, rightMargin=20, topMargin=70, bottomMargin=80)
        elementos = []
        estilos = getSampleStyleSheet(); style_header_corte = ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)

        t_header_corte = Table([
            [Paragraph(f"<b>MODELO:</b> {modelo}", style_header_corte), Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), Paragraph(f"<b>FOLIO:</b> {str_folios}", style_header_corte)],
            [Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b> {fecha_txt}", estilos['Normal']), "", Paragraph("<b>FECHA DE ENTREGA:</b> _____________", ParagraphStyle(name='r', alignment=TA_RIGHT))]
        ], colWidths=[190, 190, 190])
        t_header_corte.setStyle(TableStyle([('ALIGN', (0,0), (0,0), 'LEFT'), ('ALIGN', (1,0), (1,0), 'CENTER'), ('ALIGN', (2,0), (2,0), 'RIGHT')]))
        elementos.append(t_header_corte); elementos.append(Spacer(1, 30)) 
        
        tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
        data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
        piezas_fijas = [("TRASERO", 1), ("DELANTERO", 1), ("MANGAS", "1A 1B"), ("GORROS", "1A 1B"), ("BOLSAS", 1), ("PRETINA", 1), ("PUÑOS", 2)]
        for nombre_p, mult in piezas_fijas:
            fila = [nombre_p, str(mult)]
            for t in tallas_todas:
                c = int(cuerpos_actuales.get(t, 0))
                if isinstance(mult, int): fila.append(str(c * mult) if c > 0 else "")
                else: fila.append(f"{c}A {c}B" if c > 0 else "")
            data_t1.append(fila)

        t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60])
        t1.setStyle(TableStyle([
            ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
            ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#f8fafc")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ]))
        elementos.append(t1); elementos.append(Spacer(1, 20)); elementos.append(Paragraph("<b>FECHA:</b> _________________", estilos['Normal'])); elementos.append(Spacer(1, 5))

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
                fila = [f"Marcado\n{num_m + 1}" if i == 0 else "", d["color"], str(d["lienzos"])]
                suma_lienzos += d["lienzos"]
                for t in tallas_todas:
                    fila.append(str(d["totales_talla"].get(t, 0)) if d["totales_talla"].get(t, 0) > 0 else "")
                    suma_tallas[t] += d["totales_talla"].get(t, 0)
                fila.append(str(d["gran_total"])); gran_total += d["gran_total"]; data_t2.append(fila); row_idx += 1
            if len(marcado_data) > 1: estilos_tabla2.append(('SPAN', (0, start_row), (0, row_idx - 1)))

        fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
        for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
        fila_final.append(str(gran_total)); data_t2.append(fila_final)
        
        estilos_tabla2.extend([
            ('SPAN', (0, row_idx), (1, row_idx)), ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#e2e8f0")), 
            ('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black), ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
        ])
        t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45])
        t2.setStyle(TableStyle(estilos_tabla2))
        elementos.append(t2); elementos.append(PageBreak())

        t_title = ParagraphStyle('titulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
        style_color_inv = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=7.5, leading=8)

        w_color = 65; w_talla = 22; espacio_total_tabla = 285 
        w_vacio = max(10, (espacio_total_tabla - w_color - (w_talla * len(tallas_usadas))) / 2.0) 
        anchos_columnas = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_usadas)

        for i_f, data_folio in enumerate(datos_inventario_global):
            folio = data_folio["folio"]; estampados_data = data_folio["estampados"]
            t_header = Table([
                [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                 Paragraph(f"<b>FOLIO:</b> {folio}<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
            ], colWidths=[285, 285])
            elementos.append(t_header); elementos.append(Spacer(1, 15))

            tablas_estampados = []
            for i_e, est_item in enumerate(estampados_data):
                est_nombre = est_item["nombre"]; filas_colores = est_item["filas"]
                title = Paragraph(f"<font color='#3b82f6'>▐</font> <b>ESTAMPADO {i_e + 1}: {est_nombre}</b>", t_title)
                data_t = [["COLOR", "", ""] + tallas_usadas]; totales_tallas = {t: 0 for t in tallas_usadas}
                for fila in filas_colores:
                    p_color = Paragraph(fila["color"], style_color_inv)
                    r = [p_color, "", ""]
                    for t in tallas_usadas:
                        cant = fila["tallas"][t]; r.append(str(cant) if cant > 0 else ""); totales_tallas[t] += cant
                    data_t.append(r)

                f_tot = ["TOTAL", "", ""]
                for t in tallas_usadas: f_tot.append(str(totales_tallas[t]))
                data_t.append(f_tot)

                t_inv = Table(data_t, colWidths=anchos_columnas)
                t_inv.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                    ('SPAN', (0, -1), (2, -1)), ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")), ('BOTTOMPADDING', (0,0), (-1,-1), 3), ('TOPPADDING', (0,0), (-1,-1), 3),
                ]))
                
                wrap_table = Table([[title], [Spacer(1, 4)], [t_inv]], colWidths=[285])
                wrap_table.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0)]))
                tablas_estampados.append(wrap_table)

            while len(tablas_estampados) < 4: tablas_estampados.append("")
            grid_data = [[tablas_estampados[0], tablas_estampados[1]], [Spacer(1, 20), Spacer(1, 20)], [tablas_estampados[2], tablas_estampados[3]]]
            t_grid = Table(grid_data, colWidths=[291, 291])
            t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
            elementos.append(t_grid)
            
            if i_f < len(datos_inventario_global) - 1: elementos.append(PageBreak())

        doc.build(elementos, onFirstPage=FirmasAbsolutas().draw, onLaterPages=FirmasAbsolutas().draw)
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Produccion_{str_folios}.pdf"})
    except Exception as e: return jsonify({'error': str(e)}), 500

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

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=20, rightMargin=20, topMargin=70, bottomMargin=80)
        elementos = []
        estilos = getSampleStyleSheet(); style_header_corte = ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)

        folio_actual = folio_arranque 

        # 1. DIBUJAR HOJAS DE CORTE
        for particion in particiones:
            grupo_tallas, cuerpos, lienzos = particion
            
            t_header_corte = Table([
                [Paragraph(f"<b>MODELO:</b> {modelo}", style_header_corte), 
                 Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
                 Paragraph(f"<b>FOLIO:</b> {str(folio_actual).zfill(2)} (PEDIDO)", style_header_corte)],
                [Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b> {fecha_txt}", estilos['Normal']), "", Paragraph("<b>FECHA DE ENTREGA:</b> _____________", ParagraphStyle(name='r', alignment=TA_RIGHT))]
            ], colWidths=[190, 190, 190])
            t_header_corte.setStyle(TableStyle([('ALIGN', (0,0), (0,0), 'LEFT'), ('ALIGN', (1,0), (1,0), 'CENTER'), ('ALIGN', (2,0), (2,0), 'RIGHT')]))
            elementos.append(t_header_corte); elementos.append(Spacer(1, 30))
            
            tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
            data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
            piezas_fijas = [("TRASERO", 1), ("DELANTERO", 1), ("MANGAS", "1A 1B"), ("GORROS", "1A 1B"), ("BOLSAS", 1), ("PRETINA", 1), ("PUÑOS", 2)]
            for nombre_p, mult in piezas_fijas:
                fila = [nombre_p, str(mult)]
                for t in tallas_todas:
                    c_val = cuerpos.get(t, 0)
                    if isinstance(mult, int): fila.append(str(c_val * mult) if c_val > 0 else "")
                    else: fila.append(f"{c_val}A {c_val}B" if c_val > 0 else "")
                data_t1.append(fila)

            t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60])
            t1.setStyle(TableStyle([
                ('SPAN', (2, 0), (-1, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),  
                ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#fef3c7")), ('TEXTCOLOR', (0,0), (-1,1), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ]))
            elementos.append(t1); elementos.append(Spacer(1, 20)); elementos.append(Paragraph("<b>FECHA:</b> _________________", estilos['Normal'])); elementos.append(Spacer(1, 5))

            data_t2 = [["N° ROLLO\n(Marcado)", "COLOR", "N° LIENZO"] + tallas_todas + ["TOTAL"]]
            suma_lienzos = 0; suma_tallas = {t: 0 for t in tallas_todas}; gran_total = 0; idx_color = 0
            for c, l_cant in lienzos.items():
                if l_cant == 0: continue
                fila = ["Marcado\n1" if idx_color == 0 else "", c, str(l_cant)]; suma_lienzos += l_cant
                for t in tallas_todas:
                    prod = l_cant * cuerpos.get(t, 0)
                    fila.append(str(prod) if prod > 0 else ""); suma_tallas[t] += prod
                tot_fila = sum(l_cant * cuerpos.get(tx, 0) for tx in grupo_tallas)
                fila.append(str(tot_fila)); gran_total += tot_fila; data_t2.append(fila); idx_color += 1

            fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
            for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
            fila_final.append(str(gran_total)); data_t2.append(fila_final)
            
            t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45])
            t2.setStyle(TableStyle([
                ('SPAN', (0, 1), (0, idx_color)), ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fef3c7")), 
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9), ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('SPAN', (0, -1), (1, -1)), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#fde68a")), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            ]))
            elementos.append(t2); elementos.append(PageBreak())

        # 2. CALCULAR INVENTARIO UNIFICADO
        total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
        for particion in particiones:
            grupo_tallas, cuerpos, lienzos = particion
            for c, l_cant in lienzos.items():
                for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos.get(t, 0)

        # 3. DIBUJAR INVENTARIOS UNIFICADOS (DISEÑO 2x2)
        t_title = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
        style_color_inv = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=8, leading=9)
        
        t_header_inv = Table([
            [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
             Paragraph(f"<b>FOLIO:</b> {str(folio_actual).zfill(2)} (PEDIDO)<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
        ], colWidths=[285, 285])
        elementos.append(t_header_inv); elementos.append(Spacer(1, 15))

        num_est = len(estampados)
        total_ingresado_nube = 0
        mapa_bd = {"CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX CH": "talla_ex_ch", "XG": "talla_ex_g", "EX G": "talla_ex_g", "T-12": "talla_t12", "T-16": "talla_t16"}

        for i_e, est in enumerate(estampados):
            title = Paragraph(f"<font color='#d97706'>▐</font> <b>ESTAMPADO {i_e + 1}: {est}</b>", ParagraphStyle('titulo_grande', fontSize=12, fontName='Helvetica-Bold'))
            elementos.append(title); elementos.append(Spacer(1, 10))
            
            w_color = 75; w_talla = 30
            w_vacio = max(10, (285 - w_color - (w_talla * len(tallas_activas))) / 2.0)
            anchos = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_activas)
            
            data_tot = [["COLOR", "", ""] + tallas_activas]; sum_tot = {t: 0 for t in tallas_activas}
            data_ped = [["COLOR", "", ""] + tallas_activas]; sum_ped = {t: 0 for t in tallas_activas}
            data_sob = [["COLOR", "", ""] + tallas_activas]; sum_sob = {t: 0 for t in tallas_activas}
            
            for c in colores_activos:
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
                        modelo_folio_nube = f"{modelo} {str(folio_actual).zfill(2)}"
                        col_sql = mapa_bd.get(t, "talla_ex_g")
                        
                        cursor.execute("SELECT id FROM panel_stock WHERE modelo=%s AND estampado=%s AND color=%s", (modelo_folio_nube, est, c))
                        res = cursor.fetchone()
                        
                        v_stock = {"talla_t12":0, "talla_t16":0, "talla_ex_ch":0, "talla_ch":0, "talla_m":0, "talla_g":0, "talla_ex_g":0}
                        v_stock[col_sql] = sob_est
                        
                        if res:
                            cursor.execute("UPDATE panel_stock SET talla_t12=talla_t12+%s, talla_t16=talla_t16+%s, talla_ex_ch=talla_ex_ch+%s, talla_ch=talla_ch+%s, talla_m=talla_m+%s, talla_g=talla_g+%s, talla_ex_g=talla_ex_g+%s WHERE id=%s", 
                                           (v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"], res['id']))
                            panel_id = res['id']
                        else:
                            cursor.execute("INSERT INTO panel_stock (modelo, estampado, color, talla_t12, talla_t16, talla_ex_ch, talla_ch, talla_m, talla_g, talla_ex_g, genero, estilo, tipo_prenda) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', 'NORMAL', 'SUDADERA')", 
                                           (modelo_folio_nube, est, c, v_stock["talla_t12"], v_stock["talla_t16"], v_stock["talla_ex_ch"], v_stock["talla_ch"], v_stock["talla_m"], v_stock["talla_g"], v_stock["talla_ex_g"]))
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
                ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('TOPPADDING', (0,0), (-1,-1), 4),
            ])
            t_tot = Table(data_tot, colWidths=anchos); t_tot.setStyle(style_tabla_3)
            t_ped = Table(data_ped, colWidths=anchos); t_ped.setStyle(style_tabla_3)
            t_sob = Table(data_sob, colWidths=anchos); t_sob.setStyle(style_tabla_3)

            wrap_tot = Table([[Paragraph("<font color='#3b82f6'>1. TOTAL PRODUCIDO</font>", ParagraphStyle('t', fontSize=9, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_tot]])
            wrap_ped = Table([[Paragraph("<font color='#16a34a'>2. PEDIDO CLIENTE</font>", ParagraphStyle('t', fontSize=9, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_ped]])
            wrap_sob = Table([[Paragraph("<font color='#e63946'>3. A NUBE (SOBRANTE)</font>", ParagraphStyle('t', fontSize=9, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_sob]])

            grid_data = [
                [wrap_tot, wrap_ped],
                [Spacer(1, 20), Spacer(1, 20)],
                [wrap_sob, ""]
            ]
            t_grid = Table(grid_data, colWidths=[291, 291])
            t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
            
            elementos.append(t_grid)
            elementos.append(FirmasAbsolutas())
            
            if i_e < len(estampados) - 1: elementos.append(PageBreak())

        if total_ingresado_nube > 0:
            cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE (SOBRANTES)', 'SISTEMA')", 
                           (modelo, total_ingresado_nube, fecha_txt))
                           
        cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folio_actual + 1, modelo))
        db.commit(); cursor.close(); db.close()

        doc.build(elementos, onFirstPage=FirmasAbsolutas().draw, onLaterPages=FirmasAbsolutas().draw)
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Pedido_{str(folio_arranque).zfill(2)}.pdf", 'siguiente_folio': folio_actual + 1})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
