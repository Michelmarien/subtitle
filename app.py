import os
import logging
import json
import hashlib
import pickle
from pathlib import Path
from datetime import datetime
from functools import lru_cache, partial
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

import numpy as np
import spacy
import whisper
from moviepy import AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip
from tqdm import tqdm

# === CONFIGURATION ===
CONFIG = {
    'font_size': 90,
    'text_color': 'white',
    'font': "font/ANTON-REGULAR.TTF",
    'video_size': (1920, 1080),
    'fps': 30,
    'whisper_model_size': 'small',
    'device': 'cpu',
    'videos_storage_dir': 'videos_created',
    'metadata_file': 'videos_metadata.json',
    'transcription_cache_dir': '.transcription_cache',
    'max_clip_workers': 4,
}

SPACY_MODELS = {
    "fr": "fr_core_news_md",
    "en": "en_core_web_trf"
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# === CLASSE OPTIMISÉE NLP ===
class OptimizedNLPProcessor:
    """Processeur NLP optimisé avec cache et vectorisation"""
    
    def __init__(self, nlp_model):
        self.nlp = nlp_model
        self.impact_vectors = self._precompute_impact_vectors()
        self.token_cache = {}
    
    def _precompute_impact_vectors(self):
        """Pré-calcul des vecteurs d'impact"""
        concepts = ['powerful', 'strong', 'intense', 'extreme', 'incredible']
        vectors = {}
        
        for concept in concepts:
            if concept in self.nlp.vocab and self.nlp.vocab[concept].has_vector:
                vectors[concept] = self.nlp.vocab[concept].vector
        
        logger.info(f"✅ {len(vectors)} vecteurs d'impact pré-calculés")
        return vectors
    
    @lru_cache(maxsize=10000)
    def is_impact_word_fast(self, word_text, pos_tag, dep_tag):
        """Détection rapide avec cache"""
        # Règles rapides (pas de calcul vectoriel)
        if pos_tag in ['JJS', 'RBS']:
            return True, 1.5
        
        if word_text.isupper() and len(word_text) > 2:
            return True, 1.8
        
        if dep_tag == 'neg':
            return True, 1.3
        
        # Calcul vectoriel (seulement si nécessaire)
        cache_key = (word_text, pos_tag)
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        try:
            token = self.nlp(word_text)[0]
            
            if not token.has_vector or not self.impact_vectors:
                return False, 0
            
            token_vec = token.vector
            max_sim = 0
            
            for vec in self.impact_vectors.values():
                sim = np.dot(token_vec, vec) / (
                    np.linalg.norm(token_vec) * np.linalg.norm(vec) + 1e-8
                )
                max_sim = max(max_sim, sim)
            
            result = (max_sim > 0.7, max_sim)
            self.token_cache[cache_key] = result
            return result
        
        except:
            return False, 0
    
    def process_segments_batch(self, segments):
        """Traite tous les segments en une seule passe spaCy"""
        # Concaténer avec séparateurs
        texts = []
        for seg in segments:
            text = " ".join([w['word'].strip() for w in seg.get('words', [])])
            texts.append(text)
        
        full_text = " |SEP| ".join(texts)
        
        # UNE SEULE analyse spaCy
        doc = self.nlp(full_text)
        
        # Découper et retourner par segment
        results = []
        current_tokens = []
        
        for token in doc:
            if token.text == "|SEP|":
                results.append(current_tokens)
                current_tokens = []
            else:
                current_tokens.append(token)
        
        if current_tokens:
            results.append(current_tokens)
        
        return results

# === FONCTIONS DE CACHE ===
def get_audio_hash(audio_path):
    """Hash MD5 du fichier audio"""
    with open(audio_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_cached_transcription(audio_path, cache_dir):
    """Récupère transcription depuis cache"""
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)
    
    audio_hash = get_audio_hash(audio_path)
    cache_file = cache_path / f"{audio_hash}.pkl"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                logger.info("✅ Transcription chargée depuis cache")
                return pickle.load(f)
        except:
            pass
    
    return None

def save_transcription_cache(audio_path, transcription, cache_dir):
    """Sauvegarde transcription en cache"""
    cache_path = Path(cache_dir)
    audio_hash = get_audio_hash(audio_path)
    cache_file = cache_path / f"{audio_hash}.pkl"
    
    with open(cache_file, 'wb') as f:
        pickle.dump(transcription, f)
    
    logger.info(f"💾 Transcription mise en cache")

# === FONCTIONS WHISPER OPTIMISÉES ===
def load_whisper_model(model_size="small", device="cpu"):
    """Charge modèle Whisper"""
    try:
        logger.info(f"Chargement Whisper '{model_size}' sur {device}...")
        model = whisper.load_model(model_size, device=device)
        logger.info("✅ Modèle Whisper chargé")
        return model
    except Exception as e:
        logger.error(f"❌ Erreur Whisper: {e}")
        return None

def get_transcript_optimized(filename, model, cache_dir):
    """Transcription avec cache et optimisations"""
    # Vérifier cache
    cached = get_cached_transcription(filename, cache_dir)
    if cached:
        return cached
    
    if not os.path.exists(filename):
        logger.error(f"❌ Fichier introuvable: {filename}")
        return None
    
    try:
        logger.info("🎙️ Transcription en cours...")
        audio = whisper.load_audio(filename)
        
        result = whisper.transcribe(
            model,
            audio,
            word_timestamps=True,
            fp16=False,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
        )
        
        logger.info(f"✅ Transcription terminée - Langue: {result.get('language', 'N/A').upper()}")
        
        # Sauvegarder en cache
        save_transcription_cache(filename, result, cache_dir)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur transcription: {e}")
        return None

# === FONCTIONS spaCy ===
def load_spacy_model(language_code):
    """Charge modèle spaCy"""
    model_name = SPACY_MODELS.get(language_code)
    if not model_name:
        logger.error(f"❌ Pas de modèle pour '{language_code}'")
        return None
    
    try:
        logger.info(f"Chargement spaCy: {model_name}")
        nlp = spacy.load(model_name)
        logger.info(f"✅ Modèle '{model_name}' chargé")
        return nlp
    except IOError:
        logger.error(f"❌ Installez avec: python -m spacy download {model_name}")
        return None

# === GROUPEMENT OPTIMISÉ ===
def group_words_optimized(segment, spacy_tokens, nlp_processor, max_words=5):
    """Groupement O(n) optimisé"""
    if not segment or 'words' not in segment:
        return []
    
    word_groups = []
    current_group = []
    whisper_words = segment['words']
    
    word_idx = 0
    
    for token in spacy_tokens:
        if word_idx >= len(whisper_words):
            break
        
        whisper_word = whisper_words[word_idx]
        should_break = False
        
        # Entités nommées
        if token.ent_type_:
            current_group.append(whisper_word)
            if token.ent_iob_ not in ['I']:
                should_break = True
        
        # Mots d'impact
        elif nlp_processor.is_impact_word_fast(token.text, token.pos_, token.dep_)[0]:
            if current_group:
                word_groups.append(current_group)
                current_group = []
            word_groups.append([whisper_word])
        
        # Ponctuation
        elif token.is_punct and token.text in ['.', '!', '?', ';']:
            current_group.append(whisper_word)
            should_break = True
        
        # Standard
        else:
            current_group.append(whisper_word)
            if len(current_group) >= max_words:
                should_break = True
        
        if should_break and current_group:
            word_groups.append(current_group)
            current_group = []
        
        word_idx += 1
    
    if current_group:
        word_groups.append(current_group)
    
    return word_groups

# === CRÉATION CLIPS PARALLÈLE ===
def create_text_clip_safe(group_info, config):
    """Crée un clip de texte (thread-safe)"""
    group, start_time, end_time = group_info
    
    try:
        text = " ".join([w['word'].strip() for w in group]).upper()
        
        clip = (
            TextClip(
                text=text,
                font=config['font'],
                font_size=config['font_size'],
                color=config['text_color'],
                size=config['video_size'],
                method='caption',
            )
            .with_start(start_time)
            .with_duration(end_time - start_time)
            .with_position('center')
        )
        
        return clip
    except Exception as e:
        logger.warning(f"⚠️ Échec clip: {e}")
        return None

def generate_clips_parallel(transcription, nlp_processor, config):
    """Génère clips en parallèle"""
    
    # 1. Traitement NLP batch
    logger.info("🧠 Analyse NLP...")
    segments = transcription.get("segments", [])
    all_tokens = nlp_processor.process_segments_batch(segments)
    
    # 2. Préparation tâches
    clip_tasks = []
    
    for segment, tokens in zip(segments, all_tokens):
        groups = group_words_optimized(segment, tokens, nlp_processor)
        
        for group in groups:
            if group:
                clip_tasks.append((
                    group,
                    group[0]['start'],
                    group[-1]['end']
                ))
    
    logger.info(f"📝 {len(clip_tasks)} clips à créer")
    
    # 3. Création parallèle
    clips = []
    create_func = partial(create_text_clip_safe, config=config)
    
    with ThreadPoolExecutor(max_workers=config['max_clip_workers']) as executor:
        futures = {executor.submit(create_func, task): task for task in clip_tasks}
        
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="🎬 Création clips"
        ):
            clip = future.result()
            if clip:
                clips.append(clip)
    
    logger.info(f"✅ {len(clips)} clips créés")
    return clips

# === GESTION VIDÉO OPTIMISÉE ===
@contextmanager
def managed_clip(clip_or_path, is_path=True):
    """Context manager pour clips"""
    clip = None
    try:
        if is_path:
            if isinstance(clip_or_path, str):
                if clip_or_path.endswith(('.mp4', '.mov', '.avi')):
                    clip = VideoFileClip(clip_or_path)
                else:
                    clip = AudioFileClip(clip_or_path)
            else:
                clip = clip_or_path
        else:
            clip = clip_or_path
        
        yield clip
    finally:
        if clip:
            try:
                clip.close()
            except:
                pass

def prepare_background_optimized(bg_path, config):
    """Prépare vidéo de fond avec gestion mémoire"""
    try:
        logger.info(f"📹 Chargement vidéo: {bg_path}")
        
        bg = VideoFileClip(bg_path)
        logger.info(f"⏱️ Durée: {bg.duration:.2f}s")
        
        bg_resized = bg.resized(config['video_size'])
        bg_final = bg_resized.without_audio()
        
        logger.info("✅ Vidéo préparée")
        return bg_final
        
    except Exception as e:
        logger.error(f"❌ Erreur vidéo: {e}")
        return None

# === FONCTION PRINCIPALE OPTIMISÉE ===
def create_video_optimized(audio_file, bg_video_file, output_file, config, auto_store=True):
    """Création vidéo complète OPTIMISÉE"""
    
    logger.info("🎬 DÉMARRAGE PROCESSUS OPTIMISÉ")
    
    audio_clip = None
    bg_clip = None
    final_video = None
    text_clips = []
    
    try:
        # 1. Whisper avec cache
        whisper_model = load_whisper_model(config['whisper_model_size'], config['device'])
        if not whisper_model:
            return False, None
        
        transcription = get_transcript_optimized(
            audio_file,
            whisper_model,
            config['transcription_cache_dir']
        )
        
        if not transcription:
            return False, None
        
        language = transcription.get('language', 'en')
        
        # 2. spaCy
        nlp = load_spacy_model(language)
        if not nlp:
            return False, None
        
        nlp_processor = OptimizedNLPProcessor(nlp)
        
        # 3. Audio
        logger.info("🎵 Chargement audio...")
        audio_clip = AudioFileClip(audio_file)
        
        if not hasattr(audio_clip, 'duration') or audio_clip.duration is None:
            raise ValueError("Durée audio invalide")
        
        duration = audio_clip.duration
        logger.info(f"⏱️ Durée audio: {duration:.2f}s")
        
        # 4. Vidéo de fond
        bg_clip = prepare_background_optimized(bg_video_file, config)
        if not bg_clip:
            raise ValueError("Impossible de charger vidéo de fond")
        
        # 5. Génération clips (PARALLÈLE + OPTIMISÉ)
        text_clips = generate_clips_parallel(transcription, nlp_processor, config)
        
        if not text_clips:
            logger.warning("⚠️ Aucun clip de texte créé")
        
        # 6. Gestion stockage
        final_path = output_file
        if auto_store:
            storage_dir = Path(config['videos_storage_dir'])
            storage_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            basename = Path(audio_file).stem.replace(' ', '_')
            final_path = str(storage_dir / f"{timestamp}_{basename}.mp4")
            
            logger.info(f"💾 Stockage: {final_path}")
        
        # 7. Composition
        logger.info("🎞️ Composition finale...")
        final_video = CompositeVideoClip([bg_clip] + text_clips)
        final_video = final_video.with_audio(audio_clip)
        
        # 8. Export (optimisé)
        logger.info("📤 Export en cours...")
        final_video.write_videofile(
            final_path,
            codec="libx264",
            audio_codec="aac",
            fps=config['fps'],
            threads=4,
            preset='medium',
            logger=None,  # Désactiver logging verbeux moviepy
        )
        
        logger.info("🎉 VIDÉO CRÉÉE AVEC SUCCÈS !")
        
        # 9. Métadonnées
        if auto_store:
            metadata = {
                "video_path": final_path,
                "creation_date": datetime.now().isoformat(),
                "audio_source": audio_file,
                "background_video": bg_video_file,
                "detected_language": language,
                "duration_seconds": duration,
                "file_size_mb": round(Path(final_path).stat().st_size / (1024**2), 2)
            }
            
            metadata_file = Path(config['metadata_file'])
            existing = []
            
            if metadata_file.exists():
                try:
                    existing = json.loads(metadata_file.read_text())
                except:
                    existing = []
            
            existing.append(metadata)
            metadata_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        
        return True, final_path
        
    except Exception as e:
        logger.error(f"❌ ERREUR: {e}", exc_info=True)
        return False, None
        
    finally:
        # Nettoyage mémoire
        logger.info("🧹 Nettoyage...")
        
        if audio_clip:
            audio_clip.close()
        if bg_clip:
            bg_clip.close()
        if final_video:
            final_video.close()
        
        for clip in text_clips:
            try:
                clip.close()
            except:
                pass

# === MAIN ===
if __name__ == "__main__":
    audio_file = "audio/DON'T QUIT ON YOUR DREAM - Motivational Speech.mp3"
    bg_video = "montage_final.mp4"
    output = "video_finale.mp4"
    
    if not Path(audio_file).exists() or not Path(bg_video).exists():
        print("❌ Fichiers introuvables")
        print(f"Audio: {audio_file}")
        print(f"Vidéo: {bg_video}")
    else:
        print("🚀 CRÉATION VIDÉO OPTIMISÉE")
        print("=" * 70)
        
        success, path = create_video_optimized(
            audio_file,
            bg_video,
            output,
            CONFIG,
            auto_store=True
        )
        
        if success and path:
            size_mb = Path(path).stat().st_size / (1024**2)
            print(f"\n✅ SUCCÈS !")
            print(f"📁 {path}")
            print(f"📊 {size_mb:.2f} MB")
        else:
            print("\n❌ ÉCHEC - Voir logs")
