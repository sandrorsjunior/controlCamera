import asyncio
from asyncua import Client, ua
from datetime import datetime, timedelta

URL = "opc.tcp://localhost:4840"
VARIAVEL_NOME = "CamaraS"

async def main():
    print(f"Conectando ao servidor OPC UA em {URL}...")
    
    # Abre a conexão UMA vez aqui e mantém aberta no bloco with
    async with Client(url=URL) as client:
        print("Conectado!")
        
        # 1. Encontrar a variável (Namespace 4 = Globais)
        node_id = f"ns=4;s={VARIAVEL_NOME}"
        var_node = client.get_node(node_id)
        
        status_variable = True
        
        print("Iniciando loop de interação (Ctrl+C para parar)...")
        while True:
            # 3. Escrever
            print(f"Escrevendo: {status_variable}...")
            
            dv = ua.DataValue(ua.Variant(status_variable, ua.VariantType.Boolean))
            
            # Usamos write_attribute em vez de write_value para ser mais direto
            await var_node.write_attribute(ua.AttributeIds.Value, dv)
            
            # 4. Ler valor depois para confirmar
            valor_pos_escrita = await var_node.read_value()
            print(f"Valor após escrita: {valor_pos_escrita}")
            
            status_variable = not status_variable
            await asyncio.sleep(2) # Aguarda 2 segundos com a conexão aberta

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Encerrado pelo usuário ---")
    except Exception as e:
        print("\n--- ERRO ---")
        print(e)