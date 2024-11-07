import colorsys
from dataclasses import dataclass
from colors import name_to_hex
import argparse
import re


@dataclass
class HSL:
    hue: float
    saturation: float
    lightness: float

    def tuple(self):
        return (self.hue, self.saturation, self.lightness)

    def list(self):
        return [self.hue, self.saturation, self.lightness]

    def str(self):
        return f"{self.hue},{self.saturation},{self.lightness}"

    def __str__(self):
        return str(self.list())


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, li, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, li * 100


def hsl_to_hex(h: float, s: float, li: float) -> str:
    h /= 360
    s /= 100
    li /= 100
    r, g, b = colorsys.hls_to_rgb(h, li, s)
    return '#{:02x}{:02x}{:02x}'.format(
        int(r * 255), int(g * 255), int(b * 255)
    )


def adjust_value(value: float, delta: float) -> float:
    result = value + delta
    return max(0, min(1, result))


def adjust_hue(hue: float, value: float) -> float:
    result = (hue + value) % 360
    return result


def color_action(func, original: float, parameter: str) -> float:
    if parameter.startswith("="):
        return float(parameter.lstrip("="))
    elif parameter.startswith("+"):
        delta = float(parameter.lstrip("+"))
        return func(original, delta)
    elif parameter.startswith("-"):
        delta = float(parameter.lstrip("-"))
        return func(original, -delta)
    else:
        raise ValueError("Couldn't understand parameter")


def generate_color(
    hsl: HSL,
    parameters: dict | str,
    color_palette: dict[str, HSL] | None = None
) -> HSL:
    hue = hsl.hue
    saturation = hsl.saturation
    lightness = hsl.lightness
    if isinstance(parameters, str):
        if parameters.startswith("color::"):
            name = parameters.lstrip("color::").strip()
            hex_color = name_to_hex(name)
            return HSL(*hex_to_hsl(hex_color))
        elif parameters.startswith("link::") and color_palette:
            name = parameters.lstrip("link::").strip()
            color = color_palette.get(name)
            if not color:
                raise ValueError(f"Couldn't link color to {name}")
            return color
        else:
            raise ValueError("Couldn't understand parameter")
    elif isinstance(parameters, dict):
        if "h" in parameters:
            hue = color_action(adjust_hue, hue, parameters["h"])
        if "s" in parameters:
            saturation = color_action(
                adjust_value, saturation, parameters["s"]
            )
        if "l" in parameters:
            lightness = color_action(
                adjust_value, lightness, parameters["l"]
            )

    return HSL(hue, saturation, lightness)


def generate_palette(color: HSL, palette: dict[str, str | dict]):
    links: dict[str, str | dict] = {}
    generated: dict[str, HSL] = {}
    result: dict[str, HSL] = {}
    for key, value in palette.items():
        if isinstance(value, str) and value.startswith("link::"):
            links[key] = palette[key]
            continue

        generated[key] = generate_color(color, value, generated)

    for key, value in links.items():
        generated[key] = generate_color(color, value, generated)

    for _key, _value in generated.items():
        if not _key.startswith("$"):
            result[_key] = _value

    return result


def remove_whitespace(text: str) -> str:
    return text.replace(" ", "").replace("\n", "").replace("\t", "")


def strip_whitespace(text: str) -> str:
    return text.strip(" ").strip("\n").strip("\t")


def parse_palette(string: str):
    parsed: dict[str, dict | str] = {}

    try:
        code, format = string.split(">>>", 1)
    except ValueError:
        raise ValueError("Invalid palette format. Expected '>>>'.")

    code = remove_whitespace(code)
    code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)

    lines = code.split(";")
    for line in lines:
        if len(line.strip()) < 1:
            continue

        try:
            var, value = line.split(":", 1)
        except ValueError:
            raise ValueError(
                f"Invalid line format: '{line}'. Expected 'key: value'."
            )

        if value.startswith("{") and value.endswith("}"):
            inner_value = value[1:-1].split(",")
            parsed_dict = {}
            for x in inner_value:
                try:
                    key, val = x.split(":")
                    parsed_dict[key] = val
                except ValueError:
                    raise ValueError(
                        f"Invalid format in {x}, expected 'key:value'."
                    )
            parsed[var] = parsed_dict

        elif value.startswith("=>"):
            _inner_value = value.lstrip("=>")
            parsed[var] = f"link::{_inner_value}"

        else:
            parsed[var] = f"color::{value}"

    return parsed, format.lstrip(">>>").strip()


def generate_whitespaces():
    return {f"i{i+1}": ' '*(i+1) for i in range(8)}


def format_generated(generated: dict[str, HSL], format: str):
    for_pattern = re.compile(r'for\s*\((.*?)\)', re.DOTALL)

    result = format
    _for = ""

    match = re.search(for_pattern, format)

    if match:
        format_for = strip_whitespace(match.group(1))
        items = list(generated.items())

        for i, (key, value) in enumerate(items):
            hex = hsl_to_hex(*value.tuple())
            _for += format_for.format(
                key=key,
                hsl=value.str(),
                hex=hex,
                strip_hex=hex.strip(),
                newline="\n" if i < len(items) - 1 else "",
                **generate_whitespaces()
            )

        result = re.sub(for_pattern, _for, result)

    return result.strip()


class Compiler:
    @staticmethod
    def to_css(parsed: dict[str, dict[str, str] | str]):
        template = ":root {\n<here>\n}\n"
        main_vars = "--lvc-hue: 0deg;\n--lvc-sat: 0%;\n--lvc-light: 0%;\n"

        links: dict[str, str | dict] = {}
        generated: dict[str, str] = {}
        result: dict[str, str] = {}
        for key, value in parsed.items():
            if isinstance(value, str):
                if value.startswith("link::"):
                    links[key] = parsed[key]
                elif value.startswith("color::"):
                    name = value.lstrip("color::").strip()
                    hex_color = name_to_hex(name)
                    hsl = HSL(*hex_to_hsl(hex_color))
                    hue = round(hsl.hue)
                    saturation = round(hsl.saturation)
                    lightness = round(hsl.lightness)
                    generated[key] = (
                        f"hsl({hue}deg, {saturation}%, {lightness}%)"
                    )
            elif isinstance(value, dict):
                colors = {
                    "+h": "calc(var(--lvc-hue) + {}deg)",
                    "-h": "cal(var(--lvc-hue) - {}deg)",
                    "+s": "calc(var(--lvc-sat) + {}%)",
                    "-s": "cal(var(--lvc-sat) - {}%)",
                    "+l": "calc(var(--lvc-light) + {}%)",
                    "-l": "cal(var(--lvc-light) - {}%)",
                    "=h": "{}deg",  "=s": "{}%", "=l": "{}%",
                }
                indexes = {"h": 0, "s": 1, "l": 2}
                _parsed = [
                    "var(--lvc-hue)", "var(--lvc-sat)", "var(--lvc-light)"
                ]
                for _key, _value in value.items():
                    prefix, _name, __value = _value[0], _key, _value[1:]
                    _parsed[indexes[_name]] = (
                        colors[f"{prefix}{_name}"].format(__value)
                    )
                generated[key] = f"hsl({', '.join(_parsed)})"

        for key, value in links.items():
            if isinstance(value, str):
                name = value.lstrip("link::")
                generated[key] = f"var(--{name})"

        for _key, _value in generated.items():
            if not _key.startswith("$"):
                result[_key] = _value

        output = main_vars

        for _key, _value in generated.items():
            output += f"--{_key}: {_value};\n"

        return template.replace("<here>", output.strip()).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-F", type=str)
    parser.add_argument("--output", "-O", type=str, required=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hex", "-H", type=str)
    group.add_argument("--compile", "-C", type=str, choices=["css"])

    args = parser.parse_args()

    file = args.file
    output = args.output
    hex = args.hex
    compile = args.compile

    with open(file) as f:
        parsed, format = parse_palette(f.read())

    _output = ""
    if hex:
        hsl = HSL(*hex_to_hsl(hex))
        generated = generate_palette(hsl, parsed)
        _output = format_generated(generated, format)
    elif compile:
        func = getattr(Compiler(), f"to_{compile}")
        _output = func(parsed)

    if not output:
        print(_output)
    else:
        with open(output, 'w') as f:
            f.write(_output)


if __name__ == "__main__":
    main()