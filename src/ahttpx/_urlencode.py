import re

__all__ = ["quote", "unquote", "urldecode", "urlencode"]


# Matchs a sequence of one or more '%xx' escapes.
PERCENT_ENCODED_REGEX = re.compile("(%[A-Fa-f0-9][A-Fa-f0-9])+")

# https://datatracker.ietf.org/doc/html/rfc3986#section-2.3
SAFE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"


def urlencode(multidict, safe=SAFE):
    pairs = []
    for key, values in multidict.items():
        pairs.extend([(key, value) for value in values])

    safe += "+"
    pairs = [(k.replace(" ", "+"), v.replace(" ", "+")) for k, v in pairs]

    return "&".join(
        f"{quote(key, safe)}={quote(val, safe)}"
        for key, val in pairs
    )


def urldecode(string):
    parts = [part.partition("=") for part in string.split("&") if part]
    pairs = [
        (unquote(key), unquote(val))
        for key, _, val in parts
    ]

    pairs = [(k.replace("+", " "), v.replace("+", " ")) for k, v in pairs]

    ret = {}
    for k, v in pairs:
        ret.setdefault(k, []).append(v)
    return ret


def quote(string, safe=SAFE):
    # Fast path if the string is already safe.
    if not string.strip(safe):
        return string

    # Replace any characters not in the safe set with '%xx' escape sequences.
    return "".join([
        char if char in safe else percent(char)
        for char in string
    ])


def unquote(string):
    # Fast path if the string is not quoted.
    if '%' not in string:
        return string

    # Unquote.
    parts = []
    current_position = 0
    for match in re.finditer(PERCENT_ENCODED_REGEX, string):
        start_position, end_position = match.start(), match.end()
        matched_text = match.group(0)
        # Include any text up to the '%xx' escape sequence.
        if start_position != current_position:
            leading_text = string[current_position:start_position]
            parts.append(leading_text)

        # Decode the '%xx' escape sequence.
        hex = matched_text.replace('%', '')
        decoded = bytes.fromhex(hex).decode('utf-8')
        parts.append(decoded)
        current_position = end_position

    # Include any text after the final '%xx' escape sequence.
    if current_position != len(string):
        trailing_text = string[current_position:]
        parts.append(trailing_text)

    return "".join(parts)


def percent(c):
    return ''.join(f"%{b:02X}" for b in c.encode("utf-8"))
