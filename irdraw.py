import svgwrite
import json
from node import Node
import consts
from edge import Edge
import math


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
    def draw(area=area, node=node):
        rect = svgwrite.shapes.Rect(
            insert=(
                area["left"] + consts.FUNC_MARGIN,
                area["top"] + consts.FUNC_MARGIN,
            ),
            size=(
                area["width"] - consts.FUNC_MARGIN * 2,
                area["height"] - consts.FUNC_MARGIN * 2,
            ),
            rx=consts.FUNC_ROUND,
            ry=consts.FUNC_ROUND,
            fill=consts.FUNC_FILL if node.complex else consts.SIMPLE_FILL,
            stroke=consts.FUNC_STROKE,
            opacity=0.6 if node.complex else 1,
        )
        dwg.add(rect)

        node.place(area)
        for i_p in node.in_ports:
            i_p.draw(dwg)

        for o_p in node.out_ports:
            o_p.draw(dwg)
            if o_p.id in Edge.edge_to:
                edge = Edge.edge_to[o_p.id]
                if edge.from_.node != node:
                    nodes, _, _, _ = edge.from_.node.trace_back()
                    o_p.skip = False
                    for prev_o_p in node.out_ports:
                        if "output_node" in prev_o_p.__dict__ and edge.from_.node == prev_o_p.output_node:
                            o_p.num_nodes = 0
                            o_p.output_node = None
                            o_p.skip = True
                            continue
                    if not o_p.skip:
                        o_p.num_nodes = len(nodes)
                        o_p.output_node = edge.from_.node
                else:
                    o_p.output_node = None
                    o_p.num_nodes = 0
        dwg.add(
            dwg.text(
                text=(node.function_name if node.name == "Lambda" else node.name)
                + (f": {node.value}" if hasattr(node, "value") else ""),
                insert=(
                    area["left"] + consts.FUNC_MARGIN,
                    area["top"] + consts.FUNC_MARGIN + consts.FONT_HEIGHT*1.5,
                ),
                fill="black",
                font_size="15"
            )
        )
        dwg.add(
            dwg.text(
                text=node.id,
                insert=(
                    area["left"] + consts.FUNC_MARGIN,
                    area["top"] + consts.FUNC_MARGIN + consts.FONT_HEIGHT * 2.5,
                ),
                fill="black",
                font_size="10"
            )
        )

    # consider two cases : we have nodes, and hence no special isolated num_subnodes
    # or we only have special isolated node types like "Then" or "Else"
    if node.complex:
        draw()
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
                if o_p.output_node:
                    draw_compl_node(dwg, sub_area, o_p.output_node)
        else:
            singles = ["body", "init", "condition", "range_gen", "returns"]
            multis = ["branches"]

            num_subs = 0
            subnodes = []
            for s in singles:
                if s in node.__dict__:
                    num_subs += 1
                    subnodes += [node.__dict__[s]]

            for b in multis:
                if b in node.__dict__:
                    num_subs += len(node.__dict__[b])
                    subnodes += node.__dict__[b]

            if num_subs:
                sidex = math.ceil(math.sqrt(num_subs)) if num_subs > 2 else 1
                sidey = math.ceil(math.sqrt(num_subs)) if num_subs > 2 else num_subs
                width = area["width"] / sidex - consts.FUNC_MARGIN * 2
                height = (
                    area["height"] / sidey - consts.FUNC_MARGIN * 2 - consts.PORT_HEIGHT
                )
                for i, new_node in enumerate(subnodes):
                    left = (width) * (i % sidex) + consts.FUNC_MARGIN
                    top = (
                        height * int(i / sidex)
                        + consts.FUNC_MARGIN * 2
                        + consts.PORT_HEIGHT
                    )
                    new_area = dict(
                        left=area["left"] + left,
                        top=area["top"] + top,
                        width=width,
                        height=height,
                    )

                    draw_compl_node(dwg, new_area, new_node)
    else:
        # simple small nodes
        # here we place all small nodes
        nodes, _, _, height = node.trace_back()
        level_height = area["height"] / height
        draw(
            dict(
                left=area["left"] + consts.FUNC_MARGIN,
                top=area["height"] + area["top"] - level_height,
                width=area["width"] - consts.FUNC_MARGIN,
                height=level_height - consts.FUNC_MARGIN,
            ),
            node,
        )
        # numins = len(node.in_ports)
        sub_tree_size = node.in_chain_size()
        left = 0
        for i, i_p in enumerate(node.in_ports):
            in_node = Edge.edge_to[i_p.id].from_.node
            ip_subtree_size = (in_node.in_chain_size()) / (sub_tree_size)
            sub_tree_width = area["width"] * ip_subtree_size
            if not node.is_parent(in_node):
                draw_compl_node(
                    dwg,
                    dict(
                        left=area["left"] + left,
                        top=area["top"],
                        width=sub_tree_width,
                        height=area["height"] - level_height,
                    ),
                    in_node,
                )
            left += sub_tree_width

    #    draw(area, node)


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
    for e in Edge.edges:
        x1 = e.from_.pos_x + e.from_.width / 2
        y1 = e.from_.pos_y + e.from_.height / 2 + consts.PORT_HEIGHT / 2
        x2 = e.to.pos_x + e.to.width / 2
        y2 = e.to.pos_y + e.to.height / 2 - consts.PORT_HEIGHT / 2
        dwg.add(dwg.line((x1, y1), (x2, y2), stroke=svgwrite.rgb(10, 10, 16, "%")))
    dwg.save()
    print(f"Image {name} written.")


if __name__ == "__main__":
    # print("IR Draw utility renders Cloud Sisal IR's presented in JSON")
    area = dict(width=1000, height=1000)
    import sys

    input_file_name = sys.argv[1]

    # print(f"Reading IR file {input_file_name}.")
    with open(input_file_name, "r") as file_:
        data = python_names(json.load(file_))

    functions = [Node(func) for func in data["functions"]]
    file_name = "../test.svg"
    # print(f"Drawing.")
    ir_render_to_svg(functions, area, file_name)
