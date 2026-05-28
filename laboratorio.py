import os
import time
import threading
import calendar
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import flet as ft
from flet import Border, BorderSide, BorderRadius, Padding, alignment

def main(page: ft.Page):

    # =========================================================================
    # --- MOTOR DE BASE DE DATOS SQLITE (INICIALIZACIÓN DE TABLAS) ---
    # =========================================================================
    import sqlite3

    def inicializar_db():
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        
        # Tabla principal con campos de inventario y mutables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habitaciones (
                habitacion TEXT PRIMARY KEY,
                ubicacion TEXT,
                tipo TEXT,
                estado TEXT,
                capacidad TEXT,
                adulto TEXT,
                nino TEXT,
                vista TEXT,
                sub_vista TEXT,
                incluye TEXT,
                cama TEXT,
                reserva TEXT,
                desc_tit TEXT,
                desc_val TEXT,
                prom_tit TEXT,
                prom_val TEXT,
                servicios TEXT,
                fotos TEXT
            )
        """)
        
        # Tabla autónoma para cupones administrativos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cupones (
                codigo TEXT PRIMARY KEY,
                descuento REAL,
                cupos_totales INTEGER,
                cupos_disponibles INTEGER,
                usar_tope INTEGER,
                tope_dinero REAL,
                fecha_inicio TEXT,
                fecha_fin TEXT
            )
        """)

        # Tabla autónoma para el Descuento de Reserva Global
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_reserva (
                id INTEGER PRIMARY KEY,
                activo INTEGER,
                porcentaje REAL
            )
        """)
        
        # Inyección inicial para Descuento de Reserva si está vacía
        cursor.execute("SELECT COUNT(*) FROM config_reserva")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO config_reserva VALUES (1, 0, 0.0)")
            conn.commit()

        # Carga de datos semilla iniciales para pruebas
        cursor.execute("SELECT COUNT(*) FROM habitaciones")
        if cursor.fetchone() == 0:
            cursor.execute("""
                INSERT INTO habitaciones VALUES (
                    'HAB. 101', 'EDIFICIO 3 · PISO 2', 'FAMILIAR PREMIUM', 'DISPONIBLE', '4 PERSONAS', 'USD 120.00', 'USD 50.00',
                    'Vista al jardín', 'EDIFICIO 3 · PISO 2', 'Incluye desayuno', '1 cama extra disponible',
                    'Reserva inmediata', 'DESCUENTO', 'USD 35.00', 'PROMOCIÓN', 'USD 15.00',
                    'WIFI,SMART TV,AIRE ACONDICIONADO,MINIBAR', 'fondo.png,fondo.png,fondo.png,fondo.png'
                )
            """)
            cursor.execute("""
                INSERT INTO habitaciones VALUES (
                    'HAB. 102', 'EDIFICIO 1 · PISO 2', 'FAMILIAR', 'OCUPADA', '4 PERSONAS', 'USD 75.00', 'USD 35.00',
                    'Sin vista', 'EDIFICIO 1 · PISO 2', 'No incluye desayuno', 'Sin camas extras',
                    'Confirmación previa', 'DESCUENTO', 'USD 0.00', 'PROMOCIÓN', 'USD 0.00',
                    'WIFI,TV', 'fondo.png'
                )
            """)
            cursor.execute("""
                INSERT INTO habitaciones VALUES (
                    'HAB. 201', 'EDIFICIO 3 · PISO 2', 'SUITE', 'DISPONIBLE', '3 PERSONAS', 'USD 120.00', 'USD 50.00',
                    'Vista al mar', 'EDIFICIO 3 · PISO 2', 'All Inclusive', '2 camas extras',
                    'Reserva inmediata', 'DESCUENTO', 'USD 10.00', 'PROMOCIÓN', 'USD 5.00',
                    'WIFI,SMART TV,MINIBAR', 'fondo.png'
                )
            """)
            conn.commit()
        conn.close()

    inicializar_db()

    # Configuración de página de Flet
    page.title = "Starblim V2 - ROCKSTAR EDITION"
    page.padding = 0
    page.window_maximized = True
    page.window_resizable = True

    # Estilo de bordes finos blancos del diseño original
    borde_premium = Border(
        top=BorderSide(1, "rgba(255,255,255,0.4)"),
        bottom=BorderSide(1, "rgba(255,255,255,0.4)"),
        left=BorderSide(1, "rgba(255,255,255,0.4)"),
        right=BorderSide(1, "rgba(255,255,255,0.4)")
    )

    # Variables de control de colores cebra
    color_fila_impar = "#602563EB"  
    color_fila_par = "#902563EB"    
    color_fila_hover = "#66FFB300"    
    color_fila_expandida = "#0F172A" 

    # Diccionario base de estilos de inputs flotantes
    input_style = {
        "border_color": "rgba(255, 255, 255, 0.4)",
        "focused_border_color": "#FFB300",
        "color": "white",
        "cursor_color": "#FFB300",
        "height": 45,
        "text_size": 14,
        "border_radius": 8,
    }

    # Variables de estilo de las tablas del diseño original
    color_borde_tablas = "white"         
    grosor_borde_tablas = 1              
    color_borde_encabezados = "#00C3FF" 
    color_azul_premium = "0xCC0D43AF" 
    
    borde_de_las_tablas = Border(
        top=BorderSide(grosor_borde_tablas, color_borde_tablas),
        bottom=BorderSide(grosor_borde_tablas, color_borde_tablas),
        left=BorderSide(grosor_borde_tablas, color_borde_tablas),
        right=BorderSide(grosor_borde_tablas, color_borde_tablas)
    )

    borde_azul_titulo = Border(
        top=BorderSide(1, color_borde_encabezados),
        bottom=BorderSide(1, color_borde_encabezados),
        left=BorderSide(1, color_borde_encabezados),
        right=BorderSide(1, color_borde_encabezados)
    )

    # Componentes del formulario de registro rápido principal
    txt_num = ft.TextField(label="N° Habitación", **input_style)
    txt_cap = ft.TextField(label="Capacidad", **input_style)
    txt_pre_a = ft.TextField(label="Precio Adultos", **input_style)
    txt_pre_n = ft.TextField(label="Precio Niños", **input_style)

    # Lista visual de habitaciones (Panel Derecho)
    lista_habitaciones = ft.ListView(expand=True, spacing=10)

    # --- MOTOR DEL VISOR DE FOTOS ---
    lista_fotos_actual = []
    indice_actual = 0

    def abrir_visor_carrusel(lista_fotos, indice_click):
        nonlocal lista_fotos_actual, indice_actual
        lista_fotos_actual = lista_fotos
        indice_actual = indice_click
        dialogo_visor_galeria.open = True
        actualizar_estado_visor()

    # --- LÓGICA CONSTRUCTORA DE FILAS EXPANDIBLES (Galería Dinámica) ---
    def crear_galeria_con_lapiz(fotos_lista, det, d):
        controles_fotos = []
        for idx, img_path in enumerate(fotos_lista):
            img_control = ft.Image(src=img_path, fit="cover")
            
            def abrir_buscador_nativo(e, img=img_control, index_foto=idx):
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                ruta_archivo = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp")])
                root.destroy()
                
                if ruta_archivo:
                    img.src = ruta_archivo
                    det["fotos"][index_foto] = ruta_archivo
                    fotos_comas = ",".join(det["fotos"])
                    
                    conn = sqlite3.connect("starblim.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE habitaciones 
                        SET fotos = ? 
                        WHERE habitacion = ?
                    """, (fotos_comas, d["habitacion"].upper()))
                    conn.commit()
                    conn.close()
                    page.update()

            # Estructura del Stack del diseño original
            foto_con_icono = ft.Stack([
                ft.Container(width=300, height=170, border_radius=15, clip_behavior=ft.ClipBehavior.HARD_EDGE, content=img_control),
                ft.Container(
                    right=8, top=8, bgcolor="black87", border_radius=50, width=32, height=32,
                    content=ft.IconButton(icon=ft.Icons.EDIT, icon_color="white", icon_size=16, on_click=abrir_buscador_nativo)
                )
            ])

            def capturar_tap_dinamico(index_actual=idx):
                lista_rutas_dinamicas = [
                    col.controls[0].content.controls[0].content.src for col in controles_fotos
                ]
                abrir_visor_carrusel(lista_rutas_dinamicas, index_actual)

            foto_interactiva = ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.CLICK,
                on_tap=lambda _, i=idx: capturar_tap_dinamico(i),
                content=foto_con_icono
            )
            
            bloque_foto_con_aire = ft.Column(
                [
                    foto_interactiva,
                    ft.Container(height=14)  
                ],
                spacing=0
            )
            controles_fotos.append(bloque_foto_con_aire)
            
        return ft.Row(controles_fotos, spacing=15, scroll=ft.ScrollMode.ALWAYS)

    # --- LÓGICA CONSTRUCTORA DE FILAS EXPANDIBLES (Estructura de Fila) ---
    def crear_fila_habitacion_dinamica(d, color_base="transparent"):
        expandido = False
        modo_edicion = False  
        det = d.get("detalles")

        def btn_asignar_click(e):
            abrir_modal_asignacion(d["habitacion"].upper())

        btn_agregar_huesped = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.PERSON_ADD_ALT_1,
                icon_color="white",
                icon_size=16,
                on_click=btn_asignar_click,
                style=ft.ButtonStyle(padding=0)
            ),
            bgcolor="#00CC66", 
            border_radius=6,
            width=30,
            height=30,
            alignment=ft.Alignment(0, 0)
        )

        # Controles de texto para campos editables en caliente
        input_incluye = ft.TextField(value="", text_size=12, color="rgba(255,255,255,0.7)", bgcolor="#1E1E2F", border_color="rgba(255,255,255,0.2)", height=30, content_padding=5, text_align=ft.TextAlign.CENTER)
        input_cama = ft.TextField(value="", text_size=12, color="rgba(255,255,255,0.7)", bgcolor="#1E1E2F", border_color="rgba(255,255,255,0.2)", height=30, content_padding=5, text_align=ft.TextAlign.CENTER)
        input_vista = ft.TextField(value="", text_size=12, color="rgba(255,255,255,0.7)", bgcolor="#1E1E2F", border_color="rgba(255,255,255,0.2)", height=30, content_padding=5, text_align=ft.TextAlign.CENTER)
        
        panel_vista = ft.Container(expand=3, alignment=ft.Alignment(-0.06, 0))
        inputs_servicios = []
        panel_incluye = ft.Container(expand=2, alignment=ft.Alignment(-0.06, 0))
        panel_cama = ft.Container(expand=2, alignment=ft.Alignment(0, 0))
        columna_servicios = ft.Column(spacing=4)

        def dibujar_bloque_editable():
            if not det:
                return

            if modo_edicion:
                panel_incluye.content = input_incluye
                panel_cama.content = input_cama
                panel_vista.content = input_vista  
            else:
                panel_incluye.content = ft.Text(det["incluye"], color="rgba(255,255,255,0.7)", size=12, text_align=ft.TextAlign.CENTER)
                panel_cama.content = ft.Text(det["cama"], color="rgba(255,255,255,0.7)", size=12, text_align=ft.TextAlign.CENTER)
                
                panel_vista.content = ft.Column([
                    ft.Text(det["vista"], color="rgba(255,255,255,0.7)", size=12, text_align=ft.TextAlign.CENTER), 
                    ft.Text(det["sub_vista"], color="rgba(255,255,255,0.5)", size=11, text_align=ft.TextAlign.CENTER)
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

            columna_servicios.controls.clear()
            if modo_edicion:
                for inp in inputs_servicios:
                    columna_servicios.controls.append(
                        ft.Row([
                            ft.Text("•", color="white", size=13),
                            ft.Container(content=inp, width=150, height=28)
                        ], spacing=5)
                    )
            else:
                for s in det["servicios"]:
                    if s.strip():
                        columna_servicios.controls.append(
                            ft.Text(f"• {s}", color="rgba(255,255,255,0.8)", size=13)
                        )
            page.update()

        # --- PANEL DE CONTROL DE EDICIÓN INTERNA ---
        def alternar_modo_edicion(e):
            nonlocal modo_edicion
            modo_edicion = True
            
            input_incluye.value = det["incluye"]
            input_cama.value = det["cama"]
            input_vista.value = det["vista"]  
            
            inputs_servicios.clear()
            servs_actuales = det["servicios"] + [""] * (5 - len(det["servicios"]))
            for s in servs_actuales[:5]:
                inputs_servicios.append(
                    ft.TextField(value=s, text_size=13, color="white", bgcolor="#1E1E2F", border_color="rgba(255,255,255,0.2)", height=25, content_padding=5)
                )

            btn_engranaje.visible = False
            panel_botones_edicion.visible = True
            dibujar_bloque_editable()

        def cancelar_cambios(e):
            nonlocal modo_edicion
            modo_edicion = False
            btn_engranaje.visible = True
            panel_botones_edicion.visible = False
            dibujar_bloque_editable()

        def guardar_cambios(e):
            nonlocal modo_edicion
            modo_edicion = False
            
            det["incluye"] = input_incluye.value.strip()
            det["cama"] = input_cama.value.strip()
            det["vista"] = input_vista.value.strip()  
            
            nuevos_servicios = [inp.value.strip() for inp in inputs_servicios if inp.value.strip()]
            det["servicios"] = nuevos_servicios
            servicios_comas = ",".join(nuevos_servicios)

            conn = sqlite3.connect("starblim.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE habitaciones 
                SET incluye = ?, cama = ?, servicios = ?, vista = ? 
                WHERE habitacion = ?
            """, (det["incluye"], det["cama"], servicios_comas, det["vista"], d["habitacion"].upper()))
            conn.commit()
            conn.close()

            btn_engranaje.visible = True
            panel_botones_edicion.visible = False
            
            dibujar_bloque_editable()
            detalle.update()
            contenido_fila.update()

        btn_engranaje = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_color="rgba(255,255,255,0.6)",
            icon_size=20,
            tooltip="Editar Fila",
            on_click=alternar_modo_edicion
        )

        panel_botones_edicion = ft.Row([
            ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE, 
                icon_color="#00FFCC", 
                icon_size=22, 
                tooltip="Guardar Cambios",
                on_click=guardar_cambios
            ),
            ft.IconButton(
                icon=ft.Icons.CANCEL, 
                icon_color="#FF3366", 
                icon_size=22, 
                tooltip="Cancelar",
                on_click=cancelar_cambios
            )
        ], spacing=5, visible=False)

        control_edicion_izq = ft.Container(
            content=ft.Stack([btn_engranaje, panel_botones_edicion]),
            padding=Padding(0, 15, 0, 0)
        )

        dibujar_bloque_editable()

        detalle = ft.Container(
            visible=False, padding=Padding(20, 10, 20, 20),
            content=ft.Column([
                ft.Divider(height=1, color="rgba(255,255,255,0.2)"),
                ft.Row([
                    panel_vista,    
                    panel_incluye,  
                    panel_cama,     
                    ft.Container(expand=2, alignment=ft.Alignment(0.1, 0), content=ft.Text(det["reserva"], color="rgba(255,255,255,0.7)", size=12, text_align=ft.TextAlign.CENTER)) if det else ft.Container(expand=2),
                    ft.Container(expand=2, alignment=ft.Alignment(0.14, 0), content=ft.Column([ft.Text(det["desc_tit"], color="#FFB300", size=11, weight="bold", text_align=ft.TextAlign.CENTER), ft.Text(det["desc_val"], color="#00FFCC", size=13, weight="bold", text_align=ft.TextAlign.CENTER)], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)) if det else ft.Container(expand=2),
                    ft.Container(expand=2, alignment=ft.Alignment(0.2, 0), content=ft.Column([ft.Text(det["prom_tit"], color="#FFB300", size=11, weight="bold", text_align=ft.TextAlign.CENTER), ft.Text(det["prom_val"], color="#00FFCC", size=13, weight="bold", text_align=ft.TextAlign.CENTER)], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)) if det else ft.Container(expand=2),
                ]),

                ft.Container(height=15) if det else ft.Container(height=0),
                ft.Row([
                    ft.Column([
                        ft.Text("SERVICIOS INCLUIDOS", color="white", size=15, weight="bold"), 
                        columna_servicios,   
                        control_edicion_izq  
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(width=40), 
                    ft.Container(
                        expand=True, 
                        content=crear_galeria_con_lapiz(det["fotos"], det, d) if det else ft.Container()
                    )
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START) if det else ft.Container(height=0)
            ], spacing=15)
        )

        contenido_fila = ft.Container(
            bgcolor=color_base, border_radius=12, animate=200,
            border=Border(bottom=BorderSide(0.5, "rgba(255,255,255,0.1)")),
            content=ft.Column([
                ft.Container(
                    padding=Padding(12, 0, 12, 0),
                    height=60, 
                    content=ft.Row([
                        ft.Container(
                            expand=3,
                            height=60,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Stack([
                                ft.Container(
                                    expand=True,
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Column([
                                        ft.Text(d["habitacion"].upper(), color="white", weight="bold", size=13, text_align=ft.TextAlign.CENTER), 
                                        ft.Text(d.get("sub", "EDIFICIO 3 · PISO 2").upper(), color="rgba(255,255,255,0.5)", size=11, text_align=ft.TextAlign.CENTER)
                                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
                                ),
                                ft.Container(content=btn_agregar_huesped, left=5, top=15)  
                            ])
                        ),
                        ft.Container(expand=2, height=60, alignment=ft.Alignment(-0.05, 0), content=ft.Text(d["tipo"].upper(), color="rgba(255,255,255,0.8)", size=13, text_align=ft.TextAlign.CENTER)),
                        ft.Container(expand=2, height=60, alignment=ft.Alignment(0, 0), content=ft.Text(d["capacidad"].upper(), color="rgba(255,255,255,0.8)", size=13, text_align=ft.TextAlign.CENTER)),
                        ft.Container(expand=2, height=60, alignment=ft.Alignment(0.05, 0), content=ft.Text(d["estado"].upper(), color="#00FFCC" if d["estado"] == "DISPONIBLE" else "#FF3366", weight="bold", size=12, text_align=ft.TextAlign.CENTER)),
                        ft.Container(expand=2, height=60, alignment=ft.Alignment(0.1, 0), content=ft.Text(d["adulto"], color="#FFB300", weight="bold", size=13, text_align=ft.TextAlign.CENTER)),
                        ft.Container(expand=2, height=60, alignment=ft.Alignment(0.1, 0), content=ft.Text(d["nino"], color="#FFB300", weight="bold", size=13, text_align=ft.TextAlign.CENTER)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                ),
                detalle,
            ], spacing=0)
        )

        fila = ft.GestureDetector(
            content=contenido_fila,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda _: toggle()
        )

        def toggle():
            if modo_edicion:
                return 
            nonlocal expandido
            expandido = not expandido
            detalle.visible = expandido
            contenido_fila.bgcolor = color_fila_expandida if expandido else color_base
            page.update()

        def al_entrar_mouse(e):
            if not expandido:
                contenido_fila.bgcolor = color_fila_hover
                contenido_fila.update()

        def al_salir_mouse(e):
            if not expandido:
                contenido_fila.bgcolor = color_base
                contenido_fila.update()

        fila.on_enter = al_entrar_mouse
        fila.on_exit = al_salir_mouse
        return fila

    # --- LÓGICA PARA AGREGAR HABITACIÓN DESDE EL INICIO ---
    def registrar_habitacion(e):
        if txt_num.value and txt_cap.value and txt_pre_a.value:
            cant_filas = len(lista_habitaciones.controls)
            color_asignado = color_fila_par if cant_filas % 2 != 0 else color_fila_impar
            
            datos_nueva = {
                "habitacion": txt_num.value, 
                "tipo": "ESTÁNDAR", 
                "sub": "EDIFICIO EXTRA · PISO 1",
                "capacidad": txt_cap.value, 
                "estado": "DISPONIBLE", 
                "adulto": f"USD {txt_pre_a.value}", 
                "nino": f"USD {txt_pre_n.value if txt_pre_n.value else '0.00'}",
                "detalles": None
            }
            lista_habitaciones.controls.append(crear_fila_habitacion_dinamica(datos_nueva, color_base=color_asignado))
            
            txt_num.value = ""
            txt_cap.value = ""
            txt_pre_a.value = ""
            txt_pre_n.value = ""
            dialogo_registro.open = False
            page.update()

    # --- FORMULARIO FLOTANTE DE ASIGNACIÓN RÁPIDA ---
    txt_nombre_huesped = ft.TextField(label="Nombre del Huésped", **input_style)
    habitacion_seleccionada_label = ft.Text("", color="white", size=16, weight="bold")

    def guardar_asignacion(e):
        txt_nombre_huesped.value = ""
        dialogo_asignacion.open = False
        page.update()

    dialogo_asignacion = ft.AlertDialog(
        bgcolor="#150C1E",
        title=habitacion_seleccionada_label,
        content=ft.Column([txt_nombre_huesped], spacing=10, height=80, width=300),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: setattr(dialogo_asignacion, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("CONFIRMAR", on_click=guardar_asignacion, style=ft.ButtonStyle(color="#00FFCC")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_asignacion)

    def abrir_modal_asignacion(num_hab):
        habitacion_seleccionada_label.value = f"ASIGNAR HUÉSPED - {num_hab}"
        dialogo_asignacion.open = True
        page.update()

    # --- VENTANA FLOTANTE DE REGISTRO ---
    dialogo_registro = ft.AlertDialog(
        bgcolor="#150C1E",
        title=ft.Text("REGISTRAR NUEVA HABITACIÓN", color="white", size=16, weight="bold"),
        content=ft.Column([txt_num, txt_cap, txt_pre_a, txt_pre_n], spacing=10, height=220, width=300),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: setattr(dialogo_registro, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("GUARDAR", on_click=registrar_habitacion, style=ft.ButtonStyle(color="#FFB300")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_registro)

    def abrir_modal_registro(e):
        dialogo_registro.open = True
        page.update()

    # =========================================================================
    # --- MOTOR ECONÓMICO PREMIUM V3: AJUSTE UNIFICADO POR CATEGORÍAS ---
    # =========================================================================
    
    dropdown_accion_precio = ft.Dropdown(
        label="ACCIÓN COMERCIAL",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.6)", size=11),
        height=45, text_size=13, color="white", filled=True, fill_color="#141923",
        border_color="rgba(255, 255, 255, 0.4)", border_radius=8,
        options=[
            ft.dropdown.Option("AUMENTAR", "➕ AUMENTAR PRECIOS"),
            ft.dropdown.Option("BAJAR", "➖ BAJAR PRECIOS"),
        ],
        value="AUMENTAR"
    )

    dropdown_alcance_precio = ft.Dropdown(
        label="ALCANCE DEL AJUSTE",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.6)", size=11),
        height=45, text_size=13, color="white", filled=True, fill_color="#141923",
        border_color="rgba(255, 255, 255, 0.4)", border_radius=8,
        menu_height=160,
    )

    def recargar_dropdown_alcance_desde_db():
        dropdown_alcance_precio.options = [
            ft.dropdown.Option("TODOS", "🌎 TODO EL INVENTARIO")
        ]
        
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT tipo FROM habitaciones WHERE tipo IS NOT NULL AND tipo != '' ORDER BY tipo ASC")
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            cat_name = r[0].upper().strip()
            dropdown_alcance_precio.options.append(
                ft.dropdown.Option(
                    key=f"CAT:{cat_name}", 
                    text=f"🔹 SOLO {cat_name}"
                )
            )
        dropdown_alcance_precio.value = "TODOS"

    txt_porcentaje_ajuste = ft.TextField(
        label="PORCENTAJE (%)",
        **input_style,
        keyboard_type=ft.KeyboardType.NUMBER
    )

    def ejecutar_guardado_persistente_sqlite(e):
        porcentaje = float(txt_porcentaje_ajuste.value) / 100.0
        factor = (1.0 + porcentaje) if dropdown_accion_precio.value == "AUMENTAR" else (1.0 - porcentaje)
        
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()

        if dropdown_alcance_precio.value == "TODOS":
            cursor.execute("SELECT habitacion, adulto, nino FROM habitaciones")
        else:
            cat_seleccionada = dropdown_alcance_precio.value.replace("CAT:", "")
            cursor.execute("SELECT habitacion, adulto, nino FROM habitaciones WHERE UPPER(tipo) = ?", (cat_seleccionada,))
        
        habitaciones_a_modificar = cursor.fetchall()

        for hab in habitaciones_a_modificar:
            id_hab = hab[0]
            try:
                precio_a_limpio = float(hab[1].replace("USD", "").strip())
                nuevo_adulto = f"USD {precio_a_limpio * factor:.2f}"
            except: nuevo_adulto = hab[1]
                
            try:
                precio_n_limpio = float(hab[2].replace("USD", "").strip())
                nuevo_nino = f"USD {precio_n_limpio * factor:.2f}"
            except: nuevo_nino = hab[2]

            cursor.execute("UPDATE habitaciones SET adulto = ?, nino = ? WHERE habitacion = ?", (nuevo_adulto, nuevo_nino, id_hab))

        conn.commit()
        conn.close()

        txt_porcentaje_ajuste.value = ""
        dialogo_critico_precios.open = False
        dialogo_ajuste_masivo.open = False
        page.update()
        aplicar_filtros_universales(None)

    # === CANDADOS DE CONFIRMACIÓN CRÍTICA (VERSIÓN LIMPIA Y SIN DUPLICADOS) ===
    
    # 1. Ventana de Advertencia de Peligro Irreversible (El segundo candado)
    dialogo_critico_precios = ft.AlertDialog(
        bgcolor="#0B0E14",
        title=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color="#FFB300"), ft.Text("CONFIRMACIÓN CRÍTICA", color="#FFB300", size=14, weight="bold")]),
        content=ft.Container(
            width=320, height=90,
            content=ft.Text("¿Está completamente seguro de realizar esta acción masiva? Los registros de la base de datos se modificarán de forma permanente e irreversible.", color="white", size=14.5)
        ),
        actions=[
            ft.TextButton("NO, CANCELAR", on_click=lambda _: setattr(dialogo_critico_precios, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("SÍ, CONFIRMAR", on_click=ejecutar_guardado_persistente_sqlite, style=ft.ButtonStyle(color="#00FFCC")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_critico_precios)

    def abrir_segundo_candado_precios(e):
        if not txt_porcentaje_ajuste.value: return
        try:
            float(txt_porcentaje_ajuste.value)
            dialogo_critico_precios.open = True
            page.update()
        except ValueError:
            txt_porcentaje_ajuste.error_text = "Número inválido"
            page.update()

    # Ventana principal calibrada de tarifas masivas
    dialogo_ajuste_masivo = ft.AlertDialog(
        bgcolor="#0B0E14",
        title=ft.Text("AJUSTE GLOBAL DE TARIFAS", color="#00F7FF", size=16, weight="bold"),
        content=ft.Container(
            width=340, height=285, 
            content=ft.Column([
                ft.Column([
                    ft.Text("INSTRUCCIÓN OPERATIVA:", color="white", size=13.5, weight="bold"),
                    ft.Row([
                        ft.Text("•", color="white", size=13.5, weight="bold"),
                        ft.Container(expand=True, content=ft.Text("AUMENTAR: Aplica una suba a los precios actuales.", color="white", size=13.5))
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Row([
                        ft.Text("•", color="white", size=13.5, weight="bold"),
                        ft.Container(expand=True, content=ft.Text("BAJAR: Aplica una reducción a los precios actuales.", color="white", size=13.5))
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Row([
                        ft.Text("•", color="white", size=13.5, weight="bold"),
                        ft.Container(expand=True, content=ft.Text("ALCANCE: Permite ajustar el aumento a todo el hotel o solo por categoría.", color="white", size=13.5))
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                ], spacing=4),
                ft.Container(height=4),
                dropdown_accion_precio,
                dropdown_alcance_precio, 
                txt_porcentaje_ajuste 
            ], spacing=10, tight=True)
        ),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: setattr(dialogo_ajuste_masivo, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("APLICAR", on_click=abrir_segundo_candado_precios, style=ft.ButtonStyle(color="#00F7FF")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_ajuste_masivo)

    def abrir_modal_ajuste_masivo(e):
        recargar_dropdown_alcance_desde_db()
        dialogo_ajuste_masivo.open = True
        page.update()

    # === CANDADOS DE SEGURIDAD Y EVENTOS PARA EL SWITCH DE IVA ===
    def confirmar_activacion_iva(e):
        dialogo_verificar_iva.open = False
        aplicar_filtros_universales(None)
        page.update()

    def cancelar_activacion_iva(e):
        switch_activar_iva.value = not switch_activar_iva.value
        dialogo_verificar_iva.open = False
        page.update()

    dialogo_verificar_iva = ft.AlertDialog(
        bgcolor="#0B0E14",
        modal=True, 
        title=ft.Row([ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, color="#00F7FF"), ft.Text("VERIFICACIÓN DE IMPUESTOS", color="#00F7FF", size=16, weight="bold")]),
        content=ft.Container(
            width=340, height=150, 
            content=ft.Text(
                "Usted está por alterar el cálculo impositivo global.\n\n"
                "El IVA (21%) afectará únicamente a los precios de los alojamientos visibles en las grillas (Precio Adultos/Niños). El IVA se va a adaptar de manera automatica a los descuentos o cupones que crees. Si se desactiva volveran los precios base originales", 
                color="white", 
                size=14.5 
            )
        ),
        actions=[
            ft.TextButton("CANCELAR", on_click=cancelar_activacion_iva, style=ft.ButtonStyle(color="white", text_style=ft.TextStyle(size=13, weight="bold"))),
            ft.TextButton("PROCEDER", on_click=confirmar_activacion_iva, style=ft.ButtonStyle(color="#00F7FF", text_style=ft.TextStyle(size=13, weight="bold"))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_verificar_iva)

    def gatillar_alerta_iva_reactiva(e):
        dialogo_verificar_iva.open = True
        page.update()

    # =========================================================================
    # --- MÓDULO COMERCIAL V3: TEMPORADAS CON BOTÓN DE CANCELACIÓN INTEGRADO ---
    # =========================================================================
    
    cartel_estado_temporada = ft.Container(
        content=ft.Row([
            ft.Text("", color="white", size=11.5, weight="bold", text_align=ft.TextAlign.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        padding=ft.Padding(10, 4, 10, 4), 
        border_radius=6,
        alignment=ft.Alignment(0, 0),
        margin=ft.Padding(bottom=5)
    )

    def eliminar_descuento_temporada_db(e):
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE habitaciones SET desc_tit = NULL, desc_val = 'USD 0.00'")
        conn.commit()
        conn.close()

        dialogo_temporada.open = False
        page.update()
        aplicar_filtros_universales(None)

    def chequear_y_dibujar_marquesina_temporada():
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT desc_tit, desc_val FROM habitaciones WHERE desc_tit IS NOT NULL AND desc_tit != 'DESCUENTO' AND desc_val != 'USD 0.00' LIMIT 1")
        registro = cursor.fetchone()
        conn.close()

        cartel_estado_temporada.content.controls.clear()

        if registro:
            titulo_temp = registro[0].upper()
            monto_temp = registro[1].replace("USD", "").strip()
            try:
                monto_formateado = f"{float(monto_temp):.0f}%"
            except:
                monto_formateado = f"{monto_temp}%"
                
            cartel_estado_temporada.height = 38
            cartel_estado_temporada.bgcolor = "#0D47A1" 
            
            cartel_estado_temporada.content.controls.append(
                ft.Text(f"🔥 ACTIVO: {titulo_temp} · REBAJA DEL {monto_formateado}", color="white", size=11.5, weight="bold")
            )
            cartel_estado_temporada.content.controls.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_ROUNDED,
                    icon_color="#FF5722", 
                    icon_size=16,
                    padding=0, 
                    tooltip="Eliminar temporada activa",
                    on_click=eliminar_descuento_temporada_db
                )
            )
        else:
            cartel_estado_temporada.height = 38
            cartel_estado_temporada.bgcolor = "#154360"
            cartel_estado_temporada.content.controls.append(
                ft.Text("ℹ️ ESTADO: SIN TEMPORADAS ESPECIALES ACTIVAS", color="white", size=11.5, weight="bold")
            )

    txt_nombre_temporada = ft.TextField(
        label="NOMBRE DE LA REBAJA",
        value="TEMP. BAJA",
        **input_style
    )

    txt_fecha_inicio = ft.TextField(
        label="FECHA INICIO (D/M)",
        value=datetime.now().strftime("%d/%m"),
        width=165,
        **input_style
    )
    txt_fecha_fin = ft.TextField(
        label="FECHA FIN (D/M)",
        value=datetime.now().strftime("%d/%m"),
        width=165,
        **input_style
    )

    dropdown_alcance_temporada = ft.Dropdown(
        label="ALCANCE DEL DESCUENTO",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.6)", size=11),
        height=45, text_size=13, color="white", filled=True, fill_color="#141923",
        border_color="rgba(255, 255, 255, 0.4)", border_radius=8,
        menu_height=160,
    )

    def recargar_dropdown_temporada_desde_db():
        dropdown_alcance_temporada.options = [ft.dropdown.Option("TODOS", "🌎 TODO EL INVENTARIO")]
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT tipo FROM habitaciones WHERE tipo IS NOT NULL AND tipo != '' ORDER BY tipo ASC")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            cat_name = r[0].upper().strip()
            dropdown_alcance_temporada.options.append(ft.dropdown.Option(key=f"CAT:{cat_name}", text=f"🔹 SOLO {cat_name}"))
        dropdown_alcance_temporada.value = "TODOS"

    txt_porcentaje_temporada = ft.TextField(
        label="DESCUENTO (%)",
        **input_style,
        keyboard_type=ft.KeyboardType.NUMBER
    )

    def guardar_descuento_temporada_db(e):
        if not txt_porcentaje_temporada.value or not txt_nombre_temporada.value: return
        try:
            monto_porcentaje = float(txt_porcentaje_temporada.value)
            valor_db = f"{monto_porcentaje:.2f}"
        except: return

        rango_fechas_texto = f"{txt_fecha_inicio.value.strip()}-{txt_fecha_fin.value.strip()}"
        nombre_final_titulo = f"{txt_nombre_temporada.value.strip().upper()} ({rango_fechas_texto})"
        
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()

        if dropdown_alcance_temporada.value == "TODOS":
            cursor.execute("UPDATE habitaciones SET desc_tit = ?, desc_val = ?", (nombre_final_titulo, valor_db))
        else:
            cat_puro = dropdown_alcance_temporada.value.replace("CAT:", "")
            cursor.execute("UPDATE habitaciones SET desc_tit = ?, desc_val = ? WHERE UPPER(tipo) = ?", (nombre_final_titulo, valor_db, cat_puro))
        
        conn.commit()
        conn.close()

        txt_porcentaje_temporada.value = ""
        txt_nombre_temporada.value = "TEMP. BAJA"
        dialogo_temporada.open = False
        page.update()
        aplicar_filtros_universales(None)

    dialogo_temporada = ft.AlertDialog(
        bgcolor="#0B0E14",
        title=ft.Row([
            ft.Text("PROGRAMAR DESCUENTO POR TEMPORADA", color="#00F7FF", size=15, weight="bold")
        ], alignment=ft.MainAxisAlignment.CENTER),
        content=ft.Container(
            width=400, height=380,
            content=ft.Column([
                cartel_estado_temporada,
                ft.Column([
                    ft.Text("INSTRUCCIÓN OPERATIVA:", color="white", size=13.5, weight="bold", text_align=ft.TextAlign.CENTER),
                    ft.Text("Configura una rebaja con vencimiento para todo el hotel o solo para una categoria.", color="white", size=13.5, text_align=ft.TextAlign.CENTER),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=400),
                ft.Container(height=4),
                txt_nombre_temporada, 
                dropdown_alcance_temporada,
                ft.Container(height=2),
                ft.Row([txt_fecha_inicio, txt_fecha_fin], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10),
                txt_porcentaje_temporada
            ], spacing=10, tight=True)
        ),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: setattr(dialogo_temporada, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("APLICAR", on_click=guardar_descuento_temporada_db, style=ft.ButtonStyle(color="#00F7FF")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_temporada)

    def abrir_modal_temporada(e):
        chequear_y_dibujar_marquesina_temporada()
        recargar_dropdown_temporada_desde_db()
        dialogo_temporada.open = True
        page.update()

    # --- VENTANA FLOTANTE: VISOR DE GALERÍA INDEPENDIENTE POR FILA ---
    imagen_visor = ft.Image(src="fondo.png", fit="contain", height=420)
    texto_contador = ft.Text("", color="rgba(255,255,255,0.8)", size=14, weight="bold")

    def actualizar_estado_visor():
        nonlocal indice_actual
        imagen_visor.src = lista_fotos_actual[indice_actual]
        texto_contador.value = f"IMAGEN {indice_actual + 1} / {len(lista_fotos_actual)}"
        btn_retroceder.disabled = (indice_actual == 0)
        btn_avanzar.disabled = (indice_actual == len(lista_fotos_actual) - 1)
        page.update()

    def avanzar_foto(e):
        nonlocal indice_actual
        if indice_actual < len(lista_fotos_actual) - 1:
            indice_actual += 1
            actualizar_estado_visor()

    def retroceder_foto(e):
        nonlocal indice_actual
        if indice_actual > 0:
            indice_actual -= 1
            actualizar_estado_visor()

    btn_retroceder = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_IOS_NEW, icon_color="white", icon_size=24,
        on_click=retroceder_foto, style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: "rgba(255,255,255,0.1)"})
    )
    btn_avanzar = ft.IconButton(
        icon=ft.Icons.ARROW_FORWARD_IOS, icon_color="white", icon_size=24,
        on_click=avanzar_foto, style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: "rgba(255,255,255,0.1)"})
    )

    dialogo_visor_galeria = ft.AlertDialog(
        bgcolor="blueaccent,0.46", 
        content=ft.Container(
            width=850,
            padding=Padding(4, 5, 4, 5),
            border_radius=12,
            content=ft.Column([
                ft.Row([
                    btn_retroceder,
                    ft.Container(content=imagen_visor, expand=True, alignment=ft.Alignment(0, 0)),
                    btn_avanzar
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(height=6), 
                
                ft.Row([
                    ft.Container(width=40), 
                    ft.Container(content=texto_contador, expand=True, alignment=ft.Alignment(0, 0)),
                    ft.TextButton(
                        "CERRAR", 
                        on_click=lambda _: setattr(dialogo_visor_galeria, "open", False) or page.update(), 
                        style=ft.ButtonStyle(color="white")
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], tight=True, spacing=0)
        )
    )
    page.overlay.append(dialogo_visor_galeria)

    # =========================================================================
    # --- MÓDULO AUTÓNOMO: PANEL DE ADMINISTRACIÓN PREMIUM (PARTE 1) ---
    # =========================================================================
    dialogo_escala_info = ft.AlertDialog(
        bgcolor="#141923",  
        title=ft.Text("ESCALA DE ACTIVIDAD", color="#A855F7", size=14, weight="bold"),
        content=ft.Column([
            ft.Row([ft.Container(width=16, height=16, bgcolor="#00F7FF", border_radius=4), ft.Text("NIVEL 4  ·  ACTIVIDAD PICO", size=11, color="white", weight="bold")]),
            ft.Row([ft.Container(width=16, height=16, bgcolor="#8C3AFF", border_radius=4), ft.Text("NIVEL 3  ·  ACTIVIDAD ALTA", size=11, color="white")]),
            ft.Row([ft.Container(width=16, height=16, bgcolor="#4C2277", border_radius=4), ft.Text("NIVEL 2  ·  ACTIVIDAD MEDIA", size=11, color="white")]),
            ft.Row([ft.Container(width=16, height=16, bgcolor="#2A1B40", border_radius=4), ft.Text("NIVEL 1  ·  ACTIVIDAD BAJA", size=11, color="white")]),
            ft.Row([ft.Container(width=16, height=16, bgcolor="#161920", border_radius=4), ft.Text("NIVEL 0  ·  SIN ACTIVIDAD / CERRADO", size=11, color="white")]),
        ], spacing=12, height=140, width=260),
        actions=[
            ft.TextButton("ENTENDIDO", on_click=lambda _: setattr(dialogo_escala_info, "open", False) or page.update(), style=ft.ButtonStyle(color="#00F7FF"))
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    page.overlay.append(dialogo_escala_info)

    def abrir_escala_info(e):
        dialogo_escala_info.open = True
        page.update()

    datos_tarjetas = [
        {"titulo": "INGRESO DEL DÍA", "valor": "$16,957.00", "sub": "+0.67% vs ayer", "color_sub": "#00F7FF", "tooltip": None},
        {"titulo": "INGRESO MENSUAL", "valor": "$12,050.00", "sub": "Acumulado período actual", "color_sub": "white", "tooltip": None},
        {"titulo": "OCUPACIÓN DEL DÍA", "valor": "78.4%", "sub": "", "color_sub": "transparent", "tooltip": "15 HABITACIONES OCUPADAS  ·  5 DISPONIBLES"}
    ]

    matriz_actividad = [
        [2, 3, 1, 2, 2, 4, 3],  # 08 AM
        [4, 4, 3, 4, 4, 2, 2],  # 10 AM
        [2, 2, 2, 3, 3, 4, 4],  # 12 PM
        [4, 4, 4, 4, 4, 3, 3],  # 02 PM
        [3, 4, 3, 2, 4, 3, 3],  # 04 PM
        [2, 2, 1, 2, 3, 2, 2],  # 06 PM
        [1, 1, 2, 1, 2, 3, 3],  # 08 PM
        [0, 1, 0, 0, 1, 2, 2]   # 10 PM
    ]
    
    colores_calor = {
        0: "#161920", 1: "#2A1B40", 2: "#4C2277", 3: "#8C3AFF", 4: "#00F7FF"
    }

    valores_montaña = [
        {"mes": "ENE", "h": 60, "pico": False}, 
        {"mes": "FEB", "h": 80, "pico": False}, 
        {"mes": "MAR", "h": 100, "pico": False}, 
        {"mes": "ABR", "h": 85, "pico": False}, 
        {"mes": "MAY", "h": 75, "pico": False}, 
        {"mes": "JUN", "h": 110, "pico": False}, 
        {"mes": "JUL", "h": 145, "pico": False}, 
        {"mes": "AGO", "h": 175, "pico": True},  
        {"mes": "SEP", "h": 155, "pico": False}, 
        {"mes": "OCT", "h": 135, "pico": False}, 
        {"mes": "NOV", "h": 160, "pico": False}, 
        {"mes": "DIC", "h": 195, "pico": False}
    ]

    categorias_hotel = [
        {"nom": "Suite Presidencial", "porc": 85},
        {"nom": "Junior Suite", "porc": 70},
        {"nom": "Familiar Premium", "porc": 60},
        {"nom": "Doble Estándar", "porc": 92},
        {"nom": "Single Ejecutiva", "porc": 45}
    ]

    # =========================================================================
    # --- MÓDULO AUTÓNOMO: PANEL DE ADMINISTRACIÓN PREMIUM (PARTE 2) ---
    # =========================================================================
    panel_auditoria = ft.Container(
        visible=False, bgcolor="#1E1233", padding=15, border_radius=10,
        content=ft.Column([
            ft.Text("Métricas de Rendimiento Histórico de Empleados", size=13, color="#00F7FF", weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Text("Carlos (Turno Tarde): Caja: +12% | Ocupación: 88% | Eficiencia HP: Óptima", size=11, color="white"),
                ft.Text("Juan (Turno Mañana): Caja: -2% | Ocupación: 71% | Eficiencia HP: Media", size=11, color="white")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ])
    )

    def toggle_auditoria(e):
        panel_auditoria.visible = not panel_auditoria.visible
        btn_auditar.icon_color = "#00F7FF" if panel_auditoria.visible else "white"
        page.update()

    btn_auditar = ft.IconButton(icon=ft.Icons.SETTINGS, icon_size=18, icon_color="white", tooltip="Modo Auditoría", on_click=toggle_auditoria)

    cabecera_admin = ft.Row(
        controls=[
            ft.Row([
                ft.Container(width=36, height=36, bgcolor="#621CA8", border_radius=18, alignment=ft.Alignment(0, 0), content=ft.Icon(ft.Icons.PERSON, color="white", size=20)),
                ft.Column([
                    ft.Text("Buenas tardes, Carlos", size=16, color="white", weight=ft.FontWeight.BOLD),
                    ft.Text("Administrador de Turno • Sesión Activa", size=11, color="white")
                ], spacing=1)
            ]),
            btn_auditar
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    tarjetas_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Text(t["titulo"], size=11, color="white", weight=ft.FontWeight.W_300),
                    ft.Text(t["valor"], size=20, color="white", weight=ft.FontWeight.BOLD),
                    ft.Text(t["sub"], size=10, color=t["color_sub"])
                ], spacing=2),
                bgcolor="#141923", padding=12, border_radius=8, expand=True,
                tooltip=t.get("tooltip") 
            ) for t in datos_tarjetas
        ], spacing=8
    )

    # --- MAPA DE CALOR ---
    filas_mapa = []
    horas_labels = ["08 AM", "10 AM", "12 PM", "02 PM", "04 PM", "06 PM", "08 PM", "10 PM"]
    dias_labels = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]

    filas_mapa.append(ft.Row([ft.Container(width=55)] + [ft.Container(width=30, content=ft.Text(d, size=11, color="white", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) for d in dias_labels], spacing=6))
    for i, hora in enumerate(horas_labels):
        bloques_fila = [ft.Container(width=55, content=ft.Text(hora, size=11, color="white", weight=ft.FontWeight.W_300))]
        for j in range(7):
            nivel = matriz_actividad[i][j]
            bloques_fila.append(ft.Container(width=30, height=30, bgcolor=colores_calor[nivel], border_radius=5))
        filas_mapa.append(ft.Row(controls=bloques_fila, spacing=6))

    btn_info_mapa = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE, 
            icon_size=16, 
            icon_color="rgba(255,255,255,0.4)", 
            tooltip="Ver escala de actividad", 
            mouse_cursor=ft.MouseCursor.CLICK,
            on_click=abrir_escala_info,
            style=ft.ButtonStyle(padding=0, visual_density=ft.VisualDensity.COMPACT)
        ),
        padding=Padding(0, -8, 0, 2) 
    )

    bloque_heatmap = ft.Container(
        bgcolor="#141923", padding=15, border_radius=10, 
        width=345, height=365, 
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Text("ACTIVIDAD POR HORARIO", size=13, color="#A855F7", weight=ft.FontWeight.BOLD),
                    padding=Padding(top=-2, left=0, right=0, bottom=0)
                ),
                btn_info_mapa
            ], spacing=6, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Container(height=10), 
            ft.Container(
                content=ft.Column(filas_mapa, spacing=6),
                margin=Padding(left=0, top=-12, right=0, bottom=0)
            )
        ], spacing=2) 
    )

    # --- LA MONTAÑA ANUAL ---
    bloques_montaña = []
    for item in valores_montaña:
        contenido_bloque = ft.Column(
            [
                ft.Text("PICO" if item["pico"] else "", size=8, color="#39FF14", weight=ft.FontWeight.BOLD) if item["pico"] else ft.Container(height=10),
                ft.Container(
                    width=24,
                    height=item["h"],
                    gradient=ft.LinearGradient(
                        colors=["#39FF14", "#0D3A16"],
                        begin=ft.Alignment(0, -1),
                        end=ft.Alignment(0, 1)
                    ),
                    border_radius=3
                ),
                ft.Container(height=4),
                ft.Text(item["mes"], size=9, color="white", weight=ft.FontWeight.W_500)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.END
        )
        bloques_montaña.append(contenido_bloque)

    grafico_montaña_real = ft.Row(
        controls=bloques_montaña,
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.END,
        spacing=2,  
        expand=True
    )

    bloque_montaña_izq = ft.Container(
        bgcolor="#141923", padding=15, border_radius=10, 
        expand=True, height=365, 
        content=ft.Column([
            ft.Text("CONTROL DE PRECIOS (LA MONTAÑA ANUAL)", size=13, color="#39FF14", weight=ft.FontWeight.BOLD),
            ft.Text("Tendencias para tarifas dinámicas.", size=11, color="white"),
            ft.Container(height=10),
            ft.Container(content=grafico_montaña_real, expand=True) 
        ], spacing=2)
    )

    fila_graficos_centrales = ft.Row([bloque_heatmap, bloque_montaña_izq], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

    # --- RENDIMIENTO POR CATEGORÍA ---
    lista_barras_categorias_cian = ft.Column(
        controls=[
            ft.Column([
                ft.Row([
                    ft.Text(c["nom"].upper(), size=12, color="white", weight=ft.FontWeight.W_500), 
                    ft.Text(f"{c['porc']}%", size=12, color="#00F7FF", weight=ft.FontWeight.BOLD) 
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    height=14, width=760, bgcolor="#161920", border_radius=7,
                    alignment=ft.Alignment(-1, 0), 
                    content=ft.Container(
                        height=14, 
                        width=(c["porc"] / 100) * 760, 
                        border_radius=7,
                        gradient=ft.LinearGradient(colors=["#621CA8", "#00F7FF"]) 
                    )
                )
            ], spacing=4) for c in categorias_hotel
        ],
        spacing=12
    )

    bloque_categorias_abajo = ft.Container(
        bgcolor="#141923", padding=15, border_radius=10,
        content=ft.Column([
            ft.Text("RENDIMIENTO DE CATEGORÍAS", size=13, color="white", weight=ft.FontWeight.BOLD),
            ft.Container(height=5),
            lista_barras_categorias_cian
        ])
    )

    # CONTENEDOR PRINCIPAL DEL DASHBOARD CON SCROLL
    contenido_dash = ft.Column(
        [cabecera_admin, panel_auditoria, tarjetas_row, fila_graficos_centrales, bloque_categorias_abajo], 
        spacing=12, 
        scroll=ft.ScrollMode.AUTO
    )

    # --- LÓGICA DE NAVEGACIÓN Y APERTURA DE PESTAÑAS ---
    vista_activa = ft.Container(content=contenido_dash, expand=True)

    def ir_a_tab1(e):
        vista_activa.content = contenido_dash
        t1.color, t3.color = "#00F7FF", "white"
        page.update()

    def ir_a_tab3(e):
        vista_activa.content = contenido_inventario
        t1.color, t3.color = "white", "#00F7FF"
        page.update()

    t1 = ft.Text("DASHBOARD CENTRALIZADO", size=14, color="#00F7FF", weight=ft.FontWeight.BOLD)
    t3 = ft.Text("INVENTARIO DE HAB.", size=14, color="white", weight=ft.FontWeight.BOLD)

    fila_pestañas = ft.Row(
        controls=[
            ft.GestureDetector(on_tap=ir_a_tab1, mouse_cursor=ft.MouseCursor.CLICK, content=t1),
            ft.Container(width=20),
            ft.GestureDetector(on_tap=ir_a_tab3, mouse_cursor=ft.MouseCursor.CLICK, content=t3)
        ],
        alignment=ft.MainAxisAlignment.START
    )

    # --- CONTENEDOR MAESTRO ADAPTATIVO MODAL ---
    dialogo_admin_secreto = ft.AlertDialog(
        bgcolor="#0B0E14",
        content=ft.Container(
            width=850 if page.width < 1200 else (page.width * 0.75), 
            height=540 if page.height < 800 else (page.height * 0.70),
            content=ft.Column([
                fila_pestañas,
                ft.Container(height=1, bgcolor="#141923"),
                vista_activa
            ], expand=True)
        )
    )
    page.overlay.append(dialogo_admin_secreto)

    def abrir_panel_secreto_optimo(e):
        dialogo_admin_secreto.open = True
        page.update()

    # =========================================================================
    # --- PESTAÑA INVENTARIO DE HABITACIONES PREMIUM (FORMULARIO ADAPTADO V3) ---
    # =========================================================================
    input_style_inventario = {
        "border_color": "rgba(255, 255, 255, 0.4)",
        "focused_border_color": "#00F7FF", 
        "color": "white",
        "cursor_color": "#00F7FF",
        "height": 40,
        "text_size": 13,
        "border_radius": 8,
    }

    # Definición de los 7 campos en el orden lógico solicitado
    inv_txt_num = ft.TextField(label="N° CABAÑA / HAB.", **input_style_inventario)
    inv_txt_ubicacion = ft.TextField(label="UBICACIÓN (Ej: EDIFICIO 3 · PISO 2)", **input_style_inventario)
    inv_txt_tipo = ft.TextField(label="TIPO DE UNIDAD (Ej: SUITE)", **input_style_inventario)
    
    inv_cb_estado = ft.Dropdown(
        label="ESTADO INICIAL",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.6)", size=10), # <--- CORREGIDO: label_style
        height=40,
        text_size=12,
        color="white",
        filled=True,
        fill_color="#141923",
        border_color="rgba(255, 255, 255, 0.4)",
        border_radius=8,
        options=[
            ft.dropdown.Option("DISPONIBLE"),
            ft.dropdown.Option("OCUPADA"),
            ft.dropdown.Option("MANTENIMIENTO"),
        ],
        value="DISPONIBLE"
    )

    inv_txt_cap = ft.TextField(label="CAPACIDAD TOTAL", **input_style_inventario)
    inv_txt_pre_a = ft.TextField(label="PRECIO ADULTOS (USD)", **input_style_inventario)
    inv_txt_pre_n = ft.TextField(label="PRECIO NIÑOS (USD)", **input_style_inventario)

    lista_inventario_filas = ft.ListView(expand=True, spacing=8)

    # Motor transaccional para inyectar nuevas unidades físicas
    def ejecutar_alta_inventario(e):
        if not inv_txt_num.value or not inv_txt_pre_a.value:
            return

        num_hab = inv_txt_num.value.upper().strip()
        ubicacion_hab = inv_txt_ubicacion.value.upper().strip() if inv_txt_ubicacion.value else "EDIFICIO EXTRA · PISO 1"
        tipo_hab = inv_txt_tipo.value.upper().strip() if inv_txt_tipo.value else "ESTÁNDAR"
        estado_hab = inv_cb_estado.value.upper()
        cap_hab = f"{inv_txt_cap.value.strip()} PERSONAS" if inv_txt_cap.value else "2 PERSONAS"
        
        try:
            precio_a = f"USD {float(inv_txt_pre_a.value.replace('USD', '').strip()):.2f}"
            precio_n = f"USD {float(inv_txt_pre_n.value.replace('USD', '').strip()):.2f}" if inv_txt_pre_n.value else "USD 0.00"
        except ValueError:
            return

        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO habitaciones VALUES (?, ?, ?, ?, ?, ?, ?, 
                    'Vista general', ?, 'No especificado', 'Ninguna', 
                    'Reserva inmediata', 'DESCUENTO', 'USD 0.00', 'PROMOCIÓN', 'USD 0.00', 
                    'WIFI,AIRE ACONDICIONADO', 'fondo.png,fondo.png,fondo.png,fondo.png')
            """, (num_hab, ubicacion_hab, tipo_hab, estado_hab, cap_hab, precio_a, precio_n, ubicacion_hab))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return
        conn.close()

        # Limpieza higiénica de casillas
        inv_txt_num.value = ""
        inv_txt_ubicacion.value = ""
        inv_txt_tipo.value = ""
        inv_cb_estado.value = "DISPONIBLE"
        inv_txt_cap.value = ""
        inv_txt_pre_a.value = ""
        inv_txt_pre_n.value = ""
        
        dialogo_alta_inventario.open = False
        page.update()
        
        try: aplicar_filtros_universales(None)
        except: pass

    # Ventana modal acoplada al motor de guardado superior
    dialogo_alta_inventario = ft.AlertDialog(
        bgcolor="#0B0E14", 
        title=ft.Text("REGISTRAR UNIDAD AL INVENTARIO", color="#00F7FF", size=14, weight="bold"),
        content=ft.Container(
            width=340,
            height=350,  
            content=ft.Column(
                [
                    inv_txt_num, 
                    inv_txt_ubicacion, 
                    inv_txt_tipo, 
                    inv_cb_estado, 
                    inv_txt_cap, 
                    inv_txt_pre_a, 
                    inv_txt_pre_n
                ], 
                spacing=10, 
                scroll=ft.ScrollMode.AUTO,
                tight=True
            )
        ),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: setattr(dialogo_alta_inventario, "open", False) or page.update(), style=ft.ButtonStyle(color="white")),
            ft.TextButton("AGREGAR", on_click=ejecutar_alta_inventario, style=ft.ButtonStyle(color="#00F7FF")), 
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dialogo_alta_inventario)

    def abrir_alta_inventario(e):
        dialogo_alta_inventario.open = True
        page.update()

    # =========================================================================
    # --- PESTAÑA INVENTARIO: CONTROLES Y MOTOR DE FILAS (REPARADO) ---
    # =========================================================================
    style_btn_mockup = ft.ButtonStyle(
        color="white",
        bgcolor="transparent",
        shape=ft.RoundedRectangleBorder(radius=15),
        side=borde_premium, 
        padding=11,
        text_style=ft.TextStyle(size=12, weight="bold")
    )
    def crear_fila_inventario_dinamica(d_inv):
        # 🧠 CAPTURA EN RAM DE LOS DATOS SEGUROS QUE YA TRAE TU FILA NATIVA
        num_cabaña = d_inv["habitacion"].upper().strip()
        tipo_unidad = d_inv["tipo"].upper().strip()
        capacidad_u = d_inv["capacidad"].upper().strip()
        estado_u = d_inv["estado"].upper().strip()
        adulto_raw = d_inv["adulto"]
        nino_raw = d_inv["nino"]

        # --- MOTOR INTERNO DEL MODAL DE AUDITORÍA INTELIGENTE ---
        def abrir_desglose_modal(e):
            import re
            import sqlite3
            
            def evaluar_estado_iva(texto_raw):
                if not texto_raw: return 0.0
                numerico = "".join(re.findall(r'[0-9.]+', str(texto_raw)))
                try: return float(numerico)
                except: return 0.0

            monto_base_a = evaluar_estado_iva(adulto_raw)
            monto_base_n = evaluar_estado_iva(nino_raw)

            # CONEXIÓN COMERCIAL: Validación blindada multi-formato
            iva_global_activo = False
            try:
                conn = sqlite3.connect("starblim.db")
                cursor = conn.cursor()
                cursor.execute("SELECT activo FROM config_reserva WHERE id = 1") 
                reg_iva = cursor.fetchone()
                conn.close()
                
                if reg_iva:
                    valor_real = reg_iva[0]
                    # Evaluamos de forma elástica si es entero, string o booleano
                    if valor_real == 1 or str(valor_real).strip() == "1" or valor_real is True:
                        iva_global_activo = True
            except Exception as ex:
                print(f"⚠️ ARQUITECTO - ERROR CRÍTICO DE BD: {ex}")

            if iva_global_activo:
                estado_tag = "21% • ON"
                val_iva_a = monto_base_a * 0.21
                val_iva_n = monto_base_n * 0.21
                base_display_a = f"USD {monto_base_a:.2f}"
                iva_a = f"USD {val_iva_a:.2f}"
                cliente_a = f"USD {monto_base_a + val_iva_a:.2f}"
                base_display_n = f"USD {monto_base_n:.2f}"
                iva_n = f"USD {val_iva_n:.2f}"
                cliente_n = f"USD {monto_base_n + val_iva_n:.2f}"
            else:
                estado_tag = "21% • OFF"
                base_display_a = f"USD {monto_base_a:.2f}"
                cliente_a = f"USD {monto_base_a:.2f}"
                iva_a = "USD 0.00"
                base_display_n = f"USD {monto_base_n:.2f}"
                cliente_n = f"USD {monto_base_n:.2f}"
                iva_n = "USD 0.00"

            tabla_auditoria_real = ft.DataTable(
                heading_row_color="#0D43AF", 
                heading_row_height=40,
                data_row_min_height=45,
                data_row_max_height=45,
                column_spacing=28,
                divider_thickness=0.5,
                horizontal_lines=ft.BorderSide(0.5, "rgba(255,255,255,0.1)"),
                columns=[
                    ft.DataColumn(ft.Text("MÓDULO DE CONTROL", style=ft.TextStyle(color="white", size=12, weight="bold", letter_spacing=0.5))),
                    ft.DataColumn(ft.Text("• precio base", style=ft.TextStyle(color="white", size=12, weight="bold", letter_spacing=0.5))),
                    ft.DataColumn(ft.Text("• precio cliente", style=ft.TextStyle(color="#FFB300", size=12, weight="bold", letter_spacing=0.5))),
                    ft.DataColumn(ft.Text(f"↳ detalle del iva ({estado_tag})", style=ft.TextStyle(color="#00FFFF", size=12, weight="bold", letter_spacing=0.5))),
                ],
                rows=[
                    # ⚪ GRUPO 1: PRECIO BASE (Sincronizado en Blanco)
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("ADULTO (BASE)", color="white", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_a, color="rgba(255,255,255,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_a, color="white", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_a, color="white", size=13, weight="bold")),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("NIÑO (BASE)", color="white", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_n, color="rgba(255,255,255,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_n, color="white", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_n, color="white", size=13, weight="bold")),
                    ]),
                    # 🟢 GRUPO 2: PRECIO CON DR (Sincronizado en Verde Neón)
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("ADULTO (RESERVA)", color="#00FF66", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_a, color="rgba(0,255,102,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_a, color="#00FF66", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_a, color="#00FF66", size=13, weight="bold")),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("NIÑO (RESERVA)", color="#00FF66", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_n, color="rgba(0,255,102,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_n, color="#00FF66", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_n, color="#00FF66", size=13, weight="bold")),
                    ]),
                    # 🟠 GRUPO 3: DESC. TEMPORADA (Sincronizado en Naranja Rockstar)
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("ADULTO (TEMPORADA)", color="#FF8C00", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_a, color="rgba(255,140,0,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_a, color="#FF8C00", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_a, color="#FF8C00", size=13, weight="bold")),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("NIÑO (TEMPORADA)", color="#FF8C00", size=12, weight="bold")),
                        ft.DataCell(ft.Text(base_display_n, color="rgba(255,140,0,0.8)", size=12)),
                        ft.DataCell(ft.Text(cliente_n, color="#FF8C00", size=14, weight="bold")), 
                        ft.DataCell(ft.Text(iva_n, color="#FF8C00", size=13, weight="bold")),
                    ]),
                ]
            )

            cuadro_tabla_auditoria = ft.Container(
                bgcolor="#111622", border_radius=15, padding=0, 
                border=ft.Border(
                    top=ft.BorderSide(3.0, "#FFFFFF"), bottom=ft.BorderSide(3.0, "#FFFFFF"), 
                    left=ft.BorderSide(1.0, "rgba(255,255,255,0.15)"), right=ft.BorderSide(1.0, "rgba(255,255,255,0.15)")
                ),
                content=tabla_auditoria_real
            )

            dialogo_auditoria = ft.AlertDialog(
                bgcolor="#0B0E14",
                title=ft.Row([
                    ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, color="#00F7FF", size=24),
                    ft.Text(f"AUDITORÍA DE TARIFAS — {num_cabaña}", style=ft.TextStyle(color="#00F7FF", size=16, weight="bold", letter_spacing=1.0))
                ], alignment="start"),
                content=ft.Container(width=750, height=315, content=cuadro_tabla_auditoria),
                actions=[
                    ft.TextButton(
                        "ENTENDIDO", 
                        on_click=lambda _: [setattr(dialogo_auditoria, "open", False), page.update()], 
                        style=ft.ButtonStyle(color="#00F7FF", text_style=ft.TextStyle(weight="bold", size=13))
                    )
                ],
                actions_alignment="end"
            )
            page.overlay.append(dialogo_auditoria)
            dialogo_auditoria.open = True
            page.update()

        # --- RETORNAMOS TU FILA ORIGINAL INTACTA ---
        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=abrir_desglose_modal,
            content=ft.Container(
                bgcolor="#141923", border_radius=8, 
                padding=ft.Padding(left=12, top=8, right=12, bottom=8), 
                border=ft.Border(bottom=ft.BorderSide(0.5, "rgba(255,255,255,0.1)")),
                content=ft.Row([
                    ft.Container(expand=3, alignment=ft.Alignment(0, 0), content=ft.Text(num_cabaña, color="white", weight="bold", size=14, text_align=ft.TextAlign.CENTER)),
                    ft.Container(expand=2, alignment=ft.Alignment(0, 0), content=ft.Text(tipo_unidad, color="rgba(255,255,255,0.8)", size=14, text_align=ft.TextAlign.CENTER)),
                    ft.Container(expand=2, alignment=ft.Alignment(0, 0), content=ft.Text(capacidad_u, color="rgba(255,255,255,0.8)", size=14, text_align=ft.TextAlign.CENTER)),
                    ft.Container(expand=2, alignment=ft.Alignment(0, 0), content=ft.Text(estado_u, color="#00FFCC" if estado_u == "DISPONIBLE" else "#FF3366", weight="bold", size=13, text_align=ft.TextAlign.CENTER)),
                    ft.Container(expand=2, alignment=ft.Alignment(0, 0), content=ft.Text(adulto_raw, color="#FFB300", weight="bold", size=14, text_align=ft.TextAlign.CENTER)),
                    ft.Container(expand=2, alignment=ft.Alignment(0, 0), content=ft.Text(nino_raw, color="#FFB300", weight="bold", size=14, text_align=ft.TextAlign.CENTER)),
                    ft.Container(
                        width=40, alignment=ft.Alignment(0, 0),
                        content=ft.IconButton(
                            icon=ft.Icons.SETTINGS, icon_size=18, icon_color="rgba(255,255,255,0.5)",

                            tooltip="Opciones de Habitación", mouse_cursor=ft.MouseCursor.CLICK
                        )
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    txt_filtro_buscar = ft.TextField(
        label="FILTRO PARA BUSCAR",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.4)", size=12), # <--- CORREGIDO: label_style
        width=210, height=40, text_size=12, color="white",
        border_color="rgba(255,255,255,0.2)", border_radius=10, text_align=ft.TextAlign.CENTER,
        filled=True,
        fill_color="#0D47A1", 
    )

    # --- MOTOR DE BÚSQUEDA EN TIEMPO REAL PARA EL INVENTARIO ---
    def filtrar_inventario_en_caliente(e):
        texto_busqueda = txt_filtro_buscar.value.upper().strip()
        
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM habitaciones ORDER BY habitacion ASC")
        registros = cursor.fetchall()
        conn.close()

        lista_inventario_filas.controls.clear()

        for reg in registros:
            hab_num   = reg[0]
            hab_ubic  = reg[1]
            hab_tipo  = reg[2]
            hab_estado = reg[3]
            hab_cap   = reg[4]
            hab_adulto = reg[5]
            hab_nino   = reg[6]

            if (texto_busqueda in hab_num.upper() or 
                texto_busqueda in hab_ubic.upper() or 
                texto_busqueda in hab_tipo.upper()):
                
                datos_inventario = {
                    "habitacion": hab_num,
                    "tipo": hab_tipo,
                    "capacidad": hab_cap,
                    "estado": hab_estado,
                    "adulto": hab_adulto,
                    "nino": hab_nino
                }
                lista_inventario_filas.controls.append(crear_fila_inventario_dinamica(datos_inventario))
        page.update()

    txt_filtro_buscar.on_change = filtrar_inventario_en_caliente

    # --- BOTÓN DE AUMENTO GENERAL CON DEGRADADO VERDE-ROJO ---
    btn_aumento_general = ft.Container(
        content=ft.TextButton(
            content=ft.Text("APLICAR AUMENTO GENERAL", color="white", size=12, weight="bold"),
            style=ft.ButtonStyle(
                bgcolor="transparent",              
                padding=11,                         
                alignment=ft.Alignment(0, 0),       
                overlay_color="rgba(255,255,255,0.15)" 
            ),
            on_click=abrir_modal_ajuste_masivo
        ),
        border_radius=15,
        border=borde_premium,
        gradient=ft.LinearGradient(
            colors=["#1B8F57", "#8B1A1A"],    
            begin=ft.Alignment(-1, 0),         
            end=ft.Alignment(1, 0),           
        ),
    )

    # --- SWITCH DE IVA REACTIVO ---
    switch_activar_iva = ft.Switch(
        label="Activar IVA",
        label_text_style=ft.TextStyle(color="rgba(255,255,255,0.8)", size=11, weight="bold"),
        thumb_color={ft.ControlState.SELECTED: "#2979FF"},
        track_color={ft.ControlState.SELECTED: "#1A237E"},
        value=False,
        on_change=gatillar_alerta_iva_reactiva  
    )

    fila_herramientas_alta = ft.Row(
        controls=[
            ft.Container(content=txt_filtro_buscar, width=210),
            ft.Container(expand=True), 
            btn_aumento_general,
            ft.Container(expand=True), 
            ft.Container(content=switch_activar_iva, width=210, alignment=ft.Alignment(1, 0)) 
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    # --- BOTÓN CIRCULAR (+) CON HOVER NATIVO CALIBRADO ---
    btn_agregar_unidad_tabla = ft.IconButton(
        icon=ft.Icons.ADD,
        icon_size=18,
        mouse_cursor=ft.MouseCursor.CLICK, 
        style=ft.ButtonStyle(
            icon_color={
                ft.ControlState.HOVERED: "#00F7FF",       
                ft.ControlState.DEFAULT: "#00C3FF",       
            },
            overlay_color="transparent",                  
            padding=0,                                    
            visual_density=ft.VisualDensity.COMPACT,      
        ),
        on_click=abrir_alta_inventario 
    )

    def texto_titulo_inv(texto, peso):
        return ft.Container(
            content=ft.Text(texto, color="white", weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.CENTER),
            expand=peso, alignment=ft.Alignment(0, 0)
        )

    encabezado_tabla_inventario = ft.Container(
        content=ft.Row([
            texto_titulo_inv("HABITACIÓN", 3),
            texto_titulo_inv("TIPO", 2),
            texto_titulo_inv("CAPACIDAD", 2),
            texto_titulo_inv("ESTADO", 2),
            texto_titulo_inv("ADULTO", 2),
            texto_titulo_inv("NIÑO", 2),
            ft.Container(width=40, alignment=ft.Alignment(0, 0), content=btn_agregar_unidad_tabla)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#030097", border_radius=6, padding=Padding(12, 8, 12, 8)
    )

    cartel_guia_precios = ft.Container(
        content=ft.Text(
            "PARA VER MÁS DETALLES SOBRE LOS PRECIOS DE LAS HABITACIONES, SELECCIONE UNA HABITACIÓN DE LA LISTA",
            color="white", size=10, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
        ),
        bgcolor="#0D47A1",                 
        padding=ft.Padding(15, 12, 15, 12), 
        alignment=ft.Alignment(0, 0),      
        margin=ft.Padding(left=-15, top=10, right=-15, bottom=-15),
        border_radius=ft.BorderRadius(
            top_left=0, top_right=0, bottom_left=12, bottom_right=12
        )
    )

    cuadro_inventario_filas = ft.Container(
        content=ft.Column([
            encabezado_tabla_inventario,
            ft.Container(height=4),
            lista_inventario_filas,        
            cartel_guia_precios            
        ], expand=True, spacing=0),
        bgcolor="#85000000", border=borde_de_las_tablas, border_radius=12, padding=15, expand=True
    )

    btn_descuento_temporada = ft.TextButton(
        content=ft.Text("DESCUENTO POR TEMPORADA", color="white", size=12, weight="bold"),
        style=ft.ButtonStyle(
            bgcolor="#E65100", 
            shape=ft.RoundedRectangleBorder(radius=15),
            side=borde_premium, padding=11
        ),
        on_click=abrir_modal_temporada 
    )

    # =========================================================================
    # --- MÓDULO DE CUPONES PREMIUM: CONSOLA DE MONITOREO Y APERTURA V3 ---
    # =========================================================================
    
    lista_cupones_tabla_contenedor = ft.ListView(expand=True, spacing=0, height=140)

    # Inputs estilizados nativos con bordes violetas fijos de alto contraste
    cp_txt_codigo = ft.TextField(
        label="ASIGNAR NOMBRE/CÓDIGO", 
        width=250, height=40, text_size=13, color="white",
        cursor_color="#8B5CF6", border_width=1.5, border_color="#8B5CF6",
        focused_border_color="#AF7AC5", border_radius=8
    )
    cp_txt_porcentaje = ft.TextField(
        label="DESCUENTO (%)", 
        height=40, text_size=13, color="white", cursor_color="#8B5CF6",
        keyboard_type=ft.KeyboardType.NUMBER, border_width=1.5, border_color="#8B5CF6",
        focused_border_color="#AF7AC5", border_radius=8
    )
    cp_txt_cupos = ft.TextField(
        label="CANT. CUPOS", 
        height=40, text_size=13, color="white", cursor_color="#8B5CF6",
        keyboard_type=ft.KeyboardType.NUMBER, border_width=1.5, border_color="#8B5CF6",
        focused_border_color="#AF7AC5", border_radius=8
    )
    cp_txt_tope_dinero = ft.TextField(
        label="TOPE MÁX (USD)", 
        hint_text="0.00 sin tope", height=40, text_size=13, color="white",
        cursor_color="#8B5CF6", keyboard_type=ft.KeyboardType.NUMBER, border_width=1.5,
        border_color="#8B5CF6", focused_border_color="#AF7AC5", border_radius=8
    )
    cp_txt_fecha_inicio = ft.TextField(
        label="INICIO (D/M/A)", 
        value=datetime.now().strftime("%d/%m/%y"), 
        width=115, height=40, text_size=13, color="white", cursor_color="#FC7A00",
        border_width=1.5, border_color="#FC7A00", focused_border_color="#B15F12", border_radius=8
    )
    cp_txt_fecha_fin = ft.TextField(
        label="VENCE (D/M/A)", 
        value=datetime.now().strftime("%d/%m/%y"), 
        width=115, height=40, text_size=13, color="white", cursor_color="#FC7A00",
        border_width=1.5, border_color="#FC7A00", focused_border_color="#B15F12", border_radius=8
    )

    def al_enfocar_tope(e):
        if cp_txt_tope_dinero.value == "0.00 sin tope":
            cp_txt_tope_dinero.value = ""
            cp_txt_tope_dinero.color = "white"
            page.update()

    def al_desenfocar_tope(e):
        if cp_txt_tope_dinero.value.strip() == "" or cp_txt_tope_dinero.value.strip() == "0":
            cp_txt_tope_dinero.value = "0.00 sin tope"
            cp_txt_tope_dinero.color = "rgba(255, 255, 255, 0.4)"
            page.update()

    cp_txt_tope_dinero.on_focus = al_enfocar_tope
    cp_txt_tope_dinero.on_blur = al_desenfocar_tope

    # 4. Motor de borrado individual de registros en caliente
    def eliminar_cupon_individual_db(e, codigo_borrar):
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cupones WHERE codigo = ?", (codigo_borrar.upper().strip(),))
        conn.commit()
        conn.close()
        recargar_consola_cupones_desde_db()

    # 5. Renderizador nativo en cuadrícula (DataTable con Columna de Vencimiento)
    def recargar_consola_cupones_desde_db():
        lista_cupones_tabla_contenedor.controls.clear()
        
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cupones ORDER BY codigo ASC")
        registros = cursor.fetchall()
        conn.close()

        filas_datos_tabla = []
        for reg in registros:
            cod = reg[0]
            pct = f"{reg[1]:.0f}%"
            f_vence = reg[7] if reg[7] else "--/--/--"
            
            tope = f"USD {reg[5]:.2f}" if reg[4] == 1 else "LIBRE"

            filas_datos_tabla.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(cod, color="white", size=13, weight="bold")),
                        ft.DataCell(ft.Text(pct, color="#5CECF6", size=13, weight="bold")),
                        ft.DataCell(ft.Text(f_vence, color="white", size=13)),  
                        ft.DataCell(ft.Text(tope, color="#00FFCC" if reg[4] == 1 else "rgba(255,255,255,0.4)", size=13, weight="bold")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.DELETE_ROUNDED, icon_color="#FF5722", icon_size=15, padding=0,
                                on_click=lambda e, c=cod: eliminar_cupon_individual_db(e, c)
                            )
                        ),
                    ]
                )
            )

        tabla_real_cupones = ft.DataTable(
            heading_row_color="#030097",
            heading_row_height=32,
            data_row_min_height=28,
            data_row_max_height=28,
            column_spacing=24,
            divider_thickness=0.5,
            horizontal_lines=ft.BorderSide(0.5, "rgba(255,255,255,0.1)"),
            columns=[
                ft.DataColumn(ft.Text("CÓDIGO", color="white", size=13, weight="bold")),
                ft.DataColumn(ft.Text("REBAJA", color="white", size=13, weight="bold")),
                ft.DataColumn(ft.Text("VENCE", color="white", size=13, weight="bold")), 
                ft.DataColumn(ft.Text("TOPE", color="white", size=13, weight="bold")),
                ft.DataColumn(ft.Text("", width=20)),
            ],
            rows=filas_datos_tabla
        )
        
        lista_cupones_tabla_contenedor.controls.append(tabla_real_cupones)
        page.update()

    # 6. Guardado transaccional en SQLite con soporte para el tope sutil 
    def ejecutar_alta_cupon_db(e):
        if not cp_txt_codigo.value or not cp_txt_porcentaje.value or not cp_txt_cupos.value:
            return
        
        cod_final = cp_txt_codigo.value.upper().strip()
        try:
            pct_final = float(cp_txt_porcentaje.value)
            cup_final = int(cp_txt_cupos.value)
            
            texto_tope = cp_txt_tope_dinero.value.strip()
            if texto_tope == "0.00 sin tope" or texto_tope == "" or texto_tope == "0":
                tope_final = 0.0
                flag_tope = 0
            else:
                tope_final = float(texto_tope)
                flag_tope = 1
        except ValueError:
            return

        f_ini = cp_txt_fecha_inicio.value.strip()
        f_fin = cp_txt_fecha_fin.value.strip()

        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cupones VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cod_final, pct_final, cup_final, cup_final, flag_tope, tope_final, f_ini, f_fin))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return
        conn.close()

        cp_txt_codigo.value = ""
        cp_txt_porcentaje.value = ""
        cp_txt_cupos.value = ""
        cp_txt_tope_dinero.value = "0.00 sin tope"
        cp_txt_tope_dinero.color = "rgba(255, 255, 255, 0.4)"
        
        recargar_consola_cupones_desde_db()

    # Cartel flotante de ayuda secundario de cupones
    dialogo_ayuda_cupones_info = ft.AlertDialog(
        bgcolor="#0B0E14",
        title=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, color="#8B5CF6"),
            ft.Text("INSTRUCCIÓN OPERATIVA DE CUPONES", color="#8B5CF6", size=14, weight="bold")
        ], alignment=ft.MainAxisAlignment.START),
        content=ft.Container(
            width=400, height=210,
            content=ft.Column([
                ft.Row([
                    ft.Text("•", color="white", size=13.5, weight="bold"),
                    ft.Container(expand=True, content=ft.Text("CUPONES: Se pueden crear códigos promocionales con vencimiento y límite de stock, los cupones solo afectan al precio del alojamiento y solo se canjean a la hora de registrar al cliente.", color="white", size=14.5))
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=4),
                ft.Row([
                    ft.Text("•", color="white", size=13.5, weight="bold"),
                    ft.Container(expand=True, content=ft.Text("TOPE DE DINERO (OPCIONAL): afecta a determinado monto (ejemplo: se pone un tope de $1000, entonces, si un cliente gasta $3000, solo recibira un descuento en los primeros $1000). Sino se quiere aplicar tope dejarlo en 0 (en este caso, el descuento se aplicará al total del precio del alojamiento).", color="white", size=14.5))
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=6, tight=True)
        ),
        actions=[
            ft.TextButton("ENTENDIDO", on_click=lambda _: [setattr(dialogo_ayuda_cupones_info, "open", False), page.update()], style=ft.ButtonStyle(color="#8B5CF6"))
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    page.overlay.append(dialogo_ayuda_cupones_info)

    def abrir_ayuda_cupones_popup(e):
        dialogo_ayuda_cupones_info.open = True
        page.update()

    # 8. Ventana flotante definitiva: Consola de cupones con ayuda integrada
    dialogo_cupones_maestro = ft.AlertDialog(
        bgcolor="#0B0E14",
        modal=True,
        title=ft.Row([
            ft.Container(expand=1),
            ft.Container(
                expand=3,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("CREAR CUPÓN DE DESCUENTO", color="#8B5CF6", size=20, weight="bold")
            ),
            ft.Container(
                expand=1,
                alignment=ft.Alignment(1, 0),
                content=ft.IconButton(
                    icon=ft.Icons.INFO_OUTLINE, 
                    icon_size=20, 
                    icon_color="#00ACF0",
                    tooltip="Ver instrucciones operativas", 
                    on_click=abrir_ayuda_cupones_popup,
                    style=ft.ButtonStyle(
                        padding=0, 
                        visual_density=ft.VisualDensity.COMPACT,
                        overlay_color="rgba(139, 92, 246, 0.15)"
                    )
                )
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),

        content=ft.Container(
            width=580, height=415,
            padding=ft.Padding(12, 5, 12, 5),
            content=ft.Column([
                ft.Container(height=6),
                ft.Row([cp_txt_codigo], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=14),
                ft.Row([
                    ft.Container(content=cp_txt_porcentaje, expand=True),
                    ft.Container(content=cp_txt_cupos, expand=True),
                    ft.Container(content=cp_txt_tope_dinero, expand=True)
                ], spacing=12),
                ft.Container(height=14),
                ft.Row([
                    ft.Container(content=cp_txt_fecha_inicio, expand=True),
                    ft.Container(content=cp_txt_fecha_fin, expand=True)
                ], spacing=12),
                ft.Container(height=16),
                ft.Container(
                    content=ft.TextButton(
                        content=ft.Text("GENERAR E INYECTAR CUPÓN V3", color="white", size=12, weight="bold"),
                        style=ft.ButtonStyle(bgcolor="#8B5CF6", shape=ft.RoundedRectangleBorder(radius=8), padding=12),
                        on_click=ejecutar_alta_cupon_db
                    ),
                    alignment=ft.Alignment(0, 0)
                ),
                ft.Container(height=10),
                ft.Divider(height=1, color="rgba(255,255,255,0.2)"),
                ft.Container(height=10),
                ft.Text("CONSOLA DE MONITOREO DE CUPONES ACTIVOS", color="white", size=11, weight="bold"),
                ft.Container(height=6),
                ft.Container(
                    expand=True,
                    bgcolor="#40000000",
                    border=borde_de_las_tablas,
                    border_radius=8,
                    padding=6,
                    content=ft.Container(content=lista_cupones_tabla_contenedor, expand=True)
                )
            ], spacing=0, tight=True)
        ),
        actions=[
            ft.TextButton(
                "CERRAR PANEL", 
                on_click=lambda _: [setattr(dialogo_cupones_maestro, "open", False), page.update()],
                style=ft.ButtonStyle(color="white", text_style=ft.TextStyle(size=12, weight="bold"))
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )

    def abrir_modal_cupones_completo(e):
        recargar_consola_cupones_desde_db()
        dialogo_cupones_maestro.open = True
        page.update()

    # 9. Botón físico violeta renovado acoplado a la lista final
    btn_cupon_descuento = ft.TextButton(
        content=ft.Text("CREAR CUPÓN DE DESCUENTO", color="white", size=12, weight="bold"),
        style=ft.ButtonStyle(
            bgcolor="#8B5CF6", 
            shape=ft.RoundedRectangleBorder(radius=15),
            side=borde_premium, padding=11
        ),
        on_click=abrir_modal_cupones_completo
    )

    # =========================================================================
    # --- MÓDULO DESCUENTO RESERVA GLOBAL: FORMULARIO Y SEGURIDAD V3 ---
    # =========================================================================
    
    dr_txt_porcentaje = ft.TextField(
        label="PORCENTAJE (%)",
        value="0.0", width=150, height=40, text_size=13, color="white",
        cursor_color="#2E7D32", border_width=1.5, border_color="#00FFCC",
        focused_border_color="#2E7D32", border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER
    )

    switch_activar_descuento_reserva = ft.Switch(
        label="Activar o desactivar",
        label_text_style=ft.TextStyle(color="rgba(255,255,255,0.8)", size=11, weight="bold"),
        active_color="#00FFCC",
        value=False
    )

    def guardar_descuento_reserva_persistente(e):
        try:
            pct_final = float(dr_txt_porcentaje.value)
        except ValueError:
            return

        flag_activo = 1 if switch_activar_descuento_reserva.value else 0

        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE config_reserva 
            SET activo = ?, porcentaje = ? 
            WHERE id = 1
        """, (flag_activo, pct_final))
        conn.commit()
        conn.close()

        dialogo_seguridad_reserva.open = False
        dialogo_descuento_reserva_maestro.open = False
        page.update()
        aplicar_filtros_universales(None)

    dialogo_seguridad_reserva = ft.AlertDialog(
        bgcolor="#0B0E14",
        title=ft.Row([
            ft.Icon(ft.Icons.WARNING_ROUNDED, color="#FF3366"),
            ft.Text("ADVERTENCIA DE TARIFAS", color="#FF3366", size=14, weight="bold")
        ], alignment=ft.MainAxisAlignment.START),
        content=ft.Container(
            width=320, height=75,
            content=ft.Text(
                "¿Está seguro de alterar el precio base de todas las unidades? Este cambio impactará de inmediato en las tarifas visibles al cliente.",
                color="white", size=12.5
            )
        ),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda _: [setattr(dialogo_seguridad_reserva, "open", False), page.update()], style=ft.ButtonStyle(color="white")),
            ft.TextButton("SÍ, PROCEDER", on_click=guardar_descuento_reserva_persistente, style=ft.ButtonStyle(color="#00FFCC")),
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    page.overlay.append(dialogo_seguridad_reserva)

    def lanzar_confirmacion_seguridad_dr(e):
        try:
            float(dr_txt_porcentaje.value)
            dialogo_seguridad_reserva.open = True
            page.update()
        except ValueError:
            dr_txt_porcentaje.error_text = "Número inválido"
            page.update()

    # 5. Ventana flotante principal de Descuento de Reserva Global
    dialogo_descuento_reserva_maestro = ft.AlertDialog(
        bgcolor="#0B0E14",
        modal=True,
        title=ft.Row([
            ft.Container(expand=1),
            ft.Container(
                expand=3,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("APLICAR DESCUENTO RESERVA", color="#00FFCC", size=15, weight="bold")
            ),
            ft.Container(expand=1)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=400, 
            height=190,  
            padding=ft.Padding(12, 5, 12, 5),
            content=ft.Column([
                ft.Row([
                    ft.Text("•", color="white", size=15, weight="bold"),
                    ft.Container(expand=True, content=ft.Text("Aplica un descuento sobre el precio base de todos los alojamientos del hotel, solo afecta a los clientes que hicieron una reserva.", color="white", size=14))
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                
                ft.Container(height=16),  
                
                ft.Row([
                    ft.Container(content=dr_txt_porcentaje),
                    ft.Container(content=switch_activar_descuento_reserva, padding=ft.Padding(10, 0, 0, 0))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Container(height=16),
                
                ft.Container(
                    content=ft.TextButton(
                        content=ft.Text("APLICAR Y ACTUALIZAR TARIFAS", color="white", size=12, weight="bold"),
                        style=ft.ButtonStyle(bgcolor="#2E7D32", shape=ft.RoundedRectangleBorder(radius=8), padding=12),
                        on_click=lanzar_confirmacion_seguridad_dr
                    ),
                    alignment=ft.Alignment(0, 0)
                )
            ], spacing=0, tight=True)
        ),
        actions=[
            ft.TextButton(
                "CERRAR PANEL", 
                on_click=lambda _: [setattr(dialogo_descuento_reserva_maestro, "open", False), page.update()],
                style=ft.ButtonStyle(color="white", text_style=ft.TextStyle(size=12, weight="bold"))
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    page.overlay.append(dialogo_descuento_reserva_maestro)

    def abrir_modal_descuento_reserva_completo(e):
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT activo, porcentaje FROM config_reserva WHERE id = 1")
        reg = cursor.fetchone()
        conn.close()

        if reg:
            switch_activar_descuento_reserva.value = True if reg[0] == 1 else False
            dr_txt_porcentaje.value = str(reg[1])
            dr_txt_porcentaje.error_text = None

        dialogo_descuento_reserva_maestro.open = True
        page.update()

    # Nuevo Botón físico verde acoplado perfectamente al panel inferior
    btn_descuento_reserva = ft.TextButton(
        content=ft.Text("APLICAR DESCUENTO RESERVA", color="white", size=12, weight="bold"),
        style=ft.ButtonStyle(
            bgcolor="#2E7D32",
            shape=ft.RoundedRectangleBorder(radius=15),
            side=borde_premium,
            padding=11,
            overlay_color="rgba(255, 255, 255, 0.15)"
        ),
        on_click=abrir_modal_descuento_reserva_completo
    )

    fila_acciones_baja = ft.Row(
        controls=[btn_descuento_temporada, btn_cupon_descuento, btn_descuento_reserva],
        alignment=ft.MainAxisAlignment.CENTER, spacing=20
    )

    contenido_inventario = ft.Container(
        padding=Padding(15, 15, 15, 15), expand=True,
        content=ft.Column([
            fila_herramientas_alta, 
            ft.Container(height=10),
            cuadro_inventario_filas, 
            ft.Container(height=10),
            fila_acciones_baja 
        ], spacing=0, margin=0)
    )

    # =========================================================================
    # --- MOTOR DE RENDERIZADO GENERAL DESDE BASE DE DATOS REAL (SQLITE) ---
    # =========================================================================
    def actualizar_grillas_desde_db():
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM habitaciones ORDER BY habitacion ASC")
        registros = cursor.fetchall()
        conn.close()

        lista_habitaciones.controls.clear()
        lista_inventario_filas.controls.clear()

        for idx, reg in enumerate(registros):
            hab_num     = reg[0]
            hab_ubic    = reg[1]
            hab_tipo    = reg[2]
            hab_estado  = reg[3]
            hab_cap     = reg[4]
            
            texto_adulto_db = reg[5]
            texto_nino_db   = reg[6]

            # MOTOR REACTIVO EN CALIENTE DE IVA (FACTOR 21%)
            if switch_activar_iva.value == True:
                try:
                    val_a = float(texto_adulto_db.replace("USD", "").strip())
                    hab_adulto = f"USD {val_a * 1.21:.2f}"
                except: hab_adulto = texto_adulto_db
                
                try:
                    val_n = float(texto_nino_db.replace("USD", "").strip())
                    hab_nino = f"USD {val_n * 1.21:.2f}"
                except: hab_nino = texto_nino_db
            else:
                hab_adulto = texto_adulto_db
                hab_nino   = texto_nino_db

            detalles_dict = {
                "vista": reg[7],
                "sub_vista": reg[8],
                "incluye": reg[9],
                "cama": reg[10],
                "reserva": reg[11],
                "desc_tit": reg[12],
                "desc_val": reg[13],
                "prom_tit": reg[14],
                "prom_val": reg[15],
                "servicios": reg[16].split(",") if reg[16] else [],
                "fotos": reg[17].split(",") if (reg[17] and "," in reg[17]) else ["fondo.png", "fondo.png", "fondo.png", "fondo.png"]
            }

            datos_principal = {
                "habitacion": hab_num,
                "tipo": hab_tipo,
                "sub": hab_ubic,
                "capacidad": hab_cap,
                "estado": hab_estado,
                "adulto": hab_adulto,
                "nino": hab_nino,
                "detalles": detalles_dict
            }
            
            color_cebra_p = color_fila_par if idx % 2 != 0 else color_fila_impar
            lista_habitaciones.controls.append(
                crear_fila_habitacion_dinamica(datos_principal, color_base=color_cebra_p)
            )

            datos_inventario = {
                "habitacion": hab_num,
                "tipo": hab_tipo,
                "capacidad": hab_cap,
                "estado": hab_estado,
                "adulto": hab_adulto,
                "nino": hab_nino
            }
            lista_inventario_filas.controls.append(
                crear_fila_inventario_dinamica(datos_inventario)
            )

        page.update()

    # --- SISTEMA DE FILTRADO COMBINADO CON SCROLL ---
    cb_tipo_panel = ft.Dropdown(
        label="Tipo de Habitación",
        label_style=ft.TextStyle(color="rgba(255,255,255,0.6)", size=10), 
        height=40,                         
        text_size=12,
        color="white",                     
        filled=True,                       
        fill_color="#902563EB",              
        border_color="black", 
        border_radius=10,
        text_align=ft.TextAlign.CENTER,    
        options=[
            ft.dropdown.Option("TODAS"),
            ft.dropdown.Option("2 ADULTOS"),
            ft.dropdown.Option("FAMILIAR"),
            ft.dropdown.Option("SUITE"),
        ],
        value="TODAS"
    )

    switch_precio = ft.Switch(
        label="Filtrar por Precio (Menor a Mayor)",
        label_text_style=ft.TextStyle(color="rgba(255,255,255,0.8)", size=11, weight="bold"),
        active_color="#FFB300", 
        value=False,
    )

    switch_disponibles = ft.Switch(
        label="Mostrar solo Disponibles",
        label_text_style=ft.TextStyle(color="rgba(255,255,255,0.8)", size=11, weight="bold"),
        active_color="#00FFCC", 
        value=False,
    )

    # === SISTEMA DE FILTRADO COMBINADO CON CONEXIÓN DIRECTA A SQLITE (REPARADO) ===
    def aplicar_filtros_universales(e):
        # 1. Traemos la data fresca directamente de la Base de Datos para filtrar sobre lo real
        conn = sqlite3.connect("starblim.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM habitaciones ORDER BY habitacion ASC")
        registros = cursor.fetchall()
        
        # Consultamos SQLite una sola vez al inicio para saber el estado del descuento verde (Optimiza rendimiento)
        cursor.execute("SELECT activo, porcentaje FROM config_reserva WHERE id = 1")
        reg_dr = cursor.fetchone()
        conn.close()

        # 2. Armamos la estructura en caliente calculando Descuentos e IVA sobre la marcha en la RAM
        datos_transformados = []
        for reg in registros:
            # Capturamos los textos puros de tarifa guardados en el disco duro
            texto_adulto_db = reg[5]
            texto_nino_db   = reg[6]

            # Saneamos los textos extrayendo el "USD" para poder operar matemáticamente
            try: val_base_adulto = float(texto_adulto_db.replace("USD", "").strip())
            except: val_base_adulto = 0.0
            
            try: val_base_nino = float(texto_nino_db.replace("USD", "").strip())
            except: val_base_nino = 0.0

            # 🟢 CAPA 1: Aplicamos el Descuento de Reserva Global si está encendido en SQLite
            if reg_dr and reg_dr[0] == 1:
                factor_descuento_reserva = 1.0 - (reg_dr[1] / 100.0)
                val_base_adulto = val_base_adulto * factor_descuento_reserva
                val_base_nino = val_base_nino * factor_descuento_reserva

            # 📊 CAPA 2: Aplicamos el Impuesto de IVA (21%) arriba del precio neto calculado
            if switch_activar_iva.value == True:
                precio_final_adulto = f"USD {val_base_adulto * 1.21:.2f}" if val_base_adulto > 0 else texto_adulto_db
                precio_final_nino = f"USD {val_base_nino * 1.21:.2f}" if val_base_nino > 0 else texto_nino_db
            else:
                # Si el IVA está apagado, muestra el precio neto con dos decimales configurados
                precio_final_adulto = f"USD {val_base_adulto:.2f}" if val_base_adulto > 0 else texto_adulto_db
                precio_final_nino = f"USD {val_base_nino:.2f}" if val_base_nino > 0 else texto_nino_db

            # Inyectamos las tarifas inteligentes calculadas en RAM dentro del árbol visual
            datos_transformados.append({
                "habitacion": reg[0],
                "tipo": reg[2],
                "sub": reg[1],
                "capacidad": reg[4],
                "estado": reg[3],
                "adulto": precio_final_adulto,
                "nino": precio_final_nino,
                "detalles": {
                    "vista": reg[7],
                    "sub_vista": reg[8],
                    "incluye": reg[9],
                    "cama": reg[10],
                    "reserva": reg[11],
                    "desc_tit": reg[12],
                    "desc_val": reg[13],
                    "prom_tit": reg[14],
                    "prom_val": reg[15],
                    "servicios": reg[16].split(",") if reg[16] else [],
                    "fotos": reg[17].split(",") if reg[17] else ["fondo.png"]
                }
            })

        # 3. Aplicamos las reglas de filtrado sobre el set de datos corregido que bajó de SQLite
        datos_filtrados = datos_transformados.copy()

        # [Filtro 1] Dropdown Tipo de Unidad
        if cb_tipo_panel.value != "TODAS":
            datos_filtrados = [d for d in datos_filtrados if d["tipo"].upper() == cb_tipo_panel.value.upper()]

        # [Filtro 2] Switch Disponibles
        if switch_disponibles.value:
            datos_filtrados = [d for d in datos_filtrados if d["estado"].upper() == "DISPONIBLE"]

        # [Filtro 3] Switch Precio (Menor a Mayor)
        if switch_precio.value:
            def extraer_monto(item):
                try:
                    limpio = item["adulto"].replace("USD", "").replace(".", "").strip()
                    return float(limpio)
                except:
                    return 0.0
            datos_filtrados.sort(key=extraer_monto)

        # 4. Limpiamos y redibujamos la grilla derecha con su correspondiente color cebra
        lista_habitaciones.controls.clear()
        lista_inventario_filas.controls.clear()
        
        for idx, d in enumerate(datos_filtrados):
            color_asignado = color_fila_par if idx % 2 != 0 else color_fila_impar
            lista_habitaciones.controls.append(crear_fila_habitacion_dinamica(d, color_base=color_asignado))
            
            # Armamos la estructura de datos reducida que espera el constructor de la tabla del inventario
            datos_inv = {
                "habitacion": d["habitacion"],
                "tipo": d["tipo"],
                "capacidad": d["capacidad"],
                "estado": d["estado"],
                "adulto": d["adulto"],
                "nino": d["nino"]
            }
            lista_inventario_filas.controls.append(crear_fila_inventario_dinamica(datos_inv))
            
        page.update()

    # Enganchamos los tres componentes al mismo motor de actualización
    cb_tipo_panel.on_change = aplicar_filtros_universales
    switch_precio.on_change = aplicar_filtros_universales
    switch_disponibles.on_change = aplicar_filtros_universales

    texto_reservas = ft.Text("Selecciona un día...", color="rgba(255,255,255,0.5)", size=13)
    lista_reservas_dia = ft.Column([texto_reservas], spacing=5)

    reloj_hora = ft.Text("00:00", size=38, color="#FFB300", weight="bold")
    reloj_fecha = ft.Text("--- ---", size=26, color="white", weight="bold")

    def actualizar_reloj():
        dias_corto = {"Mon": "LUN", "Tue": "MAR", "Wed": "MIE", "Thu": "JUE", "Fri": "VIE", "Sat": "SAB", "Sun": "DOM"}
        meses_letras = {
            1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
            7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
        }
        while True:
            ahora = datetime.now()
            reloj_hora.value = ahora.strftime("%H:%M")
            dia_ingles = ahora.strftime("%a")
            dia_espanol = dias_corto.get(dia_ingles, "---")
            mes_espanol = meses_letras.get(ahora.month, "---")
            reloj_fecha.value = f"| {dia_espanol} · {mes_espanol}"
            try: page.update()
            except: break
            time.sleep(1)

    threading.Thread(target=actualizar_reloj, daemon=True).start()

    # --- LOGO STARBLIM CON ESTRELLA INTERACTIVA ---
    logo_starblim_top = ft.Row(
        [
            ft.IconButton(
                icon=ft.Icons.STAR,
                icon_size=30,
                mouse_cursor=ft.MouseCursor.CLICK, 
                style=ft.ButtonStyle(
                    icon_color={
                        ft.ControlState.HOVERED: "#00F7FF",       
                        ft.ControlState.DEFAULT: "#00C3FF",       
                    },
                    overlay_color="transparent",                  
                    padding=0,                                    
                    visual_density=ft.VisualDensity.COMPACT,      
                ),
                on_click=abrir_panel_secreto_optimo
            ),
            ft.Text(
                "STARBLIM",
                style=ft.TextStyle(
                    size=26,
                    color="white",
                    weight=ft.FontWeight.W_500,
                    letter_spacing=2.0
                )
            )
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    btn1 = ft.Container(
        content=ft.Text("CERRAR TURNO", color="#FFB300", size=12, weight="bold"), 
        border=borde_premium, border_radius=15, padding=11
    )
    btn2 = ft.Container(
        content=ft.Text("INICIO", color="#FFB300", size=12, weight="bold"), 
        border=borde_premium, border_radius=15, padding=11
    )
    btn3 = ft.Container(
        content=ft.Text("REGISTRAR", color="#FFB300", size=12, weight="bold"), 
        border=borde_premium, border_radius=15, padding=11,
        on_click=abrir_modal_registro
    )

    reloj_bloque_horizontal = ft.Row(
        [reloj_hora, reloj_fecha], 
        spacing=10, 
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    bloque_operative_central = ft.Row(
        [reloj_bloque_horizontal, ft.Container(width=10), btn2, ft.Container(width=5), btn3],
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    menu_superior = ft.Row(
        [
            ft.Container(content=logo_starblim_top, padding=ft.Padding(left=15, top=0, right=0, bottom=0)), 
            ft.Container(expand=True),                                                                    
            bloque_operative_central,                                                                     
            ft.Container(expand=True),                                                                    
            ft.Container(content=btn1, padding=ft.Padding(left=0, top=0, right=15, bottom=0))              
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    def cambiar_dia(e):
        dia = e.control.data
        if not dia: return
        lista_reservas_dia.controls.clear()
        lista_reservas_dia.controls.append(
            ft.Column([
                ft.Text(f"RESERVAS PARA EL DÍA {dia}/{str(mes_visible).zfill(2)}/{anio_visible}:", color="#00FFCC", weight="bold", size=12),
                ft.Text("•  Hab 101  -  Registro Activo (PAGADO)", color="white", size=12),
            ], spacing=4)
        )
        page.update()

    # --- ALMANAQUE DINÁMICO ---
    fecha_sistema = datetime.now()
    mes_visible = fecha_sistema.month
    anio_visible = fecha_sistema.year

    nombres_meses = {
        1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
        7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
    }

    def celda_dia(texto, es_numero=True, es_hoy=False):
        if texto == "": return ft.Container(expand=True, height=32)
        color_texto = "black" if es_hoy else ("white" if es_numero else "#FFB300")
        fondo_base = "#FFB300" if es_hoy else "rgba(255,255,255,0.06)"
        fondo_hover = "#FFB300" if es_hoy else "rgba(255, 179, 0, 0.45)"
        borde_celda = ft.BorderSide(0.5, "white") if (es_numero and not es_hoy) else ft.BorderSide(0, "transparent")

        return ft.Container(
            content=ft.TextButton(
                content=ft.Text(texto, color=color_texto, size=12 if es_numero else 13, weight="bold", text_align=ft.TextAlign.CENTER),
                style=ft.ButtonStyle(
                    bgcolor={
                        ft.ControlState.DEFAULT: "#FFB300" if es_hoy else "transparent",
                        ft.ControlState.HOVERED: fondo_hover,
                        ft.ControlState.FOCUSED: "#FFB300" if es_hoy else "transparent",
                        ft.ControlState.PRESSED: fondo_hover,
                    },
                    shape=ft.RoundedRectangleBorder(radius=5 if es_numero else 0),
                    padding=0, overlay_color="rgba(255, 255, 255, 0.25)", 
                ),
                data=texto if es_numero else None,
                on_click=cambiar_dia if (es_numero and texto != "") else None,
                disabled=not es_numero 
            ),
            expand=True, height=32, margin=0,
            bgcolor=fondo_base if not es_hoy else None, border_radius=5 if es_numero else 0,
            border=Border(top=borde_celda, bottom=borde_celda, left=borde_celda, right=borde_celda) if not es_hoy else None,
        )

    almanaque_completo = ft.Column(spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True)
    texto_mes_anio = ft.Text("", color="white", weight="bold", size=13)

    def redibujar_calendario_dinamico():
        almanaque_completo.controls.clear()
        row_nom = ft.Row([celda_dia("D", False), celda_dia("L", False), celda_dia("M", False), celda_dia("M", False), celda_dia("J", False), celda_dia("V", False), celda_dia("S", False)], spacing=4, expand=True)
        almanaque_completo.controls.append(row_nom)
        cal = calendar.Calendar(firstweekday=6)
        semanas_del_mes = cal.monthdayscalendar(anio_visible, mes_visible)
        hoy_real = datetime.now()
        for semana in semanas_del_mes:
            celdas_de_esta_semana = []
            for dia in semana:
                if dia == 0: celdas_de_esta_semana.append(celda_dia(""))
                else:
                    es_dia_hoy = (dia == hoy_real.day and mes_visible == hoy_real.month and anio_visible == hoy_real.year)
                    celdas_de_esta_semana.append(celda_dia(str(dia), es_numero=True, es_hoy=es_dia_hoy))
            almanaque_completo.controls.append(ft.Row(celdas_de_esta_semana, spacing=4, expand=True))
        texto_mes_anio.value = f"{nombres_meses[mes_visible]} {anio_visible}"
        page.update()

    def ir_al_mes_anterior(e):
        nonlocal mes_visible, anio_visible
        if mes_visible == 1: mes_visible = 12; anio_visible -= 1
        else: mes_visible -= 1
        redibujar_calendario_dinamico()

    def ir_al_mes_siguiente(e):
        nonlocal mes_visible, anio_visible
        if mes_visible == 12: mes_visible = 1; anio_visible += 1
        else: mes_visible += 1
        redibujar_calendario_dinamico()

    cuadro_nuevo = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("INFORMACIÓN GENERAL", color="white", weight="bold", size=13), 
                bgcolor=color_azul_premium, border=borde_azul_titulo, alignment=ft.Alignment(0, 0), 
                padding=Padding(0, 8, 0, 8), border_radius=6, margin=Padding(-9, -9, -9, 10)
            ),
            ft.Divider(height=1, color="rgba(255,255,255,0.2)"),
            
            ft.ListView([
                ft.Container(height=10),
                ft.Container(
                    content=cb_tipo_panel, 
                    alignment=ft.Alignment(0, 0),  
                    width=210,                     
                ),
                ft.Container(height=14),
                switch_precio,       
                ft.Container(height=6),
                switch_disponibles,  
            ], expand=True, spacing=0) 
        ], spacing=0), 
        bgcolor="#85000000", border=borde_de_las_tablas, border_radius=12, padding=Padding(15, 15, 15, 15), expand=1 
    )

    cuadro_cronograma = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Row([
                ft.TextButton(content=ft.Text("<", color="white", size=16, weight="bold"), on_click=ir_al_mes_anterior, style=ft.ButtonStyle(padding=0, shape=ft.RoundedRectangleBorder(radius=17), bgcolor={ft.ControlState.DEFAULT: "transparent", ft.ControlState.HOVERED: "rgba(255, 255, 255, 0.15)"})),
                texto_mes_anio,
                ft.TextButton(content=ft.Text(">", color="white", size=16, weight="bold"), on_click=ir_al_mes_siguiente, style=ft.ButtonStyle(padding=0, shape=ft.RoundedRectangleBorder(radius=17), bgcolor={ft.ControlState.DEFAULT: "transparent", ft.ControlState.HOVERED: "rgba(255, 255, 255, 0.15)"})),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor=color_azul_premium, border=borde_azul_titulo, padding=Padding(15, 0, 15, 0), border_radius=6, margin=Padding(-9, -9, -9, 10)),
            ft.Divider(height=1, color="rgba(255,255,255,0.2)"),
            ft.Container(content=almanaque_completo, padding=Padding(0, 10, 0, 0), expand=True)
        ], spacing=0), bgcolor="#85000000", border=borde_de_las_tablas, border_radius=12, padding=Padding(15, 15, 15, 15), expand=2
    )

    cuadro_reservas = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Text("RESERVAS PAGADAS", color="white", weight="bold", size=13), bgcolor=color_azul_premium, border=borde_azul_titulo, alignment=ft.Alignment(0, 0), padding=Padding(0, 8, 0, 8), border_radius=6, margin=Padding(-9, -9, -9, 10)),
            ft.Divider(height=1, color="rgba(255,255,255,0.2)"),
            ft.Container(content=lista_reservas_dia, padding=Padding(0, 10, 0, 0), expand=True)
        ], spacing=0), bgcolor="#85000000", border=borde_de_las_tablas, border_radius=12, padding=Padding(15, 15, 15, 15), expand=1
    )

    panel_izquierdo = ft.Column([cuadro_nuevo, cuadro_cronograma, cuadro_reservas], expand=1, spacing=14)
    redibujar_calendario_dinamico()

    # --- TABLA DERECHA CON COLUMNAS COMPATIBLES ---
    def texto_encabezado(texto, espacio):
        return ft.Container(
            content=ft.Text(texto, color="white", weight=ft.FontWeight.BOLD, size=13, text_align=ft.TextAlign.CENTER),
            expand=espacio, alignment=ft.Alignment(0, 0),
        )

    tabla_encabezado = ft.Container(
        content=ft.Row([
            ft.Container(
                expand=3,                     
                padding=Padding(10, 0, 0, 0), 
                content=texto_encabezado("HABITACIÓN", 3)
            ),
            texto_encabezado("TIPO", 2),
            texto_encabezado("CAPACIDAD", 2),
            texto_encabezado("ESTADO", 2),
            texto_encabezado("ADULTO", 2),
            texto_encabezado("NIÑO", 2),
        ]),
        bgcolor="#030097", border=borde_azul_titulo, border_radius=6,
        padding=Padding(12, 8, 12, 8), margin=Padding(-9, -9, -9, 12),
    )

    cuadro_tabla = ft.Container(
        content=ft.Column([tabla_encabezado, lista_habitaciones], expand=True),
        bgcolor="#85000000", border=borde_de_las_tablas, border_radius=12, padding=15, expand=3
    )

    # --- LÓGICA DE DETECCIÓN ADAPTATIVA ---
    def ajustar_pantalla(e):
        if page.width < 800:
            panel_izquierdo.expand = 2  
            cuadro_tabla.expand = 3     
        else:
            panel_izquierdo.expand = 1
            cuadro_tabla.expand = 3
        page.update()

    page.on_resize = ajustar_pantalla

    cuerpo_principal = ft.Row([panel_izquierdo, cuadro_tabla], expand=True, spacing=20)

    contenedor_master = ft.Container(
        image=ft.DecorationImage(src="fondo.png", fit="cover"),
        expand=True, padding=20,
        content=ft.Column([menu_superior, ft.Container(height=12), cuerpo_principal], expand=True)
    )

    page.overlay.append(dialogo_cupones_maestro)
    page.add(contenedor_master)
    
    # Renderizado y calibración inicial
    actualizar_grillas_desde_db()
    aplicar_filtros_universales(None)
    ajustar_pantalla(None)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
