import math
import cv2 as cv
import numpy as np
import os


class ProcessImage:

    def __init__(self, image=None, file_name=None):
        self.file_name = file_name
        self.img_original = image if image is not None else self.get_image(file_name)
        self.count_objects = 0
        self.count_circles = 0
        self.objects = {}
        
        # Inicializa o dicionário de estatísticas zerado
        self.stats = {
            'total_objects': 0,
            'circular_objects': 0,
            'non_circular_objects': 0,
            'objects_with_holes': 0,
            'red_objects': 0,
            'blue_objects': 0,
            'white_objects': 0,
            'undefined_objects': 0
        }
    
    def get_image(self, name):
        # Tenta carregar a imagem do caminho padrão
        try:
            return cv.imread(f"resources/{name}.jpg")
        except Exception as e:
            print(f"ERRO: Imagem 'resources/{name}.jpg' não encontrada.")
            return None
    
    def show_info(self):
        # Exibe informações básicas e o relatório se houver objetos detectados
        if self.img_original is None:
            print("Nenhuma imagem carregada.")
            return
            
        h, w = self.img_original.shape[:2]
        print(f"Imagem carregada com sucesso: Largura={w}, Altura={h}")

        if self.count_objects == 0:
            print("Nenhum objeto detectado ainda.")
        else:
            print(f"\n{'='*60}")
            print(f"RELATÓRIO DE ANÁLISE DE OBJETOS")
            print(f"{'='*60}")
            print(f"\n📊 ESTATÍSTICAS GERAIS:")
            print(f"  • Total de objetos: {self.stats['total_objects']}")
            print(f"  • Objetos circulares: {self.stats['circular_objects']}")
            print(f"  • Objetos não circulares: {self.stats['non_circular_objects']}")
            print(f"  • Objetos com furos: {self.stats['objects_with_holes']}")
            
            print(f"\n🎨 CLASSIFICAÇÃO POR COR:")
            print(f"  • Vermelhos: {self.stats['red_objects']}")
            print(f"  • Azuis: {self.stats['blue_objects']}")
            print(f"  • Brancos: {self.stats['white_objects']}")
            print(f"  • Indefinidos: {self.stats['undefined_objects']}")
            
            print(f"\n📋 DETALHES DOS OBJETOS:")
            print(f"{'-'*70}")
            for obj_id, info in self.objects.items():
                if isinstance(info, dict):
                    print(f"\n  ID: {obj_id}")
                    print(f"    Cor: {info['color']}")
                    print(f"    Área: {info['area']:.2f} px²")
                    print(f"    Perímetro: {info['perimeter']:.2f} px")
                    print(f"    Centro: {info['center']}")
                    print(f"    Circular: {'Sim' if info['is_circular'] else 'Não'}")
                    print(f"    Possui furo: {'Sim' if info['has_hole'] else 'Não'}")
                    if info['has_hole']:
                        print(f"    Quantidade de furos: {info['hole_count']}")
            print(f"\n{'='*70}\n")
    
    def convert_to_hsv(self):
        # Converte a imagem original (BGR) para o espaço de cor HSV
        return cv.cvtColor(self.img_original, cv.COLOR_BGR2HSV)

    @staticmethod
    def get_central_point(objecto):
        """Calcula o centroide de um contorno."""
        M = cv.moments(objecto)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return cx, cy
        return None, None
    
    def create_mask_by_HSV(self, lower_bound, upper_bound):
        # Cria uma máscara binária filtrando pelos intervalos de cor HSV
        img_hsv = self.convert_to_hsv()
        mask = cv.inRange(img_hsv, lower_bound, upper_bound)
        return mask
    
    def remove_noise(self, mask, erode_kernel_size=(6,6), dilate_kernel_size=(3,3)):
        # Cria kernels para as operações morfológicas
        kernel_dilate = np.ones(dilate_kernel_size, np.uint8)
        kernel_erode = np.ones(erode_kernel_size, np.uint8)
        
        # Aplica erosão para remover pequenos ruídos brancos
        mask = cv.erode(mask, kernel_erode)
        # Aplica dilatação para restaurar o tamanho dos objetos restantes
        mask = cv.dilate(mask, kernel_dilate)
        return mask

    def get_contours(self, mask, th1=70, th2=150):
        # Detecta bordas com Canny e encontra contornos externos
        edges = cv.Canny(mask, th1, th2)
        objetos, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        return objetos
    
    def get_contours_hierarchy(self, mask):
        # Encontra contornos e a hierarquia (necessário para detectar furos/filhos)
        contours, hierarchy = cv.findContours(mask, cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE)
        return contours, hierarchy
    
    def get_color_of_point(self, img, point):
        """
        Classifica a cor de um pixel em: red, blue, white ou undefined
        """
        x, y = point
        pixel = img[y, x]
        
        # Extrai componentes BGR
        b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
        color_data = [(b, g, r)]
        
        max_rgb = max(b, g, r)
        
        # Lógica de classificação baseada em limiares RGB empíricos
        if max_rgb < 30:
            # Cor muito escura
            color_data.append('undefined')
        elif r > 120 and (r - b) > 80:
            # Predominância clara de vermelho
            color_data.append('red')
        elif b > 150 and (b - r) > 50:
            # Predominância clara de azul
            color_data.append('blue')
        elif max_rgb > 120:
            # Claro o suficiente para ser branco (se não for nem vermelho nem azul)
            color_data.append('white')
        else:
            color_data.append('undefined')
            
        return color_data
    
    def draw_bounding_rect(self, img, contour):
        x, y, w, h = cv.boundingRect(contour)
        cv.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    def get_circles(self, mask, min_dist=40, param1=50, param2=25, min_radius=10, max_radius=100):
        # Aplica desfoque para reduzir ruído antes da Transformada de Hough
        blurred = cv.GaussianBlur(mask, (9, 9), 2)
        
        circles = cv.HoughCircles(
            blurred, 
            cv.HOUGH_GRADIENT, 
            dp=1, 
            minDist=min_dist,
            param1=param1,
            param2=param2,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        if circles is not None:
            return np.uint16(np.around(circles))[0]
        return []

    def detect_circles(self, mask, image_overlay, draw=False, **kwargs):
        # Detecta círculos e desenha na imagem de sobreposição
        circles = self.get_circles(mask, **kwargs)
        for circle in circles:
            x, y, r = int(circle[0]), int(circle[1]), int(circle[2])
            area = math.pi * (r ** 2)
            if area > 50:
                self.count_circles += 1
                if draw:
                    cv.circle(image_overlay, (x, y), r, (0, 255, 0), 2)
        
        self.objects["total_circle"] = self.count_circles
        return image_overlay

    def draw_central_point(self, img, point):
        cv.circle(img, point, 5, (0, 0, 255), -1)

    def draw_color_text(self, img, text, contour, ajust=0):
        x, y, w, h = cv.boundingRect(contour)
        font = cv.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 2
        (text_w, text_h), _ = cv.getTextSize(text, font, scale, thickness)
        cv.putText(img, text, (ajust + x + (w - text_w) // 2, ajust + y + (h + text_h) // 2), 
                   font, scale, (255, 255, 255), thickness)

    def is_circular(self, contour, threshold=0.75):
        """
        Determina se um contorno é circular usando o índice de circularidade.
        Circularidade = 4π * área / perímetro²
        
        Um círculo perfeito tem circularidade = 1.0
        threshold: valor mínimo para considerar circular (padrão 0.75)
        """
        perimeter = cv.arcLength(contour, True)
        if perimeter == 0:
            return False
        
        area = cv.contourArea(contour)
        if area == 0:
            return False
            
        circularity = 4 * math.pi * (area / (perimeter * perimeter))
        return circularity >= threshold

    def objects_detection(self, 
                          objetos, 
                          tolerance=170, 
                          show_contours=False, 
                          central_point=False, 
                          show_color=False, 
                          show_id=False, 
                          hierarchy=None, 
                          show_holes=False):
        """
        Detecta objetos na imagem e coleta todas as informações solicitadas.
        """
        # Cria uma cópia da imagem para desenhar os resultados sem alterar a original
        image_overlay = self.img_original.copy()
        
        # Reseta as estatísticas para esta nova detecção
        self.stats = {
            'total_objects': 0,
            'circular_objects': 0,
            'non_circular_objects': 0,
            'objects_with_holes': 0,
            'red_objects': 0,
            'blue_objects': 0,
            'white_objects': 0,
            'undefined_objects': 0
        }
        
        # Obtém a hierarquia (se disponível) para verificar pais/filhos
        hier = hierarchy[0] if hierarchy is not None else None

        for i, objeto in enumerate(objetos):
            # Se houver hierarquia, verifica se o contorno é um "filho" (furo)
            # hier[i][3] é o índice do pai. Se != -1, significa que está dentro de outro contorno.
            if hier is not None:
                parent_idx = hier[i][3]
                if parent_idx != -1:
                    continue # Ignora contornos internos na contagem principal

            # Filtra objetos muito pequenos (ruído)
            object_area = cv.contourArea(objeto)
            if object_area >= tolerance:
                self.count_objects += 1
                self.stats['total_objects'] += 1
                
                # Calcula o centroide
                cx, cy = self.get_central_point(objeto)
                
                perimeter = cv.arcLength(objeto, True)
                
                # Verifica circularidade
                is_circular = self.is_circular(objeto)
                if is_circular:
                    self.stats['circular_objects'] += 1
                else:
                    self.stats['non_circular_objects'] += 1
                
                # Identifica a cor no ponto central
                color = self.get_color_of_point(image_overlay, (cx, cy))
                color_name = color[1]
                
                # Atualiza estatísticas de cor
                if color_name == 'red':
                    self.stats['red_objects'] += 1
                elif color_name == 'blue':
                    self.stats['blue_objects'] += 1
                elif color_name == 'white':
                    self.stats['white_objects'] += 1
                else:
                    self.stats['undefined_objects'] += 1
                
                # Desenha o retângulo delimitador
                self.draw_bounding_rect(image_overlay, objeto)
                
                # Desenha informações adicionais conforme solicitado
                if show_contours:
                    cv.drawContours(image_overlay, [objeto], -1, (0, 255, 0), 2)
                if central_point:
                    self.draw_central_point(image_overlay, (cx, cy))
                if show_color:
                    self.draw_color_text(image_overlay, color_name, objeto)
                if show_id:
                    self.draw_color_text(image_overlay, str(self.count_objects), objeto, ajust=-15)

                # Verificação de furos (filhos na hierarquia)
                has_hole = False
                hole_count = 0
                if hier is not None:
                    # hier[i][2] é o índice do primeiro filho
                    child_idx = hier[i][2]
                    while child_idx != -1:
                        hole_count += 1
                        has_hole = True
                        child_idx = hier[child_idx][0] # Próximo irmão do filho

                    # Atualiza estatísticas de furos
                    if has_hole:
                        self.stats['objects_with_holes'] += 1
                        if show_holes:
                            hole_text = f"Furos: {hole_count}"
                            cv.putText(image_overlay, hole_text, (cx - 30, cy + 20), 
                                     cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                # Armazena os dados do objeto detectado
                self.objects[self.count_objects] = {
                    "area": object_area,
                    "perimeter": perimeter,
                    "center": (cx, cy),
                    "color": color_name,
                    "central_color": color[0],
                    "is_circular": is_circular,
                    "has_hole": has_hole,
                    "hole_count": hole_count
                }
                
        return image_overlay

    def get_statistics(self):
        """Retorna um dicionário com todas as estatísticas."""
        return self.stats.copy()

    def save_image(self, folder="resources/output"):
        name = f"{self.file_name}.jpg"
        output_path = os.path.join(folder, name)
        if not os.path.exists(folder):
            os.makedirs(folder)
        cv.imwrite(output_path, self.img_original) 
    
    def show_image(self, window_name="Image"):
        cv.imshow(window_name, self.img_original)
        cv.waitKey(0)
        cv.destroyAllWindows()