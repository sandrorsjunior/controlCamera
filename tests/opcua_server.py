import asyncio
import logging
from asyncua import Server, ua

# --- CLASSE PARA MONITORAR ALTERAÇÕES ---
class SubHandler:
    """
    Esta classe recebe notificações quando variáveis assinadas mudam de valor.
    Armazenamos o último valor em um dicionário para poder mostrar o 'Antigo'.
    """
    def __init__(self):
        self._last_values = {}

    def datachange_notification(self, node, val, data):
        node_id_str = str(node.nodeid)
        
        # Recupera o valor antigo, se já tivermos visto essa variável antes
        old_val = self._last_values.get(node_id_str, "N/A (Inicial)")
        
        print(f"\n[MONITOR] Alteração detectada no Node: {node_id_str}")
        print(f"   Valor Antigo: {old_val}")
        print(f"   Novo Valor:   {val}")
        
        # Atualiza o histórico com o novo valor
        self._last_values[node_id_str] = val

async def main():
    # Configuração básica do servidor
    server = Server()
    await server.init()
    
    # Define o endpoint. 0.0.0.0 permite conexões de qualquer IP na rede local
    server.set_endpoint("opc.tcp://0.0.0.0:4840")
    
    # Nome do servidor exibido para clientes
    server.set_server_name("Meu Servidor OPCUA Python")

    # --- CONFIGURAÇÃO DO NAMESPACE ---
    # Seu cliente espera ns=4.
    # Por padrão: ns=0 é OPC UA Foundation, ns=1 é o próprio Servidor.
    # Vamos registrar namespaces até o índice ser 4.
    
    uri_dummy_2 = "http://dummy.namespace/2"
    uri_dummy_3 = "http://dummy.namespace/3"
    uri_custom = "http://meu.servidor.custom/4" # Este será o ns=4

    await server.register_namespace(uri_dummy_2) # ns=2
    await server.register_namespace(uri_dummy_3) # ns=3
    idx = await server.register_namespace(uri_custom) # ns=4

    print(f"Namespace alvo registrado com índice: {idx}")

    # --- CRIAÇÃO DA VARIÁVEL ---
    # Pegamos o nó de Objetos (pasta raiz para dados)
    objects = server.nodes.objects

    # Criamos um objeto organizador (opcional, mas boa prática)
    my_obj = await objects.add_object(idx, "Controlador")

    # Criamos a variável EXATAMENTE como seu cliente procura:
    # NodeID: ns=4;s=SinalPython
    # Valor inicial: True (para você ver a mudança para False)
    # Tipo: Boolean
    var_node_id = f"ns={idx};s=SinalPython"
    SinalPython = await my_obj.add_variable(var_node_id, "SinalPython", True)
    
    var_node_id_cam = f"ns={idx};s=CamaraS"
    CamaraS = await my_obj.add_variable(var_node_id_cam, "CamaraS", True)
    
    # Define explicitamente como Boolean (embora o Python infira pelo True)
    await SinalPython.set_value(True, varianttype=ua.VariantType.Boolean)
    await CamaraS.set_value(True, varianttype=ua.VariantType.Boolean)

    # --- PERMISSÕES ---
    # Torna a variável gravável (writable) pelo cliente
    await SinalPython.set_writable()
    await CamaraS.set_writable()

    # --- CONFIGURAÇÃO DO MONITORAMENTO (SUBSCRIPTION) ---
    # Criamos o handler e a assinatura
    handler = SubHandler()
    sub = await server.create_subscription(500, handler) # Checa a cada 500ms
    
    # Inscrevemos a variável no monitoramento
    await sub.subscribe_data_change(SinalPython)
    await sub.subscribe_data_change(CamaraS)

    print("Servidor rodando!")
    print(f"Endpoint: opc.tcp://0.0.0.0:4840")
    print(f"Variável monitorada: {var_node_id}")
    print("Pressione Ctrl+C para parar.")

    # Loop principal
    async with server:
        while True:
            # Mantém o servidor vivo
            await asyncio.sleep(1)

if __name__ == "__main__":
    # Configuração de log para ver detalhes de conexão (opcional)
    logging.basicConfig(level=logging.WARNING)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor parado pelo usuário.")