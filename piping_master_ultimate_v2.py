import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import math
import json
import os

MATERIALS_FILE = "materials.json"

DEFAULT_MATERIALS = {
    "P235GH (Stal węglowa)": {
        "Rm_20": 360.0, "Gęstość": 7850.0, "Alpha": 11.5, "Modul_E": 206000,
        "Rp02_T": {"20": 235, "100": 214, "150": 198, "200": 181, "250": 165, "300": 147, "350": 132, "400": 120,
                   "450": 110}
    },
    "P265GH (Stal węglowa)": {
        "Rm_20": 410.0, "Gęstość": 7850.0, "Alpha": 11.5, "Modul_E": 206000,
        "Rp02_T": {"20": 265, "100": 241, "150": 223, "200": 205, "250": 188, "300": 173, "350": 153, "400": 138,
                   "450": 125}
    },
    "16Mo3 (Stal stopowa)": {
        "Rm_20": 450.0, "Gęstość": 7850.0, "Alpha": 11.3, "Modul_E": 205000,
        "Rp02_T": {"20": 280, "100": 259, "150": 247, "200": 235, "250": 219, "300": 200, "350": 182, "400": 170,
                   "450": 161}
    },
    "1.4301 / 304 (Stal nierdzewna)": {
        "Rm_20": 520.0, "Gęstość": 7900.0, "Alpha": 16.0, "Modul_E": 193000,
        "Rp02_T": {"20": 210, "100": 157, "150": 142, "200": 127, "250": 118, "300": 110, "350": 104, "400": 98,
                   "450": 94}
    },
    "1.4404 / 316L (Stal nierdzewna)": {
        "Rm_20": 490.0, "Gęstość": 7950.0, "Alpha": 16.0, "Modul_E": 190000,
        "Rp02_T": {"20": 200, "100": 165, "150": 150, "200": 137, "250": 127, "300": 119, "350": 113, "400": 108,
                   "450": 103}
    }
}


def zaladuj_materialy():
    if not os.path.exists(MATERIALS_FILE):
        try:
            with open(MATERIALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_MATERIALS, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    try:
        with open(MATERIALS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for mat in data.values():
                mat["Rp02_T"] = {int(k): v for k, v in mat["Rp02_T"].items()}
            return data
    except Exception:
        return DEFAULT_MATERIALS


def zapisz_materialy(data):
    try:
        with open(MATERIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się zapisać bazy materiałów: {e}")


EN10220_THICKNESSES = [
    2.0, 2.3, 2.6, 2.9, 3.2, 3.6, 4.0, 4.5, 5.0, 5.4, 5.6, 6.3, 7.1,
    8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0, 17.5, 20.0, 22.2, 25.0
]

DIAMETERS = ["21.3", "26.9", "33.7", "42.4", "48.3", "60.3", "76.1",
             "88.9", "114.3", "139.7", "168.3", "219.1", "273.0", "323.9"]

TEMPERATURES = [str(i) for i in range(20, 451)]
PRESSURES = [f"{i / 10:.1f}" for i in range(1, 401)]
Z_FACTORS = ["1.0", "0.85", "0.7"]
C1_VALUES = ["12.5", "10.0", "0.5", "0.3", "0.0"]
C2_VALUES = ["0.0", "0.5", "1.0", "1.5", "2.0", "3.0"]
C3_VALUES = ["0.0", "0.5", "1.0", "1.5", "2.0"]
BEND_RADII = ["1.5D", "3D", "5D"]


def interpoluj_rp(temp, slownik_rp):
    temperatury = sorted(slownik_rp.keys())
    if temp <= temperatury[0]: return slownik_rp[temperatury[0]]
    if temp >= temperatury[-1]: return slownik_rp[temperatury[-1]]
    for i in range(len(temperatury) - 1):
        t1, t2 = temperatury[i], temperatury[i + 1]
        if t1 <= temp <= t2:
            rp1, rp2 = slownik_rp[t1], slownik_rp[t2]
            return rp1 + (rp2 - rp1) * (temp - t1) / (t2 - t1)


def dobierz_grubosc_z_szeregu(e_req):
    for t in EN10220_THICKNESSES:
        if t >= e_req: return t
    return e_req


def dobierz_klase_kolnierza(p_mpa, temp):
    p_bar = p_mpa * 10.0
    wsp = 1.0 if temp <= 100 else (0.9 if temp <= 200 else (0.75 if temp <= 300 else 0.6))
    p_efektywne = p_bar / wsp
    if p_efektywne <= 16:
        return "PN16"
    elif p_efektywne <= 25:
        return "PN25"
    elif p_efektywne <= 40:
        return "PN40"
    elif p_efektywne <= 63:
        return "PN63"
    elif p_efektywne <= 100:
        return "PN100"
    else:
        return "PN160 lub wyższy"


class MaterialEditorWindow(tk.Toplevel):
    def __init__(self, parent, update_callback):
        super().__init__(parent)
        self.title("Edytor Bazy Materiałów")
        self.geometry("450x420")
        self.resizable(False, False)
        self.update_callback = update_callback
        self.materials_data = zaladuj_materialy()
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Wybierz materiał do edycji lub dodaj nowy:").pack(anchor=tk.W, pady=2)
        self.combo_mats = ttk.Combobox(frame, values=list(self.materials_data.keys()), state="readonly", width=40)
        self.combo_mats.pack(anchor=tk.W, pady=5)
        self.combo_mats.bind("<<ComboboxSelected>>", self.on_select)

        form_frame = ttk.LabelFrame(frame, text="Parametry materiału", padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(form_frame, text="Nazwa:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.e_name = ttk.Entry(form_frame, width=25)
        self.e_name.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(form_frame, text="Rm w 20°C (MPa):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.e_rm = ttk.Entry(form_frame, width=25)
        self.e_rm.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(form_frame, text="Gęstość (kg/m3):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.e_dens = ttk.Entry(form_frame, width=25)
        self.e_dens.grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Label(form_frame, text="Alpha (10^-6/K):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.e_alpha = ttk.Entry(form_frame, width=25)
        self.e_alpha.grid(row=3, column=1, sticky=tk.W, pady=2)

        ttk.Label(form_frame, text="Moduł Younga E (MPa):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.e_mod = ttk.Entry(form_frame, width=25)
        self.e_mod.grid(row=4, column=1, sticky=tk.W, pady=2)

        btn_f = ttk.Frame(frame)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="Zapisz", command=self.zapisz).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Usuń", command=self.usun).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Nowy", command=self.nowy).pack(side=tk.LEFT, padx=5)

        if self.materials_data:
            self.combo_mats.current(0)
            self.on_select()

    def on_select(self, event=None):
        name = self.combo_mats.get()
        if name in self.materials_data:
            m = self.materials_data[name]
            self.e_name.delete(0, tk.END);
            self.e_name.insert(0, name)
            self.e_rm.delete(0, tk.END);
            self.e_rm.insert(0, str(m.get("Rm_20", 360)))
            self.e_dens.delete(0, tk.END);
            self.e_dens.insert(0, str(m.get("Gęstość", 7850)))
            self.e_alpha.delete(0, tk.END);
            self.e_alpha.insert(0, str(m.get("Alpha", 11.5)))
            self.e_mod.delete(0, tk.END);
            self.e_mod.insert(0, str(m.get("Modul_E", 206000)))

    def nowy(self):
        self.combo_mats.set('')
        self.e_name.delete(0, tk.END);
        self.e_rm.delete(0, tk.END)
        self.e_dens.delete(0, tk.END);
        self.e_dens.insert(0, "7850")
        self.e_alpha.delete(0, tk.END);
        self.e_alpha.insert(0, "11.5")
        self.e_mod.delete(0, tk.END);
        self.e_mod.insert(0, "206000")

    def zapisz(self):
        name = self.e_name.get().strip()
        if not name: return
        try:
            rm = float(self.e_rm.get().replace(',', '.'))
            dens = float(self.e_dens.get().replace(',', '.'))
            alpha = float(self.e_alpha.get().replace(',', '.'))
            mod = float(self.e_mod.get().replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Błąd", "Błędne dane liczbowe.")
            return

        old_name = self.combo_mats.get()
        rp_dict = self.materials_data.get(old_name, {}).get("Rp02_T", {20: 235, 100: 214, 200: 181, 300: 147, 400: 120})
        if old_name and old_name in self.materials_data and old_name != name:
            del self.materials_data[old_name]

        self.materials_data[name] = {
            "Rm_20": rm, "Gęstość": dens, "Alpha": alpha, "Modul_E": mod,
            "Rp02_T": {str(k): v for k, v in rp_dict.items()}
        }
        zapisz_materialy(self.materials_data)
        self.update_callback()
        messagebox.showinfo("Sukces", "Zapisano materiał.")
        self.combo_mats['values'] = list(self.materials_data.keys())
        self.combo_mats.set(name)

    def usun(self):
        name = self.combo_mats.get()
        if name in self.materials_data and len(self.materials_data) > 1:
            del self.materials_data[name]
            zapisz_materialy(self.materials_data)
            self.update_callback()
            self.combo_mats['values'] = list(self.materials_data.keys())
            self.combo_mats.current(0);
            self.on_select()
            messagebox.showinfo("Sukces", "Usunięto materiał.")


class PipingMasterPROUltimate(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PipingMaster PRO (Ultimate Suite v2.0)")
        self.geometry("1020x960")
        self.resizable(False, False)

        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        self.materials = zaladuj_materialy()
        self.dark_mode = False
        self.wyniki_dane = {}

        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_calc = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calc, text=" Kalkulator Rurociągu ")
        self.create_calculator_tab(self.tab_calc)

        self.tab_batch = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_batch, text=" Tabela Linii (Line List) ")
        self.create_batch_tab(self.tab_batch)

    def create_calculator_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        lf_mat = ttk.LabelFrame(left_frame, text="1. Materiał i Warunki", padding="8")
        lf_mat.pack(fill=tk.X, pady=2)

        ttk.Label(lf_mat, text="Materiał:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.combo_mat = ttk.Combobox(lf_mat, values=list(self.materials.keys()), state="readonly", width=22)
        self.combo_mat.grid(row=0, column=1, sticky=tk.W, pady=2)
        if self.materials: self.combo_mat.current(0)
        self.combo_mat.bind("<<ComboboxSelected>>", self.on_temp_change)

        ttk.Button(lf_mat, text="Edytor", command=self.otworz_edytor).grid(row=0, column=2, padx=2)

        ttk.Label(lf_mat, text="Temperatura T (°C):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.combo_temp = ttk.Combobox(lf_mat, values=TEMPERATURES, width=12)
        self.combo_temp.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.combo_temp.set("200")
        self.combo_temp.bind("<KeyRelease>", self.on_temp_change)
        self.combo_temp.bind("<<ComboboxSelected>>", self.on_temp_change)

        ttk.Label(lf_mat, text="Rp0.2 w temp. T (MPa):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.entry_rp = ttk.Entry(lf_mat, width=14)
        self.entry_rp.grid(row=2, column=1, sticky=tk.W, pady=2)

        self.lbl_creep = ttk.Label(lf_mat, text="", foreground="red")
        self.lbl_creep.grid(row=3, column=0, columnspan=3, sticky=tk.W)

        lf_geom = ttk.LabelFrame(left_frame, text="2. Geometria, Ciśnienie i Próżnia", padding="8")
        lf_geom.pack(fill=tk.X, pady=2)

        ttk.Label(lf_geom, text="Średnica zewnętrzna D_o (mm):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.combo_d = ttk.Combobox(lf_geom, values=DIAMETERS, width=12)
        self.combo_d.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.combo_d.set(DIAMETERS[8])

        ttk.Label(lf_geom, text="Ciśnienie obliczeniowe p_c (MPa):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.combo_p = ttk.Combobox(lf_geom, values=PRESSURES, width=12)
        self.combo_p.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.combo_p.set("4.0")

        self.vacuum_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(lf_geom, text="Praca pod próżnią / Ciśnienie zewn.", variable=self.vacuum_mode).grid(row=2,
                                                                                                             column=0,
                                                                                                             columnspan=2,
                                                                                                             sticky=tk.W,
                                                                                                             pady=2)

        ttk.Label(lf_geom, text="Współczynnik złącza z:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.combo_z = ttk.Combobox(lf_geom, values=Z_FACTORS, width=12)
        self.combo_z.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.combo_z.set("1.0")

        ttk.Label(lf_geom, text="Promień gięcia kolana:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.combo_bend = ttk.Combobox(lf_geom, values=BEND_RADII, width=12)
        self.combo_bend.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.combo_bend.set("1.5D")

        lf_allow = ttk.LabelFrame(left_frame, text="3. Naddatki i Izolacja", padding="8")
        lf_allow.pack(fill=tk.X, pady=2)

        self.c1_mode = tk.StringVar(value="%")
        ttk.Label(lf_allow, text="c1 (Tolerancja hutnicza):").grid(row=0, column=0, sticky=tk.W, pady=2)
        f_c1 = ttk.Frame(lf_allow)
        f_c1.grid(row=0, column=1, sticky=tk.W)
        self.combo_c1 = ttk.Combobox(f_c1, values=C1_VALUES, width=6)
        self.combo_c1.pack(side=tk.LEFT, padx=(0, 5))
        self.combo_c1.set("12.5")
        ttk.Radiobutton(f_c1, text="%", variable=self.c1_mode, value="%").pack(side=tk.LEFT)
        ttk.Radiobutton(f_c1, text="mm", variable=self.c1_mode, value="mm").pack(side=tk.LEFT)

        ttk.Label(lf_allow, text="c2 (Korozja) / c3 (Pocienienie):").grid(row=1, column=0, sticky=tk.W, pady=2)
        f_c23 = ttk.Frame(lf_allow)
        f_c23.grid(row=1, column=1, sticky=tk.W)
        self.combo_c2 = ttk.Combobox(f_c23, values=C2_VALUES, width=5)
        self.combo_c2.pack(side=tk.LEFT, padx=(0, 2));
        self.combo_c2.set("1.5")
        self.combo_c3 = ttk.Combobox(f_c23, values=C3_VALUES, width=5)
        self.combo_c3.pack(side=tk.LEFT);
        self.combo_c3.set("0.0")

        ttk.Label(lf_allow, text="Izolacja grubość (mm) / Gęstość:").grid(row=2, column=0, sticky=tk.W, pady=2)
        f_ins = ttk.Frame(lf_allow)
        f_ins.grid(row=2, column=1, sticky=tk.W)
        self.entry_ins_th = ttk.Entry(f_ins, width=5)
        self.entry_ins_th.pack(side=tk.LEFT, padx=(0, 2));
        self.entry_ins_th.insert(0, "50")
        self.entry_ins_dens = ttk.Entry(f_ins, width=6)
        self.entry_ins_dens.pack(side=tk.LEFT);
        self.entry_ins_dens.insert(0, "150")

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="OBLICZ", command=self.oblicz).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2,
                                                                       ipady=5)
        ttk.Button(btn_frame, text="Kopiuj", command=self.kopiuj_do_schowka).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                  padx=2, ipady=5)

        btn_frame2 = ttk.Frame(left_frame)
        btn_frame2.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame2, text="Zapisz TXT", command=self.generuj_raport_txt).pack(side=tk.LEFT, expand=True,
                                                                                        fill=tk.X, padx=2, ipady=5)
        ttk.Button(btn_frame2, text="Zapisz PDF", command=self.generuj_raport_pdf).pack(side=tk.LEFT, expand=True,
                                                                                        fill=tk.X, padx=2, ipady=5)

        btn_frame3 = ttk.Frame(left_frame)
        btn_frame3.pack(fill=tk.X, pady=4)
        self.btn_theme = ttk.Button(btn_frame3, text="Przełącz Tryb Ciemny (Dark Mode)", command=self.toggle_dark_mode)
        self.btn_theme.pack(fill=tk.X, ipady=3)

        lf_canvas = ttk.LabelFrame(right_frame, text="Schemat przekroju rury", padding="5")
        lf_canvas.pack(fill=tk.X, pady=2)

        self.canvas = tk.Canvas(lf_canvas, width=410, height=190, bg="white", highlightthickness=1,
                                highlightbackground="#ccc")
        self.canvas.pack(padx=5, pady=5)
        self.narysuj_schemat_domyslny()

        lf_res = ttk.LabelFrame(right_frame, text="Wyniki Obliczeń, Kołnierze i Analityka", padding="5")
        lf_res.pack(fill=tk.BOTH, expand=True, pady=2)

        self.txt_wyniki = tk.Text(lf_res, height=13, width=50, font=("Consolas", 9), bg="#fcfcfc")
        self.txt_wyniki.pack(fill=tk.BOTH, expand=True)

        self.txt_wyniki.tag_config("red", foreground="#cc0000", font=("Consolas", 9, "bold"))
        self.txt_wyniki.tag_config("green", foreground="#008800", font=("Consolas", 9, "bold"))
        self.txt_wyniki.tag_config("normal", foreground="#333333")

        self.txt_wyniki.insert(tk.END, "Wprowadź dane i kliknij 'OBLICZ'...")
        self.txt_wyniki.config(state=tk.DISABLED)
        self.on_temp_change()

    def create_batch_tab(self, parent):
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Tabela Linii Projektowych:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)

        columns = ("id", "material", "dn", "p", "t", "t_nom", "mawp")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree.heading("id", text="Nr Linii")
        self.tree.heading("material", text="Materiał")
        self.tree.heading("dn", text="D_o (mm)")
        self.tree.heading("p", text="p_c (MPa)")
        self.tree.heading("t", text="T (°C)")
        self.tree.heading("t_nom", text="Wym. t_nom (mm)")
        self.tree.heading("mawp", text="MAWP (MPa)")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        ctrl_f = ttk.Frame(frame)
        ctrl_f.pack(fill=tk.X, pady=10)

        ttk.Button(ctrl_f, text="Dodaj przykładową linię", command=self.batch_add_sample).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_f, text="Przelicz wszystkie linie", command=self.batch_calculate).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_f, text="Usuń zaznaczoną", command=self.batch_remove).pack(side=tk.LEFT, padx=5)

    def batch_add_sample(self):
        self.tree.insert("", tk.END, values=("LINE-001", "P235GH (Stal węglowa)", "114.3", "4.0", "200", "-", "-"))

    def batch_calculate(self):
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            mat_name = vals[1]
            d_o = float(vals[2])
            p_c = float(vals[3])
            temp = float(vals[4])

            mat_data = self.materials.get(mat_name, list(self.materials.values())[0])
            rm = mat_data["Rm_20"]
            rp_dict_int = {int(k): v for k, v in mat_data["Rp02_T"].items()}
            rp = interpoluj_rp(temp, rp_dict_int)
            f = min(rp / 1.5, rm / 2.4)

            e = (p_c * d_o) / (2 * f * 1.0 + p_c)
            e_min = e + 1.5
            e_req = e_min / (1 - 0.125)
            t_nom = dobierz_grubosc_z_szeregu(e_req)

            t_min_rzecz = t_nom * (1 - 0.125)
            mawp = (2 * f * 1.0 * (t_min_rzecz - 1.5)) / (d_o - (t_min_rzecz - 1.5))

            self.tree.item(item, values=(vals[0], vals[1], vals[2], vals[3], vals[4], str(t_nom), f"{mawp:.2f}"))
        messagebox.showinfo("Batch", "Przeliczono wszystkie linie w tabeli!")

    def batch_remove(self):
        selected = self.tree.selection()
        for item in selected:
            self.tree.delete(item)

    def otworz_edytor(self):
        MaterialEditorWindow(self, self.odswiez_baze_materialow)

    def odswiez_baze_materialow(self):
        self.materials = zaladuj_materialy()
        self.combo_mat['values'] = list(self.materials.keys())
        if self.materials: self.combo_mat.current(0)
        self.on_temp_change()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        bg_col = "#2b2b2b" if self.dark_mode else "#f0f0f0"
        text_col = "#ffffff" if self.dark_mode else "#000000"
        canvas_bg = "#1e1e1e" if self.dark_mode else "white"
        text_bg = "#222222" if self.dark_mode else "#fcfcfc"

        self.config(bg=bg_col)
        self.canvas.config(bg=canvas_bg)
        self.txt_wyniki.config(bg=text_bg, fg=text_col)
        self.btn_theme.config(
            text="Przełącz Tryb Jasny (Light Mode)" if self.dark_mode else "Przełącz Tryb Ciemny (Dark Mode)")

    def str_to_float(self, val):
        return float(val.replace(',', '.')) if val.strip() else 0.0

    def on_temp_change(self, event=None):
        try:
            mat_nazwa = self.combo_mat.get()
            temp = self.str_to_float(self.combo_temp.get())
            if "węglowa" in mat_nazwa and temp > 400:
                self.lbl_creep.config(text="⚠ UWAGA: T > 400°C. Pełzanie!")
            else:
                self.lbl_creep.config(text="")
            rp_dict = self.materials[mat_nazwa]["Rp02_T"]
            rp_dict_int = {int(k): v for k, v in rp_dict.items()}
            rp_interpolowane = interpoluj_rp(temp, rp_dict_int)
            self.entry_rp.delete(0, tk.END)
            self.entry_rp.insert(0, f"{rp_interpolowane:.1f}")
        except:
            pass

    def narysuj_schemat_domyslny(self):
        self.canvas.delete("all")
        bg_col = "#1e1e1e" if self.dark_mode else "white"
        txt_col = "#aaaaaa" if self.dark_mode else "#888888"
        self.canvas.config(bg=bg_col)
        self.canvas.create_text(205, 95, text="Schemat przekroju rury\n(pojawi się po obliczeniach)", justify=tk.CENTER,
                                fill=txt_col, font=("Arial", 10))

    def narysuj_schemat(self, d_o, t_nom, ins_th):
        self.canvas.delete("all")
        cx, cy = 205, 95
        max_rozmiar = d_o + 2 * ins_th * 1.5
        skala = min(130 / max_rozmiar, 1.0)

        r_zew = (d_o / 2.0) * skala
        r_wew = ((d_o - 2 * t_nom) / 2.0) * skala
        r_izol = ((d_o + 2 * ins_th) / 2.0) * skala

        if ins_th > 0:
            self.canvas.create_oval(cx - r_izol, cy - r_izol, cx + r_izol, cy + r_izol, fill="#e1f5fe",
                                    outline="#0288d1", width=2)
            self.canvas.create_text(cx, cy - r_izol - 8, text=f"Izolacja: {ins_th} mm", fill="#01579b",
                                    font=("Arial", 8, "bold"))

        self.canvas.create_oval(cx - r_zew, cy - r_zew, cx + r_zew, cy + r_zew, fill="#cfd8dc", outline="#37474f",
                                width=2)
        self.canvas.create_oval(cx - r_wew, cy - r_wew, cx + r_wew, cy + r_wew,
                                fill="#2b2b2b" if self.dark_mode else "white", outline="#37474f", width=1)

        # POPRAWIONE WYMIAROWANIE D_o (dokładnie od lewej do prawej zewnętrznej krawędzi)
        y_wymiaru = cy + r_zew + 18
        self.canvas.create_line(cx - r_zew, y_wymiaru, cx + r_zew, y_wymiaru, arrow=tk.BOTH,
                                fill="#ff5252" if self.dark_mode else "#d32f2f", width=1.5)
        self.canvas.create_text(cx, y_wymiaru + 12, text=f"D_o = {d_o} mm",
                                fill="#ff5252" if self.dark_mode else "#d32f2f", font=("Arial", 9, "bold"))

        # Wymiarowanie grubości ścianki t
        self.canvas.create_line(cx, cy, cx + r_zew, cy, arrow=tk.LAST, fill="#448aff" if self.dark_mode else "#1976d2",
                                width=1.5)
        self.canvas.create_text(cx + (r_zew / 2), cy - 12, text=f"t = {t_nom} mm",
                                fill="#448aff" if self.dark_mode else "#1976d2", font=("Arial", 8, "bold"))

    def oblicz(self):
        try:
            mat_nazwa = self.combo_mat.get()
            temp = self.str_to_float(self.combo_temp.get())
            rp = self.str_to_float(self.entry_rp.get())
            mat_data = self.materials[mat_nazwa]
            rm = mat_data["Rm_20"]
            rp_dict_int = {int(k): v for k, v in mat_data["Rp02_T"].items()}
            rp_20 = rp_dict_int[20]
            dens = mat_data["Gęstość"]
            alpha = mat_data["Alpha"]
            e_mod = mat_data["Modul_E"]

            d_o = self.str_to_float(self.combo_d.get())
            p_c = self.str_to_float(self.combo_p.get())
            is_vacuum = self.vacuum_mode.get()
            z = self.str_to_float(self.combo_z.get())
            bend_type = self.combo_bend.get()

            c1_val = self.str_to_float(self.combo_c1.get())
            c2_val = self.str_to_float(self.combo_c2.get())
            c3_val = self.str_to_float(self.combo_c3.get())
            is_c1_percent = (self.c1_mode.get() == "%")

            ins_th = self.str_to_float(self.entry_ins_th.get())
            ins_dens = self.str_to_float(self.entry_ins_dens.get())

            f = min(rp / 1.5, rm / 2.4)
            e = (p_c * d_o) / (2 * f * z + p_c)
            e_min = e + c2_val + c3_val
            e_req = e_min / (1 - c1_val / 100.0) if is_c1_percent else e_min + c1_val
            t_nom = dobierz_grubosc_z_szeregu(e_req)

            buckling_status = "Brak (Ciśnienie wewnętrzne)"
            if is_vacuum:
                p_crit = 2.0 * e_mod * (t_nom / d_o) ** 3 / (1.0 - 0.3 ** 2)
                buckling_status = f"OK (P_crit ~ {p_crit:.2f} MPa)" if p_crit >= 0.1 else "RYZYKO WYBOCZENIA POD PRÓŻNIĄ!"

            R_bend_factor = 1.5 if "1.5D" in bend_type else (3.0 if "3D" in bend_type else 5.0)
            R_bend = R_bend_factor * d_o
            i_ext = (4 * R_bend / d_o - 1) / (4 * R_bend / d_o - 2)
            i_int = (4 * R_bend / d_o + 1) / (4 * R_bend / d_o + 2)
            e_bend_ext = e * i_ext
            e_bend_int = e * i_int

            t_min_rzecz = t_nom * (1 - c1_val / 100.0) if is_c1_percent else t_nom - c1_val
            e_calc = t_min_rzecz - c2_val - c3_val
            mawp = (2 * f * z * e_calc) / (d_o - e_calc) if e_calc > 0 else 0.0

            klasa_kolnierza = dobierz_klase_kolnierza(p_c, temp)

            f_test_20 = min(rp_20 / 1.05, rm / 2.4)
            p_test = max(1.43 * p_c, 1.25 * p_c * (f_test_20 / f))
            e_test_req = (p_test * d_o) / (2 * f_test_20 * z + p_test)
            test_ok = "ZGODNY" if t_min_rzecz >= e_test_req else "NIEZGODNY!"

            t_m_metr = (d_o - t_nom) * t_nom * math.pi * dens * 1e-6
            d_wew = d_o - 2 * t_nom
            woda_metr = (math.pi * (d_wew ** 2) / 4) * 1000 * 1e-6
            d_izol_zew = d_o + 2 * ins_th
            izol_metr = (math.pi * ((d_izol_zew / 1000) ** 2 - (d_o / 1000) ** 2) / 4) * ins_dens

            Z_mod = (math.pi * (d_o ** 4 - d_wew ** 4)) / (32 * d_o)
            w_calkowite = (t_m_metr + woda_metr) * 9.81
            L_stress = math.sqrt((8 * Z_mod * f) / w_calkowite) if w_calkowite > 0 else 5.0
            max_span = min(L_stress, 12.0)

            delta_T = max(0.0, temp - 20.0)
            wydluzenie_mm_m = alpha * delta_T * 1e-3

            self.wyniki_dane = {
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "D_o": d_o, "t_nom": t_nom, "Material": mat_nazwa, "T": temp, "p_c": p_c,
                "mawp": round(mawp, 3), "p_test": round(p_test, 3), "masa_sucha": round(t_m_metr, 2),
                "masa_woda": round(t_m_metr + woda_metr, 2), "wydluzenie": round(wydluzenie_mm_m, 2),
                "max_span": round(max_span, 2), "kolnierz": klasa_kolnierza
            }

            self.narysuj_schemat(d_o, t_nom, ins_th)

            self.txt_wyniki.config(state=tk.NORMAL)
            self.txt_wyniki.delete(1.0, tk.END)

            raport = f"""=== RAPORT ULTIMATE EN 13480 ===
1. GEOMETRIA: D_o={d_o} mm | p_c={p_c} MPa | T={temp}°C | Próżnia: {'TAK' if is_vacuum else 'NIE'}
2. DOBÓR ŚCIANKI: e_req={e_req:.3f} mm => RURA: {d_o} x {t_nom} mm
3. KOLANA (R={bend_type}): Extrados={e_bend_ext:.3f} | Intrados={e_bend_int:.3f} mm
"""
            self.txt_wyniki.insert(tk.END, raport, "normal")

            if mawp >= p_c:
                self.txt_wyniki.insert(tk.END, f"4. MAWP = {mawp:.3f} MPa (Ciśnienie dopuszczalne - OK)\n", "green")
            else:
                self.txt_wyniki.insert(tk.END, f"4. MAWP = {mawp:.3f} MPa (Poniżej p_c - ZA NISKIE!)\n", "red")

            self.txt_wyniki.insert(tk.END, f"5. DOBÓR KOŁNIERZA (EN 1092-1): Wymagana klasa {klasa_kolnierza}\n",
                                   "normal")
            self.txt_wyniki.insert(tk.END, f"6. SPRAWDZENIE PRÓŻNI/WYBOCZENIA: {buckling_status}\n", "normal")

            if t_min_rzecz >= e_test_req:
                self.txt_wyniki.insert(tk.END, f"7. HYDROTEST ({p_test:.3f} MPa): Status {test_ok}\n", "green")
            else:
                self.txt_wyniki.insert(tk.END, f"7. HYDROTEST ({p_test:.3f} MPa): Status {test_ok}\n", "red")

            stress_info = f"""----------------------------------------
[DANE ANALITYCZNE I NAPRĘŻENIOWE]:
- Masa rury (sucha / z wodą): {t_m_metr:.2f} / {t_m_metr + woda_metr:.2f} kg/m
- Szacowany max. rozstaw podpór: {max_span:.2f} m
- Moduł Younga (E): {e_mod:.0f} MPa | Wydłużenie: {wydluzenie_mm_m:.2f} mm/m
"""
            self.txt_wyniki.insert(tk.END, stress_info, "normal")
            self.txt_wyniki.config(state=tk.DISABLED)

        except ValueError:
            messagebox.showerror("Błąd danych", "Sprawdź poprawność wprowadzonych wartości.")

    def kopiuj_do_schowka(self):
        if not self.wyniki_dane:
            messagebox.showwarning("Brak danych", "Wykonaj najpierw obliczenia.")
            return
        tekst = f"D_o: {self.wyniki_dane['D_o']} | t_nom: {self.wyniki_dane['t_nom']} | MAWP: {self.wyniki_dane['mawp']} MPa | Kołnierz: {self.wyniki_dane['kolnierz']}"
        self.clipboard_clear();
        self.clipboard_append(tekst)
        messagebox.showinfo("Schowek", "Skopiowano podstawowe podsumowanie do schowka!")

    def generuj_raport_txt(self):
        tresc = self.txt_wyniki.get(1.0, tk.END).strip()
        if not tresc or "Wprowadź" in tresc: return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("TXT", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f: f.write(tresc)
            messagebox.showinfo("Sukces", "Zapisano plik TXT.")

    def generuj_raport_pdf(self):
        tresc = self.txt_wyniki.get(1.0, tk.END).strip()
        if not tresc or "Wprowadź" in tresc: return
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if path:
                c = canvas.Canvas(path, pagesize=letter)
                c.drawString(50, 750, "RAPORT PIPINGMASTER PRO ULTIMATE")
                y = 710
                for line in tresc.split('\n'):
                    c.drawString(50, y, line);
                    y -= 16
                c.save()
                messagebox.showinfo("Sukces", "Zapisano plik PDF.")
        except ImportError:
            messagebox.showerror("Błąd", "Brak biblioteki ReportLab (pip install reportlab)")


if __name__ == "__main__":
    app = PipingMasterPROUltimate()
    app.mainloop()