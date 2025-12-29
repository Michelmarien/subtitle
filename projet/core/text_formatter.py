import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class TextSegment:
    """Représente un segment de texte avec métadonnées"""
    text: str
    start: float
    end: float
    duration: float
    words: List[Dict]
    emphasis_level: int  # 0=normal, 1=moyen, 2=fort
    
    @property
    def word_count(self):
        return len(self.words)
    
    @property
    def chars_per_second(self):
        return len(self.text) / self.duration if self.duration > 0 else 0


class IntelligentTextFormatter:
    """
    Formate intelligemment le texte en groupes optimisés
    avec détection automatique des mots d'emphase
    """
    
    def __init__(self, nlp_processor, config: Dict):
        """
        Args:
            nlp_processor: Instance de OptimizedNLPProcessor
            config: Configuration du formatage
        """
        self.nlp = nlp_processor
        self.config = config
        
        # Paramètres de groupement
        self.max_words_per_group = config.get('max_words_per_group', 4)
        self.max_chars_per_line = config.get('max_chars_per_line', 40)
        self.min_duration = config.get('min_segment_duration', 0.5)
        self.max_duration = config.get('max_segment_duration', 3.0)
        
    def format_transcription(self, transcription: Dict) -> List[TextSegment]:
        """
        Transforme la transcription brute en segments formatés
        
        Args:
            transcription: Résultat de Whisper avec word_timestamps
            
        Returns:
            Liste de TextSegment optimisés
        """
        segments = transcription.get('segments', [])
        
        if not segments:
            logger.warning("Aucun segment dans la transcription")
            return []
        
        logger.info(f"📝 Formatage de {len(segments)} segments...")
        
        all_formatted_segments = []
        
        for segment in segments:
            words = segment.get('words', [])
            
            if not words:
                continue
            
            # Analyser emphase de chaque mot
            words_with_emphasis = self._analyze_emphasis(words, segment['text'])
            
            # Grouper intelligemment
            grouped_segments = self._group_words_intelligently(words_with_emphasis)
            
            # Convertir en TextSegment
            for group in grouped_segments:
                text_segment = self._create_text_segment(group)
                if text_segment:
                    all_formatted_segments.append(text_segment)
        
        logger.info(f"✅ {len(all_formatted_segments)} segments formatés")
        
        return all_formatted_segments
    
    def _analyze_emphasis(self, words: List[Dict], segment_text: str) -> List[Dict]:
        """
        Détecte les mots nécessitant une emphase
        
        Args:
            words: Liste des mots avec timestamps
            segment_text: Texte complet du segment
            
        Returns:
            Liste de mots enrichis avec niveau d'emphase
        """
        # Utiliser le NLP processor pré-optimisé
        impact_words = self.nlp.detect_impact_words_batch([segment_text])[0]
        impact_words_set = set(impact_words)
        
        words_enriched = []
        
        for word_data in words:
            word_text = word_data['word'].strip().lower()
            
            # Déterminer niveau d'emphase
            emphasis = 0
            
            if word_text in impact_words_set:
                emphasis = 2  # Fort
            elif len(word_text) > 8:  # Mots longs souvent importants
                emphasis = 1  # Moyen
            
            words_enriched.append({
                **word_data,
                'emphasis': emphasis,
                'clean_word': word_text
            })
        
        return words_enriched
    
    def _group_words_intelligently(self, words: List[Dict]) -> List[List[Dict]]:
        """
        Groupe les mots de manière intelligente
        
        Critères :
        - Respect des pauses naturelles
        - Longueur optimale (3-4 mots)
        - Cohérence sémantique
        - Durée raisonnable
        """
        if not words:
            return []
        
        groups = []
        current_group = []
        current_chars = 0
        
        for i, word in enumerate(words):
            word_text = word['word'].strip()
            word_len = len(word_text)
            
            # Conditions de rupture de groupe
            should_break = (
                len(current_group) >= self.max_words_per_group or
                current_chars + word_len > self.max_chars_per_line or
                self._is_natural_break(word, words, i)
            )
            
            if should_break and current_group:
                groups.append(current_group)
                current_group = []
                current_chars = 0
            
            current_group.append(word)
            current_chars += word_len + 1  # +1 pour espace
        
        # Ajouter le dernier groupe
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _is_natural_break(self, word: Dict, all_words: List[Dict], index: int) -> bool:
        """Détecte une pause naturelle (ponctuation, pause longue)"""
        word_text = word['word'].strip()
        
        # Ponctuation forte
        if word_text[-1] in '.!?,;:':
            return True
        
        # Pause longue avant le mot suivant
        if index < len(all_words) - 1:
            next_word = all_words[index + 1]
            pause_duration = next_word['start'] - word['end']
            
            if pause_duration > 0.4:  # 400ms = pause significative
                return True
        
        return False
    
    def _create_text_segment(self, word_group: List[Dict]) -> Optional[TextSegment]:
        """Crée un TextSegment depuis un groupe de mots"""
        if not word_group:
            return None
        
        # Texte complet
        text = ' '.join([w['word'].strip() for w in word_group])
        
        # Timestamps
        start = word_group[0]['start']
        end = word_group[-1]['end']
        duration = end - start
        
        # Validation durée
        if duration < self.min_duration:
            logger.debug(f"Segment trop court ignoré: '{text}' ({duration:.2f}s)")
            return None
        
        # Niveau d'emphase maximal du groupe
        max_emphasis = max([w.get('emphasis', 0) for w in word_group])
        
        return TextSegment(
            text=text,
            start=start,
            end=end,
            duration=duration,
            words=word_group,
            emphasis_level=max_emphasis
        )


# === FONCTION HELPER ===

def format_transcription_to_segments(
    transcription: Dict,
    nlp_processor,
    config: Dict
) -> List[TextSegment]:
    """
    Fonction helper pour formater une transcription
    
    Usage:
        segments = format_transcription_to_segments(
            transcription,
            nlp_processor,
            {'max_words_per_group': 3, 'max_chars_per_line': 35}
        )
    """
    formatter = IntelligentTextFormatter(nlp_processor, config)
    return formatter.format_transcription(transcription)
