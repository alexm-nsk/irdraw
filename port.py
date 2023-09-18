#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Port for code generator
"""

from itertools import count
import svgwrite
import consts


class Port:
    __ids__ = count()

    def __init__(self, node, type: dict, index, label, in_port: bool):
        self.node = node
        self.type = type
        self.index = index
        self.label = label
        self.id = next(Port.__ids__)
        self.value = None
        self.renamed = False  # set it to True when renamed
        self.in_port = in_port  # shows if is it an in-port

    def __repr__(self):
        return (
            f"Port<{self.node}, {self.index}, {self.label}"
            f", {self.type}, {self.value}>"
        )

    # drawing section:
    pos_x: float
    pos_y: float
    width: float = 10
    height: float = consts.PORT_HEIGHT

    def draw(self, dwg: svgwrite.Drawing):
        dwg.add(svgwrite.shapes.Rect(
            insert=(self.pos_x, self.pos_y),
            size=(self.width, self.height),
            rx=consts.FUNC_ROUND,
            ry=consts.FUNC_ROUND,
            fill=consts.INPORT_FILL if self.in_port else consts.OUTPORT_FILL,
            stroke="#111111"))
        dwg.add(
            dwg.text(text=self.label if self.label else "output",
                     insert=(self.pos_x + self.width/2,
                             self.pos_y + consts.PORT_MARGIN + consts.FONT_HEIGHT),
                     fill="black")
        )


def copy_port_values(src_ports, dst_ports):
    """Copy C++ values assigned to source ports to matching destination ports.
    Ex. If a new variable is defined in Init or LoopBody, we expect it to be
    available in Returns"""
    for d_p in dst_ports:
        try:
            d_p.value = next(s_p.value for s_p in src_ports if s_p.label == d_p.label)
        except:
            # print(d_p.label, d_p.node)
            # print(list(s_p.label for s_p in src_ports))
            # print()
            pass


def copy_port_values_explicit(src_ports, dst_ports):
    """Copy C++ values assigned to source ports to matching destination ports.
    Ex. If a new variable is defined in Init or LoopBody, we expect it to be
    available in Returns"""
    for index, (src, dst) in enumerate(zip(src_ports, dst_ports)):
        if src.label != dst.label:
            raise CodeGenError(
                f"mismatch between port labels: {src.id}"
                f" and {dst.id} {src.label} {dst.label} "
                f"{src.node} {dst.node}"
                f"port number {index}",
                src.type.location,
            )
        dst.value = src.value


def copy_port_labels(src_ports, dst_ports):
    for src, dst in zip(src_ports, dst_ports):
        dst.label = src.label
