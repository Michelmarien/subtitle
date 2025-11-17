import subprocess
import sys
import os
import glob

def download_mp3(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
        url
    ]
    subprocess.run(command, check=True)
    # Trouver le fichier mp3 téléchargé
    mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
    if mp3_files:
        return mp3_files[0]
    else:
        return None

def main():
    # Demander l'URL à l'utilisateur si elle n'est pas fournie en argument
    if len(sys.argv) < 2:
        url = input("Veuillez entrer l'URL YouTube : ").strip()
        if not url:
            print("Erreur : aucune URL fournie.")
            sys.exit(1)
    else:
        url = sys.argv[1]
    
    print("Téléchargement de l'audio MP3...")
    mp3_path = download_mp3(url)
    if not mp3_path:
        print("Erreur : aucun fichier MP3 téléchargé.")
        sys.exit(1)
    print(f"Fichier audio téléchargé : {mp3_path}")

    # Transcription avec Whisper
    try:
        import whisper
    except ImportError:
        print("Le module 'whisper' n'est pas installé. Installez-le avec : pip install openai-whisper")
        sys.exit(1)

    print("Transcription avec Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(mp3_path, verbose=True)

    # Sauvegarder la transcription avec timecodes exacts dans un fichier JSON
    import json
    output_json = os.path.splitext(mp3_path)[0] + "_whisper.json"
    segments = result["segments"]
    data = []
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        data.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": text
        })
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Transcription Whisper enregistrée dans : {output_json}")
    print("Terminé.")

if __name__ == "__main__":
    main()