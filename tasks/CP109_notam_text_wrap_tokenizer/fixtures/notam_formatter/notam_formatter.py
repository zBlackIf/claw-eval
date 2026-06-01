"""
NOTAM E-Item Text Formatter - Tokenizer and Line Wrapper

This module provides text formatting for aviation NOTAM (Notice to Airmen) E-item
content. It must handle Chinese/English mixed text properly:

1. Tokenize text into atomic "word units":
   - CJK characters: each character is one token (width=2 in monospace)
   - English words: consecutive letters + connectors (-, ', /) between letters
     form a single indivisible unit (e.g., "VOR/DME", "co-ordinate", "don't")
   - Numbers: consecutive digits form one token
   - Punctuation: each punctuation character is its own token
   - Spaces: whitespace tokens (used for joining English words)
   - Newlines: '\n' characters are preserved as special tokens

2. Line wrapping:
   - Given a line_width threshold (in half-width character units),
     accumulate tokens on the current line
   - When adding the next token would exceed line_width, start a new line
   - When encountering a '\n' token, force a new line and reset width counter
   - CJK characters count as width 2, ASCII characters count as width 1

Requirements:
- Function `tokenize(text: str) -> list[str]`: split text into atomic tokens
- Function `char_width(ch: str) -> int`: return display width (2 for CJK, 1 otherwise)
- Function `token_width(token: str) -> int`: sum of char_width for each char
- Function `wrap_lines(text: str, line_width: int = 40) -> str`: full pipeline
  tokenize -> greedy wrap -> joined result string

Known Issues in Current Implementation:
- English words get split character-by-character (e.g., "available" -> "a","v","a",...)
- Connectors like / - ' between letters don't merge with adjacent words
- This causes ugly mid-word line breaks in English text
"""

import re
import unicodedata


def is_cjk(ch: str) -> bool:
    """Check if a character is CJK."""
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF) or
        (0x3400 <= cp <= 0x4DBF) or
        (0x20000 <= cp <= 0x2A6DF) or
        (0x2A700 <= cp <= 0x2B73F) or
        (0xF900 <= cp <= 0xFAFF)
    )


def char_width(ch: str) -> int:
    """Return display width of a single character."""
    if is_cjk(ch):
        return 2
    return 1


def token_width(token: str) -> int:
    """Return total display width of a token."""
    return sum(char_width(c) for c in token)


def tokenize(text: str) -> list:
    """
    Tokenize text into atomic word units.

    BUG: Current implementation splits English words character by character.
    TODO: Fix so that consecutive ASCII letters (and connectors like -, ', /
    between letters) form a single token.
    """
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]

        if ch == '\n':
            tokens.append('\n')
            i += 1

        elif ch.isspace():
            # collect consecutive whitespace (non-newline)
            j = i
            while j < len(text) and text[j].isspace() and text[j] != '\n':
                j += 1
            tokens.append(text[i:j])
            i = j

        elif is_cjk(ch):
            tokens.append(ch)
            i += 1

        elif ch.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            tokens.append(text[i:j])
            i = j

        elif ch.isalpha():
            # BUG: should collect entire word unit including connectors
            # Currently just takes one character at a time
            tokens.append(ch)
            i += 1

        else:
            # punctuation or other
            tokens.append(ch)
            i += 1

    return tokens


def wrap_lines(text: str, line_width: int = 40) -> str:
    """
    Wrap text at line_width boundary using tokenization.

    Algorithm:
    - Tokenize input text
    - Greedily accumulate tokens on current line
    - When next token would exceed line_width, emit newline
    - When token is '\n', emit newline and reset
    - Spaces at line boundaries are skipped (no leading/trailing spaces on lines)
    """
    tokens = tokenize(text)
    lines = []
    current_line = []
    current_width = 0

    for token in tokens:
        if token == '\n':
            lines.append(''.join(current_line))
            current_line = []
            current_width = 0
            continue

        tw = token_width(token)

        # skip leading space on a new line
        if current_width == 0 and token.isspace():
            continue

        if current_width + tw > line_width and current_width > 0:
            # need to wrap - but don't leave trailing space
            while current_line and current_line[-1].isspace():
                current_line.pop()
            lines.append(''.join(current_line))
            current_line = []
            current_width = 0
            # skip token if it's just whitespace
            if token.isspace():
                continue

        current_line.append(token)
        current_width += tw

    if current_line:
        lines.append(''.join(current_line))

    return '\n'.join(lines)


if __name__ == "__main__":
    # Quick test
    sample = "RWY 09L/27R CLSD FOR MAINT DLY 0800-1600.\nILS RWY 09L U/S频率已调整为108.9MHZ，请各航空器注意。"
    print(wrap_lines(sample, 40))
