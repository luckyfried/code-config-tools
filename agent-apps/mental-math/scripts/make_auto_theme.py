"""Writes site/themes/auto.css from the other three themes: slate's light tokens, chalk's dark tokens, and candy's
light and dark tokens for kid players. Run it after changing slate.css, chalk.css, or candy.css:

    python3 scripts/make_auto_theme.py
"""

import re
import sys
from pathlib import Path

THEMES = Path(__file__).resolve().parents[1] / "site" / "themes"
LIGHT = re.compile(r"^:root \{\n(.*?)^\}", re.S | re.M)
DARK = re.compile(r"@media \(prefers-color-scheme: dark\) \{\n  :root \{\n(.*?)^  \}", re.S | re.M)


def blocks(name):
    text = (THEMES / f"{name}.css").read_text(encoding="utf-8")
    light, dark = LIGHT.search(text), DARK.search(text)
    if not light or not dark:
        sys.exit(f"{name}.css needs a :root block and a dark :root block in the form the other themes use.")
    return light.group(1), dark.group(1)


def main():
    slate, _ = blocks("slate")
    _, chalk = blocks("chalk")
    candy_light, candy_dark = blocks("candy")
    text = (
        "/* auto: slate by day, chalk at night, and candy for kid players in both. Tokens only. */\n"
        f":root {{\n{slate}}}\n\n"
        f"@media (prefers-color-scheme: dark) {{\n  :root {{\n{chalk}  }}\n}}\n\n"
        f":root[data-kid] {{\n{candy_light}}}\n\n"
        f"@media (prefers-color-scheme: dark) {{\n  :root[data-kid] {{\n{candy_dark}  }}\n}}\n"
    )
    (THEMES / "auto.css").write_text(text, encoding="utf-8")
    print("Wrote site/themes/auto.css.")


if __name__ == "__main__":
    main()
