import svgwrite
import json
from node import Node
import consts
from edge import Edge


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


def draw_compl_node(dwg, area, node: Node):
    rect = svgwrite.shapes.Rect(
        insert=(area["left"] + consts.FUNC_MARGIN, area["top"] + consts.FUNC_MARGIN),
        size=(
            area["width"] - consts.FUNC_MARGIN * 2,
            area["height"] - consts.FUNC_MARGIN * 2,
        ),
        rx=consts.FUNC_ROUND,
        ry=consts.FUNC_ROUND,
        fill=consts.FUNC_FILL,
        stroke=consts.FUNC_STROKE,
    )
    dwg.add(rect)

    node.place(area)
    for i_p in node.in_ports:
        i_p.draw(dwg)

    for o_p in node.out_ports:
        o_p.draw(dwg)
        if o_p.id in Edge.edge_to:
            edge = Edge.edge_to[o_p.id]
            nodes, _, _ = edge.from_.node.trace_back()
            o_p.num_nodes = len(nodes)
            o_p.output_node = edge.from_.node

    # consider two cases : we have nodes, and hence no special isolated num_subnodes
    # or we only have special isolated node types like "Then" or "Else"
    special = not ("nodes" in node.__dict__)
    # case #1
    if not special:
        total_nodes = sum([o_p.num_nodes for o_p in node.out_ports])
        left = area["left"]
        for o_p in node.out_ports:
            o_p.portion = o_p.num_nodes / total_nodes
            vert_offset = consts.FUNC_MARGIN * 2 + consts.PORT_HEIGHT
            sub_width = o_p.portion * area["width"] - consts.FUNC_MARGIN * 2
            sub_area = dict(
                left=left + consts.FUNC_MARGIN,
                top=area["top"] + vert_offset,
                width=sub_width,
                height=area["height"] - vert_offset * 2,
            )
            left += sub_width
            # print(sub_area)
            draw_compl_node(dwg, sub_area, o_p.output_node)

    dwg.add(
        dwg.text(
            text=node.function_name if node.name == "Lambda" else node.name,
            insert=(
                area["left"] + consts.FUNC_MARGIN,
                area["top"] + consts.FUNC_MARGIN + consts.FONT_HEIGHT,
            ),
            fill="black",
        )
    )


def ir_render_to_svg(functions: list, area: dict, name: str) -> str:
    """converts an ir as python dict to an svg string"""
    image_width = area["width"]
    image_height = area["height"]

    dwg = svgwrite.Drawing(name, size=(image_width, image_height))

    for func in functions:
        func.num_subs = func.num_subnodes()
    total_subnodes = sum([func.num_subs for func in functions])

    left = 0
    for func in functions:
        function_width = image_width * (func.num_subs / total_subnodes)

        draw_compl_node(
            dwg, dict(left=left, top=0, width=function_width, height=image_height), func
        )
        left += function_width
    # dwg.add(dwg.line((0, 0), (10, 0), stroke=svgwrite.rgb(10, 10, 16, "%")))
    # dwg.add(dwg.text("Test", insert=(0, 5), fill="red"))
    dwg.save()
    print(f"Image {name} written.")


if __name__ == "__main__":
    # print("IR Draw utility renders Cloud Sisal IR's presented in JSON")
    area = dict(width=1920, height=1080)

    input_file_name = "ir.json"

    # print(f"Reading IR file {input_file_name}.")
    with open(input_file_name, "r") as file_:
        data = python_names(json.load(file_))

    functions = [Node(func) for func in data["functions"]]
    file_name = "../test.svg"
    # print(f"Drawing.")
    ir_render_to_svg(functions, area, file_name)
