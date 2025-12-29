from moviepy import TextClip, ColorClip, CompositeVideoClip
from .base_theme import BaseTheme, ThemeConfig
import logging

logger = logging.getLogger(__name__)


class MinimalistTheme(BaseTheme):
    """
    Thème minimaliste épuré
    
    Caractéristiques :
    - Fond noir pur
    - Texte blanc sans fioritures
    - Emphase par taille uniquement
    - Transitions douces
    """
    
    def __init__(self, config: ThemeConfig = None):
        super().__init__(config)
        logger.info("🎨 Thème Minimaliste activé")
    
    def create_text_clip(
        self,
        text: str,
        start: float,
        duration: float,
        emphasis_level: int = 0,
        **kwargs
    ) -> TextClip:
        """Crée un clip texte minimaliste"""
        
        font_size = self._get_font_size(emphasis_level)
        color = self._get_text_color(emphasis_level)
        position = self._get_position(emphasis_level)
        
        try:
            # Création du clip de base
            clip = TextClip(
                text=text,
                font=self.config.font_family,
                font_size=font_size,
                color=color,
                size=(self.config.video_width - 100, None),  # Marges latérales
                method='caption',
                align='center',
            )
            
            # Positionnement
            clip = clip.with_position(position)
            
            # Timing
            clip = clip.with_start(start).with_duration(duration)
            
            # Transitions douces
            if self.config.fade_in_duration > 0:
                clip = clip.crossfadein(self.config.fade_in_duration)
            
            if self.config.fade_out_duration > 0:
                clip = clip.crossfadeout(self.config.fade_out_duration)
            
            logger.debug(f"✅ Clip créé: '{text[:20]}...' @ {start:.2f}s ({emphasis_level})")
            
            return clip
            
        except Exception as e:
            logger.error(f"❌ Erreur création clip: {e}")
            return None
    
    def get_background_clip(self, duration: float):
        """Retourne un fond noir pur"""
        return ColorClip(
            size=(self.config.video_width, self.config.video_height),
            color=self.config.background_color,
            duration=duration
        )
