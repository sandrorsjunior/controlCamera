import tkinter as tk
from tkinter import ttk
import cv2

from src.screens.stream.PaginaVideo import PaginaVideo
from src.screens.ImageConfigurations.PaginaFuntions import PaginaFunctions
from src.screens.configurations.PaginaFile import PaginaFile
from src.screens.status.StatusWindow import StatusWindow
from src.controller.SharedPLC import SharedPLC


class AplicacaoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configurações da Janela Principal
        self.title("Sistema de Video Monitorização")
        self.geometry("1100x600")
        
        # Inicializar a captura de vídeo (0 é geralmente a webcam padrão)
        #"http://10.223.45.145:8080/video"
        self.cap = cv2.VideoCapture(0)  # Pode ser substituído por 0 para webcam local
        
        # Contentor principal onde as "janelas" (frames) serão mostradas
        self.container = ttk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Dicionário para guardar as referências das janelas
        self.frames = {}
        
        # Serviço Compartilhado de PLC
        self.shared_plc = SharedPLC()
        
        # Criar o Menu Superior (Fixo em todas as janelas)
        self.criar_menu()
        
        # Inicializar as páginas
        # Adicionamos a HomePage (Video) e as outras páginas
        for F in (PaginaVideo, PaginaFunctions, PaginaFile, StatusWindow):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            # Coloca todas as janelas na mesma grelha, empilhadas
            frame.grid(row=0, column=0, sticky="nsew")
        
        # Mostrar a janela inicial
        self.mostrar_frame("PaginaVideo")
        
        # Protocolo para fechar corretamente a câmara ao sair
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

    def criar_menu(self):
        barra_menu = tk.Menu(self)
        
        # Menu File
        menu_file = tk.Menu(barra_menu, tearoff=0)
        menu_file.add_command(label="Ir para File", command=lambda: self.mostrar_frame("PaginaFile"))
        menu_file.add_separator()
        menu_file.add_command(label="Sair", command=self.fechar_app)
        barra_menu.add_cascade(label="File", menu=menu_file)
        
        # Menu Functions
        menu_func = tk.Menu(barra_menu, tearoff=0)
        menu_func.add_command(label="Ir para Functions", command=lambda: self.mostrar_frame("PaginaFunctions"))
        menu_func.add_command(label="Voltar ao Video", command=lambda: self.mostrar_frame("PaginaVideo"))
        barra_menu.add_cascade(label="Functions", menu=menu_func)
        
        # Menu Monitor
        menu_monitor = tk.Menu(barra_menu, tearoff=0)
        menu_monitor.add_command(label="Status Variáveis", command=lambda: self.mostrar_frame("StatusWindow"))
        barra_menu.add_cascade(label="Monitor", menu=menu_monitor)
        
        self.config(menu=barra_menu)

    def mostrar_frame(self, page_name):
        '''Traz a frame escolhida para o topo da pilha'''
        frame = self.frames[page_name]
        frame.tkraise()
        
        # Se for a página de vídeo, certificar-se que o loop de vídeo está ativo
        if page_name == "PaginaVideo":
            frame.iniciar_video()
        else:
            # Opcional: Parar processamento de vídeo se sair da tela para poupar CPU
            self.frames["PaginaVideo"].parar_video()
            
        # Lógica para StatusWindow (Monitoramento)
        if page_name == "StatusWindow":
            frame.iniciar_monitoramento()
        elif "StatusWindow" in self.frames:
            # Para o monitoramento se sair da tela de status
            self.frames["StatusWindow"].parar_monitoramento()

    def fechar_app(self):
        if self.cap.isOpened():
            self.cap.release()
        self.shared_plc.stop()
        self.destroy()
