import cv2
import math
import numpy as np
import json

from src.model.OpcuaDTO import OpcuaDTO
from .util.ProcessImage import ProcessImage


class VideoController:
    """
    Classe responsável pela lógica de controle do vídeo, estados e processamento.
    Separa a lógica de negócio da interface gráfica (View).
    """
    def __init__(self, view, cap):
        self.view = view  # Referência para a GUI (PaginaVideo) para ler sliders e atualizar imagem
        self.cap = cap    # Objeto VideoCapture do OpenCV
        
        # Variáveis de Estado
        self.sending_plc = False # Flag para evitar envios sobrepostos
        self.imagem_congelada = None 
        self.modo_estatico = False
        self.running = False
        self.circle_detected = False
        self.msg_sent_to_plc = False
        self.fps = 0
        self.read_errors = 0
        
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
            self.read_errors = 0
            # Mostra o frame cru (ou processado se quiséssemos live processing)
            # Aqui, conforme lógica original, mostramos o frame e processamos em background/overlay
            self.view.mostrar_imagem_no_label(frame)
            self.atualizar_processamento(frame)
        else:
            self.read_errors += 1
            if self.read_errors > 5:
                # Se falhar consecutivamente, desacelera o loop para evitar spam de log e alto uso de CPU
                self.view.after(500, self.loop)
                return
        
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

        self._process_plc_logic()

        # Decide qual imagem mostrar baseado na seleção da View
        self.view.atualizar_visualizacao_final(img_processar, mask, mask_clean, self.imagem_congelada)

    def _process_plc_logic(self):
        """Gerencia a lógica de interação com o PLC (Trigger e Sinais)."""
        if not self.view.var_mode_trigger.get():
            return

        try:
            # Recupera valores do DTO com segurança
            trigger_node = f"ns=4;s={self.view.var_trigger_name.get()}"
            signal_node = "ns=4;s=SinalPython"
            
            dto = OpcuaDTO()
            trigger_active = dto.get_variable(trigger_node) if dto.isVariableSet(trigger_node) else False
            signal_active = dto.get_variable(signal_node) if dto.isVariableSet(signal_node) else False

            # Lógica de disparo
            if self.circle_detected and not self.msg_sent_to_plc and trigger_active:
                self.trigger_plc_signals(value=True)
                print("Trigger PLC Enviado: TRUE")
            
            # Lógica de reset (pulso)
            elif signal_active and self.msg_sent_to_plc:
                self.trigger_plc_signals(value=False)
                print("Trigger PLC Enviado: False")
                
        except Exception as e:
            print(f"Erro no processamento PLC: {e}")

    def trigger_plc_signals(self, sgnals=None, value=True):
        """Lê a configuração e envia sinal para o PLC."""
        if sgnals is None:
            sgnals = ["SinalPython"]
            
        self.sending_plc = True
        try:
            url = self.plc_config.get("url")
            variables = self.plc_config.get("variables", [])
            
            # Usa o serviço compartilhado se estiver conectado
            shared = self.view.controller.shared_plc
            for ns, name in variables:
                if name in sgnals:
                    shared.write(ns, name, value)
                    # Envia True para as variáveis configuradas usando a conexão existente
            self.msg_sent_to_plc = value
            
        finally:
            self.sending_plc = False