import asyncio
import threading
from asyncua import Client, ua
from src.model.OpcuaDTO import OpcuaDTO

class SubHandler:
    """
    Handler para receber eventos de mudança de dados do OPC UA.
    """
    def __init__(self, subscriptions):
        self.subscriptions = subscriptions

    def datachange_notification(self, node, val, data):
        try:
            # Obtém os componentes do NodeId diretamente para comparação segura
            ns_idx = node.nodeid.NamespaceIndex
            ident = node.nodeid.Identifier
            
            # Atualiza o DTO (Fonte única de verdade)
            target_id = f"ns={ns_idx};s={ident}"
            OpcuaDTO().set_variable(target_id, val)
            
            # Debug: Mostra o que chegou do PLC
            # print(f"[SharedPLC] Notificação: ns={ns_idx}, id={ident}, val={val}")
            
            # Itera sobre as subscrições para encontrar a correspondente
            found = False
            for sub in self.subscriptions:
                # Compara Namespace e Nome (converte para string para garantir igualdade)
                if str(sub['ns']) == str(ns_idx) and str(sub['name']) == str(ident):
                    found = True
                    if sub['callback']:
                        # Reconstrói o NodeID esperado pela UI para garantir que a chave do dicionário bata
                        target_id = f"ns={sub['ns']};s={sub['name']}"
                        sub['callback'](target_id, val)
            
            if not found:
                print(f"[SharedPLC] AVISO: Nenhuma subscrição encontrada para ns={ns_idx}, id={ident}")
        except Exception as e:
            print(f"Erro no callback OPC UA: {e}")

class SharedPLC:
    """
    Classe Singleton-ish para manter a conexão OPC UA viva em background.
    Gerencia um loop asyncio em uma thread separada para não bloquear o Tkinter.
    """
    def __init__(self):
        self.url = "opc.tcp://localhost:4840"
        self.connected = False
        self.running = False
        self.log_callback = print
        self._subscriptions = [] # Lista de dicts: {'ns':..., 'name':..., 'callback':...}
        self._loop = None
        self._thread = None
        self._client = None
        self._sub_obj = None

    def set_log_callback(self, cb):
        self.log_callback = cb

    def start(self, url):
        if self.running: return
        
        # Se existir uma thread antiga (ex: parando), aguarda ela terminar para evitar duplicidade
        if self._thread and self._thread.is_alive():
            self.running = False
            self._thread.join(2.0) # Aguarda até 2s para limpeza
            
        self.url = url
        self.running = True
        # Inicia a thread daemon que rodará o loop asyncio
        self._thread = threading.Thread(target=self._thread_run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.connected = False

    def subscribe(self, ns, name, callback):
        """Registra uma variável para monitoramento."""
        sub = {"ns": str(ns), "name": name, "callback": callback}
        self._subscriptions.append(sub)
        # Se já estiver conectado, adiciona dinamicamente
        if self.connected and self._loop and self._sub_obj:
             asyncio.run_coroutine_threadsafe(self._add_monitored_item(sub), self._loop)

    def write(self, ns, name, value):
        """Envia comando de escrita para a thread do PLC."""
        if self.connected and self._loop:
            asyncio.run_coroutine_threadsafe(self._write_value(ns, name, value), self._loop)

    def _thread_run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main_loop())
        self._loop.close()

    async def _main_loop(self):
        self.log_callback(f"Conectando a {self.url}...")
        while self.running:
            try:
                async with Client(url=self.url) as client:
                    self._client = client
                    self.connected = True
                    self.log_callback("Conectado ao PLC.")
                    
                    # Cria a subscrição
                    handler = SubHandler(self._subscriptions)
                    self._sub_obj = await client.create_subscription(500, handler)
                    
                    # Adiciona itens já registrados
                    for sub in self._subscriptions:
                        await self._add_monitored_item(sub)
                        
                    while self.running and self.connected:
                        await asyncio.sleep(1)
            except Exception as e:
                self.connected = False
                self.log_callback(f"Erro de conexão: {e}")
                await asyncio.sleep(5) # Tenta reconectar em 5s
        self.log_callback("Serviço PLC Parado.")

    async def _add_monitored_item(self, sub):
        try:
            node_id = f"ns={sub['ns']};s={sub['name']}"
            node = self._client.get_node(node_id)
            await node.read_value() # Verifica se existe
            await self._sub_obj.subscribe_data_change(node)
        except Exception as e:
            self.log_callback(f"Falha ao subscrever {sub['name']}: {e}")

    async def _write_value(self, ns, name, value):
        try:
            node_id = f"ns={ns};s={name}"
            node = self._client.get_node(node_id)
            # Força tipo Boolean conforme uso no projeto
            dv = ua.DataValue(ua.Variant(value, ua.VariantType.Boolean))
            await node.write_attribute(ua.AttributeIds.Value, dv)
            self.log_callback(f"Escrito {value} em {name}")
        except Exception as e:
            self.log_callback(f"Falha ao escrever em {name}: {e}")