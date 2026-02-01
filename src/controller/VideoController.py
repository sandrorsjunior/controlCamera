import cv2
import math
import numpy as np
import json
import threading
import asyncio
from .util.ProcessImage import ProcessImage
from src.controller.PLCController import PLCController



class VideoController:
    """
    Classe responsável pela lógica de controle do vídeo, estados e processamento.
    Separa a lógica de negócio da interface gráfica (View).
    """
    def __init__(self, view, cap):
        self.view = view  # Referência para a GUI (PaginaVideo) para ler sliders e atualizar imagem
        self.cap = cap    # Objeto VideoCapture do OpenCV
        
        # Variáveis de Estado
        self.plc_controller = PLCController()
        self.sending_plc = False # Flag para evitar envios sobrepostos
        self.running = False
        self.imagem_congelada = None 
        self.modo_estatico = False
        self.circle_detected = False
        self.msg_sent_to_plc = False
        self.fps = 0
        
        # Cache da configuração do PLC para evitar leitura de disco constante
        self.plc_config = {}
        self.load_plc_config()

    def load_plc_config(self):
        try:
            with open("plc_config.json", "r") as f:
                self.plc_config = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config PLC: {e}")
            self.plc_config = {}

    def iniciar(self):
        self.load_plc_config() # Recarrega caso tenha mudado noutra tela
        if not self.running and not self.modo_estatico:
            self.running = True
            self.loop()

    def parar(self):
        self.running = False

    def get_image(self):
        """Captura a frame atual, para o vídeo e processa."""
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.imagem_congelada = frame
                self.modo_estatico = True
                self.running = False # Para o loop de vídeo
                self.atualizar_processamento() # Processa a imagem congelada

    def clean_image(self):
        """Limpa a imagem congelada e retoma o vídeo."""
        self.modo_estatico = False
        self.imagem_congelada = None
        self.view.var_pecas_detectadas.set("0")
        self.view.lbl_video.configure(image="") # Limpa visualmente
        self.iniciar() # Reinicia o loop

    def loop(self):
        if not self.running or self.modo_estatico:
            return

        ret, frame = self.cap.read()
        if ret:
            # Mostra o frame cru (ou processado se quiséssemos live processing)
            # Aqui, conforme lógica original, mostramos o frame e processamos em background/overlay
            self.view.mostrar_imagem_no_label(frame)
            self.atualizar_processamento(frame)
        
        if self.fps <= 50:
            self.fps += 1
        else:
            self.fps = 0
            self.msg_sent_to_plc = False

        self.view.after(15, self.loop)

    def atualizar_processamento(self, image=None):
        if self.imagem_congelada is None and image is None:
            return
        elif image is not None:
            img_processar = image
        else:
            img_processar = self.imagem_congelada.copy()

        # Acessa configurações da View
        blur_val = int(self.view.slider_blur.get())
        if blur_val % 2 == 0: blur_val += 1
        if blur_val > 1:
            img_processar = cv2.GaussianBlur(img_processar, (blur_val, blur_val), 0)
        
        processor = ProcessImage(image=img_processar)

        lower, upper = np.array([(self.view.slider_Hue_min.get(), self.view.slider_Sat_min.get(), self.view.slider_Value_min.get()),
                                 (self.view.slider_Hue_max.get(), self.view.slider_Sat_max.get(), self.view.slider_Value_max.get())])
        
        seg_type = self.view.var_type_of_segmentation.get()
        if seg_type == "by_color":
            mask = processor.create_mask_by_HSV(lower, upper, self.view.check_inverseMask.get())
        elif seg_type == "by_limiar":
            mask = processor.create_mask_by_threshold(self.view.slider_threshold_min.get(), self.view.slider_threshold_max.get(), self.view.check_inverseMask.get())
        else:
            # Fallback ou implementação futura para by_shape
            mask = processor.create_mask_by_HSV(lower, upper, self.view.check_inverseMask.get())
        
        mask_clean = processor.remove_noise(mask)
        contours, hierarchy = processor.get_contours(mask_clean)
        
        circles = processor.get_circles(mask_clean, 
                                        int(self.view.slider_circle_dp.get()), 
                                        int(self.view.slider_circle_min_dist.get()),
                                        int(self.view.slider_circle_param1.get()),
                                        int(self.view.slider_circle_param2.get()),
                                        int(self.view.slider_circle_min_radius.get()), 
                                        int(self.view.slider_circle_max_radius.get()))
        
        if len(circles) > 0:
            for circle in circles:
                x, y, r = int(circle[0]), int(circle[1]), int(circle[2])
                area = math.pi * (r ** 2)
                if area > 50:
                    self.view.var_pecas_detectadas.set(str(len(circles)))
                    img_processar = cv2.circle(img_processar, (x, y), r, (0, 255, 0), 2)
                    self.circle_detected = True
        else:
            self.circle_detected = False


        if self.circle_detected and not self.msg_sent_to_plc:
            self.trigger_plc_signals()
            #print("Trigger PLC Signal", self.fps, self.msg_sent_to_plc)
            self.msg_sent_to_plc = True
        else:
            self.view.var_pecas_detectadas.set("0")

        # Decide qual imagem mostrar baseado na seleção da View
        self.view.atualizar_visualizacao_final(img_processar, mask, mask_clean, self.imagem_congelada)

    def check_blue_circle(self, contour, image):
        """Verifica se o contorno é um círculo e se a cor média é azul."""
        # 1. Verificar Circularidade
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0: return False
        
        area = cv2.contourArea(contour)
        if area < 500: return False # Ignorar ruído muito pequeno
        
        # Fórmula da circularidade: 4 * pi * Area / Perimetro^2
        # Círculo perfeito = 1.0. Aceitamos > 0.7
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity < 0.7:
            return False

        # 2. Verificar Cor (Azul)
        # Criar máscara para o contorno específico
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        
        # Calcular cor média dentro do contorno (BGR)
        mean_val = cv2.mean(image, mask=mask)[:3]
        
        # Converter BGR médio para HSV
        mean_hsv = cv2.cvtColor(np.uint8([[mean_val]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = mean_hsv
        
        # Faixa de Azul no OpenCV (H: 0-180). Azul é aprox 120.
        # Definindo intervalo: H=[100, 140], S>50, V>50
        return 100 <= h <= 140 and s > 50 and v > 50

    def trigger_plc_signals(self):
        """Lê a configuração e envia sinal para o PLC."""
        self.sending_plc = True
        try:
            url = self.plc_config.get("url")
            variables = self.plc_config.get("variables", [])
            
            # Callback simples para log (pode ser melhorado para usar o log da UI)
            log_cb = lambda msg: print(f"[PLC Auto]: {msg}")
            
            for ns, name in variables:
                # Envia True para as variáveis configuradas
                asyncio.run(self.plc_controller.connect_and_send(url, str(ns), name, True, log_cb))
                
        except Exception as e:
            print(f"Erro ao enviar para PLC: {e}")
        finally:
            self.sending_plc = False