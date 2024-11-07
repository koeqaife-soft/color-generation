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

    @staticmethod
    def from_hex(hex):
        return HSL(*hex_to_hsl(hex))


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip('#')

    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])

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
    parameters: dict | str
) -> HSL:
    hue = hsl.hue
    saturation = hsl.saturation
    lightness = hsl.lightness
    if isinstance(parameters, str):
        if parameters.startswith("color::"):
            name = parameters.lstrip("color::").strip()
            hex_color = name_to_hex(name)
            return HSL.from_hex(hex_color)
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

        generated[key] = generate_color(color, value)

    for key, value in links.items():
        if isinstance(value, str):
            name = value.lstrip("link::")
            generated[key] = generated[name]

    for _key, _value in generated.items():
        if not _key.startswith("$"):
            result[_key] = _value

    return result


def remove_whitespace(text: str) -> str:
    return text.replace(" ", "").replace("\n", "").replace("\t", "")


def strip_whitespace(text: str) -> str:
    return text.strip(" ").strip("\n").strip("\t")


def is_number(string: str) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


def parse_palette(string: str):
    parsed: dict[str, dict | str] = {}

    try:
        code, format = string.split(">>>", 1)
    except ValueError:
        raise ValueError("Invalid palette format. Expected '>>>'.")

    code = re.sub(r'\/\/.*', '', code, re.MULTILINE).strip()
    code = remove_whitespace(code)

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

        var = var.strip()
        value = value.strip()

        if value.startswith("{") and value.endswith("}"):
            inner_value = value[1:-1].split(",")
            parsed_dict = {}
            for x in inner_value:
                x = x.strip()
                try:
                    key, val = x.split(":")
                except ValueError:
                    raise ValueError(
                        f"Invalid format in '{x}', expected 'key: value'."
                    )
                if not is_number(val[1:]):
                    raise ValueError(
                        f"The value '{val[1:]}' must be a number."
                    )
                key = key.strip()
                val = val.strip()
                parsed_dict[key] = val

            if value.count("{") != value.count("}"):
                raise ValueError(f"Unmatched curly braces in value: '{value}'")

            parsed[var] = parsed_dict

        elif value.startswith("=>"):
            _inner_value = value.lstrip("=>").strip()
            if not re.match(r'^[a-zA-Z0-9\-_\$]+$', _inner_value):
                raise ValueError(
                    f"Invalid link format: '{_inner_value}'. Only alphanumeric"
                    " characters, dashes, and underscores are allowed."
                )
            if _inner_value not in parsed:
                raise ValueError(f"Variable '{_inner_value}' not found")
            parsed[var] = f"link::{_inner_value}"

        else:
            if not re.match(r'^[#a-zA-Z0-9]+$', value):
                raise ValueError(
                    f"Invalid color format: '{value}'. Only hex codes and "
                    "alphanumeric colors are allowed."
                )
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
            hsl_css = f"{value.hue}deg,{value.saturation}%,{value.lightness}%"
            _for += format_for.format(
                key=key,
                hsl=value.str(),
                hsl_css=hsl_css,
                hex=hex,
                strip_hex=hex.strip(),
                newline="\n" if i < len(items) - 1 else "",
                **generate_whitespaces()
            )

        result = re.sub(for_pattern, _for, result)

    return result.strip()


@dataclass
class HSLFormat:
    hue: str = "{}deg"
    saturation: str = "{}%"
    lightness: str = "{}%"
    hsl: str = "hsl({h}, {s}, {l})"
    round: bool = True

    def format_value(self, value: float | int) -> float | int:
        return round(value) if self.round else value

    def format_full(self, hsl: HSL):
        format_value = self.format_value
        return self.hsl.format(
            h=self.hue.format(format_value(hsl.hue)),
            s=self.saturation.format(format_value(hsl.saturation)),
            l=self.lightness.format(format_value(hsl.lightness))
        )

    def format_hsl(self, value: dict[str, str] | list[str]):
        if isinstance(value, dict):
            return self.hsl.format(value, dict)
        elif isinstance(value, list):
            return self.hsl.format(
                h=value[0], s=value[1], l=value[2]
            )


class Compiler:
    @staticmethod
    def compile(
        parsed: dict[str, dict[str, str] | str],
        color_actions: dict[str, str],
        predefined_colors: dict[str, str],
        indexes: dict[str, int] = {"h": 0, "s": 1, "l": 2},
        pre_conf: list[str] = [],
        hsl_format: HSLFormat = HSLFormat(),
        var_format: str = "{}",
        output_var_format: str = "{key}:{value}\n",
        template: str = "<here>"
    ) -> str:
        generated: dict[str, str] = predefined_colors

        links: dict[str, str | dict] = {}
        result: dict[str, str] = {}
        for key, value in parsed.items():
            if isinstance(value, str):
                if value.startswith("link::"):
                    links[key] = parsed[key]
                elif value.startswith("color::"):
                    name = value.lstrip("color::")
                    hex_color = name_to_hex(name)
                    hsl = HSL.from_hex(hex_color)
                    generated[key] = hsl_format.format_full(hsl)
            elif isinstance(value, dict):
                colors = color_actions
                _parsed = pre_conf
                for _key, _value in value.items():
                    prefix, _name, __value = _value[0], _key, _value[1:]
                    _parsed[indexes[_name]] = (
                        colors[f"{prefix}{_name}"].format(__value)
                    )
                generated[key] = hsl_format.format_hsl(_parsed)

        for key, value in links.items():
            if isinstance(value, str):
                name = value.lstrip("link::")
                generated[key] = var_format.format(name)

        for _key, _value in generated.items():
            if not _key.startswith("$"):
                result[_key] = _value

        output = ""

        for _key, _value in generated.items():
            output += output_var_format.format(
                key=_key, value=_value
            )

        return template.replace("<here>", output)

    @staticmethod
    def to_css(parsed: dict[str, dict[str, str] | str]) -> str:
        template = ":root {<here>\n}\n"
        color_actions = {
            "+h": "calc(var(--lvc-h) + {}deg)",
            "-h": "calc(var(--lvc-h) - {}deg)",
            "+s": "calc(var(--lvc-s) + {}%)",
            "-s": "calc(var(--lvc-s) - {}%)",
            "+l": "calc(var(--lvc-l) + {}%)",
            "-l": "calc(var(--lvc-l) - {}%)",
            "=h": "{}deg",  "=s": "{}%", "=l": "{}%",
        }
        predefined_colors = {
            "lvc-h": "0deg",
            "lvc-s": "0%",
            "lvc-l": "0%"
        }
        indexes = {"h": 0, "s": 1, "l": 2}
        pre_conf = ["var(--lvc-h)", "var(--lvc-s)", "var(--lvc-l)"]
        var_format = "var(--{})"
        output_var_format = "\n  --{key}: {value};"

        return Compiler.compile(
            parsed, color_actions, predefined_colors, indexes,
            pre_conf, HSLFormat(), var_format, output_var_format,
            template
        )

    @staticmethod
    def to_scss(parsed: dict[str, dict[str, str] | str]) -> str:
        color_actions = {
            "+h": "$lvc-h + {}deg",
            "-h": "$lvc-h - {}deg",
            "+s": "$lvc-s + {}%",
            "-s": "$lvc-s - {}%",
            "+l": "$lvc-l + {}%",
            "-l": "$lvc-l - {}%",
            "=h": "{}deg",  "=s": "{}%", "=l": "{}%",
        }
        predefined_colors = {
            "lvc-h": "0deg",
            "lvc-s": "0%",
            "lvc-l": "0%"
        }
        indexes = {"h": 0, "s": 1, "l": 2}
        pre_conf = ["$lvc-h", "$lvc-s", "$lvc-l"]
        var_format = "${}"
        output_var_format = "${key}: {value};\n"

        return Compiler.compile(
            parsed, color_actions, predefined_colors, indexes,
            pre_conf, HSLFormat(), var_format, output_var_format
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-F", type=str)
    parser.add_argument("--output", "-O", type=str, required=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hex", "-H", type=str)
    group.add_argument("--compile", "-C", type=str, choices=["css", "scss"])

    args = parser.parse_args()

    file = args.file
    output = args.output
    hex = args.hex
    compile = args.compile

    with open(file) as f:
        parsed, format = parse_palette(f.read())

    _output = ""
    if hex:
        hsl = HSL.from_hex(hex)
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
