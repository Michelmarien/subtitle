from moviepy import TextClip, ColorClip, CompositeVideoClip
import numpy as np
from .base_theme import BaseTheme, ThemeConfig
import logging

logger = logging.getLogger(__name__)


class CinematicTheme(BaseTheme):
    """
    Thème cinématique style sous-titres film
    
    Caractéristiques :
    - Bandes noires haute/basse (letterbox)
    - Texte centré bas avec ombre portée
    - Emphase par MAJUSCULES
    - Style Netflix/Prime Video
    """
    
    def __init__(self, config: ThemeConfig = None):
        super().__init__(config)
        self.letterbox_height = 150  # Hauteur des bandes noires
        logger.info("🎨 Thème Cinématique activé")
    
    def create_text_clip(
        self,
        text: str,
        start: float,
        duration: float,
        emphasis_level: int = 0,
        **kwargs
    ) -> TextClip:
        """Crée un clip style sous-titre film"""
        
        # Emphase = MAJUSCULES
        if emphasis_level >= 2:
            text = text.upper()
        
        font_size = self._get_font_size(emphasis_level)
        
        try:
            # Clip principal
            clip = TextClip(
                text=text,
                font=self.config.font_family,
                font_size=font_size,
                color='white',
                size=(self.config.video_width - 200, None),
                method='caption',
                align='center',
                stroke_color='black',
                stroke_width=3,  # Contour fort pour lisibilité
            )
            
            # Position : bas de l'écran, au-dessus de la bande noire
            y_position = self.config.video_height - self.letterbox_height - 80
            clip = clip.with_position(('center', y_position))
            
            # Timing
            clip = clip.with_start(start).with_duration(duration)
            
            # Fade très rapide (style sous-titres)
            clip = clip.crossfadein(0.1).crossfadeout(0.1)
            
            logger.debug(f"✅ Clip ciné: '{text[:25]}...'")
            
            return clip
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return None
    
    def get_background_clip(self, duration: float):
        """
        Fond avec bandes noires cinématiques (letterbox 2.39:1)
        """
        # Fond noir complet
        bg = ColorClip(
            size=(self.config.video_width, self.config.video_height),
            color=(0, 0, 0),
            duration=duration
        )
        
        # Bandes letterbox (optionnel, pour renforcer l'effet)
        top_bar = ColorClip(
            size=(self.config.video_width, self.letterbox_height),
            color=(0, 0, 0),
            duration=duration
        ).with_position(('center', 0))
        
        bottom_bar = ColorClip(
            size=(self.config.video_width, self.letterbox_height),
            color=(0, 0, 0),
            duration=duration
        ).with_position(('center', self.config.video_height - self.letterbox_height))
        
        # Composition
        return CompositeVideoClip([bg, top_bar, bottom_bar])
