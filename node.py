#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
code generator node (mostly deserealizing code)
"""
from port import Port

from edge import Edge
import consts


def get_node(node_id):
    return Node.node_index[node_id]


classes = {
    "Lambda",
    "If",
    "Else",
    "ElseIf",
    "Then",
    "Branch",
    "Condition",
    "Binary",
    "Unary",
    "FunctionCall",
    "Literal",
    "LoopExpression",
    "Init",
    "PreCondition",
    "PostCondition",
    "Body",
    "Returns",
    "OldValue",
    "Reduction",
    "ArrayAccess",
    "BuiltInFunctionCall",
    "Let",
    "RangeGen",
    "Range",
    "Scatter",
    "ArrayInit",
    "RecordInit",
    "RecordAccess",
}


class Node:
    node_index = {}
    needs_init = False

    def name_child_ports(self):
        # label child nodes' output ports:
        for o_p in self.out_ports:
            src_port = Edge.edge_to[o_p.id].from_
            # make sure it's not input value
            # which must be determined by now:
            if not src_port.in_port:
                src_port.label = o_p.label
                # mark port as renamed, so it can pick
                # appropriate name for it's variable:
                src_port.renamed = True

    @staticmethod
    def get_node(node_id):
        return Node.node_index[node_id]

    def get_node_paragma_group(node):
        if not hasattr(node, "pragma_group"):
            return [node]

        return [
            n
            for _, n in Node.node_index.items()
            if hasattr(n, "pragma_group") and n.pragma_group == node.pragma_group
        ]

    def get_group(group_index):
        return [
            node
            for _, node in Node.node_index.items()
            if hasattr(node, "pragma_group") and node.pragma_group == group_index
        ]

    def get_parent_node(self):
        for name, node in Node.node_index.items():
            if hasattr(node, "nodes") and self in node.nodes:
                return node

            if hasattr(node, "branches"):
                for br in node.branches:
                    if hasattr(br, "nodes") and self in br.nodes:
                        return br

            for sub_node in ["init", "body", "condition", "range_gen", "returns"]:
                if (
                    hasattr(node, sub_node)
                    and hasattr(node.__dict__[sub_node], "nodes")
                    and self in node.__dict__[sub_node].nodes
                ):
                    return sub_node

        return None

    def get_containing_function(self):
        parent = self.get_parent_node()
        while True:
            new_parent = parent.get_parent_node()
            if not new_parent:
                if parent.name == "Lambda":
                    return parent
                else:
                    raise Exception("IR error: top node isn't a function.")
            else:
                parent = new_parent

    @staticmethod
    def parse_port(port, in_port):
        return Port(
            Node.get_node(port["node_id"]),
            port["type"],  # chooses an appropriate class
            port["index"],
            port["label"] if "label" in port else None,
            in_port,
        )

    def parse_ports(self, in_ports, out_ports):
        if in_ports:
            self.in_ports = [self.parse_port(port, in_port=True) for port in in_ports]
        else:
            self.in_ports = []

        if out_ports:
            self.out_ports = [
                self.parse_port(port, in_port=False) for port in out_ports
            ]
        else:
            self.out_ports = []

    def is_parent(self, compared_node):
        if self == compared_node:
            return True
        if "nodes" not in compared_node.__dict__:
            return False
        if self in compared_node.nodes:
            return True
        return False

    def parse_edges(self, edges):
        self.edges = []
        for edge in edges:
            if "from" in edge and "to" in edge:
                src_index = edge["from"][1]
                dst_index = edge["to"][1]

                src_node = self.node_index[edge["from"][0]]
                dst_node = self.node_index[edge["to"][0]]

                from_type = "in" if dst_node.is_parent(src_node) else "out"
                to_type = "out" if src_node.is_parent(dst_node) else "in"
                from_ = src_node.__dict__[from_type + "_ports"][src_index]
                to = dst_node.__dict__[to_type + "_ports"][dst_index]

            else:
                # sisal-cl IRs:
                src_index = edge[0]["index"]
                dst_index = edge[1]["index"]

                src_node = self.node_index[edge[0]["node_id"]]
                dst_node = self.node_index[edge[1]["node_id"]]

                from_type = "in" if dst_node.is_parent(src_node) else "out"
                to_type = "out" if src_node.is_parent(dst_node) else "in"

                from_ = src_node.__dict__[from_type + "_ports"][src_index]
                to = dst_node.__dict__[to_type + "_ports"][dst_index]

            self.edges.append(Edge(from_, to))

    def get_pragma(self, name):
        if hasattr(self, "pragmas"):
            for p in self.pragmas:
                if p["name"] == name:
                    return p
        return None

    def remove_pragma(self, name):
        if hasattr(self, "pragmas"):
            for p in self.pragmas:
                if p["name"] == name:
                    self.pragmas.remove(p)
        return None

    def read_data(self, data):
        if "dont_register" not in data or not data["dont_register"]:
            Node.node_index[data["id"]] = self
        self.location = data["location"] if "location" in data else None
        self.id = data["id"]
        self.name = data["name"]
        self.parse_ports(
            data["in_ports"] if "in_ports" in data else None,
            data["out_ports"] if "out_ports" in data else None,
        )

        if "nodes" in data:
            self.nodes = [Node(node) for node in data["nodes"]]

        if "branches" in data:
            self.branches = [Node(br) for br in data["branches"]]

        # sisal-cl IRs only:
        if "results" in data:
            for index, result in enumerate(data["results"]):
                self.out_ports[index].label = result[0]

        # sisal-cl IRs only:
        if "params" in data:
            for index, result in enumerate(data["params"]):
                self.in_ports[index].label = result[0]

        if self.name == "Let":
            from .ast_.let import LetBody

            self.body = LetBody(data["body"])
            del data["body"]

        for field, value in data.items():
            if isinstance(value, dict):
                if "name" in value and value["name"] in classes:
                    self.__dict__[field] = Node(value)
            elif field in [
                "value",
                "operator",
                "function_name",
                "callee",
                "field",
                "pragmas",
                "pragma_group",
                "port_to_name_index",
            ]:
                self.__dict__[field] = value

        if "edges" in data:
            self.parse_edges(data["edges"])

    def __new__(cls, data):
        return object.__new__(cls)

    def __init__(self, data):
        self.read_data(data)

    @property
    def complex(self):
        any_ = any(
            [
                (field in self.__dict__)
                for field in (Node.subnodes_fields + ["branches"])
            ]
        )
        return ("nodes" in self.__dict__ and self.nodes != []) == True or any_

    def trace_back(self):
        """Finds all chains nodes leading to this node's inputs.
        Returns the Nodes and all involved Edges.
        """
        internal_edges = []
        input_edges = []
        nodes = [self]

        for i_p in self.in_ports:
            input_edge = Edge.edge_to[i_p.id]
            from_ = input_edge.from_
            if not from_.in_port:
                new_nodes, new_edges, new_input_edges = from_.node.trace_back()
                nodes.extend(new_nodes)
                internal_edges.extend(new_edges)
                input_edges.extend(new_input_edges)
                internal_edges.append(input_edge)
            else:
                input_edges.append(input_edge)

        return nodes, internal_edges, input_edges

    subnodes_fields = ["body", "init", "condition", "range_gen", "returns"]

    def num_subnodes(self):
        num_subnodes = 0
        for s_n in self.subnodes_fields:
            if s_n in self.__dict__:
                num_subnodes += 1 + self.__dict__[s_n].num_subnodes()

        for s_n in ["nodes", "branches"]:
            if s_n in self.__dict__:
                for subnode in self.__dict__[s_n]:
                    num_subnodes += 1 + subnode.num_subnodes()

        return num_subnodes

    # drawing section:
    pos_x: float
    pos_y: float
    width: float
    height: float

    def place(self, area: dict):
        num_ins = len(self.in_ports)
        port_width = 0.8 * area["width"] / (num_ins)
        left = area["width"] / 2 - (
            ((port_width + consts.PORT_MARGIN * 2) * num_ins) / 2
        )
        for i, i_p in enumerate(self.in_ports):
            i_p.pos_x = left + i * port_width + area["left"] + consts.FUNC_MARGIN
            i_p.pos_y = consts.FUNC_MARGIN + consts.PORT_MARGIN
            i_p.width = port_width

        num_outs = len(self.out_ports)
        port_width = 0.8 * area["width"] / (num_outs)
        left = area["width"] / 2 - (
            ((port_width + consts.PORT_MARGIN * 2) * num_outs) / 2
        )

        for i, o_p in enumerate(self.out_ports):
            o_p.pos_x = left + i * port_width + area["left"] + consts.FUNC_MARGIN
            o_p.pos_y = (
                area["height"] - o_p.height - consts.FUNC_MARGIN - consts.PORT_MARGIN
            )
            o_p.width = port_width
