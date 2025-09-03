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
import xml.etree.ElementTree as ET

try:
    from .. import tag_common
except ImportError:
    import tag_common
    
from .common import initialize_definitions, parse_all_xmls, dump_merged_xml, merge_parent_tag, DUMP_XML

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

def generate_defs(base_dir, output_dir):
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

        generated_xmls[fourcc] = root

    regolith_map = {}
    for elem in generated_xmls.values():
        for subelem in elem.iter():
            reg_id = subelem.attrib.get("regolithID")
            if reg_id:
                regolith_map[reg_id] = subelem

    merged_cache = {}
    for group in generated_xmls:
        merge_parent_tag(group, generated_xmls, merged_cache, tag_common.h1_tag_groups, tag_common.h1_tag_extensions)

    for tag_def in merged_cache:
        initialize_definitions(merged_cache[tag_def], regolith_map)

    if DUMP_XML:
        dump_merged_xml(merged_cache, output_dir, tag_common.h1_tag_groups)

    return merged_cache
