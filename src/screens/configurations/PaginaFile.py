import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import threading
from src.controller.PLCController import PLCController

class PaginaFile(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Instancia o controlador de PLC
        self.plc_controller = PLCController()
        
        # --- Estilos ---
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 10))
        
        # --- Frame de Configuração ---
        config_frame = ttk.LabelFrame(self, text="Configurações de Conexão", padding="15")
        config_frame.pack(fill="x", padx=10, pady=10)

        # URL
        ttk.Label(config_frame, text="URL do Servidor:").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_url = ttk.Entry(config_frame, width=40)
        self.entry_url.insert(0, "opc.tcp://192.168.250.1:4840")
        self.entry_url.grid(row=0, column=1, padx=5, pady=5)

        # Namespace (Index)
        ttk.Label(config_frame, text="Namespace Index (ns):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_ns = ttk.Entry(config_frame, width=10)
        self.entry_ns.insert(0, "4")
        self.entry_ns.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Nome da Variável (String ID)
        ttk.Label(config_frame, text="Nome da Variável (s):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_var = ttk.Entry(config_frame, width=30)
        self.entry_var.insert(0, "SinalPython")
        self.entry_var.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # --- Frame de Ação ---
        action_frame = ttk.LabelFrame(self, text="Comandos", padding="15")
        action_frame.pack(fill="x", padx=10, pady=5)

        # Checkbox para Valor Booleano
        self.bool_var = tk.BooleanVar(value=False)
        self.chk_value = ttk.Checkbutton(action_frame, text="Enviar valor TRUE (Ativado)", variable=self.bool_var, command=self.update_chk_text)
        self.chk_value.pack(anchor="w", pady=5)

        # Botão de Enviar
        self.btn_send = ttk.Button(action_frame, text="Enviar Dados para o PLC", command=self.start_async_thread)
        self.btn_send.pack(fill="x", pady=10)

        # --- Área de Log ---
        log_frame = ttk.LabelFrame(self, text="Logs de Execução", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

    def update_chk_text(self):
        """Atualiza o texto do checkbox visualmente"""
        if self.bool_var.get():
            self.chk_value.config(text="Enviar valor: TRUE (Ativado)")
        else:
            self.chk_value.config(text="Enviar valor: FALSE (Desativado)")

    def log(self, message):
        """Função auxiliar para escrever na área de log de forma segura"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # Scroll automático para o fim
        self.log_area.config(state='disabled')

    def start_async_thread(self):
        """Inicia a thread separada para não travar a GUI"""
        self.btn_send.config(state="disabled") # Desabilita botão para evitar cliques múltiplos
        self.log("-" * 30)
        
        # Pega os valores da GUI
        url = self.entry_url.get()
        ns = self.entry_ns.get()
        var_name = self.entry_var.get()
        valor_booleano = self.bool_var.get()

        # Cria e inicia a thread
        thread = threading.Thread(target=self.run_async_task, args=(url, ns, var_name, valor_booleano))
        thread.start()

    def run_async_task(self, url, ns, var_name, valor_booleano):
        """Wrapper para rodar o asyncio dentro da thread"""
        try:
            # Passamos self.log como callback para o controller
            asyncio.run(self.plc_controller.connect_and_send(url, ns, var_name, valor_booleano, self.log))
        except Exception as e:
            self.log(f"ERRO CRÍTICO: {e}")
        finally:
            # Reabilita o botão na thread principal
            self.after(0, lambda: self.btn_send.config(state="normal"))
