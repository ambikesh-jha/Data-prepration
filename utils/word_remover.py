import re
from typing import Tuple, List

class WordRemover:
    def __init__(self):
        self.packaging_pattern = re.compile(
            r'\b\d*\s*(?:PK|CA|BG|BX|BO|DZ|EA|RL|PR|SH|ST|KT|EACH|BOX|CASE)(?:\/(?:PK|CA|BG|BX|BO|DZ|EA|RL|PR|SH|ST|KT|EACH|BOX|CASE))?\b',
            re.IGNORECASE
        )
        self.trailing_pattern = re.compile(r'\/(?:PK|CA|BG|BX|BO|DZ|EA|RL|PR|SH|ST|KT|EACH|BOX|CASE)\b', re.IGNORECASE)
        self.exclude_words_pattern = re.compile(r'\bLF\b|\bNS\b|\bSTERILE\b', re.IGNORECASE)
        self.measurement_pattern = re.compile(
            r'\(?\d+(\.\d+)?(X\d+(\.\d+)?)?(CM|MM|IN|FT|MR|ML|MG|GR|KG|LT|OZ|YARD|YD|GALLON|GAL|GL|OUNCE|%)[^)\s]*\)?|\d+(\.\d+)?',
            re.IGNORECASE
        )

    def remove_unwanted_words(self, text: str) -> Tuple[str, List[str]]:
        """Remove packaging terms and unwanted words, returning cleaned text and removed words."""
        removed = []
        words = text.split(maxsplit=1)
        first_word = words[0] if words else ""
        rest_of_text = words[1] if len(words) > 1 else ""

        # Find and remove unwanted words
        for pattern in [self.packaging_pattern, self.trailing_pattern, self.exclude_words_pattern]:
            matches = pattern.findall(rest_of_text)
            removed.extend(matches)
            rest_of_text = pattern.sub("", rest_of_text)

        # Clean up extra spaces and trailing slashes
        rest_of_text = re.sub(r'\s+', ' ', rest_of_text).strip().rstrip('/')
        return f"{first_word} {rest_of_text}".strip(), removed

    def remove_measurements(self, word_list: List[str]) -> List[str]:
        """Remove measurements, percentages, and standalone numbers from a list of words."""
        filtered_words = []
        for word in word_list:
            word = word.replace('/', ' ')
            cleaned_word = self.measurement_pattern.sub('', word).strip()
            cleaned_word = re.sub(r'^[^\w\s]+$', '', cleaned_word).strip()
            cleaned_word = cleaned_word.replace('-', '').rstrip('_')
            if cleaned_word:
                filtered_words.append(cleaned_word)
        return filtered_words