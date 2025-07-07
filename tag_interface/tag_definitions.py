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
import json
import tag_common
import xml.etree.ElementTree as ET

from copy import deepcopy

DUMP_XML = False

WHITELIST_TAGS = {"Angle", "AngleBounds", "ArgbColor", "Array", "Block", "ByteFlags", "CharBlockIndex",
    "CharEnum", "CharInteger", "CustomLongBlockIndex", "CustomShortBlockIndex", "Data",
    "LongBlockIndex", "LongEnum", "LongFlags", "LongInteger", "LongString", "OldStringId",
    "Pad", "Point2D", "Ptr", "Real", "RealArgbColor", "RealBounds", "RealEulerAngles2D",
    "RealEulerAngles3D", "RealFraction", "RealFractionBounds", "RealPlane2D", "RealPlane3D",
    "RealPoint2D", "RealPoint3D", "RealQuaternion", "RealRgbColor", "RealVector2D",
    "RealVector3D", "Rectangle2D", "RgbColor", "ShortBlockIndex", "ShortBounds", "ShortEnum",
    "ShortInteger", "Skip", "String", "StringId", "Struct", "Tag", "TagReference",
    "UselessPad", "VertexBuffer", "WordBlockFlags", "WordFlags"}

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
                name = root_elem.attrib.get("name")
                if name:
                    tag_group_defs[name] = root_elem

    return tag_group_defs, regolith_map

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

def merge_taggroup(tag_name, tag_defs, merged_cache, tag_groups, tag_extensions):
    if tag_name in merged_cache:
        return merged_cache[tag_name]

    tag_elem = tag_defs.get(tag_name)
    if tag_elem is None:
        raise ValueError(f"Tag group {tag_name} not found.")

    parent_name = tag_groups.get(tag_elem.attrib.get("parent"))
    merged_elem = deepcopy(tag_elem)
    if parent_name:
        parent_merged = merge_taggroup(parent_name, tag_defs, merged_cache, tag_groups, tag_extensions)
        child_layout = merged_elem.find(".//Layout")
        parent_layout = parent_merged.find(".//Layout")
        if child_layout is not None and parent_layout is not None:
            merge_layouts(parent_layout, child_layout)

    merged_cache[tag_name] = merged_elem

    return merged_elem

def safe_filename(group):
    return "%s.xml" % group

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
        filename = safe_filename(group)
        output_path = os.path.join(output_dir, filename)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            tree.write(f, encoding="unicode", xml_declaration=True)

def collect_flattened_fields(fieldset_element):
    collected = []
    for child in fieldset_element:
        if child.tag in {"Struct", "Array"}:
            layout = child.find("Layout")
            if layout is not None:
                for nested_fieldset in layout.findall("FieldSet"):
                    collected.extend(collect_flattened_fields(nested_fieldset))

        else:
            collected.append(child)

    return collected

def fix_fieldset_names(fieldsets):
    flattened_fieldsets = [collect_flattened_fields(fs) for fs in fieldsets]
    tag_type_counters = {}
    for fs_idx, fields in enumerate(flattened_fieldsets):
        type_instance_counters = {}
        seen_names = set()
        for node in fields:
            tag = node.tag
            current_name = node.get("name")
            if tag not in WHITELIST_TAGS:
                continue

            inst_idx = type_instance_counters.get(tag, 0)
            type_instance_counters[tag] = inst_idx + 1
            if current_name is None:
                fallback_name = None
                for prev_fields in flattened_fieldsets[:fs_idx]:
                    match_count = 0
                    for prev_node in prev_fields:
                        if prev_node.tag != tag:
                            continue

                        if match_count == inst_idx:
                            prev_name = prev_node.get("name")
                            if prev_name:
                                fallback_name = prev_name

                            break

                        match_count += 1

                    if fallback_name:
                        break

                if fallback_name:
                    new_name = fallback_name

                else:
                    fallback_count = tag_type_counters.get(tag, 0)
                    new_name = f"{tag}_{fallback_count}"
                    tag_type_counters[tag] = fallback_count + 1

                node.set("name", new_name)
                seen_names.add(new_name)

            else:
                if current_name in seen_names:
                    count = tag_type_counters.get(current_name, 1)
                    new_name = f"{current_name}_{count}"
                    node.set("name", new_name)
                    tag_type_counters[current_name] = count + 1
                    seen_names.add(new_name)

                else:
                    seen_names.add(current_name)

def fix_names_in_merged_taggroups(merged_cache, regolith_map):
    for merged in merged_cache.values():
        resolve_xrefs(merged, regolith_map)

    for merged in merged_cache.values():
        for elem in merged.iter():
            if elem.tag in {"TagGroup", "Block"}:
                layout = elem.find("Layout")
                if layout is not None:
                    fieldsets = layout.findall("FieldSet")
                    if fieldsets:
                        fix_fieldset_names(fieldsets)

def get_pad_size(field_node):
    return int(field_node.attrib.get('length', 0))

def calculate_field_size(field_node):
    tag = field_node.tag
    if tag in tag_common.pad_tags:
        return get_pad_size(field_node)

    return tag_common.field_sizes.get(tag, 0)

def calculate_fieldset_size(fieldset_node):
    total_size = 0
    for child in fieldset_node:
        count = int(child.attrib.get('count', '1'))
        tag = child.tag
        if tag == 'Struct':
            layout = child.find('Layout')
            if layout is not None:
                nested_fieldsets = layout.findall('FieldSet')
                for nested_fs in nested_fieldsets:
                    calculate_fieldset_size(nested_fs)
                    nested_size = int(nested_fs.attrib.get('sizeofValue', '0'))
                    total_size += nested_size * count

            else:
                pass

        else:
            field_size = calculate_field_size(child)
            total_size += field_size * count

    fieldset_node.attrib['sizeofValue'] = str(total_size)

def resolve_inherited_fields(struct_def, root_lookup):
    fields = []
    inherits_value = struct_def.get('inherits')
    if inherits_value:
        inherited_struct = root_lookup.get(inherits_value)
        if not inherited_struct:
            inherited_struct = next((v for k, v in root_lookup.items() if k.lower() == inherits_value.lower()), None)

        if inherited_struct:
            inherited_fields = resolve_inherited_fields(inherited_struct, root_lookup)
            fields.extend(inherited_fields)

        else:
            print(f"Warning: Could not resolve inherited struct '{inherits_value}'")

    fields.extend(struct_def.get('fields', []))

    return fields

def generate_h1_defs(base_dir, output_dir):
    all_data = []
    for filename in os.listdir(base_dir):
        if filename.endswith('.json'):
            with open(os.path.join(base_dir, filename), 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)

                except Exception as e:
                    print(f"Error in {filename}: {e}")

    root_lookup = {item['name']: item for item in all_data if isinstance(item, dict) and 'name' in item}
    generated_xmls = {}

    for group_entry in [item for item in all_data if item.get('type') == 'group']:
        name = group_entry['name']
        struct_name = group_entry['struct']
        version = str(group_entry.get('version', 0))
        fourcc = next((k for k, v in tag_common.h1_tag_groups.items() if v == name), "unknown")

        root = ET.Element('TagGroup', group=fourcc, name=name, version=version)
        layout = ET.SubElement(root, 'Layout')
        fieldset = ET.SubElement(layout, 'FieldSet', version="0", sizeofValue="0", sizeofSource=f"sizeof(struct {name}_group)", isLatest="true")

        struct_def = root_lookup.get(struct_name)
        if not struct_def:
            print(f"Missing struct definition for {struct_name}")
            continue

        def add_fields(fields, parent):
            for field in fields:
                if isinstance(field, str):
                    continue

                field_type = field.get('type')
                field_name = field.get('name') or field.get('heading') or field_type
                count = field.get('count', 1)
                if field_type == 'editor_section':
                    for _ in range(count):
                        node = ET.SubElement(parent, 'Explanation', name=field_name)
                        if "cache_only" in field:
                            node.set("cacheOnly", str(field["cache_only"]).lower())

                        if "endian_override" in field:
                            node.set("endianOverride", field["endian_override"])

                        desc = field.get('description')
                        if desc:
                            node.set('description', desc.replace('\n', '&#10;'))

                    continue

                if field_type == 'pad':
                    for _ in range(count):
                        node = ET.SubElement(parent, 'Pad', name=field_name)
                        if "cache_only" in field:
                            node.set("cacheOnly", str(field["cache_only"]).lower())

                        if "endian_override" in field:
                            node.set("endianOverride", field["endian_override"])

                        if 'size' in field:
                            node.set('length', str(field['size']))

                    continue

                if field_type == 'Reflexive':
                    for _ in range(count):
                        node = ET.SubElement(parent, 'Block', name=field_name)
                        if "cache_only" in field:
                            node.set("cacheOnly", str(field["cache_only"]).lower())

                        if "endian_override" in field:
                            node.set("endianOverride", field["endian_override"])

                        if 'limit' in field:
                            node.set('maxElementCount', str(field['limit']))

                        ref_struct_name = field.get('struct')
                        ref_struct = root_lookup.get(ref_struct_name)
                        if ref_struct:
                            inner_layout = ET.SubElement(node, 'Layout')
                            inner_fieldset = ET.SubElement(inner_layout, 'FieldSet', version="0", sizeofValue="0", isLatest="true")
                            ref_fields = resolve_inherited_fields(ref_struct, root_lookup)
                            add_fields(ref_fields, inner_fieldset)
                            calculate_fieldset_size(inner_fieldset)

                    continue

                if field_type == 'TagReference':
                    for _ in range(count):
                        node = ET.SubElement(parent, 'TagReference', name=field_name)
                        if "cache_only" in field:
                            node.set("cacheOnly", str(field["cache_only"]).lower())

                        if "endian_override" in field:
                            node.set("endianOverride", field["endian_override"])

                        c_style = field_name.replace(' ', '_').lower()
                        pascal_style = ''.join(w.capitalize() for w in field_name.split(' '))
                        node.set('CStyleName', c_style)
                        node.set('pascalStyleName', pascal_style)
                        groups = field.get('groups', [])
                        if len(groups) == 1:
                            tag = ET.SubElement(node, 'tag')
                            tag.text = groups[0]

                        elif len(groups) == 0:
                            ET.SubElement(node, 'tag')

                    continue

                if field.get("bounds", False):
                    for _ in range(count):
                        if field_type == "float":
                            key = "RealBounds"
                            xml_tag = tag_common.invader_key_conversion.get(key)
                            if not xml_tag:
                                print(f"Missing conversion for type: {key}")
                                continue

                            node = ET.SubElement(parent, xml_tag, name=field_name)
                            if "cache_only" in field:
                                node.set("cacheOnly", str(field["cache_only"]).lower())

                            if "endian_override" in field:
                                node.set("endianOverride", field["endian_override"])

                        elif field_type == "Angle":
                            key = "AngleBounds"
                            xml_tag = tag_common.invader_key_conversion.get(key)
                            if not xml_tag:
                                print(f"Missing conversion for type: {key}")
                                continue

                            node = ET.SubElement(parent, xml_tag, name=field_name)
                            if "cache_only" in field:
                                node.set("cacheOnly", str(field["cache_only"]).lower())

                            if "endian_override" in field:
                                node.set("endianOverride", field["endian_override"])

                        elif field_type == "int16":
                            key = "ShortBounds"
                            xml_tag = tag_common.invader_key_conversion.get(key)
                            if not xml_tag:
                                print(f"Missing conversion for type: {key}")
                                continue

                            node = ET.SubElement(parent, xml_tag, name=field_name)
                            if "cache_only" in field:
                                node.set("cacheOnly", str(field["cache_only"]).lower())

                            if "endian_override" in field:
                                node.set("endianOverride", field["endian_override"])

                        elif field_type in ("ColorRGBFloat", "ColorARGBFloat"):
                            key = field_type
                            xml_tag = tag_common.invader_key_conversion.get(key)
                            if not xml_tag:
                                print(f"Missing conversion for type: {key}")
                                continue

                            for suffix in [" lower bound", " upper bound"]:
                                node = ET.SubElement(parent, xml_tag, name=field_name + suffix)
                                if "cache_only" in field:
                                    node.set("cacheOnly", str(field["cache_only"]).lower())

                                if "endian_override" in field:
                                    node.set("endianOverride", field["endian_override"])
                    continue

                ref_struct = root_lookup.get(field_type)
                if ref_struct:
                    actual_type = ref_struct.get('type')
                    key = f"bitfield{ref_struct.get('width')}" if actual_type == 'bitfield' else actual_type
                    xml_tag = tag_common.invader_key_conversion.get(key)
                    if not xml_tag:
                        print(f"Missing conversion for type: {key}")
                        continue

                    for _ in range(count):
                        struct_node = ET.SubElement(parent, xml_tag, name=field_name)
                        if "cache_only" in field:
                            struct_node.set("cacheOnly", str(field["cache_only"]).lower())

                        if "endian_override" in field:
                            struct_node.set("endianOverride", field["endian_override"])

                        if xml_tag == 'Struct':
                            inner_layout = ET.SubElement(struct_node, 'Layout')
                            inner_fieldset = ET.SubElement(inner_layout, 'FieldSet', version="0", sizeofValue="0", isLatest="true")
                            ref_fields = resolve_inherited_fields(ref_struct, root_lookup)
                            add_fields(ref_fields, inner_fieldset)
                            calculate_fieldset_size(inner_fieldset)

                    continue

                key = f"bitfield{field.get('width')}" if field_type == 'bitfield' else field_type
                xml_tag = tag_common.invader_key_conversion.get(key)
                if not xml_tag:
                    print(f"Missing conversion for type: {key}")
                    continue

                for _ in range(count):
                    node = ET.SubElement(parent, xml_tag, name=field_name)
                    if "cache_only" in field:
                        node.set("cacheOnly", str(field["cache_only"]).lower())

                    if "endian_override" in field:
                        node.set("endianOverride", field["endian_override"])

                    if field_type in {"uint8", "uint16", "uint32"}:
                        node.set("unsigned", "true")

        resolved_fields = resolve_inherited_fields(struct_def, root_lookup)
        add_fields(resolved_fields, fieldset)
        calculate_fieldset_size(fieldset)

        generated_xmls[name] = root

    regolith_map = {}
    for elem in generated_xmls.values():
        for subelem in elem.iter():
            reg_id = subelem.attrib.get("regolithID")
            if reg_id:
                regolith_map[reg_id] = subelem

    merged_cache = {}
    for group in generated_xmls:
        merge_taggroup(group, generated_xmls, merged_cache, tag_common.h1_tag_groups, tag_common.h1_tag_extensions)

    fix_names_in_merged_taggroups(merged_cache, regolith_map)
    for merged in merged_cache.values():
        unravel_arrays_in_xml(merged)

    fix_names_in_merged_taggroups(merged_cache, regolith_map)
    if DUMP_XML:
        dump_merged_xml(merged_cache, output_dir, tag_common.h1_tag_extensions)

    return merged_cache

def generate_h2_defs(base_dir, output_dir):
    tag_defs, regolith_map = parse_all_xmls(base_dir)
    merged_cache = {}
    for tag_def in tag_defs:
        merged = merge_taggroup(tag_def, tag_defs, merged_cache, tag_common.h2_tag_groups, tag_common.h2_tag_extensions)

    fix_names_in_merged_taggroups(merged_cache, regolith_map)
    for merged in merged_cache.values():
        unravel_arrays_in_xml(merged)

    fix_names_in_merged_taggroups(merged_cache, regolith_map)
    if DUMP_XML:
        dump_merged_xml(merged_cache, output_dir, tag_common.h2_tag_extensions)

    return merged_cache
