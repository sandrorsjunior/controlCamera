import tkinter as tk
from tkinter import ttk
import json
import os


class PaginaFunctions(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        label = ttk.Label(self, text="Carregar Perfil de Configuração", font=("Helvetica", 16))
        label.pack(side="top", fill="x", pady=10, padx=10)
        
        # Frame para a lista e scrollbarlist_frame = ttk.Frame(self)
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configuração da Treeview
        columns = ("profile", "description")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("profile", text="Perfil")
        self.tree.heading("description", text="Descrição")
        self.tree.column("profile", width=150, anchor="w")
        self.tree.column("description", width=300, anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind de seleção
        self.tree.bind("<<TreeviewSelect>>", self.on_select_profile)
        
        # Botões
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        btn_refresh = ttk.Button(btn_frame, text="Atualizar Lista", command=self.load_profiles)
        btn_refresh.pack(side="left", padx=5)
        
        btn_back = ttk.Button(btn_frame, text="Voltar à Câmara",
                        command=lambda: controller.mostrar_frame("PaginaVideo"))
        btn_back.pack(side="right", padx=5)
        
        # Dados
        self.profiles = []
        self.plc_data = {}
        self.load_profiles()

    def load_profiles(self):
        # Limpa a lista atual
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.profiles = []
        file_path = "plc_config.json"
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", [])
                    self.plc_data = {
                        "url": data.get("url", ""),
                        "variables": data.get("variables", [])
                    }
                
                for i, p in enumerate(self.profiles):
                    self.tree.insert("", "end", iid=str(i), values=(p.get("profile"), p.get("description")))
            except Exception as e:
                print(f"Erro ao carregar perfis: {e}")

    def on_select_profile(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        index = int(selected_items[0])
        if 0 <= index < len(self.profiles):
            profile = self.profiles[index]
            self.apply_profile(profile)

    def apply_profile(self, profile):
        # Obtém a referência da página de vídeo
        if "PaginaVideo" in self.controller.frames:
            page_video = self.controller.frames["PaginaVideo"]
            
            # Função auxiliar para atualizar slider e label
            def update_slider(slider, value):
                slider.set(value)
                if hasattr(slider, 'label_var'):
                    slider.label_var.set(f"{float(value):.0f}")

            # Atualiza HSV Min
            hsv_min = profile.get("hsv_min", [0, 0, 0])
            update_slider(page_video.slider_Hue_min, hsv_min[0])
            update_slider(page_video.slider_Sat_min, hsv_min[1])
            update_slider(page_video.slider_Value_min, hsv_min[2])

            # Atualiza HSV Max
            hsv_max = profile.get("hsv_max", [180, 255, 255])
            update_slider(page_video.slider_Hue_max, hsv_max[0])
            update_slider(page_video.slider_Sat_max, hsv_max[1])
            update_slider(page_video.slider_Value_max, hsv_max[2])

            # Atualiza Threshold
            thresh = profile.get("threshold", [0, 255])
            update_slider(page_video.slider_threshold_min, thresh[0])
            update_slider(page_video.slider_threshold_max, thresh[1])

            # Atualiza Círculo Hough
            circle_params = profile.get("circle_hough", [0, 0, 0, 0, 0, 0])
            update_slider(page_video.slider_circle_dp, circle_params[0])
            update_slider(page_video.slider_circle_min_dist, circle_params[1])
            update_slider(page_video.slider_circle_param1, circle_params[2])
            update_slider(page_video.slider_circle_param2, circle_params[3])
            update_slider(page_video.slider_circle_min_radius, circle_params[4])
            update_slider(page_video.slider_circle_max_radius, circle_params[5])

            # Atualiza Blur
            update_slider(page_video.slider_blur, profile.get("blur", 1))

            # Atualiza Checkboxes e Opções
            page_video.check_contour.set(profile.get("contour", True))
            page_video.check_inverseMask.set(profile.get("inverse_mask", False))
            page_video.var_type_of_segmentation.set(profile.get("segmentation_type", "by_color"))

            # Atualiza Campos de Texto (Perfil e Descrição)
            page_video.entry_profile.delete(0, tk.END)
            page_video.entry_profile.insert(0, profile.get("profile", ""))
            
            page_video.entry_desc.delete(0, tk.END)
            page_video.entry_desc.insert(0, profile.get("description", ""))

            # Força atualização do processamento de imagem
            page_video.ao_mexer_slider()

        # Atualiza PaginaFile
        if "PaginaFile" in self.controller.frames:
            page_file = self.controller.frames["PaginaFile"]
            
            # Atualiza URL
            url = profile.get("url", self.plc_data.get("url", ""))
            page_file.entry_url.delete(0, tk.END)
            page_file.entry_url.insert(0, url)
            
            # Atualiza Variáveis
            variables = profile.get("variables", self.plc_data.get("variables", []))
            
            for item in page_file.tree.get_children():
                page_file.tree.delete(item)
                
            for var in variables:
                if isinstance(var, list) and len(var) >= 2:
                    page_file.tree.insert("", "end", values=(var[0], var[1]))