import logging
from pathlib import Path
from typing import List
from moviepy import CompositeVideoClip, AudioFileClip
from tqdm import tqdm

from themes.base_theme import BaseTheme

logger = logging.getLogger(__name__)


class VideoComposer:
    """
    Assemble les clips de texte avec le fond et l'audio
    
    Responsabilités :
    - Composition finale (fond + textes + audio)
    - Export optimisé
    - Gestion de la mémoire
    """
    
    def __init__(self, theme: BaseTheme):
        self.theme = theme
    
    def compose_video(
        self,
        text_clips: List,
        audio_path: str,
        output_path: str,
        codec: str = 'libx264',
        fps: int = 30,
        bitrate: str = '5000k',
        preset: str = 'medium',
        **kwargs
    ) -> bool:
        """
        Crée la vidéo finale
        
        Args:
            text_clips: Liste des TextClip à superposer
            audio_path: Chemin vers fichier audio
            output_path: Chemin de sortie
            codec: Codec vidéo ('libx264', 'libx265')
            fps: Images par seconde
            bitrate: Débit vidéo
            preset: Preset ffmpeg ('ultrafast' à 'veryslow')
            
        Returns:
            True si succès, False sinon
        """
        audio_clip = None
        background_clip = None
        final_video = None
        
        try:
            # 1. Charger l'audio
            logger.info(f"🎵 Chargement audio: {Path(audio_path).name}")
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 2. Créer le fond
            logger.info(f"🎨 Génération fond ({self.theme.__class__.__name__})...")
            background_clip = self.theme.get_background_clip(duration)
            
            # 3. Composition
            logger.info(f"🎬 Composition de {len(text_clips)} clips texte...")
            
            # Trier par start time
            text_clips_sorted = sorted(text_clips, key=lambda c: c.start)
            
            # Composer
            final_video = CompositeVideoClip(
                [background_clip] + text_clips_sorted,
                size=(self.theme.config.video_width, self.theme.config.video_height)
            )
            
            # Ajouter l'audio
            final_video = final_video.with_audio(audio_clip)
            
            # 4. Export
            logger.info(f"💾 Export vers: {output_path}")
            logger.info(f"   Codec: {codec} | FPS: {fps} | Bitrate: {bitrate}")
            
            final_video.write_videofile(
                output_path,
                codec=codec,
                fps=fps,
                bitrate=bitrate,
                preset=preset,
                audio_codec='aac',
                audio_bitrate='192k',
                logger=None,  # Désactiver log verbose moviepy
                # Progress bar custom
                verbose=False,
                # Threads
                threads=4,
            )
            
            logger.info(f"✅ Vidéo créée: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur composition vidéo: {e}", exc_info=True)
            return False
        
        finally:
            # Libérer mémoire
            logger.info("🧹 Nettoyage mémoire...")
            
            if audio_clip:
                audio_clip.close()
            if background_clip:
                background_clip.close()
            if final_video:
                final_video.close()
            
            for clip in text_clips:
                try:
                    clip.close()
                except:
                    pass
