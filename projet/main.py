import logging
from pathlib import Path

# Core
from core.transcription import get_transcript_faster_whisper
from core.nlp_processor import OptimizedNLPProcessor
from core.text_formatter import format_transcription_to_segments

# Themes
from themes.minimalist import MinimalistTheme
from themes.dynamic import DynamicTheme
from themes.cinematic import CinematicTheme
from themes.base_theme import ThemeConfig

# Rendering
from rendering.text_renderer import TextRenderer
from rendering.video_composer import VideoComposer

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# === CONFIGURATION ===

CONFIG = {
    # Transcription
    'whisper_model_size': 'small',
    'device': 'cpu',  # ou 'cuda'
    'transcription_cache_dir': '.cache/transcriptions',
    
    # Formatage texte
    'max_words_per_group': 4,
    'max_chars_per_line': 40,
    'min_segment_duration': 0.5,
    'max_segment_duration': 3.0,
    
    # Thème visuel
    'theme': 'minimalist',  # 'minimalist', 'dynamic', 'cinematic'
    
    # Export vidéo
    'video_width': 1080,
    'video_height': 1920,
    'fps': 30,
    'codec': 'libx264',
    'bitrate': '5000k',
    'preset': 'medium',  # 'ultrafast' pour tests, 'slow' pour qualité
}


def create_text_video(
    audio_path: str,
    output_path: str,
    theme_name: str = 'minimalist',
    config: dict = None
):
    """
    Crée une vidéo avec texte stylisé sur fond noir
    
    Args:
        audio_path: Chemin vers fichier audio
        output_path: Chemin de sortie vidéo
        theme_name: Nom du thème ('minimalist', 'dynamic', 'cinematic')
        config: Configuration personnalisée
    """
    
    config = config or CONFIG
    
    logger.info("=" * 70)
    logger.info("🎬 CRÉATION VIDÉO TEXTE STYLISÉ")
    logger.info("=" * 70)
    
    # === ÉTAPE 1 : TRANSCRIPTION ===
    
    logger.info("\n📝 ÉTAPE 1/5 : Transcription audio")
    
    transcription = get_transcript_faster_whisper(
        audio_path,
        model_size=config['whisper_model_size'],
        device=config['device'],
        cache_dir=config['transcription_cache_dir']
    )
    
    if not transcription:
        logger.error("❌ Échec transcription")
        return False
    
    language = transcription.get('language', 'en')
    logger.info(f"✅ Langue détectée: {language.upper()}")
    
    # === ÉTAPE 2 : ANALYSE NLP ===
    
    logger.info("\n🧠 ÉTAPE 2/5 : Analyse linguistique")
    
    nlp_processor = OptimizedNLPProcessor(language)
    if not nlp_processor.load_model():
        logger.error("❌ Échec chargement modèle NLP")
        return False
    
    # === ÉTAPE 3 : FORMATAGE TEXTE ===
    
    logger.info("\n✍️ ÉTAPE 3/5 : Formatage intelligent")
    
    text_segments = format_transcription_to_segments(
        transcription,
        nlp_processor,
        config
    )
    
    if not text_segments:
        logger.error("❌ Aucun segment généré")
        return False
    
    logger.info(f"✅ {len(text_segments)} segments formatés")
    
    # === ÉTAPE 4 : GÉNÉRATION CLIPS ===
    
    logger.info("\n🎨 ÉTAPE 4/5 : Rendu visuel")
    
    # Sélection du thème
    theme_config = ThemeConfig(
        video_width=config['video_width'],
        video_height=config['video_height'],
        font_family="font/ANTON-REGULAR.TTF",
        position='center',
    )
    
    if theme_name == 'minimalist':
        theme = MinimalistTheme(theme_config)
    elif theme_name == 'dynamic':
        theme = DynamicTheme(theme_config)
    elif theme_name == 'cinematic':
        theme = CinematicTheme(theme_config)
    else:
        logger.warning(f"⚠️ Thème '{theme_name}' inconnu, utilisation de 'minimalist'")
        theme = MinimalistTheme(theme_config)
    
    # Rendu des clips
    renderer = TextRenderer(theme, max_workers=4)
    text_clips = renderer.render_segments(text_segments)
    
    if not text_clips:
        logger.error("❌ Aucun clip créé")
        return False
    
    # === ÉTAPE 5 : ASSEMBLAGE FINAL ===
    
    logger.info("\n🎬 ÉTAPE 5/5 : Composition finale")
    
    composer = VideoComposer(theme)
    success = composer.compose_video(
        text_clips=text_clips,
        audio_path=audio_path,
        output_path=output_path,
        codec=config['codec'],
        fps=config['fps'],
        bitrate=config['bitrate'],
        preset=config['preset'],
    )
    
    if success:
        file_size = Path(output_path).stat().st_size / (1024 ** 2)
        logger.info(f"\n🎉 SUCCÈS !")
        logger.info(f"📁 Fichier: {output_path}")
        logger.info(f"📊 Taille: {file_size:.2f} MB")
        logger.info(f"🎨 Thème: {theme_name}")
        return True
    else:
        logger.error("\n❌ ÉCHEC création vidéo")
        return False


# === EXÉCUTION ===

if __name__ == "__main__":
    
    # Fichiers d'entrée
    audio_file = "audio/DON'T QUIT ON YOUR DREAM - Motivational Speech.mp3"
    
    # Test des 3 thèmes
    themes_to_test = [
        ('minimalist', 'output_minimalist.mp4'),
        ('dynamic', 'output_dynamic.mp4'),
        ('cinematic', 'output_cinematic.mp4'),
    ]
    
    # Vérifier existence audio
    if not Path(audio_file).exists():
        print(f"❌ Fichier audio introuvable: {audio_file}")
        exit(1)
    
    # Générer vidéos
    for theme_name, output_file in themes_to_test:
        print(f"\n{'='*70}")
        print(f"Génération avec thème: {theme_name.upper()}")
        print(f"{'='*70}\n")
        
        create_text_video(
            audio_path=audio_file,
            output_path=output_file,
            theme_name=theme_name,
            config=CONFIG
        )
        
        print("\n" + "="*70 + "\n")
    
    print("✨ Tous les thèmes ont été générés !")
