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

import io
import base64
import struct
import xml.etree.ElementTree as ET

from math import copysign, radians
from enum import Flag, Enum, auto

class FunctionTypeEnum(Enum):
    identity = 0
    constant = auto()
    transition = auto()
    periodic = auto()
    linear = auto()
    linear_key = auto()
    multi_linear_key = auto()
    spline = auto()
    multi_spline = auto()
    exponent = auto()
    spline2 = auto()

class OutputTypeFlags(Flag):
    scalar_intensity = 0
    _range = 1
    constant = 16
    _2_color = 32
    _3_color = 48
    _4_color = 64

def restore_neg_zero(val):
    if val == "-0":
        val =  -0.0
    return val

def get_result(field_key, tag_block_fields):
    result = tag_block_fields.pop(field_key, 0)

    if isinstance(result, (list, tuple)):
        result = type(result)(restore_neg_zero(item) for item in result)
    else:
        result = restore_neg_zero(result)

    return result

def set_block_result(field_key, tag_block_fields):
    tag_block_fields[field_key] = []

def set_color_result(field_key, tag_block_fields, result, has_alpha=False):
    if has_alpha:
        A, R, G, B = result
        formatted_field = {"A": A,"R": R, "G": G, "B": B}
    else:
        R, G, B = result
        formatted_field = {"R": R, "G": G, "B": B}

    tag_block_fields[field_key] = formatted_field

def replace_neg_zero(val):
    if isinstance(val, float) and val == 0.0 and copysign(1.0, val) == -1.0:
        val = "-0"
    return val

def uppercase_struct_letters(struct_string):
    struct_letters = 'bhiqnl'
    result = []
    for char in struct_string:
        if char in struct_letters:
            result.append(char.upper())
        else:
            result.append(char)
    return ''.join(result)

def set_result(field_key, tag_block_fields, result):
    if isinstance(result, (list, tuple)):
        new_result = type(result)(replace_neg_zero(item) for item in result)
        tag_block_fields[field_key] = new_result
    else:
        tag_block_fields[field_key] = replace_neg_zero(result)

def read_real(function_stream, unsigned_key, field_key, tag_block_fields, endian_override):
    struct_string = '%sf' % endian_override
    if unsigned_key:
        struct_string = uppercase_struct_letters(struct_string)

    result = (struct.unpack(struct_string, function_stream.read(4)))[0]
    set_result(field_key, tag_block_fields, result)

def write_real(function_stream, struct_string, result):
    if result is not None:
        function_stream.write(struct.pack(struct_string, result))
    else:
        function_stream.write(struct.pack(struct_string, 0.0))

def upgrade_function(merged_defs, field_element, tag_block_fields, endian_override):
    field_set_0 = None
    field_set_1 = None
    for layout in tag_block_fields:
        for struct_field_set in layout:
            if int(struct_field_set.attrib.get('version')) == 0:
                field_set_0 = struct_field_set
            elif int(struct_field_set.attrib.get('version')) == 1:
                field_set_1 = struct_field_set

    function_type_result = 0
    flag_result = 0
    function_stream = io.BytesIO()
    for field_node_element in field_set_0:
        unsigned_key = field_node_element.get("unsigned")
        field_endian = field_node_element.get("endianOverride")
        if field_endian:
            endian_override = field_endian

        field_key = field_node_element.get("name")
        field_tag = field_node_element.tag
        if field_tag == "RgbColor":
            struct_string = '%s4B' % endian_override
            result = get_result(field_key, field_element)
            color_pad_result = get_result("%s_pad" % field_key, field_element)
            if color_pad_result is None:
                color_pad_result = 0
            if result is not None:
                function_stream.write(struct.pack(struct_string, *reversed(result.values()), color_pad_result))
            else:    
                function_stream.write(struct.pack(struct_string, *(0, 0, 0), color_pad_result))

        elif field_tag == "Block":
            struct_string = '%sf' % endian_override
            if unsigned_key:
                struct_string = uppercase_struct_letters(struct_string)
            tag_block_value = field_element.pop(field_key, [])
            for tag_element in tag_block_value:
                write_real(function_stream, struct_string, tag_element["Value"])

        elif field_tag == "CharInteger":
            struct_string = '%sb' % endian_override
            if unsigned_key:
                struct_string = uppercase_struct_letters(struct_string)
            result = get_result(field_key, field_element)
            if field_key.startswith("Function Type"):
                function_type_result = result

            if result is not None:
                function_stream.write(struct.pack(struct_string, result))
            else:
                function_stream.write(struct.pack(struct_string, 0))
        elif field_tag == "ByteFlags":
            struct_string = '%sb' % endian_override
            if unsigned_key:
                struct_string = uppercase_struct_letters(struct_string)
            result = get_result(field_key, field_element)
            if field_key.startswith("Flags"):
                flag_result = result
            if result is not None:
                function_stream.write(struct.pack(struct_string, result))
            else:
                function_stream.write(struct.pack(struct_string, 0))

    for field_node_element in field_set_1:
        unsigned_key = field_node_element.get("unsigned")
        field_endian = field_node_element.get("endianOverride")
        if field_endian:
            endian_override = field_endian

        field_key = field_node_element.get("name")
        field_tag = field_node_element.tag
        if field_tag == "Block":
            tag_block = field_element[field_key] = []
            for byte in function_stream.getbuffer():
                signed_byte = byte if byte < 128 else byte - 256
                tag_block.append({"Value": signed_byte})

            field_element["TagBlock_%s" % field_key] = {"unk1": 0,"unk2": 0}
            field_element["TagBlockHeader_%s" % field_key] = {"name": "tbfd", "version": 0, "size": 1}

def upgrade_effect_function(function_type, function_1_value, min_value, field_element, tag_block_fields, endian_override):
    field_set = None
    for layout in tag_block_fields:
        for struct_field_set in layout:
            if int(struct_field_set.attrib.get('version')) == 1:
                field_set = struct_field_set

    function_stream = io.BytesIO()
    function_stream.write(struct.pack('%sb' % endian_override, function_type)) # Transition function type
    function_stream.write(struct.pack('%sb' % endian_override, 0))
    function_stream.write(struct.pack('%sb' % endian_override, function_1_value))
    function_stream.write(struct.pack('%sb' % endian_override, 0))
    function_stream.write(struct.pack('%s4B' % endian_override, *(0, 0, 0), 0))
    function_stream.write(struct.pack('%s4B' % endian_override, *(0, 0, 0), 0))
    function_stream.write(struct.pack('%s4B' % endian_override, *(0, 0, 0), 0))
    function_stream.write(struct.pack('%s4B' % endian_override, *(0, 0, 0), 0))
    write_real(function_stream, '%sf' % endian_override, min_value)
    write_real(function_stream, '%sf' % endian_override, 0.0)
    write_real(function_stream, '%sf' % endian_override, 0.0)
    write_real(function_stream, '%sf' % endian_override, 0.0)

    for field_node_element in field_set:
        unsigned_key = field_node_element.get("unsigned")
        field_endian = field_node_element.get("endianOverride")
        if field_endian:
            endian_override = field_endian

        field_key = field_node_element.get("name")
        field_tag = field_node_element.tag
        if field_tag == "Block":
            tag_block = field_element[field_key] = []
            for byte in function_stream.getbuffer():
                signed_byte = byte if byte < 128 else byte - 256
                tag_block.append({"Value": signed_byte})

            field_element["TagBlock_%s" % field_key] = {"unk1": 0,"unk2": 0}
            field_element["TagBlockHeader_%s" % field_key] = {"name": "tbfd", "version": 0, "size": 1}

def biped_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        biped_def = merged_defs["bipd"]
        root = tag_dict["Data"]
        tag_block_version = 1
        tag_block_header = root.get("TagBlockHeader_biped")
        if tag_block_header is not None:
            tag_block_version = tag_block_header["version"]

        function_struct_field = biped_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        if tag_block_version == 0:
            root["flags_2"] = root.pop("Skip", 0)

            root["height standing"] = root.pop("standing collision height", 0.0)
            root["height crouching"] = root.pop("crouching collision height", 0.0)
            root["radius"] = root.pop("collision radius", 0.0)
            root["mass"] = root.pop("collision mass", 0.0)
            root["living material name"] = root.pop("collision global material name", "")
            root["dead material name"] = root.pop("dead collision global material name", "")

            root["StructHeader_ground physics"] = {"name": "chgr", "version": 0, "size": 48}
            root["StructHeader_flying physics"] = {"name": "chfl", "version": 0, "size": 44}

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

        seats_tag_block = root.get("seats")
        seat_header = root.get("TagBlockHeader_seats")
        if seats_tag_block is not None and seat_header is not None and not seat_header["version"] == 3:
            for seat_element in seats_tag_block:
                if seat_header["version"] == 0:
                    yaw = seat_element.pop("yaw rate", 0.0)
                    seat_element["yaw rate bounds"] = {"Min": yaw, "Max": yaw}

                    pitch = seat_element.pop("pitch rate", 0.0)
                    seat_element["pitch rate bounds"] = {"Min": pitch, "Max": pitch}

                seat_element["acceleration range"] = seat_element.pop("acceleration scale", (0.0, 0.0, 0.0))
                seat_element["StructHeader_acceleration"] = {"name": "usas", "version": 0, "size": 20}

def bitmap_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    root = tag_dict["Data"]
    tag_block_version = 2
    if preserve_version:
        tag_block_header = root["TagBlockHeader_bitmaps"]
        tag_block_version = tag_block_header["version"]

    for bitmap_element in root["bitmaps"]:
        #TODO: Skip and Ptr have some unknown value. Need to figure out how it's generated for this to work properly.
        if tag_block_version == 1:
            bitmap_element["Skip_0"] = base64.b64encode(bytes(12)).decode('utf-8')
            bitmap_element["Skip_1"] = base64.b64encode(bytes(12)).decode('utf-8')
            bitmap_element["Skip_2"] = base64.b64encode(bytes(12)).decode('utf-8')
            bitmap_element["Skip_3"] = base64.b64encode(bytes(4)).decode('utf-8')

            bitmap_element["Ptr_0"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_1"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_2"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_3"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_4"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_5"] = base64.b64encode(bytes(4)).decode('utf-8')

        elif tag_block_version == 2:
            data_length = base64.b64decode(root["processed pixel data"]["encoded"])

            bitmap_element["Skip_0"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Skip_1"] = base64.b64encode(bytes(12)).decode('utf-8')
            bitmap_element["Skip_2"] = base64.b64encode(bytes([0xFF] * 12)).decode('utf-8')
            bitmap_element["Skip_3"] = base64.b64encode(struct.pack("%si8x" % file_endian, len(data_length))).decode('utf-8')
            bitmap_element["Skip_4"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Skip_5"] = base64.b64encode(bytes(20)).decode('utf-8')

            bitmap_element["Ptr_0"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_1"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_2"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_3"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_4"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_5"] = base64.b64encode(bytes(4)).decode('utf-8')
            bitmap_element["Ptr_6"] = base64.b64encode(bytes(4)).decode('utf-8')

def breakable_surface_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        breakable_surface_def = merged_defs["bsdt"]
        root = tag_dict["Data"]

        mapping_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping"}']")
        mapping_1_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_1"}']")
        mapping_2_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_2"}']")
        mapping_3_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_3"}']")
        mapping_4_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_4"}']")
        mapping_5_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_5"}']")
        mapping_6_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_6"}']")
        mapping_7_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_7"}']")
        mapping_8_struct_field = breakable_surface_def.find(f".//Struct[@name='{"StructHeader_Mapping_8"}']")

        particle_effects_tag_block = root.get("particle effects")
        if particle_effects_tag_block is not None:
            for particle_effect_element in particle_effects_tag_block:
                emitters_tag_block = particle_effect_element.get("emitters")
                if emitters_tag_block is not None:
                    for emitter_element in emitters_tag_block:
                        mapping_header = emitter_element.get("StructHeader_Mapping")
                        mapping_1_header = emitter_element.get("StructHeader_Mapping_1")
                        mapping_2_header = emitter_element.get("StructHeader_Mapping_2")
                        mapping_3_header = emitter_element.get("StructHeader_Mapping_3")
                        mapping_4_header = emitter_element.get("StructHeader_Mapping_4")
                        mapping_5_header = emitter_element.get("StructHeader_Mapping_5")
                        mapping_6_header = emitter_element.get("StructHeader_Mapping_6")
                        mapping_7_header = emitter_element.get("StructHeader_Mapping_7")
                        mapping_8_header = emitter_element.get("StructHeader_Mapping_8")
                        if mapping_header is not None and mapping_header["name"] == "MAPP" and mapping_header["version"] == 0:
                            mapping_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_struct_field, file_endian)
                        if mapping_1_header is not None and mapping_1_header["name"] == "MAPP" and mapping_1_header["version"] == 0:
                            mapping_1_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_1_struct_field, file_endian)
                        if mapping_2_header is not None and mapping_2_header["name"] == "MAPP" and mapping_2_header["version"] == 0:
                            mapping_2_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_2_struct_field, file_endian)
                        if mapping_3_header is not None and mapping_3_header["name"] == "MAPP" and mapping_3_header["version"] == 0:
                            mapping_3_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_3_struct_field, file_endian)
                        if mapping_4_header is not None and mapping_4_header["name"] == "MAPP" and mapping_4_header["version"] == 0:
                            mapping_4_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_4_struct_field, file_endian)
                        if mapping_5_header is not None and mapping_5_header["name"] == "MAPP" and mapping_5_header["version"] == 0:
                            mapping_5_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_5_struct_field, file_endian)
                        if mapping_6_header is not None and mapping_6_header["name"] == "MAPP" and mapping_6_header["version"] == 0:
                            mapping_6_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_6_struct_field, file_endian)
                        if mapping_7_header is not None and mapping_7_header["name"] == "MAPP" and mapping_7_header["version"] == 0:
                            mapping_7_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_7_struct_field, file_endian)
                        if mapping_8_header is not None and mapping_8_header["name"] == "MAPP" and mapping_8_header["version"] == 0:
                            mapping_8_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, emitter_element, mapping_8_struct_field, file_endian)

def character_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        root = tag_dict["Data"]
        tag_block_version = 2
        tag_block_header = root.get("TagBlockHeader_character")
        if tag_block_header is not None:
            tag_block_version = tag_block_header["version"]

        if tag_block_version == 0:
            root["look properties"] = root.pop("Look properties", [])
            root["movement properties"] = root.pop("Movement properties", [])
            root["engage properties"] = root.pop("Engage properties", [])
            root["evasion properties"] = root.pop("Evasion properties", [])
            root["cover properties"] = root.pop("Cover properties", [])

        if not tag_block_version == 2:
            variant_name = root.pop("model variant", "")

            variant_block = root.get("TagBlock_variants")
            variant_header = root.get("TagBlockHeader_variants")
            variant_data = root.get("variants")
            if variant_block is None:
                root["TagBlock_variants"] = {"unk1": 0, "unk2": 0}
            if variant_header is None:
                root["TagBlockHeader_variants"] = {"name": "tbfd", "version": 0, "size": 12}
            if variant_data is None:
                variant_data = root["variants"] = []

            variant_element = {"variant name": variant_name, "variant index": -1, "variant designator": ""}
            variant_data.append(variant_element)

        presearch_header = root.get("TagBlockHeader_pre-search properties")
        presearch_data = root.get("pre-search properties")
        if presearch_data is not None and presearch_header is not None and not presearch_header["version"] == 1:
            presearch_header = {"name": "tbfd", "version": 1, "size": 36}
            for presearch_element in presearch_data:
                old_presearch_bounds = presearch_element.pop("Min/Max pre-search bounds", {"Min": 0.0, "Max": 0.0})
                presearch_element["min presearch time"] = {"Min": old_presearch_bounds["Min"], "Max": old_presearch_bounds["Min"]}
                presearch_element["max presearch time"] = {"Min": old_presearch_bounds["Max"], "Max": old_presearch_bounds["Max"]}
                presearch_element["min suppressing time"] = {"Min": 2, "Max": 3}
                
        weapons_header = root.get("TagBlockHeader_weapons properties")
        weapons_data = root.get("weapons properties")
        if weapons_data is not None and weapons_header is not None and not weapons_header["version"] == 1:
            weapons_header = {"name": "tbfd", "version": 1, "size": 224}
            for weapon_element in weapons_data:
                weapon_element["maximum firing range"] = weapon_element.pop("maximum firing distance", 0.0)
                rate_of_fire = weapon_element.pop("rate of fire", 0.0)
                projectile_error = weapon_element.pop("projectile error", 0.0)
                desired_combat_range = weapon_element.pop("desired combat range", {"Min": 0.0, "Max": 0.0})
                target_tracking = weapon_element.pop("target tracking", 0.0)
                target_leading = weapon_element.pop("target leading", 0.0)
                weapon_damage_modifier = weapon_element.pop("weapon damage modifier", 0.0)
                burst_origin_radius = weapon_element.pop("burst origin radius", 0.0)
                burst_origin_angle = weapon_element.pop("burst origin angle", 0.0)
                burst_return_length = weapon_element.pop("burst return length", {"Min": 0.0, "Max": 0.0})
                burst_return_angle = weapon_element.pop("burst return angle", 0.0)
                burst_duration = weapon_element.pop("burst duration", {"Min": 0.0, "Max": 0.0})
                burst_separation = weapon_element.pop("burst separation", {"Min": 0.0, "Max": 0.0})
                burst_angular_velocity = weapon_element.pop("burst angular velocity", 0.0)

                weapon_element["normal combat range"] = desired_combat_range
                weapon_element["timid combat range"] = desired_combat_range
                weapon_element["aggressive combat range"] = desired_combat_range

                firing_patterns_block = presearch_element.get("TagBlock_firing patterns")
                firing_patterns_header = presearch_element.get("TagBlockHeader_firing patterns")
                firing_patterns_data = presearch_element.get("firing patterns")
                if firing_patterns_block is None:
                    weapon_element["TagBlock_firing"] = {"unk1": 0, "unk2": 0}
                if firing_patterns_header is None:
                    weapon_element["TagBlockHeader_firing patterns"] = {"name": "tbfd", "version": 0, "size": 64}
                if firing_patterns_data is None:
                    firing_patterns_data = root["firing patterns"] = []

                firing_pattern_element = {"rate of fire": rate_of_fire, 
                                   "target tracking": target_tracking, 
                                   "target leading": target_leading,
                                   "burst origin radius": burst_origin_radius,
                                   "burst origin angle": burst_origin_angle,
                                   "burst return length": burst_return_length,
                                   "burst return angle": burst_return_angle,
                                   "burst duration": burst_duration,
                                   "burst separation": burst_separation,
                                   "weapon damage modifier": weapon_damage_modifier,
                                   "projectile error": projectile_error,
                                   "burst angular velocity": burst_angular_velocity,
                                   "maximum error angle": radians(90)}

                firing_patterns_data.append(firing_pattern_element)

        charge_header = root.get("TagBlockHeader_charge properties")
        charge_data = root.get("charge properties")
        if charge_data is not None and charge_header is not None and not charge_header["version"] == 3:
            charge_header = {"name": "tbfd", "version": 3, "size": 72}
            for charge_element in charge_data:
                charge_element["melee_chance"] = 1

                if charge_header["version"] <= 1:
                    melee_leap_velocity = weapon_element.pop("melee leap velocity", 0.0)

                    charge_element["ideal leap velocity"] = melee_leap_velocity
                    charge_element["max leap velocity"] = melee_leap_velocity

def chocolate_mountain_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        chocolate_mountain_def = merged_defs["gldf"]
        root = tag_dict["Data"]

        function_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function"}']")
        function_1_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function_1"}']")
        function_2_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function_2"}']")
        function_3_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function 1"}']")

        lighting_tag_block = root.get("lighting variables")
        if lighting_tag_block is not None:
            for lighting_element in lighting_tag_block:
                function_header = lighting_element.get("StructHeader_function")
                function_1_header = lighting_element.get("StructHeader_function_1")
                function_2_header = lighting_element.get("StructHeader_function_2")
                function_3_header = lighting_element.get("StructHeader_function 1")
                if function_header is not None and function_header["name"] == "MAPP" and function_header["version"] == 0:
                    function_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, lighting_element, function_struct_field, file_endian)
                if function_1_header is not None and function_1_header["name"] == "MAPP" and function_1_header["version"] == 0:
                    function_1_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, lighting_element, function_1_struct_field, file_endian)
                if function_2_header is not None and function_2_header["name"] == "MAPP" and function_2_header["version"] == 0:
                    function_2_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, lighting_element, function_2_struct_field, file_endian)
                if function_3_header is not None and function_3_header["name"] == "MAPP" and function_3_header["version"] == 0:
                    function_3_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, lighting_element, function_3_struct_field, file_endian)

def crate_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        crate_def = merged_defs["bloc"]
        root = tag_dict["Data"]

        function_struct_field = crate_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def creature_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        creature_def = merged_defs["crea"]
        root = tag_dict["Data"]

        function_struct_field = creature_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def damage_effect_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        damage_effect_def = merged_defs["jpt!"]
        root = tag_dict["Data"]

        tag_block_header = tag_dict.get("TagBlockHeader_damage_effect")
        if tag_block_header["version"] == 0:
            tag_block_header = tag_dict["TagBlockHeader_damage_effect"] = {"name": "tbfd","version": 1,"size": 212}

            player_responses_block = root.get("TagBlock_player responses")
            player_responses_header = root.get("TagBlockHeader_player responses")
            player_responses_data = root.get("player responses")
            if player_responses_block is None:
                root["TagBlock_player responses"] = {"unk1": 0, "unk2": 0}
            if player_responses_header is None:
                root["TagBlockHeader_player responses"] = {"name": "tbfd", "version": 0, "size": 88}
            if player_responses_data is None:
                player_responses_data = root["player responses"] = []

            player_response_element = {
                                "response type": {"type": "ShortEnum","value": 2,"value name": ""}, 
                                "type": root.pop("type", 0), 
                                "priority": root.pop("priority", 0),
                                "duration": root.pop("duration", 0.0),
                                "fade function": root.pop("fade function", 0),
                                "maximum intensity": root.pop("maximum intensity", 0.0),
                                "color": root.pop("color", 0.0),
                                "duration_2": root.pop("duration_1", 0.0),
                                "TagBlock_data": {"unk1": 0,"unk2": 0},
                                "TagBlockHeader_data": {"name": "tbfd", "version": 0, "size": 1},
                                "data_1": [],
                                "duration_3": root.pop("duration_2", 0.0),
                                "TagBlock_data_1": {"unk1": 0,"unk2": 0},
                                "TagBlockHeader_data_1": {"name": "tbfd", "version": 0, "size": 1},
                                "data_2": [],
                                "effect name": "",
                                "duration_1": 0.0,
                                "TagBlock_data_2": {"unk1": 0,"unk2": 0},
                                "TagBlockHeader_data_2": {"name": "tbfd", "version": 0, "size": 1},
                                "data": [],
                                }

            root["rider direct damage scale"] = root.pop("Real", 0.0)
            root["rider maximum transfer damage scale"] = root.pop("Real_1", 0.0)
            root["rider minimum transfer damage scale"] = root.pop("Real_2", 0.0)

            root["duration"] = root.pop("duration_3", 0.0)
            root["fade function"] = root.pop("fade function_3", 0)

            root["duration_1"] = root.pop("duration_4", 0.0)
 

            vibration_function_field = damage_effect_def.find(f".//Struct[@name='{"StructHeader_dirty whore"}']")
            frequency_function_field = damage_effect_def.find(f".//Struct[@name='{"StructHeader_dirty whore_1"}']")
            scale_function_field = damage_effect_def.find(f".//Struct[@name='{"StructHeader_effect scale function"}']")

            upgrade_effect_function(2, (root.pop("fade function_1", {}) or {}).get("Value", 0), root.pop("frequency", 0.0), player_response_element, vibration_function_field, file_endian)
            upgrade_effect_function(2, (root.pop("fade function_2", {}) or {}).get("Value", 0), root.pop("frequency_1", 0.0), player_response_element, frequency_function_field, file_endian)
            upgrade_effect_function(0, 0, 0, player_response_element, scale_function_field, file_endian)

            player_responses_data.append(player_response_element)

def device_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        device_def = merged_defs["devi"]
        root = tag_dict["Data"]

        function_struct_field = device_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_control_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        device_control_def = merged_defs["ctrl"]
        root = tag_dict["Data"]

        function_struct_field = device_control_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_light_fixture_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        device_light_fixture_def = merged_defs["lifi"]
        root = tag_dict["Data"]

        function_struct_field = device_light_fixture_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_machine_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        device_machine_def = merged_defs["mach"]
        root = tag_dict["Data"]

        function_struct_field = device_machine_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def effect_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        effect_def = merged_defs["effe"]
        root = tag_dict["Data"]

        function_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function"}']")
        function_1_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function_1"}']")
        function_2_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function_2"}']")
        function_3_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function_3"}']")
        function_4_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function_4"}']")
        function_5_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_function_5"}']")
        mapping_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping"}']")
        mapping_1_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_1"}']")
        mapping_2_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_2"}']")
        mapping_3_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_3"}']")
        mapping_4_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_4"}']")
        mapping_5_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_5"}']")
        mapping_6_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_6"}']")
        mapping_7_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_7"}']")
        mapping_8_struct_field = effect_def.find(f".//Struct[@name='{"StructHeader_Mapping_8"}']")
    
        events_tag_block = root.get("events")
        if events_tag_block is not None:
            for event_element in events_tag_block:
                beams_tag_block = event_element.get("beams")
                if beams_tag_block is not None:
                    for beam_element in beams_tag_block:
                        function_header = beam_element.get("StructHeader_function")
                        if function_header is not None and function_header["name"] == "MAPP" and function_header["version"] == 0:
                            function_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_struct_field, file_endian)
                        function_1_header = beam_element.get("StructHeader_function_1")
                        if function_1_header is not None and function_1_header["name"] == "MAPP" and function_1_header["version"] == 0:
                            function_1_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_1_struct_field, file_endian)
                        function_2_header = beam_element.get("StructHeader_function_2")
                        if function_2_header is not None and function_2_header["name"] == "MAPP" and function_2_header["version"] == 0:
                            function_2_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_2_struct_field, file_endian)
                        function_3_header = beam_element.get("StructHeader_function_3")
                        if function_3_header is not None and function_3_header["name"] == "MAPP" and function_3_header["version"] == 0:
                            function_3_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_3_struct_field, file_endian)
                        function_4_header = beam_element.get("StructHeader_function_4")
                        if function_4_header is not None and function_4_header["name"] == "MAPP" and function_4_header["version"] == 0:
                            function_4_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_4_struct_field, file_endian)
                        function_5_header = beam_element.get("StructHeader_function_5")
                        if function_5_header is not None and function_5_header["name"] == "MAPP" and function_5_header["version"] == 0:
                            function_5_header = {"name": "MAPP", "version": 1, "size": 12}
                            upgrade_function(merged_defs, beam_element, function_5_struct_field, file_endian)
                particle_systems_tag_block = event_element.get("particle systems")
                if particle_systems_tag_block is not None:
                    for particle_system_element in particle_systems_tag_block:
                        emitters_tag_block = particle_system_element.get("emitters")
                        if emitters_tag_block is not None:
                            for emitter_element in emitters_tag_block:
                                mapping_header = emitter_element.get("StructHeader_Mapping")
                                if mapping_header is not None and mapping_header["name"] == "MAPP" and mapping_header["version"] == 0:
                                    mapping_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_struct_field, file_endian)
                                mapping_1_header = emitter_element.get("StructHeader_Mapping_1")
                                if mapping_1_header is not None and mapping_1_header["name"] == "MAPP" and mapping_1_header["version"] == 0:
                                    mapping_1_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_1_struct_field, file_endian)
                                mapping_2_header = emitter_element.get("StructHeader_Mapping_2")
                                if mapping_2_header is not None and mapping_2_header["name"] == "MAPP" and mapping_2_header["version"] == 0:
                                    mapping_2_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_2_struct_field, file_endian)
                                mapping_3_header = emitter_element.get("StructHeader_Mapping_3")
                                if mapping_3_header is not None and mapping_3_header["name"] == "MAPP" and mapping_3_header["version"] == 0:
                                    mapping_3_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_3_struct_field, file_endian)
                                mapping_4_header = emitter_element.get("StructHeader_Mapping_4")
                                if mapping_4_header is not None and mapping_4_header["name"] == "MAPP" and mapping_4_header["version"] == 0:
                                    mapping_4_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_4_struct_field, file_endian)
                                mapping_5_header = emitter_element.get("StructHeader_Mapping_5")
                                if mapping_5_header is not None and mapping_5_header["name"] == "MAPP" and mapping_5_header["version"] == 0:
                                    mapping_5_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_5_struct_field, file_endian)
                                mapping_6_header = emitter_element.get("StructHeader_Mapping_6")
                                if mapping_6_header is not None and mapping_6_header["name"] == "MAPP" and mapping_6_header["version"] == 0:
                                    mapping_6_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_6_struct_field, file_endian)
                                mapping_7_header = emitter_element.get("StructHeader_Mapping_7")
                                if mapping_7_header is not None and mapping_7_header["name"] == "MAPP" and mapping_7_header["version"] == 0:
                                    mapping_7_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_7_struct_field, file_endian)
                                mapping_8_header = emitter_element.get("StructHeader_Mapping_8")
                                if mapping_8_header is not None and mapping_8_header["name"] == "MAPP" and mapping_8_header["version"] == 0:
                                    mapping_8_header = {"name": "MAPP", "version": 1, "size": 12}
                                    upgrade_function(merged_defs, emitter_element, mapping_8_struct_field, file_endian)

def equipment_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        equipment_def = merged_defs["eqip"]
        root = tag_dict["Data"]

        function_struct_field = equipment_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def garbage_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        garbage_def = merged_defs["garb"]
        root = tag_dict["Data"]

        function_struct_field = garbage_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def globals_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        globals_def = merged_defs["matg"]
        root = tag_dict["Data"]

        sound_globals_tag_block = root.get("sound globals")
        tag_block_header = root.get("TagBlockHeader_sound globals")
        if sound_globals_tag_block is not None and tag_block_header is not None:
            if tag_block_header["version"] == 0:
                for sound_globals_element in sound_globals_tag_block:
                    sound_globals_element["legacy sound classes"] = {"group name": "snmx"," unk1": 0," length": 15," unk2": 0," path": "sound\sound_mix"}

            else:
                for sound_globals_element in sound_globals_tag_block:
                    sound_globals_element["legacy sound classes"] = sound_globals_element.pop("sound classes")
                    
def item_postprocess(merged_defs, tag_dict, file_endian, preserve_version):
    if not preserve_version:
        item_def = merged_defs["item"]
        root = tag_dict["Data"]

        function_struct_field = item_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_default function")
                if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

postprocess_functions = {
    "obje": None,
    "devi": device_postprocess,
    "item": item_postprocess,
    "unit": None,
    "hlmt": None,
    "mode": None,
    "coll": None,
    "phmo": None,
    "bitm": bitmap_postprocess,
    "colo": None,
    "unic": None,
    "bipd": biped_postprocess,
    "vehi": None,
    "scen": None,
    "bloc": crate_postprocess,
    "crea": creature_postprocess,
    "phys": None,
    "cont": None,
    "weap": None,
    "ligh": None,
    "effe": effect_postprocess,
    "prt3": None,
    "PRTM": None,
    "pmov": None,
    "matg": globals_postprocess,
    "snd!": None,
    "lsnd": None,
    "eqip": equipment_postprocess,
    "ant!": None,
    "MGS2": None,
    "tdtl": None,
    "devo": None,
    "whip": None,
    "BooM": None,
    "trak": None,
    "proj": None,
    "mach": device_machine_postprocess,
    "ctrl": device_control_postprocess,
    "lifi": device_light_fixture_postprocess,
    "pphy": None,
    "ltmp": None,
    "sbsp": None,
    "scnr": None,
    "shad": None,
    "stem": None,
    "slit": None,
    "spas": None,
    "vrtx": None,
    "pixl": None,
    "DECR": None,
    "sky ": None,
    "wind": None,
    "snde": None,
    "lens": None,
    "fog ": None,
    "fpch": None,
    "metr": None,
    "deca": None,
    "coln": None,
    "jpt!": damage_effect_postprocess,
    "udlg": None,
    "itmc": None,
    "vehc": None,
    "wphi": None,
    "grhi": None,
    "unhi": None,
    "nhdt": None,
    "hud#": None,
    "hudg": None,
    "mply": None,
    "dobc": None,
    "ssce": None,
    "hmt ": None,
    "wgit": None,
    "skin": None,
    "wgtz": None,
    "wigl": None,
    "sily": None,
    "goof": None,
    "foot": None,
    "garb": garbage_postprocess,
    "styl": None,
    "char": character_postprocess,
    "adlg": None,
    "mdlg": None,
    "*cen": None,
    "*ipd": None,
    "*ehi": None,
    "*qip": None,
    "*eap": None,
    "*sce": None,
    "*igh": None,
    "dgr*": None,
    "dec*": None,
    "cin*": None,
    "trg*": None,
    "clu*": None,
    "*rea": None,
    "dc*s": None,
    "sslt": None,
    "hsc*": None,
    "ai**": None,
    "/**/": None,
    "bsdt": breakable_surface_postprocess,
    "mpdt": None,
    "sncl": None,
    "mulg": None,
    "<fx>": None,
    "sfx+": None,
    "gldf": chocolate_mountain_postprocess,
    "jmad": None,
    "clwd": None,
    "egor": None,
    "weat": None,
    "snmx": None,
    "spk!": None,
    "ugh!": None,
    "$#!+": None,
    "mcsr": None,
    "tag+": None,
}
