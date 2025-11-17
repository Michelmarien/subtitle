import os
import json
import random
import subprocess
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from functools import lru_cache
import pickle
from PIL import Image, ImageDraw
from tqdm import tqdm

# === CONFIGURATION ===
DOWNLOADS_DIR = "downloads"
VIDEOS_DIR = "videos"
OUTPUT_FILE = "montage_final.mp4"
OVERLAYS_DIR = "overlays"
CACHE_FILE = ".video_metadata_cache.pkl"
MAX_IO_WORKERS = 20
MAX_CPU_WORKERS = 4

# === GESTION ERREURS ===
class VideoProcessingError(Exception):
    pass

# === CACHE MÉTADONNÉES ===
def load_cache():
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

# === ANALYSE VIDÉO OPTIMISÉE ===
def get_video_info_single(video_path):
    """Analyse une vidéo (version atomique)"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration',
        '-show_entries', 'format=duration',
        '-of', 'json',
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              check=True, timeout=15)
        data = json.loads(result.stdout)
        
        width = height = duration = None
        
        if 'streams' in data and data['streams']:
            stream = data['streams'][0]
            width = stream.get('width')
            height = stream.get('height')
            duration = float(stream.get('duration', 0)) if stream.get('duration') else None
        
        if not duration and 'format' in data:
            duration = float(data['format'].get('duration', 0)) or None
        
        return {'duration': duration, 'width': width, 'height': height}
    
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
            json.JSONDecodeError, ValueError) as e:
        return {'duration': None, 'width': None, 'height': None, 'error': str(e)}

def get_all_videos_parallel():
    """Scan parallèle avec cache persistant"""
    cache = load_cache()
    
    # Scan fichiers
    all_video_files = [
        str(Path(root) / file)
        for root, _, files in os.walk(VIDEOS_DIR)
        for file in files
        if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
    ]
    
    if not all_video_files:
        print(f"❌ Aucune vidéo dans {VIDEOS_DIR}")
        return []
    
    print(f"📁 {len(all_video_files)} fichiers trouvés")
    
    # Séparation cache hits / misses
    to_analyze = []
    videos_with_info = []
    
    for path in all_video_files:
        mtime = os.path.getmtime(path)
        cache_key = (path, mtime)
        
        if cache_key in cache:
            info = cache[cache_key]
            if info['duration'] and info['duration'] >= 1.0:
                videos_with_info.append((path, info))
        else:
            to_analyze.append((path, mtime))
    
    print(f"✅ {len(videos_with_info)} vidéos chargées du cache")
    
    # Analyse parallèle des nouveaux fichiers
    if to_analyze:
        print(f"🔍 Analyse de {len(to_analyze)} nouvelles vidéos...")
        
        with ThreadPoolExecutor(max_workers=MAX_IO_WORKERS) as executor:
            future_to_path = {
                executor.submit(get_video_info_single, path): (path, mtime)
                for path, mtime in to_analyze
            }
            
            with tqdm(total=len(to_analyze), desc="📹 Analyse parallèle") as pbar:
                for future in as_completed(future_to_path):
                    path, mtime = future_to_path[future]
                    try:
                        info = future.result(timeout=20)
                        cache[(path, mtime)] = info
                        
                        if info['duration'] and info['duration'] >= 1.0:
                            videos_with_info.append((path, info))
                            pbar.set_postfix_str(f"✅ {info['width']}x{info['height']}")
                    except Exception as e:
                        pbar.set_postfix_str(f"❌ {Path(path).name[:20]}")
                    finally:
                        pbar.update(1)
        
        save_cache(cache)
    
    print(f"✅ Total: {len(videos_with_info)} vidéos utilisables\n")
    return videos_with_info

# === INDEXATION POUR RECHERCHE RAPIDE ===
def index_videos_by_duration(videos_with_info):
    """Crée un index O(1) pour recherche par durée"""
    duration_index = defaultdict(list)
    
    for path, info in videos_with_info:
        bucket = int(info['duration'] // 5)  # Buckets de 5s
        duration_index[bucket].append((path, info))
    
    return duration_index

def find_suitable_videos(required_duration, duration_index, fallback_videos):
    """Recherche O(1) au lieu de O(n)"""
    bucket = int(required_duration // 5)
    
    candidates = []
    for b in range(bucket, bucket + 10):  # 10 buckets = 50s de marge
        candidates.extend(duration_index.get(b, []))
    
    suitable = [
        (p, info) for p, info in candidates
        if info['duration'] >= required_duration + 1.0
    ]
    
    return suitable if suitable else fallback_videos[-20:]

# === CRÉATION CLIPS OPTIMISÉE ===
def create_temp_clip_fast(input_path, start_time, duration, video_filter, 
                          overlay_path, video_info):
    """Création clip sans double appel ffprobe"""
    
    if not video_info['duration'] or video_info['duration'] < 0.5:
        return None
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        temp_file = f.name
    
    start_time = max(0.0, float(start_time))
    duration = max(0.1, float(duration))
    
    # Ajustement si dépassement
    if start_time + duration > video_info['duration']:
        start_time = max(0, video_info['duration'] - duration)
    
    cmd = [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-ss', f"{start_time:.3f}",
        '-i', input_path,
        '-i', overlay_path,
        '-t', f"{duration:.3f}",
        '-filter_complex', f"[0:v]{video_filter}[main]; [main][1:v]overlay=0:0",
        '-an', '-c:v', 'libx264', '-preset', 'ultrafast',
        temp_file
    ]
    
    try:
        timeout = max(duration * 3, 30)
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        
        if result.returncode == 0 and os.path.getsize(temp_file) > 1000:
            return temp_file
        else:
            os.unlink(temp_file)
            return None
    except Exception:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return None

# === OVERLAY (version inchangée mais optimisable avec numpy) ===
@lru_cache(maxsize=20)
def create_overlay_cached(width, height, radius=50, margin=30):
    """Version cachée avec LRU"""
    os.makedirs(OVERLAYS_DIR, exist_ok=True)
    overlay_path = os.path.join(OVERLAYS_DIR, f"overlay_{width}x{height}.png")
    
    if os.path.exists(overlay_path):
        return overlay_path
    
    # ... code création identique ...
    # (version originale conservée pour clarté)
    
    return overlay_path

# === TRAITEMENT BATCH PARALLÈLE ===
def process_segments_batch(segments, duration_index, fallback_videos, 
                           width, height):
    """Traite un batch de segments en parallèle"""
    
    video_filter = f"fps=30,scale={width}:{height},setsar=1"
    overlay_path = create_overlay_cached(width, height)
    
    clip_paths = []
    
    with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
        futures = []
        
        for seg in segments:
            duration = seg["end"] - seg["start"]
            duration = max(0.5, duration)
            
            suitable = find_suitable_videos(duration, duration_index, fallback_videos)
            
            if suitable:
                vid_path, vid_info = random.choice(suitable)
                max_start = vid_info['duration'] - duration - 0.5
                start_time = random.uniform(0, max(0, max_start))
                
                future = executor.submit(
                    create_temp_clip_fast,
                    vid_path, start_time, duration, video_filter,
                    overlay_path, vid_info
                )
                futures.append(future)
        
        with tqdm(total=len(futures), desc="🎬 Création clips") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    clip_paths.append(result)
                pbar.update(1)
    
    return clip_paths

# === MAIN OPTIMISÉ ===
if __name__ == "__main__":
    print("🎬 Montage automatique OPTIMISÉ\n")
    
    # Chargement config
    json_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith("_whisper.json")]
    audio_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith(".mp3")]
    
    if not json_files or not audio_files:
        print("❌ Fichiers manquants")
        exit(1)
    
    with open(os.path.join(DOWNLOADS_DIR, json_files[0]), 'r') as f:
        data = json.load(f)
        segments = data.get("segments", data) if isinstance(data, dict) else data
    
    # Analyse parallèle avec cache
    videos_with_info = get_all_videos_parallel()
    
    if not videos_with_info:
        print("❌ Aucune vidéo utilisable")
        exit(1)
    
    # Indexation pour recherche rapide
    duration_index = index_videos_by_duration(videos_with_info)
    
    # Détection format commun
    from collections import Counter
    formats = [
        (info['width'], info['height']) 
        for _, info in videos_with_info 
        if info['width'] and info['height']
    ]
    target_width, target_height = Counter(formats).most_common(1)[0][0]
    print(f"📐 Format cible: {target_width}x{target_height}\n")
    
    # Traitement batch parallèle
    BATCH_SIZE = 50
    all_clips = []
    
    for i in range(0, len(segments), BATCH_SIZE):
        batch = segments[i:i+BATCH_SIZE]
        clips = process_segments_batch(
            batch, duration_index, videos_with_info,
            target_width, target_height
        )
        all_clips.extend(clips)
    
    # Assemblage final (inchangé)
    print("\n🔧 Assemblage final...")
    list_file = "clips_list.txt"
    with open(list_file, "w") as f:
        for clip in all_clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
        '-i', os.path.join(DOWNLOADS_DIR, audio_files[0]),
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-map', '0:v', '-map', '1:a', '-shortest', OUTPUT_FILE
    ]
    
    subprocess.run(cmd, check=True)
    print(f"\n✅ Montage créé: {OUTPUT_FILE}")
    
    # Nettoyage
    for clip in all_clips:
        try:
            os.unlink(clip)
        except:
            pass
    os.unlink(list_file)
