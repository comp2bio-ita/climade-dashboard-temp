import re

class RegexHandler:
    def __init__(self):
        self.accession_pattern = r'^\d+(?=\.)'
        self.accession_version_pattern = r'^(\d+)\.(\d+)(.*)'

    def get_accession_without_version(self, value: str) -> str:
        match = re.search(self.accession_pattern, value)
        return match.group(0) if match else None

    def get_accession_and_version(self, value: str) -> tuple[str, str]:
        match = re.search(self.accession_version_pattern, value)
        return (match.group(1), match.group(2)) if match else None
    

    def match_country(self, text: str):

        if not text:
            return None

        match = re.match(r"^(.*?):", text)

        if match:
            result = match.group(1)
            return result
        
        return text

