import svgwrite
import json
from node import Node


def python_names(obj, fields=False):
    """Converts camelCase to snake_case in a dictionary
    fields is signalling that this sub dictionary is from a user defined
    type and we must leave the keys (names of *fields* unchanged)
    """
    import re

    new_object = {}

    def convert(value, fields=False):
        if isinstance(value, dict):
            return python_names(value, fields)
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    for key, value in obj.items():
        new_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower() if not fields else key
        new_object[new_key] = convert(value, key == "fields")

    return new_object


def get_piped_input():
    import sys

    """Checks if IR is provided via pipe"""
    input_text = ""
    input_text = "".join(sys.stdin)
    return input_text


def ir_render_to_svg(functions: list, area: dict) -> str:
    """converts an ir as python dict to an svg string"""
    image_width = area["width"]
    image_height = area["height"]

    dwg = svgwrite.Drawing("../test.svg", size=(image_width, image_height))
    dwg.add(dwg.line((0, 0), (10, 0), stroke=svgwrite.rgb(10, 10, 16, "%")))
    dwg.add(dwg.text("Test", insert=(0, 5), fill="red"))
    dwg.save()
    pass


if __name__ == "__main__":
    print("IR Draw utility renders Cloud Sisal IR's presented in JSON")
    area = dict(width=800, height=600)
    with open("ir.json", "r") as file_:
        data = python_names(json.load(file_))

    functions = [Node(func) for func in data["functions"]]
    ir_render_to_svg(functions, area)
