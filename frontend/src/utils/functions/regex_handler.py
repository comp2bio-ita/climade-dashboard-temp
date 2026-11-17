import re

def match_country(text: str):
    match = re.match(r"^(.*?):", text)
    if match:
        result = match.group(1)
        return result
    return None
