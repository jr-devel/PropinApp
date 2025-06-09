import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from fpdf import FPDF

# Archivo JSON donde guardamos datos
DATA_FILE = "propinas_data.json"

# Áreas válidas
AREAS = ['Mesero', 'Barista', 'Cocina', 'Loza', 'Gerente', 'Chef']

# Función para cargar datos JSON o crear estructura base
def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # estructura base
        return {"colaboradores": [], "propinas": {}}

# Guardar datos en JSON
def guardar_datos(datos):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

# Clase principal de la app
class PropinasApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestión de Propinas")
        self.geometry("900x600")
        self.resizable(False, False)

        self.datos = cargar_datos()

        self.fecha_actual = datetime.now().strftime('%Y-%m-%d')

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("Treeview",
                             background="#f0f0f0",
                             foreground="black",
                             rowheight=25,
                             fieldbackground="#f0f0f0")
        self.style.map('Treeview', background=[('selected', '#347083')])

        self.crear_widgets()
        self.actualizar_tabla()

    def crear_widgets(self):
        # Frame superior para agregar colaborador y propinas
        frame_top = ttk.Frame(self)
        frame_top.pack(fill=tk.X, padx=10, pady=10)

        # Agregar colaborador
        ttk.Label(frame_top, text="Agregar Colaborador: ").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_nombre = ttk.Entry(frame_top, width=20)
        self.entry_nombre.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(frame_top, text="Área: ").grid(row=0, column=2, sticky=tk.W, padx=(10,0), pady=2)
        self.combo_area = ttk.Combobox(frame_top, values=AREAS, state="readonly", width=15)
        self.combo_area.grid(row=0, column=3, sticky=tk.W, pady=2)
        self.combo_area.set(AREAS[0])

        btn_agregar = ttk.Button(frame_top, text="Agregar", command=self.agregar_colaborador)
        btn_agregar.grid(row=0, column=4, padx=10, pady=2)

        # Ingreso de propinas diarias
        ttk.Label(frame_top, text="Propina total diaria: ").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.entry_propina = ttk.Entry(frame_top, width=20)
        self.entry_propina.grid(row=1, column=1, sticky=tk.W, pady=10)
        btn_registrar = ttk.Button(frame_top, text="Registrar Propina", command=self.registrar_propina)
        btn_registrar.grid(row=1, column=2, pady=10, sticky=tk.W)

        # Botones para mostrar acumulados y exportar
        frame_botones = ttk.Frame(self)
        frame_botones.pack(fill=tk.X, padx=10)

        btn_dia = ttk.Button(frame_botones, text="Mostrar Acumulado Día", command=lambda: self.mostrar_acumulado('dia'))
        btn_dia.pack(side=tk.LEFT, padx=5, pady=5)

        btn_semana = ttk.Button(frame_botones, text="Mostrar Acumulado Semana", command=lambda: self.mostrar_acumulado('semana'))
        btn_semana.pack(side=tk.LEFT, padx=5, pady=5)

        btn_mes = ttk.Button(frame_botones, text="Mostrar Acumulado Mes", command=lambda: self.mostrar_acumulado('mes'))
        btn_mes.pack(side=tk.LEFT, padx=5, pady=5)

        btn_exportar = ttk.Button(frame_botones, text="Exportar Reporte", command=self.exportar_reporte)
        btn_exportar.pack(side=tk.RIGHT, padx=5, pady=5)

        # Tabla para colaboradores
        self.tree = ttk.Treeview(self, columns=("Área", "Propina asignada", "Retenido", "Chef", "Gerente", "Cocina/Loza", "Cristalería"), show='headings', height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.CENTER, width=110)

        # Colores alternos en filas
        self.tree.tag_configure('oddrow', background='white')
        self.tree.tag_configure('evenrow', background='#f2f2f2')

    def agregar_colaborador(self):
        nombre = self.entry_nombre.get().strip()
        area = self.combo_area.get()

        if not nombre:
            messagebox.showwarning("Atención", "El nombre no puede estar vacío.")
            return

        # Validar no duplicados
        for colab in self.datos['colaboradores']:
            if colab['nombre'].lower() == nombre.lower():
                messagebox.showerror("Error", "Colaborador ya existe.")
                return

        self.datos['colaboradores'].append({"nombre": nombre, "area": area})
        guardar_datos(self.datos)

        self.entry_nombre.delete(0, tk.END)
        self.combo_area.set(AREAS[0])

        self.actualizar_tabla()
        messagebox.showinfo("Éxito", f"Colaborador '{nombre}' agregado.")

    def registrar_propina(self):
        propina_str = self.entry_propina.get().strip()
        if not propina_str:
            messagebox.showwarning("Atención", "Ingrese un valor de propina.")
            return
        try:
            propina = float(propina_str)
            if propina <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Ingrese un número válido positivo.")
            return

        fecha = self.fecha_actual
        if fecha not in self.datos['propinas']:
            self.datos['propinas'][fecha] = {}

        # Se sobreescribe la propina diaria (único registro por día)
        self.datos['propinas'][fecha]['total'] = propina
        guardar_datos(self.datos)
        self.entry_propina.delete(0, tk.END)

        self.actualizar_tabla()
        messagebox.showinfo("Registrado", f"Propina diaria {propina:.2f} registrada para {fecha}.")

    def calcular_reparto(self, total_propina):
        # Reglas:
        # Retención 6.7 puntos (ej: si la propina es 10 pts, retienen 6.7 pts)
        retenido = total_propina * 0.67
        no_retenido = total_propina - retenido

        # Del retenido (6.7), se reparte:
        # 15% Chef
        # 15% Gerente
        # 70% Cocina y Loza (repartido equitativamente)

        chef = retenido * 0.15
        gerente = retenido * 0.15
        cocina_loza_total = retenido * 0.70

        # Además 0.01% del total para cristalería (reposicion)
        cristaleria = total_propina * 0.0001

        # Cocina y Loza tienen varios colaboradores, repartir equitativamente
        cocina_loza_colabs = [c for c in self.datos['colaboradores'] if c['area'] in ['Cocina', 'Loza']]
        n_cocina_loza = len(cocina_loza_colabs)
        cocina_loza_por_colab = cocina_loza_total / n_cocina_loza if n_cocina_loza > 0 else 0

        # Meseros y Baristas reparten el 33% (del total) menos lo retenido? No, se quedan con el no retenido (33% está fuera del cálculo)
        # Según el pedido, meseros y baristas reciben la parte sin retención (33%), que es no_retenido
        # Repartiremos ese no retenido entre meseros y baristas equitativamente

        mb_colabs = [c for c in self.datos['colaboradores'] if c['area'] in ['Mesero', 'Barista']]
        n_mb = len(mb_colabs)
        mb_por_colab = no_retenido / n_mb if n_mb > 0 else 0

        # Retenciones por colaborador:
        # Meseros y Baristas: mb_por_colab retenido es la propina bruta - (retenido * 0.67)
        # Cocina y Loza: cocina_loza_por_colab + 0 (su parte del retenido)
        # Chef y Gerente: no reparten a colaboradores, solo reciben su parte fija

        # Para el reporte, haremos un dict por colaborador con nombre y lo que recibe neto

        reparto = {}

        for c in self.datos['colaboradores']:
            area = c['area']
            nombre = c['nombre']
            if area in ['Mesero', 'Barista']:
                reparto[nombre] = {
                    "area": area,
                    "recibe": mb_por_colab,
                    "retenido": mb_por_colab * 0.67  # No retienen más, 0.67 es lo que retienen del total, ya aplicado arriba.
                }
            elif area in ['Cocina', 'Loza']:
                reparto[nombre] = {
                    "area": area,
                    "recibe": cocina_loza_por_colab,
                    "retenido": 0
                }
            elif area == 'Chef':
                reparto[nombre] = {
                    "area": area,
                    "recibe": chef,
                    "retenido": 0
                }
            elif area == 'Gerente':
                reparto[nombre] = {
                    "area": area,
                    "recibe": gerente,
                    "retenido": 0
                }
            else:
                reparto[nombre] = {
                    "area": area,
                    "recibe": 0,
                    "retenido": 0
                }
        return reparto, retenido, cristaleria

    def actualizar_tabla(self):
        # Limpia tabla
        for i in self.tree.get_children():
            self.tree.delete(i)

        fecha = self.fecha_actual
        propina = self.datos['propinas'].get(fecha, {}).get('total', 0)

        reparto, retenido, cristaleria = self.calcular_reparto(propina)

        filas = []
        for idx, colab in enumerate(self.datos['colaboradores']):
            nombre = colab['nombre']
            area = colab['area']

            recibe = reparto.get(nombre, {}).get("recibe", 0)
            reten = 0
            chef = 0
            gerente = 0
            cocina_loza = 0
            crist = 0

            if area in ['Mesero', 'Barista']:
                reten = propina * 0.67
            elif area == 'Chef':
                chef = retenido * 0.15
            elif area == 'Gerente':
                gerente = retenido * 0.15
            elif area in ['Cocina', 'Loza']:
                cocina_loza = (retenido * 0.70) / max(1, len([c for c in self.datos['colaboradores'] if c['area'] in ['Cocina', 'Loza']]))
            crist = cristaleria

            self.tree.insert("", "end",
                             values=(area,
                                     f"{recibe:.2f}",
                                     f"{reten:.2f}",
                                     f"{chef:.2f}",
                                     f"{gerente:.2f}",
                                     f"{cocina_loza:.2f}",
                                     f"{crist:.4f}"),
                             tags=('evenrow' if idx % 2 == 0 else 'oddrow',))

    def mostrar_acumulado(self, periodo):
        # periodo: 'dia', 'semana', 'mes'
        acumulado = {}
        hoy = datetime.now()
        if periodo == 'dia':
            fechas = [hoy.strftime('%Y-%m-%d')]
            titulo = "Acumulado Diario"
        elif periodo == 'semana':
            inicio_sem = hoy - timedelta(days=hoy.weekday())  # Lunes
            fechas = [(inicio_sem + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            titulo = "Acumulado Semanal"
        elif periodo == 'mes':
            fechas = []
            for i in range(31):
                dia = hoy - timedelta(days=i)
                if dia.month == hoy.month:
                    fechas.append(dia.strftime('%Y-%m-%d'))
            titulo = "Acumulado Mensual"
        else:
            messagebox.showerror("Error", "Periodo inválido.")
            return

        # Sumamos propinas
        total_propina = 0
        for f in fechas:
            total_propina += self.datos['propinas'].get(f, {}).get('total', 0)

        # Sumamos reparto proporcional para colaboradores
        for colab in self.datos['colaboradores']:
            acumulado[colab['nombre']] = 0.0

        for f in fechas:
            propina = self.datos['propinas'].get(f, {}).get('total', 0)
            reparto, _, _ = self.calcular_reparto(propina)
            for nombre, data in reparto.items():
                acumulado[nombre] += data['recibe']

        # Mostrar en ventana
        ventana = tk.Toplevel(self)
        ventana.title(titulo)
        ventana.geometry("600x400")

        tree = ttk.Treeview(ventana, columns=("Nombre", "Área", "Acumulado"), show='headings')
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tree.heading("Nombre", text="Nombre")
        tree.heading("Área", text="Área")
        tree.heading("Acumulado", text="Acumulado")

        tree.column("Nombre", anchor=tk.W, width=200)
        tree.column("Área", anchor=tk.CENTER, width=100)
        tree.column("Acumulado", anchor=tk.E, width=120)

        for idx, colab in enumerate(self.datos['colaboradores']):
            nombre = colab['nombre']
            area = colab['area']
            total = acumulado.get(nombre, 0)
            tree.insert("", "end", values=(nombre, area, f"{total:.2f}"),
                        tags=('evenrow' if idx % 2 == 0 else 'oddrow',))

        tree.tag_configure('oddrow', background='white')
        tree.tag_configure('evenrow', background='#f9f9f9')

        btn_cerrar = ttk.Button(ventana, text="Cerrar", command=ventana.destroy)
        btn_cerrar.pack(pady=5)

    def exportar_reporte(self):
        # Exportar acumulado mensual en Excel y PDF

        fechas = []
        hoy = datetime.now()
        for i in range(31):
            dia = hoy - timedelta(days=i)
            if dia.month == hoy.month:
                fechas.append(dia.strftime('%Y-%m-%d'))

        acumulado = {}
        for colab in self.datos['colaboradores']:
            acumulado[colab['nombre']] = {"area": colab['area'], "total": 0.0}

        for f in fechas:
            propina = self.datos['propinas'].get(f, {}).get('total', 0)
            reparto, _, _ = self.calcular_reparto(propina)
            for nombre, data in reparto.items():
                acumulado[nombre]["total"] += data['recibe']

        # Guardar Excel
        df = pd.DataFrame([
            {"Nombre": nombre, "Área": data["area"], "Acumulado": data["total"]}
            for nombre, data in acumulado.items()
        ])
        excel_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")],
                                                  title="Guardar reporte Excel")
        if excel_path:
            df.to_excel(excel_path, index=False)

        # Crear PDF simple
        pdf_path = os.path.splitext(excel_path)[0] + ".pdf" if excel_path else None
        if pdf_path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Reporte Acumulado Mensual de Propinas", ln=1, align='C')

            pdf.set_font("Arial", size=12)
            pdf.ln(10)
            for nombre, data in acumulado.items():
                linea = f"{nombre} ({data['area']}): ${data['total']:.2f}"
                pdf.cell(0, 10, linea, ln=1)

            pdf.output(pdf_path)
            messagebox.showinfo("Exportación completada", f"Reporte guardado:\nExcel: {excel_path}\nPDF: {pdf_path}")

if __name__ == "__main__":
    app = PropinasApp()
    app.mainloop()
