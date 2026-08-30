import re


def extract_keyword(text):
    if not text:
        return ''
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)
    for ch in ['"', "'", '`', '“', '”', '«', '»']:
        text = text.replace(ch, '')
    words = text.split()
    if not words:
        return ''
    first = words[0]
    first = first.strip('.,!?;:')
    return first.lower()
    