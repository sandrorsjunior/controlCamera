from asyncua import Client, ua

class PLCController:
    """
    Classe responsável pela lógica de comunicação OPC UA.
    """
    def __init__(self):
        pass

    async def connect_and_send(self, url, ns, var_name, valor_a_escrever, log_callback):
        """
        Conecta ao servidor PLC, lê o valor atual e escreve o novo valor.
        Usa log_callback(str) para enviar mensagens de volta para a UI.
        """
        log_callback(f"Conectando a {url}...")
        
        try:
            async with Client(url=url) as client:
                log_callback("Conectado com sucesso!")
                
                # Monta o Node ID dinamicamente
                node_id_str = f"ns={ns};s={var_name}"
                log_callback(f"Buscando nó: {node_id_str}")
                
                try:
                    var_node = client.get_node(node_id_str)
                    
                    # Ler valor atual
                    valor_atual = await var_node.read_value()
                    log_callback(f"Valor atual no PLC: {valor_atual}")

                    # Escrever novo valor
                    log_callback(f"Escrevendo: {valor_a_escrever}...")
                    
                    # Cria o objeto DataValue com tipagem explícita
                    dv = ua.DataValue(ua.Variant(valor_a_escrever, ua.VariantType.Boolean))
                    
                    # Escrita via atributo
                    await var_node.write_attribute(ua.AttributeIds.Value, dv)
                    
                    # Confirmação
                    novo_valor = await var_node.read_value()
                    log_callback(f"SUCESSO! Novo valor confirmado: {novo_valor}")

                except ua.UaError as e:
                    log_callback(f"Erro de OPC UA: {e}")
                except Exception as e:
                    log_callback(f"Erro genérico ao manipular nó: {e}")

        except OSError:
            log_callback("Erro de conexão: Não foi possível conectar ao servidor (Timeout ou IP errado).")
        except Exception as e:
            log_callback(f"Erro inesperado: {e}")