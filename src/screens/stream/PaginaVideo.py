import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import json
import os
from src.controller.VideoController import VideoController


class PaginaVideo(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Instancia o controlador de vídeo
        self.video_controller = VideoController(self, self.controller.cap)
        
        # Variáveis de Controlo (Tkinter Variables)
        self.var_pecas_detectadas = tk.StringVar(value="0")
        self.var_forma = tk.StringVar(value="square")
        self.var_imagem_tipo = tk.StringVar(value="img_resultado")
        self.var_type_of_segmentation = tk.StringVar(value="by_color")
        
        # --- LAYOUT PRINCIPAL (2 Colunas) ---
        # Coluna Esquerda: Vídeo + Botões Ação
        self.frame_video_area = ttk.Frame(self)
        self.frame_video_area.pack(side="left", fill="both", expand=True, padx=10, pady=30)
        
        # Coluna Direita: Painel de Controlos
        self.container_controls = ttk.Frame(self, width=450)
        self.container_controls.pack(side="right", fill="y", padx=10, pady=10)
        self.container_controls.pack_propagate(False) # Fixar largura

        self.canvas_controls = tk.Canvas(self.container_controls, highlightthickness=0)
        self.scrollbar_controls = ttk.Scrollbar(self.container_controls, orient="vertical", command=self.canvas_controls.yview)

        # Frame interno (onde os widgets serão colocados)
        self.frame_controls = ttk.Frame(self.canvas_controls)
        
        # Configurar scrollregion quando o frame interno muda de tamanho
        self.frame_controls.bind("<Configure>", lambda e: self.canvas_controls.configure(scrollregion=self.canvas_controls.bbox("all")))

        self.window_controls = self.canvas_controls.create_window((0, 0), window=self.frame_controls, anchor="nw")
        self.canvas_controls.configure(yscrollcommand=self.scrollbar_controls.set)

        self.canvas_controls.pack(side="left", fill="both", expand=True)
        self.scrollbar_controls.pack(side="right", fill="y")

        # Ajustar largura do frame interno ao redimensionar canvas
        self.canvas_controls.bind('<Configure>', self._on_canvas_configure)
        
        # Bind MouseWheel (Scroll com o rato)
        self.container_controls.bind('<Enter>', self._bound_to_mousewheel)
        self.container_controls.bind('<Leave>', self._unbound_to_mousewheel)
        
        # --- CONSTRUÇÃO DA ÁREA ESQUERDA ---
        self.setup_video_area()
        
        # --- CONSTRUÇÃO DA ÁREA DIREITA ---
        self.setup_control_panel()

    def _on_canvas_configure(self, event):
        self.canvas_controls.itemconfig(self.window_controls, width=event.width)

    def _bound_to_mousewheel(self, event):
        self.canvas_controls.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas_controls.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas_controls.yview_scroll(int(-1*(event.delta/120)), "units")

    def setup_video_area(self):
        # 1. Label do Vídeo
        self.lbl_video = ttk.Label(self.frame_video_area, text="Sem Sinal de Vídeo")
        self.lbl_video.pack(fill="both", expand=True, pady=(0, 10))
        
        # 2. Botões (Get Image / Clean Image)
        frame_botoes = ttk.Frame(self.frame_video_area)
        frame_botoes.pack(fill="x")
        
        btn_get = ttk.Button(frame_botoes, text="GET IMAGE", command=self.video_controller.get_image)
        btn_get.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_clean = ttk.Button(frame_botoes, text="CLEAN IMAGE", command=self.video_controller.clean_image)
        btn_clean.pack(side="left", fill="x", expand=True, padx=5)

    def create_labeled_slider(self, parent, label_text, from_, to, initial):
        """Cria um slider com label de texto e valor numérico ao lado."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(frame, text=label_text, width=6).pack(side="left")
        
        var_val = tk.StringVar(value=f"{int(initial)}")
        
        def update_val(v):
            var_val.set(f"{float(v):.0f}")
            self.ao_mexer_slider()

        slider = ttk.Scale(frame, from_=from_, to=to, orient="horizontal", command=update_val)
        slider.set(initial)
        slider.label_var = var_val
        slider.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Label(frame, textvariable=var_val, width=4).pack(side="right")
        
        return slider

    def setup_control_panel(self):
        # Estilo para LabelFrames
        # ttk usa estilos nativos, removemos o dicionário style_box que usava opções do tk
        
        # 1. Contador de Peças
        lbl_contador = ttk.Label(self.frame_controls, text="Número de peças detectadas:", font=("Arial", 10))
        lbl_contador.pack(anchor="w", pady=(0, 5))
        
        # Configurar estilo para o label de valor (azul e fundo branco)
        style = ttk.Style()
        style.configure("Score.TLabel", foreground="blue", background="white", font=("Arial", 14, "bold"), relief="sunken")
        
        self.lbl_valor_pecas = ttk.Label(self.frame_controls, textvariable=self.var_pecas_detectadas,
                                        style="Score.TLabel")
        self.lbl_valor_pecas.pack(fill="x", pady=(0, 15))

        # 3. Threshold Limiar
        box_hsv_limiar_min = ttk.LabelFrame(self.frame_controls, text="HSV limits MIN")
        box_hsv_limiar_min.pack(fill="x", pady=5)
        
        self.slider_Hue_min = self.create_labeled_slider(box_hsv_limiar_min, "Hue", 0, 255, 50)
        self.slider_Sat_min = self.create_labeled_slider(box_hsv_limiar_min, "Sat", 0, 255, 150)
        self.slider_Value_min = self.create_labeled_slider(box_hsv_limiar_min, "Val", 0, 255, 150)

        box_hsv_limiar_max = ttk.LabelFrame(self.frame_controls, text="HSV limits MAX")
        box_hsv_limiar_max.pack(fill="x", pady=5)
        
        self.slider_Hue_max = self.create_labeled_slider(box_hsv_limiar_max, "Hue", 0, 255, 50)
        self.slider_Sat_max = self.create_labeled_slider(box_hsv_limiar_max, "Sat", 0, 255, 150)
        self.slider_Value_max = self.create_labeled_slider(box_hsv_limiar_max, "Val", 0, 255, 150)

        # 3. Threshold Limiar
        box_threshold = ttk.LabelFrame(self.frame_controls, text="THRESHOLD limits MIN")
        box_threshold.pack(fill="x", pady=5)
        
        self.slider_threshold_min = self.create_labeled_slider(box_threshold, "Min", 0, 255, 50)
        self.slider_threshold_max = self.create_labeled_slider(box_threshold, "Max", 0, 255, 150)

        # 7. Params of circles
        box_circle = ttk.LabelFrame(self.frame_controls, text="Circle Params")
        box_circle.pack(fill="x", pady=5, padx=5)
        
        self.slider_circle_dp = self.create_labeled_slider(box_circle, "DP", 1, 2, 1)
        self.slider_circle_min_dist = self.create_labeled_slider(box_circle, "Min Dist", 0, 100, 40)
        self.slider_circle_param1 = self.create_labeled_slider(box_circle, "Param1", 0, 100, 50)
        self.slider_circle_param2 = self.create_labeled_slider(box_circle, "Param2", 0, 100, 25)
        self.slider_circle_min_radius = self.create_labeled_slider(box_circle, "Min R", 0, 100, 10)
        self.slider_circle_max_radius = self.create_labeled_slider(box_circle, "Max R", 0, 200, 100)


        # 4. Contour & Blur Config (Lado a Lado)
        frame_configs = ttk.Frame(self.frame_controls)
        frame_configs.pack(fill="x", pady=5)
        
        box_contour = ttk.LabelFrame(frame_configs, text="Contour Config")
        box_contour.pack(side="left", fill="both", expand=True, padx=(0, 2))
        self.check_contour = tk.BooleanVar(value=True)
        self.check_inverseMask = tk.BooleanVar(value=False)
        ttk.Checkbutton(box_contour, text="Draw", variable=self.check_contour, command=self.ao_mexer_slider).pack(pady=10)
        ttk.Checkbutton(box_contour, text="Inverse Mask", variable=self.check_inverseMask, command=self.ao_mexer_slider).pack(pady=10)

        box_blur = ttk.LabelFrame(frame_configs, text="Blur Config")
        box_blur.pack(side="left", fill="both", expand=True, padx=(2, 0))
        self.slider_blur = self.create_labeled_slider(box_blur, "Blur", 1, 15, 1)



                # 6. View Type Selection
        type_of_segmentation = ttk.LabelFrame(self.frame_controls, text="Type of Segmentation")
        type_of_segmentation.pack(fill="x", pady=5)
        ttk.Radiobutton(type_of_segmentation, text="By Color", variable=self.var_type_of_segmentation, value="by_color", command=self.ao_mexer_slider).pack(anchor="w", padx=10)
        ttk.Radiobutton(type_of_segmentation, text="By Limiar", variable=self.var_type_of_segmentation, value="by_limiar", command=self.ao_mexer_slider).pack(anchor="w", padx=10)
        ttk.Radiobutton(type_of_segmentation, text="By Shape", variable=self.var_type_of_segmentation, value="by_shape", command=self.ao_mexer_slider).pack(anchor="w", padx=10)


        # 5. Profile & Description
        # CORREÇÃO AQUI: mt=10 removido, usado pady=(10, 0)
        ttk.Label(self.frame_controls, text="Profile:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.entry_profile = ttk.Entry(self.frame_controls)
        self.entry_profile.pack(fill="x", pady=(0, 5))
        
        ttk.Label(self.frame_controls, text="Description:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.entry_desc = ttk.Entry(self.frame_controls)
        self.entry_desc.pack(fill="x", pady=(0, 10))

        
        # 6. View Type Selection
        box_view = ttk.LabelFrame(self.frame_controls, text="View Type")
        box_view.pack(fill="x", pady=5)
        ttk.Radiobutton(box_view, text="Result", variable=self.var_imagem_tipo, value="img_resultado", command=self.ao_mexer_slider).pack(anchor="w", padx=10)
        ttk.Radiobutton(box_view, text="Mask Clean", variable=self.var_imagem_tipo, value="mask_clean", command=self.ao_mexer_slider).pack(anchor="w", padx=10)
        ttk.Radiobutton(box_view, text="Mask Raw", variable=self.var_imagem_tipo, value="mask", command=self.ao_mexer_slider).pack(anchor="w", padx=10)
        ttk.Radiobutton(box_view, text="Original Frozen", variable=self.var_imagem_tipo, value="imagem_congelada", command=self.ao_mexer_slider).pack(anchor="w", padx=10)

        # Botão para salvar configuração
        ttk.Button(self.frame_controls, text="Salvar Configuração", command=self.save_configuration).pack(fill="x", pady=10)

    def save_configuration(self):
        """Salva as configurações atuais num ficheiro JSON, adicionando um novo perfil."""
        profile_name = self.entry_profile.get()
        if not profile_name:
            print("Erro: O campo Profile é obrigatório.")
            return

        new_data = {
            "profile": profile_name,
            "description": self.entry_desc.get(),
            "hsv_min": [self.slider_Hue_min.get(), self.slider_Sat_min.get(), self.slider_Value_min.get()],
            "hsv_max": [self.slider_Hue_max.get(), self.slider_Sat_max.get(), self.slider_Value_max.get()],
            "threshold": [self.slider_threshold_min.get(), self.slider_threshold_max.get()],
            "blur": self.slider_blur.get(),
            "contour": self.check_contour.get(),
            "inverse_mask": self.check_inverseMask.get(),
            "segmentation_type": self.var_type_of_segmentation.get(),
            "circle_hough": [
                self.slider_circle_dp.get(),
                self.slider_circle_min_dist.get(),
                self.slider_circle_param1.get(),
                self.slider_circle_param2.get(),
                self.slider_circle_min_radius.get(),
                self.slider_circle_max_radius.get()
            ]
        }

        file_path = "plc_config.json"
        data = {}

        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        if "profiles" not in data:
            data["profiles"] = []

        data["profiles"].append(new_data)

        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)


    # --- LÓGICA DE VÍDEO E EVENTOS ---

    def ao_mexer_slider(self, _=None):
        """Chamado quando arrastamos um slider. Só atualiza se tivermos uma imagem capturada."""
        if self.video_controller.modo_estatico and self.video_controller.imagem_congelada is not None:
            self.video_controller.atualizar_processamento()

    def iniciar_video(self):
        """Wrapper para manter compatibilidade com app.py"""
        self.video_controller.iniciar()

    def parar_video(self):
        """Wrapper para manter compatibilidade com app.py"""
        self.video_controller.parar()

    def atualizar_visualizacao_final(self, img_resultado, mask, mask_clean, imagem_congelada):
        """
        Recebe as imagens processadas do Controller e decide qual mostrar
        baseado no RadioButton selecionado na GUI.
        """
        tipo = self.var_imagem_tipo.get()
        if tipo == "mask":
            self.mostrar_imagem_no_label(mask)
        elif tipo == "mask_clean":
            self.mostrar_imagem_no_label(mask_clean)
        elif tipo == "imagem_congelada" and imagem_congelada is not None:
            self.mostrar_imagem_no_label(imagem_congelada)
        else:
            self.mostrar_imagem_no_label(img_resultado)

    def mostrar_imagem_no_label(self, cv_image):
        """Função auxiliar para converter CV2(BGR) -> Tkinter e exibir"""
        # Converter BGR para RGB
        if len(cv_image.shape) == 2:
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2RGB)
        else:
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # Obtemos as dimensões originais da imagem
        h_orig, w_orig = rgb_image.shape[:2]

        # Redimensionar para caber na área de vídeo (Responsivo)
        # Pegamos a largura atual do frame de video (container)
        container_w = self.frame_video_area.winfo_width()
        container_h = self.frame_video_area.winfo_height() - 60 # Desconta botões
        
        if container_w > 10 and container_h > 10: 
             # Cálculo para manter o Aspect Ratio (Proporção)
             # Descobrimos o "menor fator de escala" para garantir que a imagem caiba inteira
             ratio = min(container_w / w_orig, container_h / h_orig)
             
             new_w = int(w_orig * ratio)
             new_h = int(h_orig * ratio)
             
             pil_img = Image.fromarray(rgb_image)
             pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
             pil_img = Image.fromarray(rgb_image)

        imgtk = ImageTk.PhotoImage(image=pil_img)
        self.lbl_video.imgtk = imgtk
        self.lbl_video.configure(image=imgtk)