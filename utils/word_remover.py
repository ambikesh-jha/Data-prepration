import re
from typing import Tuple, List

class WordRemover:
    _PACKAGING_UNITS = r'PK|CA|BG|BX|BO|DZ|EA|RL|PR|SH|ST|KT|EACH|BOX|CASE'
    _MEASUREMENT_UNITS = r'CM|MM|IN|FT|MR|ML|MG|GR|KG|LT|OZ|YARD|YD|GALLON|GAL|GL|OUNCE|%'
    
    PACKAGING_PATTERN = re.compile(rf'\b\d*\s*(?:{_PACKAGING_UNITS})(?:/(?:{_PACKAGING_UNITS}))?\b', re.IGNORECASE)
    EXCLUDE_WORDS_PATTERN = re.compile(r'\b(?:LF|NS|STERILE)\b', re.IGNORECASE)
    MEASUREMENT_PATTERN = re.compile(
        rf'\(?\d+(?:\.\d+)?(?:X\d+(?:\.\d+)?)?(?:{_MEASUREMENT_UNITS})[^)\s]*\)?|\d+(?:\.\d+)?',
        re.IGNORECASE
    )
    SPECIAL_CHAR_PATTERN = re.compile(r'^[^\w\s]+$')

    def __init__(self):
        pass

    def remove_unwanted_words(self, text: str) -> Tuple[str, List[str]]:
        """Remove packaging terms and unwanted words in a single pass."""
        removed = []
        words = text.split(maxsplit=1)
        first_word = words[0] if words else ""
        rest_of_text = words[1] if len(words) > 1 else ""

        combined_pattern = re.compile(
            rf'(?P<packaging>{self.PACKAGING_PATTERN.pattern})|(?P<exclude>{self.EXCLUDE_WORDS_PATTERN.pattern})',
            re.IGNORECASE
        )
        
        def replacer(match):
            matched_text = match.group(0)
            removed.append(matched_text)
            return ""
        
        cleaned_rest = combined_pattern.sub(replacer, rest_of_text)
        cleaned_rest = re.sub(r'\s+', ' ', cleaned_rest).strip().rstrip('/')
        return f"{first_word} {cleaned_rest}".strip(), removed

    def remove_measurements(self, word_list: List[str]) -> List[str]:
        """Remove measurements, percentages, and standalone numbers efficiently."""
        return [
            word for word in (
                self.MEASUREMENT_PATTERN.sub('', w.replace('/', ' ').replace('-', '').rstrip('_')).strip()
                for w in word_list
            )
            if word and not self.SPECIAL_CHAR_PATTERN.match(word)
        ]