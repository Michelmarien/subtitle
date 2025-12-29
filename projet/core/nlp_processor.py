import logging
import spacy
from typing import List, Set, Dict, Optional
from collections import defaultdict
from functools import lru_cache

logger = logging.getLogger(__name__)


# Mapping langues -> modèles spaCy
SPACY_MODELS = {
    "fr": "fr_core_news_md",      # Français
    "en": "en_core_web_md",       # Anglais (medium, pas transformer)
    "es": "es_core_news_md",      # Espagnol
    "de": "de_core_news_md",      # Allemand
    "it": "it_core_news_md",      # Italien
    "pt": "pt_core_news_md",      # Portugais
}


class OptimizedNLPProcessor:
    """
    Processeur NLP optimisé pour détection de mots d'impact
    
    Optimisations :
    - Cache LRU pour résultats
    - Traitement par batch
    - Désactivation pipes inutiles
    - Détection règles + NLP hybride
    """
    
    def __init__(self, language: str = "en"):
        """
        Args:
            language: Code langue ISO 639-1 ('en', 'fr', etc.)
        """
        self.language = language
        self.nlp = None
        self.model_name = SPACY_MODELS.get(language, "en_core_web_md")
        
        # Catégories de mots d'impact (approche hybride)
        self.impact_categories = {
            'emotion_strong': {
                'en': {'love', 'hate', 'fear', 'joy', 'anger', 'passion', 'dream'},
                'fr': {'amour', 'haine', 'peur', 'joie', 'colère', 'passion', 'rêve'},
            },
            'imperative': {
                'en': {'stop', 'never', 'always', 'must', 'should', 'can', 'will'},
                'fr': {'arrête', 'jamais', 'toujours', 'dois', 'faut', 'peux', 'vais'},
            },
            'intensifiers': {
                'en': {'very', 'extremely', 'absolutely', 'completely', 'totally'},
                'fr': {'très', 'extrêmement', 'absolument', 'complètement', 'totalement'},
            }
        }
    
    def load_model(self) -> bool:
        """
        Charge le modèle spaCy optimisé
        
        Returns:
            True si chargement réussi
        """
        if self.nlp is not None:
            logger.info("✅ Modèle NLP déjà chargé")
            return True
        
        try:
            logger.info(f"🧠 Chargement modèle spaCy: {self.model_name}")
            
            self.nlp = spacy.load(self.model_name)
            
            # OPTIMISATION: Désactiver pipes inutiles
            pipes_to_disable = ['ner', 'parser']  # Garde seulement tagger, lemmatizer
            
            for pipe in pipes_to_disable:
                if pipe in self.nlp.pipe_names:
                    self.nlp.disable_pipe(pipe)
                    logger.debug(f"   Pipe désactivé: {pipe}")
            
            logger.info(f"✅ Modèle chargé | Pipes actifs: {self.nlp.pipe_names}")
            
            return True
        
        except OSError:
            logger.error(f"❌ Modèle '{self.model_name}' non trouvé")
            logger.info(f"   Installation: python -m spacy download {self.model_name}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Erreur chargement NLP: {e}")
            return False
    
    @lru_cache(maxsize=1000)
    def _is_impact_word_cached(self, word: str, pos: str) -> bool:
        """
        Version cachée de la détection (évite recalculs)
        
        Args:
            word: Mot en minuscule
            pos: Part-of-speech tag
            
        Returns:
            True si mot d'impact
        """
        # Vérifier dans les catégories prédéfinies
        for category, lang_words in self.impact_categories.items():
            words_set = lang_words.get(self.language, set())
            if word in words_set:
                return True
        
        # Détection par POS tag (catégories grammaticales importantes)
        impact_pos = {'VERB', 'ADJ', 'ADV', 'PROPN'}  # Verbes, adjectifs, adverbes, noms propres
        
        if pos in impact_pos:
            # Filtre supplémentaire: mots longs souvent plus importants
            if len(word) >= 6:
                return True
        
        return False
    
    def detect_impact_words_single(self, text: str) -> List[str]:
        """
        Détecte les mots d'impact dans un texte unique
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des mots d'impact détectés
        """
        if not self.nlp:
            logger.warning("⚠️ Modèle NLP non chargé")
            return []
        
        doc = self.nlp(text)
        impact_words = []
        
        for token in doc:
            word_lower = token.text.lower()
            
            # Ignorer ponctuation et mots courts
            if token.is_punct or len(word_lower) < 3:
                continue
            
            if self._is_impact_word_cached(word_lower, token.pos_):
                impact_words.append(word_lower)
        
        return impact_words
    
    def detect_impact_words_batch(
        self,
        texts: List[str],
        batch_size: int = 50
    ) -> List[List[str]]:
        """
        Détecte les mots d'impact en batch (OPTIMISÉ)
        
        Args:
            texts: Liste de textes
            batch_size: Taille des batchs pour spaCy
            
        Returns:
            Liste de listes de mots d'impact (même ordre que texts)
        """
        if not self.nlp:
            logger.warning("⚠️ Modèle NLP non chargé")
            return [[] for _ in texts]
        
        all_impact_words = []
        
        # Traitement par batch (bien plus rapide)
        for doc in self.nlp.pipe(texts, batch_size=batch_size):
            doc_impact_words = []
            
            for token in doc:
                word_lower = token.text.lower()
                
                if token.is_punct or len(word_lower) < 3:
                    continue
                
                if self._is_impact_word_cached(word_lower, token.pos_):
                    doc_impact_words.append(word_lower)
            
            all_impact_words.append(doc_impact_words)
        
        return all_impact_words
    
    def get_cache_stats(self) -> Dict:
        """Retourne les stats du cache LRU"""
        cache_info = self._is_impact_word_cached.cache_info()
        
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'size': cache_info.currsize,
            'maxsize': cache_info.maxsize,
            'hit_rate': cache_info.hits / (cache_info.hits + cache_info.misses) 
                       if (cache_info.hits + cache_info.misses) > 0 else 0
        }
    
    def clear_cache(self):
        """Vide le cache"""
        self._is_impact_word_cached.cache_clear()
        logger.info("🧹 Cache NLP vidé")


# === FONCTION HELPER ===

def create_nlp_processor(language: str = "en") -> Optional[OptimizedNLPProcessor]:
    """
    Crée et charge un processeur NLP
    
    Args:
        language: Code langue
        
    Returns:
        ProcesseurNLP configuré ou None si échec
    """
    processor = OptimizedNLPProcessor(language)
    
    if processor.load_model():
        return processor
    else:
        return None
