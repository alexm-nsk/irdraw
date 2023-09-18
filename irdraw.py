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
        new_object[new_key] = convert(value, key=="fields")

    return new_object


def get_piped_input():
    import sys

    """Checks if IR is provided via pipe"""
    input_text = ""
    input_text = "".join(sys.stdin)
    return input_text

def ir_render_to_svg(ir: dict) -> str:
    """converts an ir as python dict to an svg string"""
    dwg = svgwrite.Drawing('test.svg', profile='tiny')
    dwg.add(dwg.line((0, 0), (10, 0), stroke=svgwrite.rgb(10, 10, 16, '%')))
    dwg.add(dwg.text('Test', insert=(0, 0.2), fill='red'))
    dwg.save()
    pass


if __name__ == "__main__":
    print("IR Draw renders Cloud Sisal IR's presented in JSON")
    with open("ir.json", "r") as file_:
        data = python_names(json.load(file_))
    for func in data["functions"]:
        function = Node(func)
        #print(node.Node.read_data(
