import re
from typing import Tuple, List, Dict
from docx import Document
import pandas as pd

class AbbreviationProcessor:
    def __init__(self, abbreviations: Dict[str, str] = None):
        self.abbreviations = abbreviations or {}
        self.pattern_cache = {}

    def load_from_doc(self, doc_file: str) -> None:
        """Load abbreviations from a Word document."""
        doc = Document(doc_file)
        for table in doc.tables:
            for row in table.rows:
                word = row.cells[0].text.strip()
                abbreviation = row.cells[1].text.strip()
                if word and abbreviation:
                    self.abbreviations[word] = abbreviation

    def load_from_excel(self, file_path: str) -> None:
        """Load abbreviations from an Excel file."""
        df = pd.read_excel(file_path)
        if 'DESCRIPTOR' not in df.columns or 'SHORT FORM' not in df.columns:
            raise ValueError("Excel must have 'DESCRIPTOR' and 'SHORT FORM' columns.")
        df = df[['DESCRIPTOR', 'SHORT FORM']].dropna().apply(lambda x: x.str.strip())
        self.abbreviations.update(dict(zip(df['DESCRIPTOR'], df['SHORT FORM'])))

    def replace_with_abbreviations(self, description: str) -> Tuple[str, Dict[str, str], int]:
        """Replace long descriptions with abbreviations, preserving the first word."""
        words = description.split()
        first_word = words[0] if words else ""
        remaining = ' '.join(words[1:]) if len(words) > 1 else ""
        replaced = {}

        sorted_keys = sorted(self.abbreviations.keys(), key=lambda x: -len(x.split()))
        for phrase in sorted_keys:
            if phrase in remaining:
                remaining = re.sub(rf'\b{phrase}\b', self.abbreviations[phrase], remaining)
                replaced[phrase] = self.abbreviations[phrase]

        remaining_words = remaining.split()
        abbreviated_words = [
            self.abbreviations.get(word, word) if word in self.abbreviations else word
            for word in remaining_words
        ]
        abbreviated_text = f"{first_word} {' '.join(abbreviated_words)}".strip()
        return abbreviated_text, replaced, len(abbreviated_text)

    def get_non_replaced_words(self, text: str) -> List[str]:
        """Identify words not replaced by abbreviations."""
        abbreviation_values = set(self.abbreviations.values())
        hash_key = hash(frozenset(self.abbreviations.items()))

        if hash_key not in self.pattern_cache:
            sorted_values = sorted(abbreviation_values, key=len, reverse=True)
            pattern_str = '|'.join(r'\b' + re.escape(v) + r'\b' for v in sorted_values if v)
            self.pattern_cache[hash_key] = re.compile(pattern_str) if pattern_str else None

        pattern = self.pattern_cache[hash_key]
        clean_text = pattern.sub('', text) if pattern else text
        words = clean_text.split()
        non_replaced = []

        for word in words:
            if word and word not in abbreviation_values:
                if any(char in word for char in ['/', '(', ')', '-', '_']):
                    parts = [p.strip() for p in re.split(r'[/\(\)\-_]', word) if p.strip()]
                    non_replaced.extend(p for p in parts if p and p not in abbreviation_values)
                else:
                    non_replaced.append(word)
        return non_replaced