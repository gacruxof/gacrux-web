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

def safe_int(val):
    try: return int(val)
    except: return 0

# 🔥 CONEXIÓN BLINDADA: Siempre verifica que Aiven esté vivo antes de proceder 🔥
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
# RUTAS WEB PRINCIPALES Y DESPERTADOR
# ==============================================================================
@app.route('/api/ping', methods=['GET'])
def api_ping():
    return jsonify({'status': 'despierto'})

@app.route('/api/login', methods=['POST'])
def api_login_movil():
    datos = request.get_json()
    user_input = datos.get('usuario', '').strip().lower()
    pass_input = datos.get('password', '').strip()
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

def generar_codigo_13_nube(cursor, modelo, estampado, color, talla):
    cursor.execute("SELECT SUBSTRING(codigo_barras, 1, 5) AS mod_id FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo,))
    res_mod = cursor.fetchone()
    if res_mod and res_mod['mod_id'] and res_mod['mod_id'].isdigit(): mod_str = res_mod['mod_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 1, 5) AS UNSIGNED)) AS max_mod FROM inventario WHERE LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'")
        res_max_mod = cursor.fetchone(); mod_str = f"{ (res_max_mod['max_mod'] if res_max_mod and res_max_mod['max_mod'] else 0) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 6, 5) AS est_id FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado))
    res_est = cursor.fetchone()
    if res_est and res_est['est_id'] and res_est['est_id'].isdigit(): est_str = res_est['est_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 6, 5) AS UNSIGNED)) AS max_est FROM inventario WHERE modelo = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo,))
        res_max_est = cursor.fetchone(); est_str = f"{(res_max_est['max_est'] if res_max_est and res_max_est['max_est'] else 0) + 1:05d}"

    cursor.execute("SELECT SUBSTRING(codigo_barras, 11, 2) AS col_id FROM inventario WHERE modelo = %s AND estampado = %s AND color = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750' LIMIT 1", (modelo, estampado, color))
    res_col = cursor.fetchone()
    if res_col and res_col['col_id'] and res_col['col_id'].isdigit(): col_str = res_col['col_id']
    else:
        cursor.execute("SELECT MAX(CAST(SUBSTRING(codigo_barras, 11, 2) AS UNSIGNED)) AS max_col FROM inventario WHERE modelo = %s AND estampado = %s AND LENGTH(codigo_barras) = 13 AND LEFT(codigo_barras, 3) != '750'", (modelo, estampado))
        res_max_col = cursor.fetchone(); col_str = f"{(res_max_col['max_col'] if res_max_col and res_max_col['max_col'] else 0) + 1:02d}"

    talla_id = {'CH': 1, 'M': 2, 'G': 3, 'XG': 4, 'EX G': 4, 'T-12': 5, 'T-16': 6, 'EG': 4}.get(talla.upper(), 9)
    return f"{mod_str}{est_str}{col_str}{talla_id:01d}"

def dibujar_footer_firmas(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(150, 50, "___________________________________")
    canvas.drawCentredString(150, 35, "DOBLADO")
    canvas.drawCentredString(150, 20, "JACQUELINE TLATELPA XOLALTENCO")
    canvas.drawCentredString(460, 50, "___________________________________")
    canvas.drawCentredString(460, 35, "ALMACÉN")
    canvas.drawCentredString(460, 20, "DULCE EVELIN POTRERO RODRIGUEZ")
    canvas.restoreState()

# ==============================================================================
# 🔥 RUTAS SEPARADAS POR PASOS (LA ESTRATEGIA DEFINITIVA) 🔥
# ==============================================================================
@app.route('/api/app/magia_madre', methods=['POST'])
def api_magia_madre():
    try:
        req = request.get_json()
        step = req.get('step', 'all') # "db" o "pdf"
        modelo = req.get('modelo', '').strip().upper()
        raw_estampados = req.get('estampados', [])
        estampados_por_folio = int(req.get('estampados_por_folio', 4))
        colores = req.get('colores', [])
        cuerpos_actuales = req.get('cuerpos_actuales', {})
        tallas_usadas = req.get('tallas_usadas', [])
        datos_lienzo_color = req.get('datos_lienzo_color', {})
        folios_a_usar = req.get('folios_a_usar', [])
        fecha_txt = datetime.datetime.now().strftime("%d/%m/%y")
        str_folios = ", ".join([str(f).zfill(2) for f in folios_a_usar])

        # 1. ORDENAR LOS DATOS COMUNES
        datos_corte = []
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
        est_por_folio = []
        estampados = []
        for chunk in est_por_folio_raw:
            clean_chunk = [e for e in chunk if e.strip()]
            if not clean_chunk: clean_chunk = ["SIN ESTAMPADO"]
            est_por_folio.append(clean_chunk); estampados.extend(clean_chunk)
            
        if not estampados: estampados = ["SIN ESTAMPADO"]; est_por_folio = [["SIN ESTAMPADO"]]
        while len(est_por_folio) < num_folios: est_por_folio.append(["SIN ESTAMPADO"])

        datos_inventario_global = []
        current_global_idx = 1
        for i_f, folio_actual in enumerate(folios_a_usar):
            estampados_del_folio = est_por_folio[i_f]
            estampados_data = []
            for est_name in estampados_del_folio:
                estampados_data.append({"nombre": est_name, "filas": [], "global_idx": current_global_idx})
                current_global_idx += 1
                
            for fila_corte in datos_corte:
                c = fila_corte["color"]
                reparto_por_talla = {t: [] for t in tallas_usadas}
                for t in tallas_usadas:
                    total_corte = fila_corte["totales_talla"][t]
                    total_folio = total_corte // num_folios
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

        mapa_bd = {"T-12": "talla_t12", "T-16": "talla_t16", "EX CH": "talla_ex_ch", "CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX G": "talla_ex_g"}

        # 🔥 PASO 1: PURA BASE DE DATOS 🔥
        if step in ['db', 'all']:
            db = None; cursor = None
            try:
                db = conectar_bd(); cursor = db.cursor(dictionary=True)
                total_ingresado_nube = 0
                for i_f, folio_actual in enumerate(folios_a_usar):
                    modelo_folio_nube = f"{modelo} {str(folio_actual).zfill(2)}"
                    for est_item in datos_inventario_global[i_f]["estampados"]:
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
                                    total_ingresado_nube += cant

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
                if total_ingresado_nube > 0:
                    cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE', 'SISTEMA')", 
                                   (modelo, total_ingresado_nube, fecha_txt))

                cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folios_a_usar[-1] + 1, modelo))
                db.commit()
            except Exception as e:
                if db: db.rollback()
                return jsonify({'error': "Error de Guardado DB: " + str(e)}), 500
            finally:
                if cursor: cursor.close()
                if db: db.close()

            if step == 'db': return jsonify({'status': 'ok'})

        # 🔥 PASO 2: PURO DIBUJO DE PDF 🔥
        if step in ['pdf', 'all']:
            db = None; cursor = None
            imagen_blob = None; formato_img = "1500x1900 (Frente)"; cuerpos_del_modelo = []
            try:
                db = conectar_bd(); cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
                row_img = cursor.fetchone()
                if row_img:
                    imagen_blob = row_img['imagen_dibujo']
                    formato_img = row_img['formato_img'] if row_img['formato_img'] else "1500x1900 (Frente)"

                cursor.execute("SELECT cuerpos_ids FROM recetas_madre WHERE modelo = %s", (modelo,))
                row_ids = cursor.fetchone()
                ids_guardados = json.loads(row_ids['cuerpos_ids']) if row_ids and row_ids.get('cuerpos_ids') else []
                if ids_guardados:
                    placeholders = ','.join(['%s']*len(ids_guardados))
                    cursor.execute(f"SELECT id, nombre, tipo_multiplicador FROM cuerpos_base WHERE id IN ({placeholders})", tuple(ids_guardados))
                    res_cuerpos = cursor.fetchall()
                    for id_g in ids_guardados:
                        for row in res_cuerpos:
                            if row['id'] == id_g: cuerpos_del_modelo.append(row); break
                if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]
            finally:
                if cursor: cursor.close()
                if db: db.close()

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=40, bottomMargin=15)
            elementos = []
            estilos = getSampleStyleSheet()
            estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)

            if imagen_blob:
                try:
                    img = PILImage.open(io.BytesIO(imagen_blob))
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.thumbnail((300, 300)) # COMPRESIÓN DE RAM 
                    temp_io = io.BytesIO()
                    img.save(temp_io, format='JPEG', quality=80)
                    temp_io.seek(0)
                    w_img = 220 if "2500" in formato_img else 130
                    logo = RLImage(temp_io, width=w_img, height=130, kind='proportional')
                except: logo = ""
            else: logo = ""

            # 1. DIBUJAR HOJAS DE CORTE
            for particion_folio in folios_a_usar:
                t_header_corte = Table([
                    [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)), 
                     Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
                     Paragraph(f"<font color='red'><b>FOLIO:</b> {str_folios}</font>", ParagraphStyle(name='hr', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=12))],
                    [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
                ], colWidths=[185, 185, 185], rowHeights=[20, 135], hAlign='CENTER')
                t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
                elementos.append(t_header_corte); elementos.append(Spacer(1, 10))

                tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
                data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
                
                for c_dict in cuerpos_del_modelo:
                    nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
                    if 'x2' in tipo_mult: txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
                    elif 'A/B' in tipo_mult: txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
                    else: txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""

                    fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
                    for t in tallas_todas: fila.append(f_calc(safe_int(cuerpos_actuales.get(t, 0))))
                    data_t1.append(fila)

                t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60], hAlign='CENTER')
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
                t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45], hAlign='CENTER')
                t2.setStyle(TableStyle(estilos_tabla2))

                tablas_encogibles = KeepInFrame(
                    maxWidth=540, maxHeight=500, 
                    content=[t1, Spacer(1, 15), Paragraph("<b>FECHA:</b> _________________", estilos['Normal']), Spacer(1, 10), t2], 
                    mode='shrink', vAlign='TOP'
                )
                elementos.append(tablas_encogibles); elementos.append(PageBreak())

            # 2. DIBUJAR INVENTARIOS UNIFICADOS
            t_title = ParagraphStyle('titulo', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
            MAX_COLORS = 10
            color_chunks = [colores[i:i + MAX_COLORS] for i in range(0, len(colores), MAX_COLORS)]

            for i_f, data_folio in enumerate(datos_inventario_global):
                folio = data_folio["folio"]; estampados_data = data_folio["estampados"]

                for chunk_idx, color_chunk in enumerate(color_chunks):
                    estampados_por_hoja = [estampados_data[i:i + estampados_por_folio] for i in range(0, len(estampados_data), estampados_por_folio)]
                    if not estampados_por_hoja: estampados_por_hoja = [[]]
                    
                    for lote_idx, lote_estampados in enumerate(estampados_por_hoja):
                        t_header_inv = Table([
                            [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                             Paragraph(f"<b>FOLIO:</b> {folio}<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
                        ], colWidths=[270, 270], hAlign='CENTER')

                        tablas_estampados = []
                        for est_item in lote_estampados:
                            est_nombre = est_item["nombre"]; filas_colores = est_item["filas"]; global_idx = est_item["global_idx"]
                            title_text = f"<font color='#3b82f6'>▐</font> <b>ESTAMPADO {global_idx}: {est_nombre}</b>"
                            if len(color_chunks) > 1: title_text += f" (Parte {chunk_idx + 1})"
                            title = Paragraph(title_text, t_title)
                            
                            num_colors_chunk = len(color_chunk)
                            if num_colors_chunk <= 6: f_size = 8; pad = 4
                            elif num_colors_chunk <= 10: f_size = 7.5; pad = 3
                            else: f_size = 6.5; pad = 1
                                
                            style_color_inv_dyn = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                            w_color = 60; w_talla = 20; espacio_total_tabla = 260 
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
                            
                            wrapper_table = Table([[title], [Spacer(1, 4)], [t_inv]], colWidths=[260], hAlign='CENTER')
                            wrapper_table.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0)]))
                            tablas_estampados.append(wrapper_table)

                        while len(tablas_estampados) < 4: tablas_estampados.append("")

                        grid_data = [[tablas_estampados[0], tablas_estampados[1]], [Spacer(1, 15), Spacer(1, 15)], [tablas_estampados[2], tablas_estampados[3]]]
                        t_grid = Table(grid_data, colWidths=[270, 270], hAlign='CENTER')
                        t_grid.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                        
                        firmas_data = [
                            [" ", " "], [" ", " "], [" ", " "],
                            ["___________________________________", "___________________________________"],
                            ["DOBLADO", "ALMACÉN"],
                            ["JACQUELINE TLATELPA XOLALTENCO", "DULCE EVELIN POTRERO RODRIGUEZ"]
                        ]
                        t_firmas = Table(firmas_data, colWidths=[270, 270], hAlign='CENTER')
                        t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                        
                        wrap_t_grid = KeepInFrame(maxWidth=540, maxHeight=490, content=[t_header_inv, Spacer(1,15), t_grid], mode='shrink', vAlign='TOP')
                        t_master = Table([[wrap_t_grid], [t_firmas]], colWidths=[540], rowHeights=[550, 110], hAlign='CENTER') 
                        t_master.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,1), (0,1), 'BOTTOM'),
                            ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                        ]))
                        elementos.append(t_master)
                        if not (i_f == len(datos_inventario_global) - 1 and chunk_idx == len(color_chunks) - 1 and lote_idx == len(estampados_por_hoja) - 1):
                            elementos.append(PageBreak())

            doc.build(elementos) # SOLO DIBUJA AQUI, NO HACE CALLBACKS FANTASMA
            pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()

            return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Produccion_{str_folios}.pdf"})
    except Exception as e:
        return jsonify({'error': "Error crítico en servidor: " + str(e)}), 500

@app.route('/api/app/magia_pedido', methods=['POST'])
def api_magia_pedido():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer gacrux-auth-"): return jsonify({'error': 'No autorizado'}), 401
        
        req = request.get_json()
        step = req.get('step', 'all')
        modelo = req.get('modelo', '').strip().upper()
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

        def total_pedido_grupo(grupo): return sum(safe_int(t_data.get(t, 0)) for c, t_data in pedidos_app.items() for t in grupo)

        def calcular_desperdicio(grupo_tallas):
            best_waste = float('inf'); best_lienzos_total = float('inf'); best_cuerpos = {}; best_lienzos_color = {}
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
                    req_lienzos = max((math.ceil(safe_int(peds.get(t, 0)) / cuerpos[t]) for t in grupo_tallas if safe_int(peds.get(t, 0)) > 0), default=0)
                    lienzos_color[c] = req_lienzos; tot_l += req_lienzos
                    for t in grupo_tallas: waste += (req_lienzos * cuerpos[t]) - safe_int(peds.get(t, 0))
                if tot_l < best_lienzos_total or (tot_l == best_lienzos_total and waste < best_waste):
                    best_lienzos_total = tot_l; best_waste = waste; best_cuerpos = cuerpos; best_lienzos_color = lienzos_color
            return best_waste, best_lienzos_total, best_cuerpos, best_lienzos_color

        def evaluar_grupo_de_3(grupo_3):
            w_all, l_all, c_all, lc_all = calcular_desperdicio(grupo_3); tot_ped = total_pedido_grupo(grupo_3)
            if tot_ped <= 30: return [(grupo_3, c_all, lc_all)]
            if w_all > (tot_ped * 0.50):
                best_split_lienzos = float('inf'); best_split_waste = float('inf'); best_split = None
                for i in range(3):
                    single = [grupo_3[i]]; pair = [grupo_3[j] for j in range(3) if j != i]
                    ws, ls, cs, lcs = calcular_desperdicio(single); wp, lp, cp, lcp = calcular_desperdicio(pair)
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

        est_por_folio_raw = [raw_estampados[i:i + estampados_por_folio] for i in range(0, len(raw_estampados), estampados_por_folio)]
        est_por_folio = []; estampados = []
        for chunk in est_por_folio_raw:
            clean_chunk = [e for e in chunk if e.strip()]
            if clean_chunk: est_por_folio.append(clean_chunk); estampados.extend(clean_chunk)
        if not estampados: estampados = ["SIN ESTAMPADO"]; est_por_folio = [["SIN ESTAMPADO"]]

        # 🔥 PASO 1: BASE DE DATOS 🔥
        if step in ['db', 'all']:
            db = None; cursor = None
            try:
                db = conectar_bd(); cursor = db.cursor(dictionary=True)
                total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
                for particion in particiones:
                    grupo_tallas, cuerpos_dict, lienzos = particion
                    for c, l_cant in lienzos.items():
                        for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos_dict.get(t, 0)

                num_est = len(estampados)
                total_ingresado_nube = 0
                mapa_bd = {"CH": "talla_ch", "M": "talla_m", "G": "talla_g", "EX CH": "talla_ex_ch", "XG": "talla_ex_g", "EX G": "talla_ex_g", "T-12": "talla_t12", "T-16": "talla_t16"}

                for i_e, est in enumerate(estampados):
                    for c in colores_activos:
                        for t in tallas_activas:
                            prod = total_prod[c][t]
                            ped = safe_int(pedidos_app.get(c, {}).get(t, 0))
                            
                            base_prod = prod // num_est; sobra_prod = prod % num_est
                            prod_est = base_prod + 1 if i_e < sobra_prod else base_prod
                            
                            base_ped = ped // num_est; sobra_ped = ped % num_est
                            ped_est = base_ped + 1 if i_e < sobra_ped else base_ped
                            
                            sob_est = max(0, prod_est - ped_est)
                            
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

                if total_ingresado_nube > 0:
                    cursor.execute("INSERT INTO historial_ventas (modelo, estampado, color, talla, cantidad, precio_unitario, total_pagado, fecha_hora, tipo_movimiento, realizado_por) VALUES (%s, 'MULTIPLES', 'MULTIPLE', 'MULTIPLE', %s, 0, 0, %s, 'INGRESO APP LOTE (SOBRANTES)', 'SISTEMA')", 
                                   (modelo, total_ingresado_nube, fecha_txt))
                                   
                cursor.execute("UPDATE recetas_madre SET folio = %s WHERE modelo = %s", (folio_arranque + 1, modelo))
                db.commit()
            except Exception as e:
                if db: db.rollback()
                return jsonify({'error': "Error de base de datos: " + str(e)}), 500
            finally:
                if cursor: cursor.close()
                if db: db.close()

            if step == 'db': return jsonify({'status': 'ok'})

        # 🔥 PASO 2: DIBUJAR PDF 🔥
        if step in ['pdf', 'all']:
            db = None; cursor = None
            imagen_blob = None; formato_img = "1500x1900 (Frente)"; cuerpos_del_modelo = []
            try:
                db = conectar_bd(); cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT imagen_dibujo, formato_img FROM modelos_base WHERE nombre = %s", (modelo,))
                row_img = cursor.fetchone()
                if row_img:
                    imagen_blob = row_img['imagen_dibujo']
                    formato_img = row_img['formato_img'] if row_img['formato_img'] else "1500x1900 (Frente)"

                cursor.execute("SELECT cuerpos_ids FROM recetas_madre WHERE modelo = %s", (modelo,))
                row_ids = cursor.fetchone()
                ids_guardados = json.loads(row_ids['cuerpos_ids']) if row_ids and row_ids.get('cuerpos_ids') else []
                if ids_guardados:
                    placeholders = ','.join(['%s']*len(ids_guardados))
                    cursor.execute(f"SELECT id, nombre, tipo_multiplicador FROM cuerpos_base WHERE id IN ({placeholders})", tuple(ids_guardados))
                    res_cuerpos = cursor.fetchall()
                    for id_g in ids_guardados:
                        for row in res_cuerpos:
                            if row['id'] == id_g: cuerpos_del_modelo.append(row); break
                if not cuerpos_del_modelo: cuerpos_del_modelo = [{'nombre': 'PIEZA GENÉRICA (Falta Configurar)', 'tipo_multiplicador': 'x1 (Normal)'}]
            finally:
                if cursor: cursor.close()
                if db: db.close()

            total_prod = {c: {t: 0 for t in tallas_activas} for c in colores_activos}
            for particion in particiones:
                grupo_tallas, cuerpos_dict, lienzos = particion
                for c, l_cant in lienzos.items():
                    for t in grupo_tallas: total_prod[c][t] += l_cant * cuerpos_dict.get(t, 0)

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=40, bottomMargin=15)
            elementos = []
            estilos = getSampleStyleSheet()
            style_header_corte = ParagraphStyle(name='hc', fontName='Helvetica-Bold', fontSize=12)
            estilo_wrap = ParagraphStyle(name='Wrap', alignment=TA_CENTER, fontName='Helvetica', fontSize=9, leading=10)

            if imagen_blob:
                try:
                    img = PILImage.open(io.BytesIO(imagen_blob))
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.thumbnail((300, 300))
                    temp_io = io.BytesIO()
                    img.save(temp_io, format='JPEG', quality=85)
                    temp_io.seek(0)
                    w_img = 220 if "2500" in formato_img else 130
                    logo = RLImage(temp_io, width=w_img, height=130, kind='proportional')
                except: logo = ""
            else: logo = ""

            folio_actual = folio_arranque 

            # 1. DIBUJAR HOJAS DE CORTE
            for particion in particiones:
                grupo_tallas, cuerpos, lienzos = particion
                t_header_corte = Table([
                    [Paragraph(f"<font color='red'><b>MODELO:</b> {modelo}</font>", style_header_corte), 
                     Paragraph("<b>HOJA DE ORDEN DEL ÁREA DE CORTE</b>", ParagraphStyle(name='c', alignment=TA_CENTER, fontName='Helvetica-Bold')), 
                     Paragraph(f"<font color='red'><b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)</font>", style_header_corte)],
                    [logo, "", Paragraph(f"<b>FECHA DE EXPEDICIÓN:</b><br/>{fecha_txt}<br/><br/><br/><b>FECHA DE ENTREGA:</b><br/>___________________", ParagraphStyle(name='r2', alignment=TA_RIGHT, leading=14))]
                ], colWidths=[185, 185, 185], rowHeights=[20, 135], hAlign='CENTER')
                t_header_corte.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,1), (0,1), 'CENTER')]))
                
                elementos.append(t_header_corte); elementos.append(Spacer(1, 10))
                tallas_todas = ["T-12", "T-16", "EX CH", "CH", "M", "G", "EX G"]
                data_t1 = [["PIEZAS", "CANTIDAD", "TALLAS", "", "", "", "", "", ""], ["", ""] + tallas_todas]
                
                for c_dict in cuerpos_del_modelo:
                    nombre_p = c_dict['nombre']; tipo_mult = c_dict.get('tipo_multiplicador', 'x1 (Normal)')
                    if 'x2' in tipo_mult: txt_cant = "2"; f_calc = lambda c: str(c * 2) if c > 0 else ""
                    elif 'A/B' in tipo_mult: txt_cant = "L-A | L-B"; f_calc = lambda c: f"{c}-A | {c}-B" if c > 0 else ""
                    else: txt_cant = "1"; f_calc = lambda c: str(c) if c > 0 else ""

                    fila = [Paragraph(nombre_p, estilo_wrap), txt_cant]
                    for t in tallas_todas: fila.append(f_calc(cuerpos.get(t, 0)))
                    data_t1.append(fila)

                t1 = Table(data_t1, colWidths=[80, 70] + [57] * 6 + [60], hAlign='CENTER')
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
                        prod = l_cant * cuerpos.get(t, 0); fila.append(str(prod) if prod > 0 else ""); suma_tallas[t] += prod
                    tot_fila = sum(l_cant * cuerpos.get(tx, 0) for tx in grupo_tallas)
                    fila.append(str(tot_fila)); gran_total += tot_fila; data_t2.append(fila); idx_color += 1

                fila_final = ["TOTAL LIENZOS:", "", str(suma_lienzos)]
                for t in tallas_todas: fila_final.append(str(suma_tallas[t]) if suma_tallas[t] > 0 else "")
                fila_final.append(str(gran_total)); data_t2.append(fila_final)
                
                t2 = Table(data_t2, colWidths=[55, 90, 50, 45, 45, 50, 45, 45, 45, 45, 45], hAlign='CENTER')
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
                elementos.append(tablas_encogibles); elementos.append(PageBreak())

            # 2. DIBUJAR INVENTARIOS UNIFICADOS
            t_title = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)
            MAX_COLORS = 10
            color_chunks = [colores_activos[i:i + MAX_COLORS] for i in range(0, len(colores_activos), MAX_COLORS)]

            for lote_idx, lote_estampados in enumerate(est_por_folio):
                for chunk_idx, color_chunk in enumerate(color_chunks):
                    
                    t_header_inv = Table([
                        [Paragraph(f"<b>CONTROL DE INVENTARIO</b><br/>MODELO: {modelo}", estilos['Normal']), 
                         Paragraph(f"<b>FOLIO:</b> {str(folio_arranque).zfill(2)} (PEDIDO)<br/><b>FECHA:</b> {fecha_txt}", ParagraphStyle(name='r', alignment=TA_RIGHT))]
                    ], colWidths=[270, 270], hAlign='CENTER')
                    
                    tablas_estampados = []
                    for idx_interno, est in enumerate(lote_estampados):
                        original_idx = estampados.index(est) + 1 if est in estampados else 1
                        title_text = f"<font color='#d97706'>▐</font> <b>ESTAMPADO {original_idx}: {est}</b>"
                        if len(color_chunks) > 1: title_text += f" (Parte {chunk_idx + 1})"
                        title = Paragraph(title_text, ParagraphStyle('titulo_grande', fontSize=10, fontName='Helvetica-Bold'))
                        
                        num_colors_chunk = len(color_chunk)
                        if num_colors_chunk <= 6: f_size = 8; pad = 4
                        elif num_colors_chunk <= 10: f_size = 7.5; pad = 3
                        else: f_size = 6.5; pad = 1
                            
                        style_color_inv = ParagraphStyle('ColorInv', fontName='Helvetica-Bold', fontSize=f_size, leading=f_size+1)
                        w_color = 60; w_talla = 20; espacio_total_tabla = 260 
                        w_vacio = max(10, (espacio_total_tabla - w_color - (w_talla * len(tallas_activas))) / 2.0) 
                        anchos = [w_color, w_vacio, w_vacio] + [w_talla] * len(tallas_activas)
                        
                        data_tot = [["COLOR", "", ""] + tallas_activas]; sum_tot = {t: 0 for t in tallas_activas}
                        data_ped = [["COLOR", "", ""] + tallas_activas]; sum_ped = {t: 0 for t in tallas_activas}
                        data_sob = [["COLOR", "", ""] + tallas_activas]; sum_sob = {t: 0 for t in tallas_activas}
                        
                        for c in color_chunk:
                            r_tot = [Paragraph(c, style_color_inv), "", ""]; r_ped = [Paragraph(c, style_color_inv), "", ""]; r_sob = [Paragraph(c, style_color_inv), "", ""]
                            for t in tallas_activas:
                                prod = total_prod[c][t]; ped = safe_int(pedidos_app.get(c, {}).get(t, 0))
                                base_prod = prod // num_est; sobra_prod = prod % num_est
                                prod_est = base_prod + 1 if estampados.index(est) < sobra_prod else base_prod
                                base_ped = ped // num_est; sobra_ped = ped % num_est
                                ped_est = base_ped + 1 if estampados.index(est) < sobra_ped else base_ped
                                sob_est = max(0, prod_est - ped_est)
                                r_tot.append(str(prod_est) if prod_est>0 else "-"); r_ped.append(str(ped_est) if ped_est>0 else "-"); r_sob.append(str(sob_est) if sob_est>0 else "-")
                                sum_tot[t] += prod_est; sum_ped[t] += ped_est; sum_sob[t] += sob_est

                            data_tot.append(r_tot); data_ped.append(r_ped); data_sob.append(r_sob)
                        
                        data_tot.append(["SUMA", "", ""] + [str(sum_tot[t]) for t in tallas_activas]); data_ped.append(["SUMA", "", ""] + [str(sum_ped[t]) for t in tallas_activas]); data_sob.append(["SUMA", "", ""] + [str(sum_sob[t]) for t in tallas_activas])

                        style_tabla_3 = TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), 
                            ('SPAN', (0, -1), (2, -1)), ('SPAN', (0, 0), (2, 0)),
                            ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (3,0), (-1,-1), 'CENTER'), ('ALIGN', (0,-1), (2,-1), 'CENTER'), 
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,-1), f_size), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
                            ('BOTTOMPADDING', (0,0), (-1,-1), pad), ('TOPPADDING', (0,0), (-1,-1), pad),
                        ])
                        t_tot = Table(data_tot, colWidths=anchos, hAlign='CENTER'); t_tot.setStyle(style_tabla_3)
                        t_ped = Table(data_ped, colWidths=anchos, hAlign='CENTER'); t_ped.setStyle(style_tabla_3)
                        t_sob = Table(data_sob, colWidths=anchos, hAlign='CENTER'); t_sob.setStyle(style_tabla_3)

                        wrap_tot = Table([[Paragraph("<font color='#3b82f6'>1. TOTAL PRODUCIDO</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_tot]], hAlign='CENTER')
                        wrap_ped = Table([[Paragraph("<font color='#16a34a'>2. PEDIDO CLIENTE</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_ped]], hAlign='CENTER')
                        wrap_sob = Table([[Paragraph("<font color='#e63946'>3. A NUBE (SOBRANTE)</font>", ParagraphStyle('t', fontSize=8, fontName='Helvetica-Bold'))], [Spacer(1,4)], [t_sob]], hAlign='CENTER')

                        tablas_estampados.append(Table([[wrap_tot, wrap_ped], [Spacer(1, 15), Spacer(1, 15)], [wrap_sob, ""]], colWidths=[270, 270], style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)], hAlign='CENTER'))
                        tablas_estampados.append(title)

                    elementos_hoja = [t_header_inv, Spacer(1, 15)]
                    for i in range(0, len(tablas_estampados), 2):
                        titulo_est = tablas_estampados[i+1]; tabla_est = tablas_estampados[i]
                        elementos_hoja.append(titulo_est); elementos_hoja.append(Spacer(1, 8)); elementos_hoja.append(tabla_est); elementos_hoja.append(Spacer(1, 15))

                    firmas_data = [
                        [" ", " "], [" ", " "], [" ", " "],
                        ["___________________________________", "___________________________________"],
                        ["DOBLADO", "ALMACÉN"],
                        ["JACQUELINE TLATELPA XOLALTENCO", "DULCE EVELIN POTRERO RODRIGUEZ"]
                    ]
                    t_firmas = Table(firmas_data, colWidths=[270, 270], hAlign='CENTER')
                    t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,4), (-1,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                    
                    wrap_elementos = KeepInFrame(maxWidth=540, maxHeight=490, content=elementos_hoja, mode='shrink', vAlign='TOP')
                    t_master = Table([[wrap_elementos], [t_firmas]], colWidths=[540], rowHeights=[550, 110], hAlign='CENTER') 
                    t_master.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('VALIGN', (0,1), (0,1), 'BOTTOM'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
                    ]))
                    elementos.append(t_master)
                    if not (lote_idx == len(est_por_folio) - 1 and chunk_idx == len(color_chunks) - 1):
                        elementos.append(PageBreak())

            doc.build(elementos)
            pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()

            return jsonify({'status': 'ok', 'pdf_base64': pdf_base64, 'filename': f"Gacrux_{modelo}_Pedido_{str(folio_arranque).zfill(2)}.pdf", 'siguiente_folio': folio_arranque + 1})

    except Exception as e:
        return jsonify({'error': "Error crítico en servidor: " + str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
