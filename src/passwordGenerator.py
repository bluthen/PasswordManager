import secrets
import string

SPECIAL_CHARS = [
    "~",
    "!",
    "@",
    "#",
    "$",
    "%",
    "^",
    "&",
    "*",
    "(",
    ")",
    "-",
    "+",
    "{",
    "}",
    "_",
    "=",
    "?",
    ",",
    ".",
    ":",
]
LOWERCASE_CHARS = list(string.ascii_lowercase)
UPPERCASE_CHARS = list(string.ascii_uppercase)
DIGIT_CHARS = list(string.digits)


def gen_alpha():
    return secrets.choice(LOWERCASE_CHARS)


def gen_special():
    return secrets.choice(SPECIAL_CHARS)


def gen_number():
    return secrets.choice(DIGIT_CHARS)


def gen_up_alpha():
    return secrets.choice(UPPERCASE_CHARS)


def generate_password(length=16):
    """Generate a cryptographically secure random password.

    Guarantees at least one lowercase, one uppercase, one number, and one special char,
    with minimum length of 16 characters by default.
    """
    if length < 8:
        length = 8

    password_chars = [
        gen_alpha(),
        gen_up_alpha(),
        gen_number(),
        gen_special(),
    ]

    all_chars = LOWERCASE_CHARS + UPPERCASE_CHARS + DIGIT_CHARS + SPECIAL_CHARS
    while len(password_chars) < length:
        password_chars.append(secrets.choice(all_chars))

    # Cryptographically secure shuffle using Fisher-Yates
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)
