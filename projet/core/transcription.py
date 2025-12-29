import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict
import whisper
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def get_audio_hash(audio_path: str) -> str:
    """
    Génère un hash unique du fichier audio pour le cache
    
    Args:
        audio_path: Chemin vers le fichier audio
        
    Returns:
        Hash MD5 du fichier
    """
    hash_md5 = hashlib.md5()
    
    with open(audio_path, "rb") as f:
        # Lire par chunks pour gérer gros fichiers
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    return hash_md5.hexdigest()


def get_cached_transcription(
    audio_path: str,
    cache_dir: str = ".cache/transcriptions"
) -> Optional[Dict]:
    """
    Récupère la transcription depuis le cache si elle existe
    
    Args:
        audio_path: Chemin vers le fichier audio
        cache_dir: Répertoire de cache
        
    Returns:
        Transcription ou None si pas en cache
    """
    # Créer le dossier cache s'il n'existe pas
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    # Générer nom de fichier cache
    audio_hash = get_audio_hash(audio_path)
    cache_file = Path(cache_dir) / f"{audio_hash}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                transcription = json.load(f)
            
            logger.info(f"✅ Transcription trouvée en cache: {cache_file.name}")
            return transcription
        
        except Exception as e:
            logger.warning(f"⚠️ Erreur lecture cache: {e}")
            return None
    
    return None


def save_transcription_to_cache(
    transcription: Dict,
    audio_path: str,
    cache_dir: str = ".cache/transcriptions"
) -> bool:
    """
    Sauvegarde la transcription dans le cache
    
    Args:
        transcription: Résultat de Whisper
        audio_path: Chemin du fichier audio source
        cache_dir: Répertoire de cache
        
    Returns:
        True si sauvegarde réussie
    """
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        audio_hash = get_audio_hash(audio_path)
        cache_file = Path(cache_dir) / f"{audio_hash}.json"
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(transcription, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Transcription sauvegardée: {cache_file.name}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde cache: {e}")
        return False


def get_transcript_whisper(
    audio_path: str,
    model_size: str = "small",
    device: str = "cpu",
    cache_dir: str = ".cache/transcriptions",
    use_cache: bool = True
) -> Optional[Dict]:
    """
    Transcrit un fichier audio avec Whisper (version standard)
    
    Args:
        audio_path: Chemin vers le fichier audio
        model_size: Taille du modèle ('tiny', 'base', 'small', 'medium', 'large')
        device: Device de calcul ('cpu' ou 'cuda')
        cache_dir: Répertoire de cache
        use_cache: Utiliser le cache si disponible
        
    Returns:
        Dictionnaire avec segments et métadonnées
    """
    if not os.path.exists(audio_path):
        logger.error(f"❌ Fichier audio introuvable: {audio_path}")
        return None
    
    # Vérifier cache
    if use_cache:
        cached = get_cached_transcription(audio_path, cache_dir)
        if cached:
            return cached
    
    # Transcription
    try:
        logger.info(f"🎙️ Transcription avec Whisper '{model_size}' sur {device}...")
        logger.info(f"   Fichier: {Path(audio_path).name}")
        
        model = whisper.load_model(model_size, device=device)
        
        result = model.transcribe(
            audio_path,
            word_timestamps=True,  # ⚠️ ESSENTIEL pour le timing des mots
            verbose=False
        )
        
        logger.info(f"✅ Transcription terminée")
        logger.info(f"   Langue: {result['language']}")
        logger.info(f"   Segments: {len(result['segments'])}")
        
        # Sauvegarder en cache
        if use_cache:
            save_transcription_to_cache(result, audio_path, cache_dir)
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Erreur transcription: {e}", exc_info=True)
        return None


def get_transcript_faster_whisper(
    audio_path: str,
    model_size: str = "small",
    device: str = "cpu",
    cache_dir: str = ".cache/transcriptions",
    use_cache: bool = True,
    compute_type: str = "int8"
) -> Optional[Dict]:
    """
    Transcrit avec Faster-Whisper (2-3x plus rapide)
    
    ⚠️ Nécessite: pip install faster-whisper
    
    Args:
        audio_path: Chemin vers le fichier audio
        model_size: Taille du modèle
        device: 'cpu', 'cuda' ou 'auto'
        cache_dir: Répertoire de cache
        use_cache: Utiliser le cache
        compute_type: 'int8', 'float16', 'float32' (précision/vitesse)
        
    Returns:
        Transcription au format standard Whisper
    """
    if not os.path.exists(audio_path):
        logger.error(f"❌ Fichier audio introuvable: {audio_path}")
        return None
    
    # Vérifier cache
    if use_cache:
        cached = get_cached_transcription(audio_path, cache_dir)
        if cached:
            return cached
    
    try:
        
        logger.info(f"🚀 Transcription avec Faster-Whisper '{model_size}'...")
        logger.info(f"   Device: {device} | Compute: {compute_type}")
        
        # Charger modèle optimisé
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        
        # Transcrire
        segments, info = model.transcribe(
            audio_path,
            word_timestamps=True,
            vad_filter=True,  # Filtrage activité vocale (améliore précision)
        )
        
        logger.info(f"✅ Langue détectée: {info.language} (prob: {info.language_probability:.2%})")
        
        # Convertir au format standard Whisper
        result = {
            "text": "",
            "segments": [],
            "language": info.language
        }
        
        full_text = []
        
        for segment in segments:
            # Extraire les mots avec timestamps
            words = []
            for word in segment.words:
                words.append({
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
            
            segment_dict = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": words,
                "avg_logprob": segment.avg_logprob,
                "no_speech_prob": segment.no_speech_prob
            }
            
            result["segments"].append(segment_dict)
            full_text.append(segment.text)
        
        result["text"] = " ".join(full_text)
        
        logger.info(f"✅ {len(result['segments'])} segments transcrits")
        
        # Sauvegarder en cache
        if use_cache:
            save_transcription_to_cache(result, audio_path, cache_dir)
        
        return result
    
    except ImportError:
        logger.warning("⚠️ faster-whisper non installé, utilisation de Whisper standard")
        logger.info("   Installation: pip install faster-whisper")
        return get_transcript_whisper(audio_path, model_size, device, cache_dir, use_cache)
    
    except Exception as e:
        logger.error(f"❌ Erreur transcription: {e}", exc_info=True)
        return None


# === FONCTION HELPER PRINCIPALE ===

def get_transcript(
    audio_path: str,
    model_size: str = "small",
    device: str = "cpu",
    use_faster_whisper: bool = True,
    **kwargs
) -> Optional[Dict]:
    """
    Fonction unifiée pour transcription
    
    Args:
        audio_path: Chemin audio
        model_size: Taille modèle
        device: Device de calcul
        use_faster_whisper: Utiliser faster-whisper si disponible
        **kwargs: Arguments additionnels
        
    Returns:
        Transcription
    """
    if use_faster_whisper:
        return get_transcript_faster_whisper(audio_path, model_size, device, **kwargs)
    else:
        return get_transcript_whisper(audio_path, model_size, device, **kwargs)
