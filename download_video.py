import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()

def download_video(url, output_path):
    """
    Télécharge une vidéo à partir de l'URL donnée et la sauvegarde à l'emplacement spécifié.
    """
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"Vidéo téléchargée : {output_path}")
    except Exception as e:
        print(f"Erreur lors du téléchargement de {url} : {e}")



def scrap(movie_title, year, size, from_idx, duration):
    """
    Récupère les clips d'un film via l'API.
    
    Args:
        movie_title (str): Titre du film
        year (str): Année du film
        size (int): Nombre de résultats par requête
        from_idx (int): Index de départ pour la pagination
        duration (str/int): Durée des clips
    
    Returns:
        dict: Données récupérées de l'API
    """
    api_key = os.getenv("API_KEY")
    api_url = os.getenv("BASE_URL")
    
    if not api_key:
        raise ValueError("API_KEY n'est pas définie dans les variables d'environnement.")
    if not api_url:
        raise ValueError("BASE_URL n'est pas définie dans les variables d'environnement.")
    
    all_hits = []
    current_from = from_idx
    
    while True:
        params = {
            "api_key": api_key,
            "movie_title": movie_title,
            "year": year,
            "duration": duration,
            "size": size,
            "from": current_from
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête API : {e}")
            break
        
        data = response.json()
        hits = data.get("hits", {}).get("hits", [])
        
        if not hits:
            break
        
        # Vérifie si tous les titres correspondent
        for item in hits:
            titre = item.get("_source", {}).get("movie_title", "")
            if titre.lower() != movie_title.lower():
                print(f"Titre inattendu trouvé : {titre}")
                return {"hits": {"hits": all_hits}}
        
        all_hits.extend(hits)
        
        if len(hits) < size:
            break  # Plus de pages à récupérer
        
        current_from += size
    
    return {"hits": {"hits": all_hits}}

def save_clipids(clipids, filename="resultat_api.json"):
    """
    Sauvegarde les clipids dans un fichier JSON.
    
    Args:
        clipids (list): Liste des clipids à sauvegarder
        filename (str): Nom du fichier de sortie
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(clipids, f, ensure_ascii=False, indent=4)
        print(f"Les clipids ont été sauvegardés dans {filename}")
    except IOError as e:
        print(f"Erreur lors de la sauvegarde : {e}")

def get_user_input():
    """
    Récupère les paramètres de l'utilisateur de manière interactive.
    
    Returns:
        tuple: (films, size, duree, from_start)
    """
    # Nombre de films
    nb_films_input = input("Combien de films à traiter ? ").strip()
    if not nb_films_input.isdigit():
        print("Erreur : le nombre de films doit être un entier positif.")
        raise ValueError("Le nombre de films doit être un entier positif.")
    nb_films = int(nb_films_input)
    if nb_films <= 0:
        print("Erreur : le nombre de films doit être strictement positif.")
        raise ValueError("Le nombre de films doit être strictement positif.")
    
    # Informations des films
    films = []
    for i in range(nb_films):
        while True:
            titre = input(f"Titre du film #{i+1} : ").strip()
            if titre:
                break
            print("Le titre ne peut pas être vide.")
        
        annee = input(f"Année du film #{i+1} : ").strip()
        films.append({"title": titre, "year": annee})
    
    # Taille des requêtes
    try:
        size_input = input("Nombre de vidéos par requête (size) ?").strip()
        size = int(size_input) if size_input else 50
        if size <= 0:
            raise ValueError("La taille doit être positive")
    except (ValueError, TypeError):
        print("Valeur invalide, utilisation de 50 par défaut.")
        size = 50
    
    # Durée
    duree_input = input("Durée (en secondes, 'all' pour >1s, ou toute chaîne ex: -2, 2-, 3-5) ? [3] ").strip()
    if duree_input == "":
        duree = "3"
    elif duree_input.lower() == "all":
        duree = "2-"
    else:
        duree = duree_input  # On prend la chaîne telle quelle, ex: -2, 2-, 3-5, etc.
    
    # Index de départ
    try:
        from_input = input("Index de départ pour la pagination (from) ? [0] ").strip()
        from_start = int(from_input) if from_input else 0
        if from_start < 0:
            raise ValueError("L'index ne peut pas être négatif")
    except (ValueError, TypeError):
        print("Valeur invalide, utilisation de 0 par défaut.")
        from_start = 0
    
    return films, size, duree, from_start

def process_films(films, size, duree, from_start):
    """
    Traite chaque film et récupère les clips.
    
    Args:
        films (list): Liste des films à traiter
        size (int): Taille des requêtes
        duree (str): Durée des clips
        from_start (int): Index de départ
    """
    for film in films:
        movie_title = film["title"]
        year = film["year"]
        all_clipids = []
        all_download_urls = []

        print(f"\nTraitement du film : {movie_title} ({year})")

        # Création du dossier pour le film (vidéos)
        safe_title = movie_title.replace(' ', '_')
        film_dir = os.path.join("videos", safe_title)
        os.makedirs(film_dir, exist_ok=True)
        # Création du dossier pour les clipids
        clipid_dir = os.path.join("clipID", safe_title)
        os.makedirs(clipid_dir, exist_ok=True)

        try:
            data = scrap(movie_title, year, size=size, from_idx=from_start, duration=duree)
            clips = data.get("hits", {}).get("hits", [])

            if not clips:
                print(f"Aucun clip trouvé pour {movie_title}.")
                continue

            for idx, clip in enumerate(clips):
                src = clip.get("_source", {})
                clipid = src.get("clipID")
                titre_clip = src.get("movie_title")
                download_url = src.get("download")

                # Vérification du titre
                if titre_clip and titre_clip.lower() != movie_title.lower():
                    print(f"Titre du film changé ({titre_clip}), arrêt de la récupération pour ce film.")
                    break

                if clipid:
                    all_clipids.append(clipid)
                if download_url:
                    all_download_urls.append(download_url)
                    print(f"Téléchargement depuis : {download_url}")
                    # Détection de l'extension
                    ext = "mp4"
                    url_path = download_url.split('?')[0]
                    if '.' in url_path:
                        ext_candidate = url_path.split('.')[-1]
                        if len(ext_candidate) <= 4:
                            ext = ext_candidate
                    output_name = os.path.join(film_dir, f"{safe_title}_{year}_clip_{idx+1}.{ext}")
                    download_video(download_url, output_name)

            print(f"Total clips récupérés pour {movie_title} : {len(all_clipids)}")

            # Sauvegarde des clipids dans le dossier clipID/film
            filename = os.path.join(clipid_dir, f"clipids_{safe_title}_{year}.json")
            save_clipids(all_clipids, filename)

        except Exception as e:
            print(f"Erreur lors du traitement du film {movie_title} : {e}")

def main():
    """
    Fonction principale du programme.
    """
    try:
        print("=== Scraper de clips de films ===")
        films, size, duree, from_start = get_user_input()
        process_films(films, size, duree, from_start)
        print("\nTraitement terminé.")
    except KeyboardInterrupt:
        print("\nProgramme interrompu par l'utilisateur.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")

if __name__ == "__main__":
    main()