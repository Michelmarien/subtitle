from moviepy import TextClip, ColorClip, CompositeVideoClip, vfx
import numpy as np
from .base_theme import BaseTheme, ThemeConfig
import logging

logger = logging.getLogger(__name__)


class DynamicTheme(BaseTheme):
    """
    Thème dynamique avec animations
    
    Caractéristiques :
    - Animations d'apparition (slide, zoom)
    - Emphase par couleur + taille
    - Effets de pulsation sur mots importants
    """
    
    def __init__(self, config: ThemeConfig = None):
        super().__init__(config)
        self.animation_type = 'slide_up'  # 'slide_up', 'zoom', 'fade'
        logger.info("🎨 Thème Dynamique activé")
    
    def create_text_clip(
        self,
        text: str,
        start: float,
        duration: float,
        emphasis_level: int = 0,
        animation: str = None,
        **kwargs
    ) -> TextClip:
        """Crée un clip texte avec animations"""
        
        font_size = self._get_font_size(emphasis_level)
        color = self._get_text_color(emphasis_level)
        position = self._get_position(emphasis_level)
        
        animation = animation or self.animation_type
        
        try:
            # Clip de base
            clip = TextClip(
                text=text,
                font=self.config.font_family,
                font_size=font_size,
                color=color,
                size=(self.config.video_width - 100, None),
                method='caption',
                align='center',
                stroke_color=self._rgb_to_hex(self.config.stroke_color),
                stroke_width=self.config.stroke_width if emphasis_level >= 1 else 0,
            )
            
            # Positionnement
            clip = clip.with_position(position)
            
            # Timing
            clip = clip.with_start(start).with_duration(duration)
            
            # Appliquer animation
            clip = self._apply_animation(clip, animation, emphasis_level)
            
            logger.debug(f"✅ Clip dynamique: '{text[:20]}...' | Anim: {animation}")
            
            return clip
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return None
    
    def _apply_animation(self, clip, animation_type: str, emphasis: int):
        """Applique l'animation choisie"""
        
        if animation_type == 'slide_up':
            return self._animate_slide_up(clip, emphasis)
        
        elif animation_type == 'zoom':
            return self._animate_zoom(clip, emphasis)
        
        elif animation_type == 'fade':
            return clip.crossfadein(0.3).crossfadeout(0.3)
        
        else:
            return clip
    
    def _animate_slide_up(self, clip, emphasis: int):
        """Animation de glissement vers le haut"""
        
        def position_function(t):
            # Glissement sur les 0.3 premières secondes
            if t < 0.3:
                progress = t / 0.3
                # Easing quadratique
                eased = 1 - (1 - progress) ** 2
                
                # Position finale
                final_x, final_y = clip.pos(0)
                
                # Décalage initial (part du bas)
                offset = 100 * (1 - eased)
                
                if isinstance(final_y, str):
                    final_y = self.config.video_height // 2
                
                return (final_x, final_y + offset)
            else:
                return clip.pos(0)
        
        return clip.with_position(position_function)
    
    def _animate_zoom(self, clip, emphasis: int):
        """Animation de zoom"""
        
        zoom_factor = 1.2 if emphasis >= 2 else 1.1
        
        def resize_function(t):
            if t < 0.2:
                # Zoom in progressif
                progress = t / 0.2
                return 0.8 + (zoom_factor - 0.8) * progress
            elif t > clip.duration - 0.2:
                # Zoom out progressif
                progress = (clip.duration - t) / 0.2
                return 0.8 + (zoom_factor - 0.8) * progress
            else:
                return zoom_factor
        
        return clip.resized(resize_function)
    
    def get_background_clip(self, duration: float):
        """Fond noir avec vignette subtile"""
        
        # Fond noir de base
        bg = ColorClip(
            size=(self.config.video_width, self.config.video_height),
            color=(0, 0, 0),
            duration=duration
        )
        
        # TODO: Ajouter vignette avec masque (optionnel)
        
        return bg
