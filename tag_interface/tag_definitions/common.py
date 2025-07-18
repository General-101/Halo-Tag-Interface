# ##### BEGIN MIT LICENSE BLOCK #####
#
# MIT License
#
# Copyright (c) 2025 Steven Garcia
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ##### END MIT LICENSE BLOCK #####

import os
import xml.etree.ElementTree as ET

from copy import deepcopy

DUMP_XML = True

def parse_all_xmls(base_dir):
    tag_group_defs = {}
    regolith_map = {}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".xml"):
                continue

            path = os.path.join(root, file)
            tree = ET.parse(path)
            root_elem = tree.getroot()
            for elem in root_elem.iter():
                reg_id = elem.attrib.get("regolithID")
                if reg_id:
                    regolith_map[reg_id] = elem

            if root_elem.tag == "TagGroup":
                name = root_elem.attrib.get("group")
                if name:
                    tag_group_defs[name] = root_elem

    return tag_group_defs, regolith_map

def safe_filename(group, tag_groups):
    tag_extention = tag_groups.get(group)
    return "%s.xml" % tag_extention

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "

        for child in elem:
            indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i + "  "

        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i

    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

def dump_merged_xml(merged_defs, output_dir, tag_extensions):
    os.makedirs(output_dir, exist_ok=True)
    for group, elem in merged_defs.items():

        indent(elem)
        tree = ET.ElementTree(elem)
        filename = safe_filename(group, tag_extensions)
        output_path = os.path.join(output_dir, filename)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            tree.write(f, encoding="unicode", xml_declaration=True)

def resolve_xrefs(elem, regolith_map):
    for child in list(elem):
        resolve_xrefs(child, regolith_map)
        if child.tag.endswith("XRef") and child.text:
            xref_key = child.text.strip()
            replacement = regolith_map.get(xref_key)
            if replacement is not None:
                idx = list(elem).index(child)
                elem.remove(child)
                new_node = deepcopy(replacement)
                elem.insert(idx, new_node)
                resolve_xrefs(new_node, regolith_map)

            else:
                print(f"Warning: Could not resolve XRef {xref_key}")

def unravel_arrays_in_xml(elem):
    for child in list(elem):
        unravel_arrays_in_xml(child)
        if child.tag == "Array" and "count" in child.attrib:
            count = int(child.attrib["count"])
            expanded_nodes = []
            for i in range(count):
                for grandchild in list(child):
                    clone = deepcopy(grandchild)
                    expanded_nodes.append(clone)

            idx = list(elem).index(child)
            elem.remove(child)
            for node in reversed(expanded_nodes):
                elem.insert(idx, node)

def merge_layouts(parent_layout, child_layout):
    parent_fieldsets = {fs.attrib.get("version"): fs for fs in parent_layout.findall("FieldSet")}
    child_fieldsets = {fs.attrib.get("version"): fs for fs in child_layout.findall("FieldSet")}
    parent_versions = [int(v) for v in parent_fieldsets if v and v.isdigit()]
    latest_parent_version = str(max(parent_versions)) if parent_versions else None
    for version, child_fs in child_fieldsets.items():
        parent_fs = parent_fieldsets.get(version)
        if parent_fs is None and latest_parent_version:
            parent_fs = parent_fieldsets.get(latest_parent_version)

        if parent_fs:
            for elem in reversed(list(parent_fs)):
                child_fs.insert(0, deepcopy(elem))

def merge_parent_tag(tag_name, tag_defs, merged_cache, tag_groups, tag_extensions):
    tag_elem = tag_defs.get(tag_name)
    if tag_elem is None:
        raise ValueError(f"Tag group {tag_name} not found.")

    parent_name = tag_elem.attrib.get("parent")
    merged_elem = deepcopy(tag_elem)
    if parent_name:
        parent_merged = merge_parent_tag(parent_name, tag_defs, merged_cache, tag_groups, tag_extensions)
        child_layout = merged_elem.find(".//Layout")
        parent_layout = parent_merged.find(".//Layout")
        if child_layout is not None and parent_layout is not None:
            merge_layouts(parent_layout, child_layout)

    merged_cache[tag_name] = merged_elem

    return merged_elem

def parse_field_set(parent_set, children_with_children, regolith_map):
    parent_node, field_names = parent_set
    unravel_arrays_in_xml(parent_node)
    resolve_xrefs(parent_node, regolith_map)
    next_children = []
    for field_node in parent_node:
        if "name" not in field_node.attrib or field_node.get("name").strip() == "":
            field_node.set("name", field_node.tag)

        field_name = field_node.get("name")
        index = 0
        while field_name in field_names:
            index += 1
            field_name = "%s_%s" % (field_node.get("name"), index)
        
        field_names.append(field_name)
        field_node.set("name", field_name)

        if field_node.tag == "Block" or field_node.tag == "Struct" or field_node.tag == "Array":
            next_children.append(field_node)

    for next_child in next_children:
        next_names = None
        if next_child.tag == "Struct":
            next_names = field_names
        children_with_children.append((next_child, next_names))


def initialize_definitions(parent_set, regolith_map):
    children_with_children = []
    parent_node, field_names = parent_set
    if parent_node.tag == "Array":
        parse_field_set(parent_set, children_with_children, regolith_map)

    else:
        for layout in parent_node:
            for field_set in reversed(layout):
                current_field_names = field_names
                if current_field_names is None:
                    current_field_names = []
                parse_field_set((field_set, current_field_names), children_with_children, regolith_map)

    for child_set in children_with_children:
        initialize_definitions(child_set, regolith_map)
