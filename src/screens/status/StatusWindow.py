import tkinter as tk  # Importa a biblioteca padrão de interface gráfica do Python.
from tkinter import ttk  # Importa widgets com estilo moderno (Themed Tkinter).
import json  # Importa biblioteca para ler arquivos de configuração JSON.
from src.model.OpcuaDTO import OpcuaDTO

class StatusWindow(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)  # Inicializa a classe pai (Frame do Tkinter).
        self.controller = controller  # Armazena referência ao controlador principal da aplicação.
        
        # Variáveis de Controle
        self.monitoring = False  # Flag para controlar se o loop de monitoramento deve continuar rodando.
        self.vars_ui = {} # Dicionário para mapear NodeId (string) -> BooleanVar (variável do Tkinter).
        self.plc_url = "opc.tcp://localhost:4840"  # URL padrão, será substituída pelo valor do JSON.
        self.subscribed_vars = set()
        
        # Layout Principal
        # Cria o título da página.
        label_title = ttk.Label(self, text="Monitoramento de Variáveis OPC UA", font=("Helvetica", 16))
        label_title.pack(side="top", fill="x", pady=10, padx=10)
        
        # Área de Lista com Rolagem (Scrollable)
        self.canvas = tk.Canvas(self)  # Cria um Canvas para permitir a rolagem do conteúdo.
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)  # Barra de rolagem vertical.
        self.scrollable_frame = ttk.Frame(self.canvas)  # Frame interno que conterá a lista de variáveis.
        
        # Configura evento para atualizar a área de rolagem sempre que o tamanho do frame interno mudar.
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Cria uma janela dentro do canvas para desenhar o frame.
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)  # Conecta o canvas à scrollbar.
        
        # Empacota (exibe) o canvas e a scrollbar na tela.
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.scrollbar.pack(side="right", fill="y")
        
        # Carregamento inicial da configuração (será recarregado ao iniciar monitoramento).
        self.load_config_and_build_ui()

    def load_config_and_build_ui(self):
        
        # Limpa a interface existente (remove widgets antigos da lista).
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.vars_ui.clear()  # Limpa o dicionário de mapeamento.
        
        variables = []  # Lista temporária para armazenar variáveis lidas do JSON.
        try:
            # Abre o arquivo de configuração.
            with open("plc_config.json", "r") as f:
                data = json.load(f)
                self.plc_url = data.get("url", self.plc_url)  # Lê a URL do PLC.
                variables = data.get("variables", [])  # Lê a lista de variáveis.
        except Exception as e:
            print(f"Erro ao ler config: {e}")
            
        # Cria os Cabeçalhos da Tabela (Nome, NodeID, Ativo).
        ttk.Label(self.scrollable_frame, text="Nome", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Label(self.scrollable_frame, text="NodeID", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        ttk.Label(self.scrollable_frame, text="Ativo", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        ttk.Label(self.scrollable_frame, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=10, pady=5, sticky="w")
        
        # Constrói as linhas da tabela iterando sobre as variáveis.
        for i, var in enumerate(variables):
            if len(var) >= 2:
                ns, name = var[0], var[1]  # Extrai namespace e nome.
                node_id = f"ns={ns};s={name}"  # Formata o NodeID padrão OPC UA.
                
                # Cria Labels para Nome e NodeID.
                ttk.Label(self.scrollable_frame, text=name).grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
                ttk.Label(self.scrollable_frame, text=node_id).grid(row=i+1, column=1, padx=10, pady=5, sticky="w")
                
                # Cria variável booleana do Tkinter para controlar o estado do checkbox.
                bool_var = tk.BooleanVar(value=False)
                # Cria o Checkbox (desabilitado para usuário, serve apenas como indicador visual).
                chk = ttk.Checkbutton(self.scrollable_frame, variable=bool_var, state="disabled")
                chk.grid(row=i+1, column=2, padx=10, pady=5)
                
                # Cria indicador LED (Canvas)
                canvas_led = tk.Canvas(self.scrollable_frame, width=20, height=20, highlightthickness=0)
                canvas_led.grid(row=i+1, column=3, padx=10, pady=5)
                led = canvas_led.create_oval(2, 2, 18, 18, fill="gray", outline="black")
                
                # Guarda a referência da variável Tkinter usando o NodeID como chave.
                self.vars_ui[node_id] = {"var": bool_var, "canvas": canvas_led, "led": led}

    def update_ui_callback(self, node_id_str, value):
        # Callback chamado pela thread secundária.
        # Usa .after(0, ...) para agendar a atualização na thread principal (Main Thread) do Tkinter.
        # print(f"Update recebido: {node_id_str} -> {value}")
        # Isso é crucial porque o Tkinter não é thread-safe.
        self.after(15, lambda n=node_id_str, v=value: self._update_checkbox(n, v))

    def _update_checkbox(self, node_id_str, value):
        # Atualiza o valor do checkbox na interface.
        if node_id_str in self.vars_ui:
            # Tratamento robusto para o valor booleano
            bool_val = value
            
            # Se for string, trata "false" como False
            if isinstance(value, str):
                bool_val = value.lower() not in ('false', '0', 'off')
            # Se for um objeto DataValue do OPC UA (caso raro), tenta extrair o valor
            elif hasattr(value, 'Value'):
                bool_val = bool(value.Value.Value)
            else:
                bool_val = bool(value)

            item = self.vars_ui[node_id_str]
            item["var"].set(bool_val)
            color = "#00FF00" if bool_val else "#FF0000" # Verde se True, Vermelho se False
            item["canvas"].itemconfig(item["led"], fill=color)
            # print(f"UI Atualizada: {node_id_str} para {color}")
        else:
            print(f"Aviso: NodeID '{node_id_str}' recebido do callback não encontrado na UI.")

    def iniciar_monitoramento(self):
        # Inicia o processo de monitoramento.
        self.load_config_and_build_ui()  # Recarrega configurações.
        # Registra esta janela como observadora do DTO
        OpcuaDTO().add_observer(self.update_ui_callback)
        self.monitoring = True  # Ativa a flag.
        
        # Verifica se o serviço compartilhado está conectado
        shared = self.controller.shared_plc
        # Inscreve todas as variáveis configuradas (O SharedPLC gerencia a conexão internamente)
        try:
            with open("plc_config.json", "r") as f:
                data = json.load(f)
                variables = data.get("variables", [])
                
                for var in variables:
                    if len(var) >= 2:
                        ns, name = var[0], var[1]
                        node_id = f"ns={ns};s={name}"
                        # Evita subscrever múltiplas vezes a mesma variável
                        if node_id not in self.subscribed_vars:
                            # Passamos None como callback, pois a atualização virá via OpcuaDTO observer
                            shared.subscribe(ns, name, None)
                        if node_id in self.subscribed_vars:
                            print(f"Monitorando: {node_id}")
                            self.subscribed_vars.add(node_id)
        except Exception as e:
            print(f"Erro ao inscrever variáveis: {e}")
        
    def parar_monitoramento(self):
        # Sinaliza para parar o loop de monitoramento.
        self.monitoring = False
        # Remove o observador para evitar chamadas em janela fechada/parada
        OpcuaDTO().remove_observer(self.update_ui_callback)