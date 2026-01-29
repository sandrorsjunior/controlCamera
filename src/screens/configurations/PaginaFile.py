import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import threading
import json
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
        
        # --- Frame de Configuração (URL) ---
        config_frame = ttk.LabelFrame(self, text="Configurações de Conexão", padding="10")
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="URL do Servidor:").pack(side="left", padx=5)
        self.entry_url = ttk.Entry(config_frame, width=40)
        self.entry_url.insert(0, "opc.tcp://192.168.250.1:4840")
        self.entry_url.pack(side="left", fill="x", expand=True, padx=5)

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
        data = {
            "url": self.entry_url.get(),
            "variables": []
        }
        
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
        valor_booleano = self.bool_var.get()

        # Pega a variável selecionada na tabela
        selected = self.tree.selection()
        if not selected:
            self.log("ERRO: Nenhuma variável selecionada na tabela.")
            self.btn_send.config(state="normal")
            return
        
        item = self.tree.item(selected[0])
        ns, var_name = item['values']

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
