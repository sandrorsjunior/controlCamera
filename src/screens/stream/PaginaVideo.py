import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
from .util.ProcessImage import ProcessImage

class PaginaVideo(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.bg_color = "#e6e6e6"
        self.configure(bg=self.bg_color)
        
        # Variáveis de Estado
        self.running = False
        self.imagem_congelada = None # Guarda a imagem quando clicamos em "Get Image"
        self.modo_estatico = False   # True se estivermos a analisar uma imagem parada
        
        # Variáveis de Controlo (Tkinter Variables)
        self.var_pecas_detectadas = tk.StringVar(value="0")
        self.var_cor_space = tk.StringVar(value="RGB")
        self.var_forma = tk.StringVar(value="square")
        
        # --- LAYOUT PRINCIPAL (2 Colunas) ---
        # Coluna Esquerda: Vídeo + Botões Ação
        self.frame_video_area = tk.Frame(self, bg=self.bg_color)
        self.frame_video_area.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Coluna Direita: Painel de Controlos
        self.frame_controls = tk.Frame(self, bg=self.bg_color, width=350)
        self.frame_controls.pack(side="right", fill="y", padx=10, pady=10)
        
        # --- CONSTRUÇÃO DA ÁREA ESQUERDA ---
        self.setup_video_area()
        
        # --- CONSTRUÇÃO DA ÁREA DIREITA ---
        self.setup_control_panel()

    def setup_video_area(self):
        # 1. Label do Vídeo
        self.lbl_video = tk.Label(self.frame_video_area, bg="black", text="Sem Sinal de Vídeo", fg="white")
        self.lbl_video.pack(fill="both", expand=True, pady=(0, 10))
        
        # 2. Botões (Get Image / Clean Image)
        frame_botoes = tk.Frame(self.frame_video_area, bg=self.bg_color)
        frame_botoes.pack(fill="x")
        
        btn_get = tk.Button(frame_botoes, text="GET IMAGE", command=self.get_image,
                            bg="#27ae60", fg="white", font=("Arial", 10, "bold"), height=2)
        btn_get.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_clean = tk.Button(frame_botoes, text="CLEAN IMAGE", command=self.clean_image,
                              bg="#c0392b", fg="white", font=("Arial", 10, "bold"), height=2)
        btn_clean.pack(side="left", fill="x", expand=True, padx=5)

    def setup_control_panel(self):
        # Estilo para LabelFrames
        style_box = {"bg": self.bg_color, "bd": 2, "relief": "groove", "font": ("Arial", 10, "bold")}
        
        # 1. Contador de Peças
        lbl_contador = tk.Label(self.frame_controls, text="Número de peças detectadas:", 
                                bg=self.bg_color, font=("Arial", 10))
        lbl_contador.pack(anchor="w", pady=(0, 5))
        
        self.lbl_valor_pecas = tk.Label(self.frame_controls, textvariable=self.var_pecas_detectadas,
                                        bg="white", relief="sunken", font=("Arial", 14, "bold"), fg="blue")
        self.lbl_valor_pecas.pack(fill="x", pady=(0, 15))
        
        # 2. Espaço de Cor (HSV, Gray, RGB)
        box_color = tk.LabelFrame(self.frame_controls, text="Color Space", **style_box)
        box_color.pack(fill="x", pady=5, ipady=5)
        
        tk.Radiobutton(box_color, text="HSV", variable=self.var_cor_space, value="HSV", bg=self.bg_color).pack(side="left", expand=True)
        tk.Radiobutton(box_color, text="Gray", variable=self.var_cor_space, value="Gray", bg=self.bg_color).pack(side="left", expand=True)
        tk.Radiobutton(box_color, text="RGB", variable=self.var_cor_space, value="RGB", bg=self.bg_color).pack(side="left", expand=True)
        
        # 3. Threshold Limiar
        box_threshold = tk.LabelFrame(self.frame_controls, text="Threshold Limiar", **style_box)
        box_threshold.pack(fill="x", pady=5)
        
        self.slider_th1 = tk.Scale(box_threshold, from_=0, to=255, orient="horizontal", label="Min Val", bg=self.bg_color, command=self.ao_mexer_slider)
        self.slider_th1.set(50)
        self.slider_th1.pack(fill="x", padx=5)
        
        self.slider_th2 = tk.Scale(box_threshold, from_=0, to=255, orient="horizontal", label="Max Val", bg=self.bg_color, command=self.ao_mexer_slider)
        self.slider_th2.set(150)
        self.slider_th2.pack(fill="x", padx=5)

        # 4. Contour & Blur Config (Lado a Lado)
        frame_configs = tk.Frame(self.frame_controls, bg=self.bg_color)
        frame_configs.pack(fill="x", pady=5)
        
        box_contour = tk.LabelFrame(frame_configs, text="Contour Config", **style_box)
        box_contour.pack(side="left", fill="both", expand=True, padx=(0, 2))
        self.check_contour = tk.BooleanVar(value=True)
        tk.Checkbutton(box_contour, text="Draw", variable=self.check_contour, bg=self.bg_color, command=self.ao_mexer_slider).pack(pady=10)

        box_blur = tk.LabelFrame(frame_configs, text="Blur Config", **style_box)
        box_blur.pack(side="left", fill="both", expand=True, padx=(2, 0))
        self.slider_blur = tk.Scale(box_blur, from_=1, to=15, orient="horizontal", bg=self.bg_color, showvalue=0, command=self.ao_mexer_slider)
        self.slider_blur.set(1)
        self.slider_blur.pack(pady=5, padx=5)

        # 5. Profile & Description
        # CORREÇÃO AQUI: mt=10 removido, usado pady=(10, 0)
        tk.Label(self.frame_controls, text="Profile:", bg=self.bg_color, font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.entry_profile = tk.Entry(self.frame_controls)
        self.entry_profile.pack(fill="x", pady=(0, 5))
        
        tk.Label(self.frame_controls, text="Description:", bg=self.bg_color, font=("Arial", 9, "bold")).pack(anchor="w")
        self.entry_desc = tk.Entry(self.frame_controls)
        self.entry_desc.pack(fill="x", pady=(0, 10))
        
        # 6. Forms Selection
        box_forms = tk.LabelFrame(self.frame_controls, text="Forms", **style_box)
        box_forms.pack(fill="x", pady=5)
        
        tk.Radiobutton(box_forms, text="Square", variable=self.var_forma, value="square", bg=self.bg_color).pack(anchor="w", padx=10)
        tk.Radiobutton(box_forms, text="Triangle", variable=self.var_forma, value="triangle", bg=self.bg_color).pack(anchor="w", padx=10)
        tk.Radiobutton(box_forms, text="Circle", variable=self.var_forma, value="circle", bg=self.bg_color).pack(anchor="w", padx=10)
        
        # 7. Custom Input
        box_custom = tk.LabelFrame(self.frame_controls, text="Custom", **style_box)
        box_custom.pack(fill="x", pady=5)
        
        frame_custom_inner = tk.Frame(box_custom, bg=self.bg_color)
        frame_custom_inner.pack(fill="x", padx=5, pady=5)
        
        tk.Radiobutton(frame_custom_inner, variable=self.var_forma, value="custom", bg=self.bg_color).pack(side="left")
        self.entry_custom = tk.Entry(frame_custom_inner)
        self.entry_custom.pack(side="left", fill="x", expand=True, padx=5)

    # --- LÓGICA DE VÍDEO E EVENTOS ---

    def get_image(self):
        """Captura a frame atual, para o vídeo e processa."""
        if self.controller.cap.isOpened():
            ret, frame = self.controller.cap.read()
            if ret:
                self.imagem_congelada = frame
                self.modo_estatico = True
                self.running = False # Para o loop de vídeo
                self.atualizar_processamento() # Processa a imagem congelada

    def clean_image(self):
        """Limpa a imagem congelada e retoma o vídeo."""
        self.modo_estatico = False
        self.imagem_congelada = None
        self.var_pecas_detectadas.set("0")
        self.lbl_video.configure(image="") # Limpa visualmente
        self.iniciar_video() # Reinicia o loop

    def ao_mexer_slider(self, _=None):
        """Chamado quando arrastamos um slider. Só atualiza se tivermos uma imagem capturada."""
        if self.modo_estatico and self.imagem_congelada is not None:
            self.atualizar_processamento()

    def atualizar_processamento(self):
        """Aplica filtros e deteção na imagem congelada."""
        if self.imagem_congelada is None: return

        # 1. Obter Imagem Base
        img_processar = self.imagem_congelada.copy()
        
        # 2. Aplicar Blur (Se configurado)
        blur_val = int(self.slider_blur.get())
        if blur_val % 2 == 0: blur_val += 1 # Blur precisa de número ímpar
        if blur_val > 1:
            img_processar = cv2.GaussianBlur(img_processar, (blur_val, blur_val), 0)

        # 3. Simulação de conversão de cores (apenas visual por enquanto, 
        #    já que o ProcessImage espera BGR, mas podemos adaptar a lógica aqui)
        cor_space = self.var_cor_space.get()
        # Nota: O ProcessImage trabalha com BGR, então enviamos BGR, 
        # mas poderíamos pré-tratar aqui se necessário.
        
        # 4. Instanciar Processador com parâmetros da GUI
        processor = ProcessImage(image=img_processar)
        
        # 5. Detetar
        # Aqui fazemos a deteção manual para usar os thresholds dos sliders
        t1 = self.slider_th1.get()
        t2 = self.slider_th2.get()
        
        # Criação manual de contornos para usar os sliders
        gray = cv2.cvtColor(img_processar, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, t1, t2)
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            img_resultado = processor.objects_detection(
                contours, 
                tolerance=500, # Área mínima fixa ou poderia ser slider
                show_contours=self.check_contour.get(),
                central_point=True,
                show_color=True,
                hierarchy=hierarchy,
                show_holes=True
            )
            # Atualizar label de contagem
            stats = processor.get_statistics()
            self.var_pecas_detectadas.set(str(stats['total_objects']))
        else:
            img_resultado = img_processar
            self.var_pecas_detectadas.set("0")

        # 6. Converter para mostrar no Tkinter
        self.mostrar_imagem_no_label(img_resultado)

    def iniciar_video(self):
        if not self.running and not self.modo_estatico:
            self.running = True
            self.loop_video()

    def parar_video(self):
        self.running = False

    def loop_video(self):
        if not self.winfo_exists() or not self.running or self.modo_estatico:
            return

        ret, frame = self.controller.cap.read()
        if ret:
            self.mostrar_imagem_no_label(frame)
        
        self.after(15, self.loop_video)

    def mostrar_imagem_no_label(self, cv_image):
        """Função auxiliar para converter CV2(BGR) -> Tkinter e exibir"""
        # Converter BGR para RGB
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