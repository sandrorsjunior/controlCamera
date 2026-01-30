import asyncio
from asyncua import Client, ua

URL = "opc.tcp://192.168.250.1:4840"
VARIAVEL_NOME = "CamaraS"

async def main():
    print(f"Conectando ao servidor OPC UA em {URL}...")
    
    async with Client(url=URL) as client:
        print("Conectado!")
        
        # 1. Encontrar a variável (Namespace 4 = Globais)
        node_id = f"ns=4;s={VARIAVEL_NOME}"
        var_node = client.get_node(node_id)
        
        # 2. Ler valor antes
        valor_atual = await var_node.read_value()
        print(f"Valor atual de '{VARIAVEL_NOME}': {valor_atual}")
        
        # 3. Escrever (O PULO DO GATO)
        # Forçamos o tipo Boolean explicitamente
        print("Tentando escrever True...")
        
        dv = ua.DataValue(ua.Variant(True, ua.VariantType.Boolean))
        
        # Usamos write_attribute em vez de write_value para ser mais direto
        await var_node.write_attribute(ua.AttributeIds.Value, dv)
        
        # 4. Ler valor depois para confirmar
        valor_pos_escrita = await var_node.read_value()
        print(f"Valor após escrita: {valor_pos_escrita}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("\n--- ERRO ---")
        print(e)