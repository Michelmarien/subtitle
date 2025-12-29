from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
from moviepy import TextClip
import numpy as np

@dataclass
class ThemeConfig:
    """Configuration d'un thème visuel"""
    # Typographie
    font_family: str = "Arial"
    font_size_normal: int = 80
    font_size_emphasis: int = 110
    
    # Couleurs (RGB)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    emphasis_color: Tuple[int, int, int] = (255, 215, 0)  # Or
    background_color: Tuple[int, int, int] = (0, 0, 0)
    
    # Positionnement
    position: str = 'center'  # 'center', 'bottom', 'top'
    margin_bottom: int = 100
    margin_top: int = 100
    
    # Animations
    fade_in_duration: float = 0.2
    fade_out_duration: float = 0.2
    
    # Effets
    stroke_width: int = 2
    stroke_color: Tuple[int, int, int] = (0, 0, 0)
    shadow: bool = True
    shadow_offset: Tuple[int, int] = (3, 3)
    
    # Dimensions vidéo
    video_width: int = 1080
    video_height: int = 1920


class BaseTheme(ABC):
    """
    Classe abstraite pour tous les thèmes
    
    Un thème définit :
    - Le style visuel du texte
    - Les animations
    - Les effets spéciaux
    """
    
    def __init__(self, config: Optional[ThemeConfig] = None):
        self.config = config or ThemeConfig()
    
    @abstractmethod
    def create_text_clip(
        self,
        text: str,
        start: float,
        duration: float,
        emphasis_level: int = 0,
        **kwargs
    ) -> TextClip:
        """
        Crée un clip de texte stylisé
        
        Args:
            text: Texte à afficher
            start: Temps de début (secondes)
            duration: Durée d'affichage (secondes)
            emphasis_level: 0=normal, 1=moyen, 2=fort
            **kwargs: Paramètres additionnels spécifiques au thème
            
        Returns:
            TextClip configuré
        """
        pass
    
    def _get_font_size(self, emphasis_level: int) -> int:
        """Retourne la taille de police selon l'emphase"""
        if emphasis_level >= 2:
            return self.config.font_size_emphasis
        elif emphasis_level == 1:
            return int(self.config.font_size_normal * 1.15)
        else:
            return self.config.font_size_normal
    
    def _get_text_color(self, emphasis_level: int) -> str:
        """Retourne la couleur selon l'emphase"""
        if emphasis_level >= 2:
            return self._rgb_to_hex(self.config.emphasis_color)
        else:
            return self._rgb_to_hex(self.config.text_color)
    
    def _get_position(self, emphasis_level: int = 0) -> Tuple[str, str]:
        """Calcule la position du texte"""
        if self.config.position == 'center':
            return ('center', 'center')
        elif self.config.position == 'bottom':
            y = self.config.video_height - self.config.margin_bottom
            return ('center', y)
        elif self.config.position == 'top':
            return ('center', self.config.margin_top)
        else:
            return ('center', 'center')
    
    @staticmethod
    def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convertit RGB en hex"""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)
    
    @abstractmethod
    def get_background_clip(self, duration: float):
        """
        Retourne le clip de fond (noir uni, dégradé, etc.)
        
        Args:
            duration: Durée totale de la vidéo
            
        Returns:
            VideoClip de fond
        """
        pass
