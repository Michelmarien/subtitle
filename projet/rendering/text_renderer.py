import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from moviepy import TextClip

from core.text_formatter import TextSegment
from themes.base_theme import BaseTheme

logger = logging.getLogger(__name__)


class TextRenderer:
    """
    Moteur de rendu des clips de texte
    
    Responsabilités :
    - Générer les clips depuis les TextSegments
    - Appliquer le thème sélectionné
    - Paralléliser la création des clips
    """
    
    def __init__(self, theme: BaseTheme, max_workers: int = 4):
        """
        Args:
            theme: Instance d'un thème (Minimalist, Dynamic, etc.)
            max_workers: Nombre de threads pour parallélisation
        """
        self.theme = theme
        self.max_workers = max_workers
    
    def render_segments(self, segments: List[TextSegment]) -> List[TextClip]:
        """
        Génère tous les clips de texte en parallèle
        
        Args:
            segments: Liste de TextSegment à rendre
            
        Returns:
            Liste de TextClip prêts à composer
        """
        if not segments:
            logger.warning("Aucun segment à rendre")
            return []
        
        logger.info(f"🎬 Rendu de {len(segments)} segments avec {self.theme.__class__.__name__}...")
        
        text_clips = []
        
        # Rendu parallèle
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_segment = {
                executor.submit(self._render_single_segment, seg): seg
                for seg in segments
            }
            
            # Progress bar
            with tqdm(total=len(segments), desc="🎨 Rendu texte", unit="clip") as pbar:
                for future in as_completed(future_to_segment):
                    segment = future_to_segment[future]
                    
                    try:
                        clip = future.result()
                        if clip:
                            text_clips.append(clip)
                            pbar.set_postfix_str(f"✅ {segment.text[:20]}...")
                        else:
                            pbar.set_postfix_str(f"❌ Échec")
                    
                    except Exception as e:
                        logger.error(f"❌ Erreur rendu segment '{segment.text[:30]}': {e}")
                    
                    pbar.update(1)
        
        logger.info(f"✅ {len(text_clips)}/{len(segments)} clips créés")
        
        return text_clips
    
    def _render_single_segment(self, segment: TextSegment) -> TextClip:
        """Rend un seul segment de texte"""
        try:
            return self.theme.create_text_clip(
                text=segment.text,
                start=segment.start,
                duration=segment.duration,
                emphasis_level=segment.emphasis_level
            )
        except Exception as e:
            logger.error(f"Erreur création clip: {e}")
            return None
