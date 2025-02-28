from typing import Tuple, List, Dict
from .measurement_converter import MeasurementConverter
from .word_remover import WordRemover
from .abbreviation_processor import AbbreviationProcessor

class DescriptionProcessor:
    def __init__(self, abbreviations: Dict[str, str] = None):
        self.measurement_converter = MeasurementConverter()
        self.word_remover = WordRemover()
        self.abbreviation_processor = AbbreviationProcessor(abbreviations)

    def process_description(self, long_description: str) -> Tuple[str, int, List[str], int, List[str]]:
        """Process a description by converting measurements, removing words, and applying abbreviations."""
        # Step 1: Remove unwanted words and convert measurements
        cleaned_text, removed_words = self.word_remover.remove_unwanted_words(long_description)
        converted_text = self.measurement_converter.convert_text(cleaned_text)

        # Step 2: Apply abbreviations
        abbreviated_text, replaced_words, length_abbreviated = (
            self.abbreviation_processor.replace_with_abbreviations(converted_text)
        )

        # Step 3: Extract non-replaced words (excluding first word)
        words = abbreviated_text.split()
        remaining_text = ' '.join(words[1:]) if len(words) > 1 else ""
        un_abbreviated_words = self.abbreviation_processor.get_non_replaced_words(remaining_text)
        if un_abbreviated_words:
            un_abbreviated_words = self.word_remover.remove_measurements(un_abbreviated_words)

        # Filter out abbreviation values and empty strings
        abbreviation_values = set(self.abbreviation_processor.abbreviations.values())
        un_abbreviated_words = [w for w in un_abbreviated_words if w and w not in abbreviation_values]

        # Calculate length of removed words
        length_removed_words = sum(len(word) for word in removed_words)
        return abbreviated_text, length_abbreviated, removed_words, length_removed_words, un_abbreviated_words