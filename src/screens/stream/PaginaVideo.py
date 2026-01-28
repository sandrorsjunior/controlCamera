import tkinter as tk
from PIL import Image, ImageTk
import cv2

class PaginaVideo(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.bg_color = "#f0f0f0"
        self.configure(bg=self.bg_color)
        self.running = False
        
        # Título
        lbl_titulo = tk.Label(self, text="Ecrã Principal - Stream de Vídeo", font=("Helvetica", 16, "bold"), bg=self.bg_color)
        lbl_titulo.pack(pady=10)
        
        # Área do Vídeo (Label onde a imagem será atualizada)
        self.lbl_video = tk.Label(self, bg="black")
        self.lbl_video.pack(padx=10, pady=10)
        
        # Área de Controlo
        frame_controlo = tk.Frame(self, bg=self.bg_color)
        frame_controlo.pack(pady=20)
        
        # Botão
        self.btn_acao = tk.Button(frame_controlo, text="Alterar Estado", command=self.alterar_label, 
                                  font=("Arial", 12), bg="#4a90e2", fg="white", width=15)
        self.btn_acao.pack(side="left", padx=10)
        
        # Label que será alterada
        self.lbl_status = tk.Label(frame_controlo, text="Estado: Aguardando...", font=("Arial", 12), bg=self.bg_color, fg="red")
        self.lbl_status.pack(side="left", padx=10)

    def alterar_label(self):
        self.lbl_status.config(text="Estado: Ação Executada!", fg="green")

    def iniciar_video(self):
        # Esta função é chamada repetidamente para atualizar a imagem
        if not self.running:
            self.running = True
            self.atualizar_frame()

    def parar_video(self):
        self.running = False

    def atualizar_frame(self):
        # Verifica se esta frame ainda está visível antes de continuar
        # (Para evitar erros se a app for fechada)
        if not self.winfo_exists() or not self.running:
            return

        ret, frame = self.controller.cap.read()
        
        if ret:
            # OpenCV usa BGR, Tkinter usa RGB. Temos de converter.
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Converter para imagem PIL e depois para ImageTk
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Atualizar a label
            self.lbl_video.imgtk = imgtk # Guardar referência para não ser apagada pelo Garbage Collector
            self.lbl_video.configure(image=imgtk)
        
        # Agendar a próxima atualização (10ms = ~100fps máx)
        # Só chamamos se esta página estiver visível (opcional, para performance)
        self.after(10, self.atualizar_frame)

