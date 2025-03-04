import docx2txt
import openpyxl
from typing import Tuple, List, Dict
import re

class AbbreviationProcessor:
    __slots__ = ['abbreviations', 'pattern_cache']
    
    def __init__(self, abbreviations: Dict[str, str] = None):
        self.abbreviations = abbreviations or {}
        self.pattern_cache = {}

    def load_from_doc(self, doc_file: str) -> None:
        text = docx2txt.process(doc_file)
        for line in text.splitlines():
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            if len(parts) == 2:
                self.abbreviations[parts[0]] = parts[1]

    def load_from_excel(self, file_path: str) -> None:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        headers = [str(cell).strip() for cell in next(ws.rows)]
        if 'DESCRIPTOR' not in headers or 'SHORT FORM' not in headers:
            raise ValueError("Excel must have 'DESCRIPTOR' and 'SHORT FORM' columns.")
        descriptor_idx = headers.index('DESCRIPTOR')
        short_form_idx = headers.index('SHORT FORM')
        for row in ws.rows:
            word = str(row[descriptor_idx].value or "").strip()
            abbr = str(row[short_form_idx].value or "").strip()
            if word and abbr:
                self.abbreviations[word] = abbr
        wb.close()

    def replace_with_abbreviations(self, description: str) -> Tuple[str, Dict[str, str], int]:
        words = description.split()
        first_word = words[0] if words else ""
        remaining = ' '.join(words[1:]) if len(words) > 1 else ""
        replaced = {}
        hash_key = hash(frozenset(self.abbreviations.items()))
        if hash_key not in self.pattern_cache:
            sorted_keys = sorted(self.abbreviations.keys(), key=lambda x: -len(x.split()))
            pattern_str = '|'.join(r'\b' + re.escape(k) + r'\b' for k in sorted_keys)
            self.pattern_cache[hash_key] = re.compile(pattern_str)
        pattern = self.pattern_cache[hash_key]
        def replacer(match):
            phrase = match.group(0)
            replaced[phrase] = self.abbreviations[phrase]
            return self.abbreviations[phrase]
        abbreviated_remaining = pattern.sub(replacer, remaining)
        abbreviated_text = f"{first_word} {abbreviated_remaining}".strip()
        return abbreviated_text, replaced, len(abbreviated_text)

    def get_non_replaced_words(self, text: str) -> List[str]:
        hash_key = hash(frozenset(self.abbreviations.values()))
        if hash_key not in self.pattern_cache:
            abbr_values = sorted(self.abbreviations.values(), key=len, reverse=True)
            pattern_str = '|'.join(r'\b' + re.escape(v) + r'\b' for v in abbr_values if v)
            self.pattern_cache[hash_key] = re.compile(pattern_str) if pattern_str else None
        pattern = self.pattern_cache[hash_key]
        clean_text = pattern.sub('', text) if pattern else text
        words = re.split(r'[\s/\(\)\-_]+', clean_text)
        return [word for word in words if word and word not in self.abbreviations.values()]