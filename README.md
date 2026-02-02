# Documentação do Sistema de Monitoramento de Vídeo e Controle PLC

Este projeto é uma aplicação desktop desenvolvida em Python utilizando **Tkinter** para a interface gráfica, **OpenCV** para processamento de imagem e **opcua-asyncio** para comunicação industrial (PLC).

O sistema captura vídeo em tempo real, processa imagens para detectar objetos/cores e comunica-se com um servidor OPC UA para leitura e escrita de variáveis de controle.

---

## 🏗️ Arquitetura e Classes Principais

O projeto segue uma estrutura modular onde a lógica de negócio (Controllers), a interface (Screens/Views) e a comunicação externa (SharedPLC) estão separadas.

### 1. `AplicacaoApp` (src/app.py)
**Tipo:** Classe Principal (Herda de `tk.Tk`)
**Função:** Gerencia o ciclo de vida da aplicação, a janela principal e a navegação entre telas.

*   **Variáveis Principais:**
    *   `self.frames`: Dicionário contendo as instâncias das telas (`PaginaVideo`, `PaginaFile`, etc.).
    *   `self.shared_plc`: Instância única (Singleton) da classe `SharedPLC`.
    *   `self.cap`: Objeto `cv2.VideoCapture` compartilhado.
*   **Métodos Chave:**
    *   `mostrar_frame(page_name)`: Alterna a tela visível e gerencia o início/parada de loops de vídeo ou monitoramento.
    *   `fechar_app()`: Garante que a câmera e a thread do PLC sejam encerradas corretamente.

### 2. `VideoController` (src/controller/VideoController.py)
**Tipo:** Controlador Lógico
**Função:** Gerencia a captura de vídeo, processamento de imagem e lógica de disparo de sinais para o PLC.

*   **Interações:**
    *   Recebe a imagem bruta do OpenCV.
    *   Usa `ProcessImage` para detectar círculos/cores.
    *   Chama `self.view.controller.shared_plc.write()` para enviar sinais ao PLC.
*   **Métodos Chave:**
    *   `loop()`: Executado repetidamente via `after()` (não bloqueante). Captura frame, processa e atualiza a UI.
    *   `trigger_plc_signals()`: Envia comando de escrita para o PLC quando uma condição visual é atendida.

### 3. `SharedPLC` (src/controller/SharedPLC.py)
**Tipo:** Serviço de Comunicação (Singleton/Thread Manager)
**Função:** Mantém a conexão OPC UA persistente em uma thread separada para não travar a interface gráfica.

*   **Variáveis Principais:**
    *   `self._thread`: A thread dedicada ao loop `asyncio`.
    *   `self._loop`: O loop de eventos assíncrono onde roda a biblioteca `asyncua`.
    *   `self._subscriptions`: Lista de variáveis monitoradas.
*   **Métodos Chave:**
    *   `start(url)`: Inicia a thread de comunicação.
    *   `subscribe(ns, name, callback)`: Registra uma função para ser chamada quando uma variável mudar no servidor.
    *   `write(ns, name, value)`: Envia um comando de escrita para a fila da thread do PLC.

### 4. `StatusWindow` (src/screens/status/StatusWindow.py)
**Tipo:** Interface de Usuário (View)
**Função:** Monitora e exibe o estado das variáveis do PLC em tempo real.

*   **Interações:**
    *   Inscreve-se no `SharedPLC` passando `self.update_ui_callback`.
*   **Métodos Chave:**
    *   `update_ui_callback(node, val)`: Recebe dados da thread do PLC e agenda a atualização visual.
    *   `_update_checkbox()`: Atualiza a cor do LED/Checkbox na thread principal.

### 5. `PaginaFile` (src/screens/configurations/PaginaFile.py)
**Tipo:** Interface de Configuração
**Função:** Permite configurar o IP do servidor e adicionar variáveis ao sistema. Salva em `plc_config.json`.

---

## 🧵 Gerenciamento de Threads e Concorrência

Este é o ponto mais crítico da aplicação. O Python (devido ao GIL) e o Tkinter (que não é thread-safe) exigem uma estratégia cuidadosa para misturar I/O de rede (PLC) com atualização de GUI e processamento de vídeo.

O sistema utiliza **duas linhas de execução principais**:

### 1. Main Thread (Thread Principal / GUI)
*   **Quem roda aqui:** O Tkinter (`mainloop`), o loop de captura de vídeo (`VideoController.loop`) e todas as atualizações de tela.
*   **Comportamento:**
    *   O vídeo **não** roda em uma thread separada. Ele usa o método `widget.after(15, self.loop)`. Isso agenda a próxima execução do loop para daqui a 15ms na fila de eventos do Tkinter. Isso cria um efeito de vídeo fluido sem bloquear a interface, desde que o processamento de cada frame seja rápido.

### 2. PLC Thread (Background Thread)
*   **Quem roda aqui:** A classe `SharedPLC` cria uma `threading.Thread` (daemon) que executa um loop `asyncio`.
*   **Por que:** A comunicação OPC UA (rede) pode ser lenta ou bloquear. Se rodasse na Main Thread, a interface congelaria a cada leitura/escrita.

---

## 🔄 Interação entre Threads

Como a **Main Thread** e a **PLC Thread** conversam sem causar erros de "Race Condition" ou travamentos?

### Cenário A: A Interface manda dados para o PLC (Escrita)
Quando você clica em um botão ou o vídeo detecta um objeto:

1.  **Origem (Main Thread):** O código chama `shared_plc.write(ns, name, value)`.
2.  **A Ponte:** O método `write` usa `asyncio.run_coroutine_threadsafe(coroutine, loop)`.
3.  **Destino (PLC Thread):** Essa função insere a tarefa de escrita no loop de eventos da thread do PLC de forma segura. O PLC processa e envia para a rede.

```python
# Exemplo simplificado do fluxo
def write(self, ...):
    # Executado na Main Thread, mas agenda trabalho na PLC Thread
    asyncio.run_coroutine_threadsafe(self._write_value(...), self._loop)
```

### Cenário B: O PLC manda dados para a Interface (Leitura/Monitoramento)
Quando uma variável muda no servidor OPC UA:

1.  **Origem (PLC Thread):** A biblioteca `asyncua` detecta a mudança e chama o método `datachange_notification` dentro da thread do PLC.
2.  **O Problema:** A thread do PLC **não pode** tocar na interface gráfica (ex: mudar a cor de um label) diretamente, ou o Tkinter irá falhar/crashar.
3.  **A Ponte:** O callback registrado na `StatusWindow` (`update_ui_callback`) usa o método `self.after(delay, function)`.
4.  **Destino (Main Thread):** O `after` coloca a função de atualização na fila da Main Thread. Assim que o Tkinter estiver livre, ele executa a atualização visual.

```python
# Exemplo no StatusWindow.py
def update_ui_callback(self, node_id, value):
    # Estamos na PLC Thread aqui.
    # Agendamos a atualização visual para rodar na Main Thread.
    self.after(15, lambda: self._update_checkbox(node_id, value))
```

---

## 📊 Diagrama de Fluxo de Dados

1.  **Vídeo:** Câmera -> `VideoController` (Main Thread) -> Processamento -> `SharedPLC.write()` -> **PLC Thread**.
2.  **Monitor:** Servidor OPC UA -> **PLC Thread** -> Callback -> `StatusWindow.after()` -> **Main Thread** (Atualiza LED).

## 🛠️ Configuração (plc_config.json)

O sistema carrega as variáveis de um arquivo JSON. Exemplo:

```json
{
    "url": "opc.tcp://localhost:4840",
    "variables": [
        ["4", "SinalPython"],
        ["4", "CamaraS"]
    ]
}
```

*   **url**: Endereço do servidor OPC UA.
*   **variables**: Lista onde cada item é `[Namespace Index, Identifier String]`.