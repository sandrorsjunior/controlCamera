import tkinter as tk


class PaginaFunctions(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        label = tk.Label(self, text="Área de Funções", font=("Helvetica", 18))
        label.pack(side="top", fill="x", pady=10)
        
        btn = tk.Button(self, text="Voltar à Câmara",
                        command=lambda: controller.mostrar_frame("PaginaVideo"))
        btn.pack()