import cv2
import numpy as np

def processar_video(fonte):
    # Inicializa a captura
    # Se 'fonte' for um número (ex: 0), usa a Webcam.
    # Se for uma string (ex: "video.mp4"), carrega o arquivo.
    cap = cv2.VideoCapture(fonte)

    if not cap.isOpened():
        print("Erro ao abrir o vídeo ou webcam.")
        return

    print("Pressione 'q' para sair.")   

    while True:
        # 1. Ler o frame atual
        ret, frame = cap.read()
        
        # Se não conseguiu ler (fim do vídeo ou erro), para o loop
        if not ret:
            break

        # --- INÍCIO DO PROCESSAMENTO DA IMAGEM (Idêntico ao anterior) ---
        
        # Converter para cinza e desfocar
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Limiarização (Ajuste o 150 conforme a iluminação do vídeo)
        _, thresh = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY)

        # Encontrar contornos
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contornos:
            area = cv2.contourArea(cnt)
            
            # Filtro de área (ajuste conforme a distância da câmera)
            if area > 2000:
                # Encontra o círculo que envolve o contorno
                (x, y), raio = cv2.minEnclosingCircle(cnt)
                centro = (int(x), int(y))
                raio = int(raio)

                # Verifica circularidade básica (opcional, para evitar quadrados)
                perimetro = cv2.arcLength(cnt, True)
                if perimetro == 0: continue
                circularidade = 4 * np.pi * (area / (perimetro * perimetro))

                # Se for razoavelmente circular (0.7 a 1.2), desenha
                if 0.7 < circularidade < 1.3:
                    cv2.circle(frame, centro, raio, (0, 255, 0), 3)
                    cv2.circle(frame, centro, 5, (0, 0, 255), -1)
                    
                    # Escreve na tela
                    cv2.putText(frame, "Peca", (int(x)-20, int(y)-20), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # --- FIM DO PROCESSAMENTO ---

        # Mostra o resultado na tela
        cv2.imshow("Deteccao em Video", frame)
        cv2.imshow("hsv", hsv)
        
        # Mostra o que o computador "vê" (útil para debugar iluminação)
        # cv2.imshow("Mascara", thresh) 

        # Espera 1ms e verifica se a tecla 'q' foi pressionada para sair
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    # Libera a câmera e fecha janelas
    cap.release()
    cv2.destroyAllWindows()

# --- CONFIGURAÇÃO ---

# Para usar a Webcam, coloque: 0
# Para usar um arquivo, coloque o nome: 'video_teste.mp4'
fonte_input = 0 

processar_video("C:\\Users\\hulk\\source\\repos\\controlCamera\\tests\\resources\\video1.mp4")