import re


color_names = {
    "white": "#ffffff",
    "black": "#000000",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "cyan": "#00ffff",
    "magenta": "#ff00ff",
    "silver": "#c0c0c0",
    "gray": "#808080",
    "maroon": "#800000",
    "olive": "#808000",
    "purple": "#800080",
    "teal": "#008080",
    "navy": "#000080",
    "orange": "#ffa500",
    "pink": "#ffc0cb",
    "brown": "#a52a2a",
    "gold": "#ffd700",
    "lime": "#00ff00",
    "indigo": "#4b0082",
    "violet": "#ee82ee",
    "khaki": "#f0e68c",
    "coral": "#ff7f50",
    "turquoise": "#40e0d0",
    "salmon": "#fa8072",
    "chocolate": "#d2691e",
    "plum": "#dda0dd",
    "orchid": "#da70d6",
    "tomato": "#ff6347",
    "tan": "#d2b48c",
    "lavender": "#e6e6fa",
    "beige": "#f5f5dc",
    "mistyrose": "#ffe4e1",
    "aquamarine": "#7fffd4",
    "snow": "#fffafa",
    "thistle": "#d8bfd8",
    "peru": "#cd853f",
    "seagreen": "#2e8b57",
    "steelblue": "#4682b4",
    "skyblue": "#87ceeb",
}


def is_hex_color(s: str) -> bool:
    return bool(re.match(r'^#([0-9a-fA-F]{3}){1,2}$', s))


def name_to_hex(color_name: str) -> str:
    if is_hex_color(color_name):
        return color_name
    try:
        return color_names[color_name.lower()]
    except KeyError:
        raise ValueError(f"Unknown color name: {color_name}")
