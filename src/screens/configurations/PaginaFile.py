import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import cv2

class PaginaFile(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # --- Estilos ---
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 10))
        
        # --- Frame de Configuração (URL) ---
        config_frame = ttk.LabelFrame(self, text="Configurações de Conexão", padding="10")
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="URL do Servidor:").pack(side="left", padx=5)
        self.entry_url = ttk.Entry(config_frame, width=40)
        self.entry_url.insert(0, "opc.tcp://192.168.250.1:4840")
        self.entry_url.pack(side="left", fill="x", expand=True, padx=5)

        # --- Frame de Configuração de Câmera ---
        camera_frame = ttk.LabelFrame(self, text="Configuração de Câmera", padding="10")
        camera_frame.pack(fill="x", padx=10, pady=5)

        self.var_use_custom_camera = tk.BooleanVar(value=False)
        self.chk_use_custom_camera = ttk.Checkbutton(camera_frame, text="Usar Câmera Personalizada", variable=self.var_use_custom_camera)
        self.chk_use_custom_camera.pack(side="left", padx=5)

        ttk.Label(camera_frame, text="Source (ID/URL):").pack(side="left", padx=5)
        self.entry_camera_source = ttk.Entry(camera_frame, width=20)
        self.entry_camera_source.insert(0, "0")
        self.entry_camera_source.pack(side="left", padx=5)

        ttk.Button(camera_frame, text="Aplicar Câmera", command=self.apply_camera_settings).pack(side="left", padx=5)

        # --- Frame de Gestão de Variáveis ---
        manage_frame = ttk.LabelFrame(self, text="Gestão de Variáveis", padding="10")
        manage_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Inputs para nova variável
        input_frame = ttk.Frame(manage_frame)
        input_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(input_frame, text="NS:").pack(side="left")
        self.entry_ns = ttk.Entry(input_frame, width=5)
        self.entry_ns.insert(0, "4")
        self.entry_ns.pack(side="left", padx=5)

        ttk.Label(input_frame, text="Nome (s):").pack(side="left")
        self.entry_var = ttk.Entry(input_frame, width=20)
        self.entry_var.insert(0, "SinalPython")
        self.entry_var.pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(input_frame, text="Adicionar", command=self.add_variable).pack(side="left", padx=5)
        ttk.Button(input_frame, text="Remover", command=self.delete_variable).pack(side="left", padx=5)

        # Tabela (Treeview)
        # Container para a tabela e scrollbar para organizar o layout
        table_frame = ttk.Frame(manage_frame)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("ns", "name")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        self.tree.heading("ns", text="NS")
        self.tree.heading("name", text="Nome da Variável")
        self.tree.column("ns", width=50, anchor="center")
        self.tree.column("name", width=300, anchor="w")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Adicionar variável padrão
        self.tree.insert("", "end", values=("4", "SinalPython"))

        # Botão Salvar Configuração
        ttk.Button(manage_frame, text="Salvar Configuração (JSON)", command=self.save_configuration).pack(fill="x", padx=5, pady=(0, 5))

        # --- Frame de Ação ---
        action_frame = ttk.LabelFrame(self, text="Comandos", padding="15")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        # Botões Start/Stop Conexão
        conn_frame = ttk.Frame(action_frame)
        conn_frame.pack(fill="x", pady=(0, 10))
        self.btn_start = ttk.Button(conn_frame, text="Start Connection", command=self.start_connection)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_stop = ttk.Button(conn_frame, text="Stop Connection", command=self.stop_connection, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=2)

        # Checkbox para Valor Booleano
        self.bool_var = tk.BooleanVar(value=False)
        self.chk_value = ttk.Checkbutton(action_frame, text="Enviar valor TRUE (Ativado)", variable=self.bool_var, command=self.update_chk_text)
        self.chk_value.pack(anchor="w", pady=5)

        # Botão de Enviar
        self.btn_send = ttk.Button(action_frame, text="Enviar para Variável Selecionada", command=self.start_async_thread)
        self.btn_send.pack(fill="x", pady=10)

        # --- Área de Log ---
        log_frame = ttk.LabelFrame(self, text="Logs de Execução", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

    def apply_camera_settings(self):
        """Aplica as configurações de câmera selecionadas."""
        source = 0
        if self.var_use_custom_camera.get():
            entry_val = self.entry_camera_source.get()
            # Tenta converter para int (índice de câmera), senão usa string (URL/Arquivo)
            if entry_val.isdigit():
                source = int(entry_val)
            else:
                source = entry_val
        
        self.log(f"Configurando câmera com source: {source}")
        
        try:
            if hasattr(self.controller, 'cap'):
                if self.controller.cap is not None:
                    self.controller.cap.release()
                
                self.controller.cap = cv2.VideoCapture(source)
                
                # Otimização para streams de rede (reduz delay e erros de buffer)
                if isinstance(source, str) and (source.lower().startswith("http") or source.lower().startswith("rtsp")):
                    self.controller.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Atualiza VideoController em qualquer tela que o tenha
                if hasattr(self.controller, 'frames'):
                    for frame in self.controller.frames.values():
                        if hasattr(frame, 'video_controller'):
                            frame.video_controller.cap = self.controller.cap
                
                status = "Aberta" if self.controller.cap.isOpened() else "Falha ao abrir"
                self.log(f"Câmera aplicada. Status: {status}")
        except Exception as e:
            self.log(f"Erro ao aplicar câmera: {e}")

    def add_variable(self):
        ns = self.entry_ns.get()
        name = self.entry_var.get()
        if ns and name:
            self.tree.insert("", "end", values=(ns, name))
            # Opcional: Limpar campo nome após adicionar
            # self.entry_var.delete(0, tk.END)

    def delete_variable(self):
        selected_item = self.tree.selection()
        if selected_item:
            self.tree.delete(selected_item)

    def save_configuration(self):
        """Salva a URL e as variáveis num ficheiro JSON"""
        data = {}
        try:
            with open("plc_config.json", "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data["url"] = self.entry_url.get()
        data["variables"] = []
        
        # Percorre todos os itens da tabela
        for item_id in self.tree.get_children():
            item = self.tree.item(item_id)
            data["variables"].append(item['values'])
            
        try:
            with open("plc_config.json", "w") as f:
                json.dump(data, f, indent=4)
            self.log("Configuração salva com sucesso em 'plc_config.json'.")
        except Exception as e:
            self.log(f"Erro ao salvar configuração: {e}")

    def update_chk_text(self):
        """Atualiza o texto do checkbox visualmente"""
        if self.bool_var.get():
            self.chk_value.config(text="Enviar valor: TRUE (Ativado)")
        else:
            self.chk_value.config(text="Enviar valor: FALSE (Desativado)")

    def log(self, message):
        """Função auxiliar para escrever na área de log de forma segura"""
        def _log():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END) # Scroll automático para o fim
            self.log_area.config(state='disabled')
        self.after(0, _log)

    def start_async_thread(self):
        """Inicia a thread separada para não travar a GUI"""
        # Pega os valores da GUI
        valor_booleano = self.bool_var.get()

        # Pega a variável selecionada na tabela
        selected = self.tree.selection()
        if not selected:
            self.log("ERRO: Nenhuma variável selecionada na tabela.")
            return
        
        item = self.tree.item(selected[0])
        ns, var_name = item['values']
        
        # Usa o serviço compartilhado
        if self.controller.shared_plc.connected:
            self.controller.shared_plc.write(ns, var_name, valor_booleano)
        else:
            self.log("ERRO: Conexão não iniciada. Clique em Start Connection.")

    def start_connection(self):
        if self.controller.shared_plc.running: return
        
        url = self.entry_url.get()
        
        # Configura o log do serviço para sair nesta tela
        self.controller.shared_plc.set_log_callback(self.log)
        
        # Inicia o serviço
        self.controller.shared_plc.start(url)
        
        # Atualiza botões
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        # Inscreve as variáveis da lista para monitoramento no log
        for item_id in self.tree.get_children():
            item = self.tree.item(item_id)
            ns, name = item['values']
            # Callback simples para logar mudanças nesta tela
            self.controller.shared_plc.subscribe(ns, name, lambda n, v: self.log(f"Monitor: {n} = {v}"))
        
    def stop_connection(self):
        self.controller.shared_plc.stop()
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
