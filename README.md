# 🎬 Subtitle Text - Générateur de Vidéos avec Sous-titres Dynamiques

Un projet Python complet pour créer automatiquement des vidéos avec sous-titres dynamiques à partir d'audio. Le système combine la transcription audio (Whisper), l'analyse NLP (spaCy), et la composition vidéo (MoviePy) pour générer des vidéos professionnelles avec des sous-titres intelligents.

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Structure du projet](#-structure-du-projet)
- [Modules détaillés](#-modules-détaillés)
- [Optimisations](#-optimisations)
- [Dépendances](#-dépendances)

---

## ✨ Fonctionnalités

### 🎯 Principales
- **Transcription audio intelligente** : Utilise OpenAI Whisper pour convertir l'audio en texte avec timestamps précis
- **Analyse NLP avancée** : Détecte les mots d'impact et les entités nommées avec spaCy
- **Génération de sous-titres dynamiques** : Crée automatiquement des clips texte synchronisés avec l'audio
- **Composition vidéo** : Combine une vidéo de fond avec les sous-titres générés
- **Téléchargement de contenu** : Récupère des vidéos et de l'audio depuis YouTube et des APIs externes

### ⚡ Optimisations
- **Cache de transcription** : Évite les re-transcriptions inutiles (hash MD5)
- **Traitement parallèle** : Utilise ThreadPoolExecutor pour accélérer la création de clips
- **Indexation vidéo** : Cache persistant des métadonnées vidéo pour recherche O(1)
- **Batch processing** : Traite les segments par lots pour optimiser la mémoire
- **Vectorisation NLP** : Pré-calcul des vecteurs d'impact pour détection rapide

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUX PRINCIPAL                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Audio Input (MP3)  ──→  Whisper Transcription            │
│                              ↓                             │
│                         [Cache Check]                      │
│                              ↓                             │
│  Transcription JSON  ──→  spaCy NLP Analysis              │
│                              ↓                             │
│                    Détection Mots d'Impact                │
│                              ↓                             │
│  Groupement Optimisé  ──→  Création Clips Parallèle       │
│                              ↓                             │
│  Vidéo Fond + Overlay ──→  Composition Finale             │
│                              ↓                             │
│                    Vidéo Finale (MP4)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prérequis
- Python 3.8+
- FFmpeg et FFprobe (pour traitement vidéo)
- CUDA (optionnel, pour accélération GPU)

### Étapes

1. **Cloner le repository**
```bash
git clone <repository-url>
cd subtitle_text
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Télécharger les modèles spaCy**
```bash
python -m spacy download fr_core_news_md  # Pour français
python -m spacy download en_core_web_trf  # Pour anglais
```

5. **Installer FFmpeg** (si nécessaire)
   - **Windows** : `choco install ffmpeg` ou télécharger depuis https://ffmpeg.org/download.html
   - **macOS** : `brew install ffmpeg`
   - **Linux** : `sudo apt-get install ffmpeg`

6. **Vérifier GPU (optionnel)**
```bash
python text.py
```

---

## ⚙️ Configuration

### Variables d'environnement (.env)

Créer un fichier `.env` à la racine du projet :

```env
# API pour scraping vidéos
API_KEY=votre_clé_api
BASE_URL=https://api.example.com/clips

# Configuration GPU/CPU
DEVICE=cpu  # ou 'cuda' si GPU disponible
```

### Configuration dans app.py

```python
CONFIG = {
    'font_size': 90,                          # Taille du texte
    'text_color': 'white',                    # Couleur du texte
    'font': "font/ANTON-REGULAR.TTF",         # Police utilisée
    'video_size': (1920, 1080),               # Résolution vidéo
    'fps': 30,                                # Images par seconde
    'whisper_model_size': 'small',            # Modèle Whisper (tiny, base, small, medium, large)
    'device': 'cpu',                          # Processeur (cpu ou cuda)
    'videos_storage_dir': 'videos_created',   # Dossier de sortie
    'metadata_file': 'videos_metadata.json',  # Fichier métadonnées
    'transcription_cache_dir': '.transcription_cache',
    'max_clip_workers': 4,                    # Nombre de workers parallèles
}
```

---

## 📖 Utilisation

### 1️⃣ Télécharger une chanson depuis YouTube

```bash
python download_song.py "https://www.youtube.com/watch?v=..."
```

**Résultat** :
- `downloads/[titre].mp3` - Fichier audio
- `downloads/[titre]_whisper.json` - Transcription avec timestamps

### 2️⃣ Télécharger des vidéos de films

```bash
python download_video.py
```

Suivi les prompts interactifs pour :
- Nombre de films à traiter
- Titre et année de chaque film
- Durée des clips souhaités
- Index de départ pour pagination

**Résultat** : Vidéos stockées dans `videos/[film]/`

### 3️⃣ Créer un montage automatique

```bash
python montage.py
```

**Processus** :
1. Scanne toutes les vidéos dans `videos/`
2. Analyse les métadonnées (résolution, durée)
3. Crée des clips temporaires avec overlay
4. Assemble le montage final avec l'audio

**Résultat** : `montage_final.mp4`

### 4️⃣ Générer la vidéo finale avec sous-titres

```bash
python app.py
```

**Processus** :
1. Charge l'audio MP3 depuis `audio/`
2. Transcrit avec Whisper (avec cache)
3. Analyse avec spaCy (détection mots d'impact)
4. Crée les clips texte en parallèle
5. Compose la vidéo finale

**Résultat** : 
- `videos_created/[timestamp]_[titre].mp4` - Vidéo finale
- `videos_metadata.json` - Métadonnées de la vidéo

---

## 📁 Structure du projet

```
subtitle_text/
├── app.py                          # 🎬 Générateur vidéo principal (OPTIMISÉ)
├── download_song.py                # 🎵 Téléchargement audio YouTube
├── download_video.py               # 📹 Scraping vidéos via API
├── montage.py                      # 🎞️ Création montage automatique
├── overlay.py                      # 🎨 Gestion overlays vidéo
├── text.py                         # 🔍 Vérification GPU/CPU
├── requirements.txt                # 📦 Dépendances Python
│
├── font/                           # 🔤 Polices de caractères
│   ├── ANTON-REGULAR.TTF
│   ├── BARBERCHOP.OTF
│   ├── BEBASNEUE-REGULAR.TTF
│   └── ... (autres polices)
│
├── audio/                          # 🎵 Fichiers audio (entrée)
│   └── DON'T QUIT ON YOUR DREAM.mp3
│
├── downloads/                      # 📥 Fichiers téléchargés
│   ├── *.mp3                       # Audio YouTube
│   └── *_whisper.json              # Transcriptions
│
├── videos/                         # 📹 Vidéos source
│   └── [film_name]/
│       └── *.mp4
│
├── videos_created/                 # 🎬 Vidéos générées
│   └── [timestamp]_[titre].mp4
│
├── overlays/                       # 🎨 Overlays générés
│   └── overlay_[width]x[height].png
│
├── transcription/                  # 📝 Transcriptions
├── analysis/                       # 📊 Analyses
├── Michou/                         # 📂 Données spécifiques
│
├── .transcription_cache/           # 💾 Cache transcriptions
├── .video_metadata_cache.pkl       # 💾 Cache métadonnées vidéo
├── videos_metadata.json            # 📋 Métadonnées vidéos créées
└── .env                            # 🔐 Variables d'environnement
```

---

## 🔧 Modules détaillés

### 📌 app.py - Générateur vidéo principal

**Classe : `OptimizedNLPProcessor`**
- Traitement NLP optimisé avec cache
- Pré-calcul des vecteurs d'impact
- Détection rapide des mots importants

**Fonctions principales** :
- `load_whisper_model()` - Charge le modèle Whisper
- `get_transcript_optimized()` - Transcription avec cache
- `load_spacy_model()` - Charge modèle spaCy
- `group_words_optimized()` - Groupement intelligent des mots
- `generate_clips_parallel()` - Création parallèle des clips
- `create_video_optimized()` - Pipeline complet

**Optimisations** :
- ✅ Cache MD5 des transcriptions
- ✅ Traitement batch spaCy
- ✅ ThreadPoolExecutor pour clips
- ✅ Context managers pour gestion mémoire

---

### 📌 montage.py - Création montage automatique

**Fonctions principales** :
- `get_all_videos_parallel()` - Scan parallèle avec cache
- `index_videos_by_duration()` - Indexation pour recherche O(1)
- `find_suitable_videos()` - Recherche rapide par durée
- `create_temp_clip_fast()` - Création clip optimisée
- `process_segments_batch()` - Traitement batch parallèle

**Optimisations** :
- ✅ Cache persistant (pickle) des métadonnées
- ✅ Indexation par buckets de durée
- ✅ Parallélisation I/O et CPU
- ✅ Gestion mémoire avec fichiers temporaires

---

### 📌 download_video.py - Scraping vidéos

**Fonctions principales** :
- `scrap()` - Récupère clips via API avec pagination
- `download_video()` - Télécharge vidéo avec streaming
- `save_clipids()` - Sauvegarde IDs clips en JSON
- `process_films()` - Traitement batch de films

**Caractéristiques** :
- ✅ Pagination automatique
- ✅ Vérification titre film
- ✅ Détection extension fichier
- ✅ Gestion erreurs robuste

---

### 📌 download_song.py - Téléchargement audio

**Fonctions principales** :
- `download_mp3()` - Télécharge audio YouTube avec yt-dlp
- `main()` - Pipeline complet avec transcription Whisper

**Résultat** :
- Fichier MP3 haute qualité
- Transcription JSON avec timestamps

---

## ⚡ Optimisations

### 1. Cache Multi-niveaux
```python
# Cache transcription (MD5)
audio_hash = hashlib.md5(file.read()).hexdigest()
cache_file = f"{hash}.pkl"

# Cache métadonnées vidéo (pickle)
cache[(path, mtime)] = video_info

# Cache NLP (LRU)
@lru_cache(maxsize=10000)
def is_impact_word_fast(word, pos, dep):
    ...
```

### 2. Traitement Parallèle
```python
# ThreadPoolExecutor pour I/O
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(task) for task in tasks]
    
# Batch processing spaCy
doc = nlp(full_text)  # UNE SEULE analyse
```

### 3. Indexation Intelligente
```python
# Buckets de durée pour recherche O(1)
duration_index[bucket] = videos
suitable = duration_index.get(bucket, [])
```

### 4. Gestion Mémoire
```python
# Context managers
with managed_clip(clip_path) as clip:
    # Utilisation
    pass  # Fermeture automatique

# Nettoyage fichiers temporaires
for clip in all_clips:
    os.unlink(clip)
```

---

## 📦 Dépendances

### Principales
| Package | Version | Utilité |
|---------|---------|---------|
| `openai-whisper` | 20250625 | Transcription audio |
| `spacy` | - | Analyse NLP |
| `moviepy` | 2.2.1 | Composition vidéo |
| `torch` | 2.7.1 | Deep learning (Whisper, spaCy) |
| `yt-dlp` | 2025.6.30 | Téléchargement YouTube |
| `opencv-python` | 4.12.0.88 | Traitement image |
| `pillow` | 11.3.0 | Création overlays |
| `numpy` | 2.2.6 | Calculs vectoriels |
| `tqdm` | 4.67.1 | Barres de progression |

### Installation complète
```bash
pip install -r requirements.txt
python -m spacy download fr_core_news_md
python -m spacy download en_core_web_trf
```

---

## 🎯 Cas d'usage

### 1. Créer une vidéo motivationnelle
```bash
# 1. Télécharger l'audio
python download_song.py "https://youtube.com/watch?v=..."

# 2. Créer le montage
python montage.py

# 3. Générer la vidéo finale
python app.py
```

### 2. Créer un montage de film
```bash
# 1. Télécharger les clips
python download_video.py

# 2. Créer le montage
python montage.py

# 3. Ajouter l'audio et les sous-titres
python app.py
```

### 3. Traiter plusieurs fichiers
```bash
# Boucle sur tous les MP3
for file in audio/*.mp3; do
    python app.py "$file"
done
```

---

## 🐛 Dépannage

### Erreur : "Modèle spaCy non trouvé"
```bash
python -m spacy download fr_core_news_md
```

### Erreur : "FFmpeg non trouvé"
- Installer FFmpeg (voir Installation)
- Vérifier que `ffmpeg` est dans le PATH

### Erreur : "Pas de GPU détecté"
```bash
python text.py  # Vérifier configuration
# Utiliser CPU en modifiant CONFIG['device'] = 'cpu'
```

### Vidéo lente à générer
- Réduire `font_size` dans CONFIG
- Augmenter `max_clip_workers` (si CPU disponible)
- Utiliser modèle Whisper plus petit (`tiny` au lieu de `small`)

---

## 📊 Performance

### Benchmarks (sur CPU)
| Opération | Durée | Notes |
|-----------|-------|-------|
| Transcription 5min | ~30s | Avec cache: <1s |
| Analyse NLP | ~5s | Batch processing |
| Création 100 clips | ~2min | Parallèle (4 workers) |
| Composition finale | ~3min | Dépend résolution |
| **Total** | **~5-6min** | Pour vidéo 5min |

### Avec GPU (CUDA)
- Transcription : **5-10x plus rapide**
- Composition : **2-3x plus rapide**

---

## 📝 Licence

Ce projet est fourni à titre personnel.

---

## 👤 Auteur

Créé par Michel - Projet personnel

---

## 🤝 Contribution

Les améliorations sont bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer des optimisations
- Ajouter de nouvelles fonctionnalités

---

## 📞 Support

Pour toute question ou problème :
1. Vérifier les logs (niveau INFO/ERROR)
2. Consulter la section Dépannage
3. Vérifier les fichiers de configuration

---

**Dernière mise à jour** : 17/11/2025
