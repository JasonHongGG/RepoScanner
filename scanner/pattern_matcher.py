import re

class PatternMatcher:
    def __init__(self, patterns):
        self.patterns = patterns
        self.compiled_patterns = {name: re.compile(regex) for name, regex in patterns.items()}

    def scan_text(self, text, context_lines=2):
        matches = []
        for name, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                # Simple finding only for now. TODO: Add context.
                matches.append({
                    "type": name,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                })
        return matches
