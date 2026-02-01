import tkinter as tk  # Importa a biblioteca padrão de interface gráfica do Python.
from tkinter import ttk  # Importa widgets com estilo moderno (Themed Tkinter).
import json  # Importa biblioteca para ler arquivos de configuração JSON.
import asyncio  # Importa biblioteca para programação assíncrona (necessária para OPC UA).
import threading  # Importa biblioteca para criar threads paralelas (evita travar a interface).
from asyncua import Client  # Importa o cliente OPC UA da biblioteca asyncua.

class SubHandler:
    """
    Classe manipuladora (Handler) responsável por receber eventos de mudança de dados do servidor OPC UA.
    """
    def __init__(self, update_callback):
        self.update_callback = update_callback  # Guarda a função que será chamada na UI quando o valor mudar.

    def datachange_notification(self, node, val, data):
        # Método chamado automaticamente pela biblioteca quando uma variável monitorada muda de valor.
        # Envia o NodeId (convertido para string) e o novo valor para o callback da interface.
        self.update_callback(str(node.nodeid), val)

class StatusWindow(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)  # Inicializa a classe pai (Frame do Tkinter).
        self.controller = controller  # Armazena referência ao controlador principal da aplicação.
        
        # Variáveis de Controle
        self.monitoring = False  # Flag para controlar se o loop de monitoramento deve continuar rodando.
        self.thread = None  # Variável para armazenar a thread secundária.
        self.vars_ui = {} # Dicionário para mapear NodeId (string) -> BooleanVar (variável do Tkinter).
        self.plc_url = "opc.tcp://localhost:4840"  # URL padrão, será substituída pelo valor do JSON.
        
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
        # Isso é crucial porque o Tkinter não é thread-safe.
        self.after(15, lambda: self._update_checkbox(node_id_str, value))

    def _update_checkbox(self, node_id_str, value):
        # Atualiza o valor do checkbox na interface.
        if node_id_str in self.vars_ui:
            item = self.vars_ui[node_id_str]
            item["var"].set(bool(value))
            color = "#00FF00" if value else "#FF0000" # Verde se True, Vermelho se False
            item["canvas"].itemconfig(item["led"], fill=color)
        else:
            print(f"Aviso: NodeID '{node_id_str}' recebido do callback não encontrado na UI.")

    def iniciar_monitoramento(self):
        # Inicia o processo de monitoramento.
        if self.monitoring:
            return  # Evita iniciar duas vezes.
        self.load_config_and_build_ui()  # Recarrega configurações.
        self.monitoring = True  # Ativa a flag.
        # Cria e inicia a thread dedicada ao loop assíncrono do OPC UA.
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()
        
    def parar_monitoramento(self):
        # Sinaliza para parar o loop de monitoramento.
        self.monitoring = False

    def _run_async_loop(self):
        # Função alvo da thread: inicia o loop de eventos do asyncio.
        asyncio.run(self._monitor_task())

    async def _monitor_task(self):
        # Tarefa assíncrona principal.
        try:
            # Conecta ao servidor OPC UA (context manager fecha conexão automaticamente ao sair).
            async with Client(url=self.plc_url) as client:
                handler = SubHandler(self.update_ui_callback)  # Instancia o manipulador de eventos.
                sub = await client.create_subscription(500, handler)  # Cria assinatura (check a cada 500ms).
                
                nodes_to_subscribe = []
                # Copia das chaves para evitar erro de iteração se modificarmos o dict
                keys = list(self.vars_ui.keys())

                # Itera sobre as variáveis configuradas na UI para encontrar seus nós no servidor.
                for node_id_str in keys:
                    try:
                        node = client.get_node(node_id_str)
                        # Garante que a chave usada no callback (str(node.nodeid)) aponte para a variável correta
                        canonical_id = str(node.nodeid)
                        if canonical_id not in self.vars_ui:
                             self.vars_ui[canonical_id] = self.vars_ui[node_id_str]
                        
                        nodes_to_subscribe.append(node)
                    except Exception:
                        pass  # Ignora nós que não existem no servidor.
                
                if nodes_to_subscribe:
                    # Inscreve os nós encontrados para receber notificações de mudança.
                    await sub.subscribe_data_change(nodes_to_subscribe)
                
                # Mantém o loop rodando enquanto a flag monitoring for True.
                while self.monitoring:
                    await asyncio.sleep(1)  # Pausa não bloqueante de 1 segundo.
        except Exception as e:
            print(f"Erro Monitoramento: {e}")
            self.monitoring = False  # Garante que a flag seja desligada em caso de erro.