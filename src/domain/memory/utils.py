import re


URL_PATTERN = re.compile(
    r"^https?://"  # Только HTTP/HTTPS
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # или IP
    r"(?::\d+)?"  # порт
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE | re.VERBOSE,
)
