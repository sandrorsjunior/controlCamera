import cv2
import numpy as np
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
        self.running = False
        self.imagem_congelada = None 
        self.modo_estatico = False

    def iniciar(self):
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
        if not self.view.winfo_exists() or not self.running or self.modo_estatico:
            return

        ret, frame = self.cap.read()
        if ret:
            # Mostra o frame cru (ou processado se quiséssemos live processing)
            # Aqui, conforme lógica original, mostramos o frame e processamos em background/overlay
            self.view.mostrar_imagem_no_label(frame)
            self.atualizar_processamento(frame)
        
        self.view.after(15, self.loop)

    def atualizar_processamento(self, image=None):
        """Aplica filtros e deteção na imagem (congelada ou frame atual)."""
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
            mask = processor.create_mask_by_HSV(lower, upper)
        elif seg_type == "by_limiar":
            mask = processor.create_mask_by_threshold(self.view.slider_threshold_min.get(), self.view.slider_threshold_max.get())
        else:
            # Fallback ou implementação futura para by_shape
            mask = processor.create_mask_by_HSV(lower, upper)
        
        mask_clean = processor.remove_noise(mask)
        contours, hierarchy = processor.get_contours_hierarchy(mask_clean)
        
        if contours:
            img_resultado = processor.objects_detection(
                contours, 
                tolerance=500,
                show_contours=self.view.check_contour.get(),
                central_point=True,
                show_color=True,
                hierarchy=hierarchy,
                show_holes=True
            )
            stats = processor.get_statistics()
            self.view.var_pecas_detectadas.set(str(stats['total_objects']))
        else:
            img_resultado = img_processar
            self.view.var_pecas_detectadas.set("0")

        # Decide qual imagem mostrar baseado na seleção da View
        self.view.atualizar_visualizacao_final(img_resultado, mask, mask_clean, self.imagem_congelada)