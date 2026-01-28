import math
import cv2 as cv
import numpy as np
import os

class ProcessImage:

    def __init__(self, file_name=None, image=None):
        """
        Adaptado para aceitar um nome de ficheiro OU uma imagem direta (da webcam).
        """
        self.file_name = file_name
        self.objects = {}
        
        if image is not None:
            self.img_original = image
        else:
            self.img_original = self.get_image(file_name)

        self.count_objects = 0
        self.count_circles = 0
        
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
        try:
            # Se o utilizador não passar nome, evita erro
            if not name: return None
            return cv.imread(f"resources/{name}.jpg")
        except Exception as e:
            print(f"ERRO: Imagem 'resources/{name}.jpg' não encontrada.")
            return None

    # ... (MÉTODOS ORIGINAIS MANTIDOS ABAIXO) ...

    def convert_to_hsv(self):
        return cv.cvtColor(self.img_original, cv.COLOR_BGR2HSV)

    @staticmethod
    def get_central_point(objecto):
        M = cv.moments(objecto)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return cx, cy
        return None, None
    
    def get_color_of_point(self, img, point):
        # Proteção para garantir que o ponto está dentro da imagem
        h, w = img.shape[:2]
        x, y = point
        if x >= w or y >= h or x < 0 or y < 0:
            return [(0,0,0), 'undefined']

        pixel = img[y, x]
        b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
        color_data = [(b, g, r)]
        max_rgb = max(b, g, r)
        
        if max_rgb < 30:
            color_data.append('undefined')
        elif r > 120 and (r - b) > 80:
            color_data.append('red')
        elif b > 150 and (b - r) > 50:
            color_data.append('blue')
        elif max_rgb > 120:
            color_data.append('white')
        else:
            color_data.append('undefined')
        return color_data
    
    def draw_bounding_rect(self, img, contour):
        x, y, w, h = cv.boundingRect(contour)
        cv.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    def is_circular(self, contour, threshold=0.75):
        perimeter = cv.arcLength(contour, True)
        if perimeter == 0: return False
        area = cv.contourArea(contour)
        if area == 0: return False
        circularity = 4 * math.pi * (area / (perimeter * perimeter))
        return circularity >= threshold

    def objects_detection(self, objetos, tolerance=170, show_contours=False, 
                          central_point=False, show_color=False, show_id=False, 
                          hierarchy=None, show_holes=False):
        
        image_overlay = self.img_original.copy()
        
        # Reset stats
        self.stats = {k: 0 for k in self.stats}
        self.count_objects = 0

        # Hierarquia: [Next, Previous, First_Child, Parent]
        hier = hierarchy[0] if hierarchy is not None else None

        for i, objeto in enumerate(objetos):
            # Se tem pai (hier[i][3] != -1), é um buraco interno, ignorar no loop principal
            if hier is not None:
                parent_idx = hier[i][3]
                if parent_idx != -1:
                    continue

            object_area = cv.contourArea(objeto)
            if object_area >= tolerance:
                self.count_objects += 1
                self.stats['total_objects'] += 1
                
                cx, cy = self.get_central_point(objeto)
                if cx is None: continue # Proteção

                perimeter = cv.arcLength(objeto, True)
                is_circular = self.is_circular(objeto)
                
                if is_circular: self.stats['circular_objects'] += 1
                else: self.stats['non_circular_objects'] += 1
                
                color = self.get_color_of_point(image_overlay, (cx, cy))
                color_name = color[1]
                
                if color_name == 'red': self.stats['red_objects'] += 1
                elif color_name == 'blue': self.stats['blue_objects'] += 1
                elif color_name == 'white': self.stats['white_objects'] += 1
                else: self.stats['undefined_objects'] += 1
                
                # Desenhar
                self.draw_bounding_rect(image_overlay, objeto)
                if show_contours:
                    cv.drawContours(image_overlay, [objeto], -1, (0, 255, 0), 2)
                if central_point:
                    cv.circle(image_overlay, (cx, cy), 5, (0, 0, 255), -1)
                if show_color:
                    # Ajuste simples de texto
                    cv.putText(image_overlay, color_name, (cx - 20, cy - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
                if show_id:
                     cv.putText(image_overlay, str(self.count_objects), (cx, cy), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 2)

                # Verificar furos (filhos)
                has_hole = False
                hole_count = 0
                if hier is not None:
                    child_idx = hier[i][2] # Primeiro filho
                    while child_idx != -1:
                        hole_count += 1
                        has_hole = True
                        child_idx = hier[child_idx][0] # Próximo irmão do filho

                    if has_hole:
                        self.stats['objects_with_holes'] += 1
                        if show_holes:
                             cv.putText(image_overlay, f"Holes:{hole_count}", (cx - 20, cy + 30), 
                                     cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        return image_overlay

    def get_statistics(self):
        return self.stats.copy()