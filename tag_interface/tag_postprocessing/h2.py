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

def pack24(format_string: str, value: int) -> bytes:
    if len(format_string) != 2 or format_string[1] not in ('u', 'U'):
        raise ValueError("Format must be '<u', '>u', '<U', or '>U'")

    byteorder = 'little' if format_string[0] == '<' else 'big'
    is_unsigned = format_string[1] == 'U'

    if is_unsigned:
        if not (0 <= value <= 0xFFFFFF):
            raise ValueError("Value out of range for unsigned 24-bit integer")
    else:
        if not (-0x800000 <= value <= 0x7FFFFF):
            raise ValueError("Value out of range for signed 24-bit integer")
        if value < 0:
            value += 1 << 24

    return value.to_bytes(3, byteorder=byteorder)

def unpack24(format_string: str, data: bytes) -> tuple[int]:
    if len(format_string) != 2 or format_string[1] not in ('u', 'U'):
        raise ValueError("Format must be '<u', '>u', '<U', or '>U'")
    if len(data) != 3:
        raise ValueError("Must provide exactly 3 bytes for 24-bit integer")

    byteorder = 'little' if format_string[0] == '<' else 'big'
    is_unsigned = format_string[1] == 'U'

    value = int.from_bytes(data, byteorder=byteorder)

    if not is_unsigned and (value & 0x800000):
        value -= 1 << 24

    return value

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

def biped_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    biped_def = merged_defs["bipd"]
    root = tag_dict["Data"]

    biped_header = tag_dict.get("TagBlockHeader_biped")
    if biped_header is not None and biped_header["version"] == 0:
        root["flags_2"] = root.pop("Skip", 0)

        root["height standing"] = root.pop("standing collision height", 0.0)
        root["height crouching"] = root.pop("crouching collision height", 0.0)
        root["radius"] = root.pop("collision radius", 0.0)
        root["mass"] = root.pop("collision mass", 0.0)
        root["living material name"] = root.pop("collision global material name", "")
        root["dead material name"] = root.pop("dead collision global material name", "")

        root["StructHeader_ground physics"] = {"name": "chgr", "version": 0, "size": 48}
        root["StructHeader_flying physics"] = {"name": "chfl", "version": 0, "size": 44}

    biped_header = tag_dict["TagBlockHeader_biped"] = {"name": "tbfd", "version": 1, "size": 988}

    function_struct_field = biped_def.find(f".//Struct[@name='{"StructHeader_default function"}']")
    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

    seats_block = root.get("seats")
    seat_header = root.get("TagBlockHeader_seats")
    if seats_block is not None and seat_header is not None and not seat_header["version"] == 3:
        for seat_element in seats_block:
            if seat_header["version"] == 0:
                yaw = seat_element.pop("yaw rate", 0.0)
                seat_element["yaw rate bounds"] = {"Min": yaw, "Max": yaw}

                pitch = seat_element.pop("pitch rate", 0.0)
                seat_element["pitch rate bounds"] = {"Min": pitch, "Max": pitch}

            seat_element["acceleration range"] = seat_element.pop("acceleration scale", (0.0, 0.0, 0.0))
            seat_element["StructHeader_acceleration"] = {"name": "usas", "version": 0, "size": 20}

        seat_header = root["TagBlockHeader_seats"] = {"name": "tbfd", "version": 3, "size": 192}

def bitmap_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    root = tag_dict["Data"]

    bitmap_block = root.get("bitmaps")
    bitmap_header = root.get("TagBlockHeader_bitmaps")
    if bitmap_block is not None and bitmap_header is not None:
        for bitmap_element in root["bitmaps"]:
            #TODO: Skip and Ptr have some unknown value. Need to figure out how it's generated for this to work properly.
            if not bitmap_header["version"] == 2:
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

        bitmap_header = root["TagBlockHeader_bitmaps"] = {"name": "tbfd", "version": 2, "size": 140}

def breakable_surface_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
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

    particle_effects_block = root.get("particle effects")
    if particle_effects_block is not None:
        for particle_effect_element in particle_effects_block:
            emitters_block = particle_effect_element.get("emitters")
            if emitters_block is not None:
                for emitter_element in emitters_block:
                    mapping_header = emitter_element.get("StructHeader_Mapping")
                    mapping_1_header = emitter_element.get("StructHeader_Mapping_1")
                    mapping_2_header = emitter_element.get("StructHeader_Mapping_2")
                    mapping_3_header = emitter_element.get("StructHeader_Mapping_3")
                    mapping_4_header = emitter_element.get("StructHeader_Mapping_4")
                    mapping_5_header = emitter_element.get("StructHeader_Mapping_5")
                    mapping_6_header = emitter_element.get("StructHeader_Mapping_6")
                    mapping_7_header = emitter_element.get("StructHeader_Mapping_7")
                    mapping_8_header = emitter_element.get("StructHeader_Mapping_8")
                    if mapping_header is not None and mapping_header["version"] == 0:
                        mapping_header = emitter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_struct_field, file_endian)
                    if mapping_1_header is not None and mapping_1_header["version"] == 0:
                        mapping_1_header = emitter_element["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_1_struct_field, file_endian)
                    if mapping_2_header is not None and mapping_2_header["version"] == 0:
                        mapping_2_header = emitter_element["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_2_struct_field, file_endian)
                    if mapping_3_header is not None and mapping_3_header["version"] == 0:
                        mapping_3_header = emitter_element["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_3_struct_field, file_endian)
                    if mapping_4_header is not None and mapping_4_header["version"] == 0:
                        mapping_4_header = emitter_element["StructHeader_Mapping_4"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_4_struct_field, file_endian)
                    if mapping_5_header is not None and mapping_5_header["version"] == 0:
                        mapping_5_header = emitter_element["StructHeader_Mapping_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_5_struct_field, file_endian)
                    if mapping_6_header is not None and mapping_6_header["version"] == 0:
                        mapping_6_header = emitter_element["StructHeader_Mapping_6"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_6_struct_field, file_endian)
                    if mapping_7_header is not None and mapping_7_header["version"] == 0:
                        mapping_7_header = emitter_element["StructHeader_Mapping_7"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_7_struct_field, file_endian)
                    if mapping_8_header is not None and mapping_8_header["version"] == 0:
                        mapping_8_header = emitter_element["StructHeader_Mapping_8"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, mapping_8_struct_field, file_endian)

def character_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    character_def = merged_defs["bipd"]
    root = tag_dict["Data"]

    character_header = tag_dict.get("TagBlockHeader_character")
    if character_header is not None:
        if character_header["version"] == 0:
            root["look properties"] = root.pop("Look properties", [])
            root["movement properties"] = root.pop("Movement properties", [])
            root["engage properties"] = root.pop("Engage properties", [])
            root["evasion properties"] = root.pop("Evasion properties", [])
            root["cover properties"] = root.pop("Cover properties", [])

        if not character_header["version"] == 2:
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

    character_header = tag_dict["TagBlockHeader_character"] = {"name": "tbfd", "version": 2, "size": 408}

    presearch_block = root.get("pre-search properties")
    presearch_header = root.get("TagBlockHeader_pre-search properties")
    if presearch_block is not None and presearch_header is not None and not presearch_header["version"] == 1:
        presearch_header = root["TagBlockHeader_pre-search properties"] = {"name": "tbfd", "version": 1, "size": 36}
        for presearch_element in presearch_block:
            old_presearch_bounds = presearch_element.pop("Min/Max pre-search bounds", {"Min": 0.0, "Max": 0.0})
            presearch_element["min presearch time"] = {"Min": old_presearch_bounds["Min"], "Max": old_presearch_bounds["Min"]}
            presearch_element["max presearch time"] = {"Min": old_presearch_bounds["Max"], "Max": old_presearch_bounds["Max"]}
            presearch_element["min suppressing time"] = {"Min": 2, "Max": 3}

    weapons_block = root.get("weapons properties")
    weapons_header = root.get("TagBlockHeader_weapons properties")
    if weapons_block is not None and weapons_header is not None and not weapons_header["version"] == 1:
        weapons_header = root["TagBlockHeader_weapons properties"] = {"name": "tbfd", "version": 1, "size": 224}
        for weapon_element in weapons_block:
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

    charge_block = root.get("charge properties")
    charge_header = root.get("TagBlockHeader_charge properties")
    if charge_block is not None and charge_header is not None and not charge_header["version"] == 3:
        charge_header = root["TagBlockHeader_charge properties"] = {"name": "tbfd", "version": 3, "size": 72}
        for charge_element in charge_block:
            charge_element["melee_chance"] = 1
            if charge_header["version"] <= 1:
                melee_leap_velocity = weapon_element.pop("melee leap velocity", 0.0)

                charge_element["ideal leap velocity"] = melee_leap_velocity
                charge_element["max leap velocity"] = melee_leap_velocity

def chocolate_mountain_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    chocolate_mountain_def = merged_defs["gldf"]
    root = tag_dict["Data"]

    function_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function"}']")
    function_1_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function_1"}']")
    function_2_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function_2"}']")
    function_3_struct_field = chocolate_mountain_def.find(f".//Struct[@name='{"StructHeader_function 1"}']")

    lighting_block = root.get("lighting variables")
    if lighting_block is not None:
        for lighting_element in lighting_block:
            function_header = lighting_element.get("StructHeader_function")
            function_1_header = lighting_element.get("StructHeader_function_1")
            function_2_header = lighting_element.get("StructHeader_function_2")
            function_3_header = lighting_element.get("StructHeader_function 1")
            if function_header is not None and function_header["version"] == 0:
                function_header = lighting_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, lighting_element, function_struct_field, file_endian)
            if function_1_header is not None and function_1_header["version"] == 0:
                function_1_header = lighting_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, lighting_element, function_1_struct_field, file_endian)
            if function_2_header is not None and function_2_header["version"] == 0:
                function_2_header = lighting_element["StructHeader_function_2"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, lighting_element, function_2_struct_field, file_endian)
            if function_3_header is not None and function_3_header["version"] == 0:
                function_3_header = lighting_element["StructHeader_function_3"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, lighting_element, function_3_struct_field, file_endian)

def collision_model_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    collision_model_def = merged_defs["coll"]
    root = tag_dict["Data"]

    regions_block = root.get("regions")
    if regions_block is not None:
        for region_element in regions_block:
            permutations_block = region_element.get("permutations")
            if permutations_block is not None:
                for permutation_element in permutations_block:
                    bsps_block = permutation_element.get("bsps")
                    if bsps_block is not None:
                        for bsp_element in bsps_block:
                            bsp_header = bsp_element.get("StructHeader_bsp")
                            if bsp_header is not None and not bsp_header["version"] == 2:
                                bsp3d_nodes_block = bsp_element.get("bsp3d nodes")
                                if bsp3d_nodes_block is not None:
                                    for bsp3d_node_element in bsp3d_nodes_block:
                                        skip_stream = io.BytesIO()
                                        skip_stream.write(struct.pack('%sh' % file_endian, bsp3d_node_element.pop("plane", 0)))
                                        skip_stream.write(pack24('%su' % file_endian, bsp3d_node_element.pop("back child", 0)))
                                        skip_stream.write(pack24('%su' % file_endian, bsp3d_node_element.pop("back child", 0)))

                                        bsp_element["Skip"] = base64.b64encode(skip_stream.getvalue()).decode('utf-8')

                                bsp_header = bsp_element["StructHeader_bsp"] = {"name": "cbsp", "version": 2, "size": 96}
                                
def crate_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    crate_def = merged_defs["bloc"]
    root = tag_dict["Data"]

    function_struct_field = crate_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def creature_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    creature_def = merged_defs["crea"]
    root = tag_dict["Data"]

    function_struct_field = creature_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def damage_effect_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    damage_effect_def = merged_defs["jpt!"]
    root = tag_dict["Data"]

    damage_effect_header = tag_dict.get("TagBlockHeader_damage_effect")
    if damage_effect_header is not None and damage_effect_header["version"] == 0:
        damage_effect_header = tag_dict["TagBlockHeader_damage_effect"] = {"name": "tbfd","version": 1,"size": 212}

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

def device_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    device_def = merged_defs["devi"]
    root = tag_dict["Data"]

    function_struct_field = device_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_control_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    device_control_def = merged_defs["ctrl"]
    root = tag_dict["Data"]

    function_struct_field = device_control_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_light_fixture_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    device_light_fixture_def = merged_defs["lifi"]
    root = tag_dict["Data"]

    function_struct_field = device_light_fixture_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def device_machine_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    device_machine_def = merged_defs["mach"]
    root = tag_dict["Data"]

    function_struct_field = device_machine_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def effect_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
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

    events_block = root.get("events")
    if events_block is not None:
        for event_element in events_block:
            beams_tag_block = event_element.get("beams")
            if beams_tag_block is not None:
                for beam_element in beams_tag_block:
                    function_header = beam_element.get("StructHeader_function")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = beam_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_struct_field, file_endian)
                    function_1_header = beam_element.get("StructHeader_function_1")
                    if function_1_header is not None and function_1_header["version"] == 0:
                        function_1_header = beam_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_1_struct_field, file_endian)
                    function_2_header = beam_element.get("StructHeader_function_2")
                    if function_2_header is not None and function_2_header["version"] == 0:
                        function_2_header = beam_element["StructHeader_function_2"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_2_struct_field, file_endian)
                    function_3_header = beam_element.get("StructHeader_function_3")
                    if function_3_header is not None and function_3_header["version"] == 0:
                        function_3_header = beam_element["StructHeader_function_3"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_3_struct_field, file_endian)
                    function_4_header = beam_element.get("StructHeader_function_4")
                    if function_4_header is not None and function_4_header["version"] == 0:
                        function_4_header = beam_element["StructHeader_function_4"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_4_struct_field, file_endian)
                    function_5_header = beam_element.get("StructHeader_function_5")
                    if function_5_header is not None and function_5_header["version"] == 0:
                        function_5_header = beam_element["StructHeader_function_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, beam_element, function_5_struct_field, file_endian)
            particle_systems_block = event_element.get("particle systems")
            if particle_systems_block is not None:
                for particle_system_element in particle_systems_block:
                    emitters_block = particle_system_element.get("emitters")
                    if emitters_block is not None:
                        for emitter_element in emitters_block:
                            mapping_header = emitter_element.get("StructHeader_Mapping")
                            if mapping_header is not None and mapping_header["version"] == 0:
                                mapping_header = emitter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_struct_field, file_endian)
                            mapping_1_header = emitter_element.get("StructHeader_Mapping_1")
                            if mapping_1_header is not None and mapping_1_header["version"] == 0:
                                mapping_1_header = emitter_element["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_1_struct_field, file_endian)
                            mapping_2_header = emitter_element.get("StructHeader_Mapping_2")
                            if mapping_2_header is not None and mapping_2_header["version"] == 0:
                                mapping_2_header = emitter_element["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_2_struct_field, file_endian)
                            mapping_3_header = emitter_element.get("StructHeader_Mapping_3")
                            if mapping_3_header is not None and mapping_3_header["version"] == 0:
                                mapping_3_header = emitter_element["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_3_struct_field, file_endian)
                            mapping_4_header = emitter_element.get("StructHeader_Mapping_4")
                            if mapping_4_header is not None and mapping_4_header["version"] == 0:
                                mapping_4_header = emitter_element["StructHeader_Mapping_4"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_4_struct_field, file_endian)
                            mapping_5_header = emitter_element.get("StructHeader_Mapping_5")
                            if mapping_5_header is not None and mapping_5_header["version"] == 0:
                                mapping_5_header = emitter_element["StructHeader_Mapping_5"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_5_struct_field, file_endian)
                            mapping_6_header = emitter_element.get("StructHeader_Mapping_6")
                            if mapping_6_header is not None and mapping_6_header["version"] == 0:
                                mapping_6_header = emitter_element["StructHeader_Mapping_6"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_6_struct_field, file_endian)
                            mapping_7_header = emitter_element.get("StructHeader_Mapping_7")
                            if mapping_7_header is not None and mapping_7_header["version"] == 0:
                                mapping_7_header = emitter_element["StructHeader_Mapping_7"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_7_struct_field, file_endian)
                            mapping_8_header = emitter_element.get("StructHeader_Mapping_8")
                            if mapping_8_header is not None and mapping_8_header["version"] == 0:
                                mapping_8_header = emitter_element["StructHeader_Mapping_8"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, emitter_element, mapping_8_struct_field, file_endian)

def equipment_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    equipment_def = merged_defs["eqip"]
    root = tag_dict["Data"]

    function_struct_field = equipment_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def garbage_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    garbage_def = merged_defs["garb"]
    root = tag_dict["Data"]

    function_struct_field = garbage_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def globals_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    globals_def = merged_defs["matg"]
    root = tag_dict["Data"]

    sound_globals_block = root.get("sound globals")
    sound_globals_header = root.get("TagBlockHeader_sound globals")
    if sound_globals_block is not None and sound_globals_header is not None:
        if sound_globals_header["version"] == 0:
            for sound_globals_element in sound_globals_block:
                sound_globals_element["legacy sound classes"] = {"group name": "snmx"," unk1": 0," length": 15," unk2": -1," path": os.path.normpath(r"sound\sound_mix")}

        else:
            for sound_globals_element in sound_globals_block:
                sound_globals_element["legacy sound classes"] = sound_globals_element.pop("sound classes")
                
        sound_globals_header = root["TagBlockHeader_sound globals"] = {"name": "tbfd", "version": 2, "size": 84}

def item_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    item_def = merged_defs["item"]
    root = tag_dict["Data"]

    function_struct_field = item_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def lens_flare_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    lens_flare_def = merged_defs["lens"]
    root = tag_dict["Data"]

    function_struct_field = lens_flare_def.find(".//Block[@name='brightness']//Struct[@name='StructHeader_function_1']")
    function_1_struct_field = lens_flare_def.find(".//Block[@name='color']//Struct[@name='StructHeader_function_1']")
    function_2_struct_field = lens_flare_def.find(".//Block[@name='rotation']//Struct[@name='StructHeader_function_1']")

    brightness_block = root.get("brightness")
    color_block = root.get("color")
    rotation_block = root.get("rotation")
    if brightness_block is not None:
        for brightness_element in brightness_block:
            function_header = brightness_element.get("StructHeader_function_1")
            if function_header is not None and function_header["version"] == 0:
                function_header = brightness_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, brightness_element, function_struct_field, file_endian)

    if color_block is not None:
        for color_element in color_block:
            function_1_header = color_element.get("StructHeader_function_1")
            if function_1_header is not None and function_1_header["version"] == 0:
                function_1_header = color_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, color_element, function_1_struct_field, file_endian)

    if rotation_block is not None:
        for rotation_element in rotation_block:
            function_2_header = rotation_element.get("StructHeader_function_1")
            if function_2_header is not None and function_2_header["version"] == 0:
                function_2_header = rotation_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, rotation_element, function_2_struct_field, file_endian)

def light_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    light_def = merged_defs["ligh"]
    root = tag_dict["Data"]

    function_struct_field = light_def.find(".//Block[@name='brightness animation']//Struct[@name='StructHeader_function']")
    function_1_struct_field = light_def.find(".//Block[@name='color animation']//Struct[@name='StructHeader_function']")
    function_2_struct_field = light_def.find(".//Block[@name='gel animation']//Struct[@name='StructHeader_dx']")
    function_3_struct_field = light_def.find(".//Block[@name='gel animation']//Struct[@name='StructHeader_dy']")

    brightness_animation_block = root.get("brightness animation")
    color_animation_block = root.get("color animation")
    gel_animation_block = root.get("gel animation")
    if brightness_animation_block is not None:
        for brightness_animation_element in brightness_animation_block:
            function_header = brightness_animation_element.get("StructHeader_function")
            if function_header is not None and function_header["version"] == 0:
                function_header = brightness_animation_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, brightness_animation_element, function_struct_field, file_endian)

    if color_animation_block is not None:
        for color_animation_element in color_animation_block:
            function_1_header = color_animation_element.get("StructHeader_function")
            if function_1_header is not None and function_1_header["version"] == 0:
                function_1_header = color_animation_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, color_animation_element, function_1_struct_field, file_endian)

    if gel_animation_block is not None:
        for gel_animation_element in gel_animation_block:
            function_2_header = gel_animation_element.get("StructHeader_dx")
            if function_2_header is not None and function_2_header["version"] == 0:
                function_2_header = gel_animation_element["StructHeader_dx"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, gel_animation_element, function_2_struct_field, file_endian)
            function_3_header = gel_animation_element.get("StructHeader_dy")
            if function_3_header is not None and function_3_header["version"] == 0:
                function_3_header = gel_animation_element["StructHeader_dy"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, gel_animation_element, function_3_struct_field, file_endian)

def light_volume_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    light_volume_def = merged_defs["MGS2"]
    root = tag_dict["Data"]

    function_struct_field = light_volume_def.find(".//Block[@name='volumes']//Struct[@name='StructHeader_function']")
    function_1_struct_field = light_volume_def.find(".//Block[@name='volumes']//Struct[@name='StructHeader_function_1']")
    function_2_struct_field = light_volume_def.find(".//Block[@name='volumes']//Struct[@name='StructHeader_function_2']")
    function_3_struct_field = light_volume_def.find(".//Block[@name='volumes']//Struct[@name='StructHeader_function_3']")
    function_4_struct_field = light_volume_def.find(".//Block[@name='volumes']//Struct[@name='StructHeader_function_4']")
    function_5_struct_field = light_volume_def.find(".//Block[@name='volumes']//Block[@name='aspect']//Struct[@name='StructHeader_function']")
    function_6_struct_field = light_volume_def.find(".//Block[@name='volumes']//Block[@name='aspect']//Struct[@name='StructHeader_function_1']")

    volumes_block = root.get("volumes")
    if volumes_block is not None:
        for volume_element in volumes_block:
            function_header = volume_element.get("StructHeader_function")
            if function_header is not None and function_header["version"] == 0:
                function_header = volume_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, volume_element, function_struct_field, file_endian)
            function_1_header = volume_element.get("StructHeader_function_1")
            if function_1_header is not None and function_1_header["version"] == 0:
                function_1_header = volume_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, volume_element, function_1_struct_field, file_endian)
            function_2_header = volume_element.get("StructHeader_function_2")
            if function_2_header is not None and function_2_header["version"] == 0:
                function_2_header = volume_element["StructHeader_function_2"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, volume_element, function_2_struct_field, file_endian)
            function_3_header = volume_element.get("StructHeader_function_3")
            if function_3_header is not None and function_3_header["version"] == 0:
                function_3_header = volume_element["StructHeader_function_3"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, volume_element, function_3_struct_field, file_endian)
            function_4_header = volume_element.get("StructHeader_function_4")
            if function_4_header is not None and function_4_header["version"] == 0:
                function_4_header = volume_element["StructHeader_function_4"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, volume_element, function_4_struct_field, file_endian)

        aspect_block = volume_element.get("aspect")
        if aspect_block is not None:
            for aspect_element in aspect_block:
                function_5_header = aspect_element.get("StructHeader_function")
                if function_5_header is not None and function_5_header["version"] == 0:
                    function_5_header = aspect_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, aspect_element, function_5_struct_field, file_endian)
                function_6_header = aspect_element.get("StructHeader_function_1")
                if function_6_header is not None and function_6_header["version"] == 0:
                    function_6_header = aspect_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, aspect_element, function_6_struct_field, file_endian)

def liquid_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    liquid_def = merged_defs["tdtl"]
    root = tag_dict["Data"]

    function_struct_field = liquid_def.find(".//Block[@name='arcs']//Struct[@name='StructHeader_function']")
    function_1_struct_field = liquid_def.find(".//Block[@name='arcs']//Struct[@name='StructHeader_function_1']")
    function_2_struct_field = liquid_def.find(".//Block[@name='arcs']//Struct[@name='StructHeader_function_2']")
    function_3_struct_field = liquid_def.find(".//Block[@name='arcs']//Struct[@name='StructHeader_function_3']")
    function_4_struct_field = liquid_def.find(".//Block[@name='arcs']//Struct[@name='StructHeader_function_4']")
    function_5_struct_field = liquid_def.find(".//Block[@name='arcs']//Block[@name='cores']//Struct[@name='StructHeader_function']")
    function_6_struct_field = liquid_def.find(".//Block[@name='arcs']//Block[@name='cores']//Struct[@name='StructHeader_function_1']")
    function_7_struct_field = liquid_def.find(".//Block[@name='arcs']//Block[@name='cores']//Struct[@name='StructHeader_function_2']")
    function_8_struct_field = liquid_def.find(".//Block[@name='arcs']//Block[@name='cores']//Struct[@name='StructHeader_function_3']")
    function_9_struct_field = liquid_def.find(".//Block[@name='arcs']//Block[@name='cores']//Struct[@name='StructHeader_function_4']")

    arcs_block = root.get("arcs")
    if arcs_block is not None:
        for arc_element in arcs_block:
            function_header = arc_element.get("StructHeader_function")
            if function_header is not None and function_header["version"] == 0:
                function_header = arc_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, arc_element, function_struct_field, file_endian)
            function_1_header = arc_element.get("StructHeader_function_1")
            if function_1_header is not None and function_1_header["version"] == 0:
                function_1_header = arc_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, arc_element, function_1_struct_field, file_endian)
            function_2_header = arc_element.get("StructHeader_function_2")
            if function_2_header is not None and function_2_header["version"] == 0:
                function_2_header = arc_element["StructHeader_function_2"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, arc_element, function_2_struct_field, file_endian)
            function_3_header = arc_element.get("StructHeader_function_3")
            if function_3_header is not None and function_3_header["version"] == 0:
                function_3_header = arc_element["StructHeader_function_3"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, arc_element, function_3_struct_field, file_endian)
            function_4_header = arc_element.get("StructHeader_function_4")
            if function_4_header is not None and function_4_header["version"] == 0:
                function_4_header = arc_element["StructHeader_function_4"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, arc_element, function_4_struct_field, file_endian)

        cores_block = arc_element.get("cores")
        if cores_block is not None:
            for core_element in cores_block:
                function_5_header = core_element.get("StructHeader_function")
                if function_5_header is not None and function_5_header["version"] == 0:
                    function_5_header = arc_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, core_element, function_5_struct_field, file_endian)
                function_6_header = core_element.get("StructHeader_function_1")
                if function_6_header is not None and function_6_header["version"] == 0:
                    function_6_header = arc_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, core_element, function_6_struct_field, file_endian)
                function_7_header = core_element.get("StructHeader_function_2")
                if function_7_header is not None and function_7_header["version"] == 0:
                    function_7_header = arc_element["StructHeader_function_2"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, core_element, function_7_struct_field, file_endian)
                function_8_header = core_element.get("StructHeader_function_3")
                if function_8_header is not None and function_8_header["version"] == 0:
                    function_8_header = arc_element["StructHeader_function_3"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, core_element, function_8_struct_field, file_endian)
                function_9_header = core_element.get("StructHeader_function_4")
                if function_9_header is not None and function_9_header["version"] == 0:
                    function_9_header = arc_element["StructHeader_function_4"] = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(merged_defs, core_element, function_9_struct_field, file_endian)

def material_effects_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    material_effects_def = merged_defs["foot"]
    root = tag_dict["Data"]

    material_effects_header = tag_dict.get("TagBlockHeader_material_effects")
    if material_effects_header["version"] == 0:
        material_effects_header = tag_dict["TagBlockHeader_material_effects"] = {"name": "tbfd", "version": 1, "size": 12}
        effects_block = root.get("effects")
        if effects_block is not None:
            for effect_element in effects_block:
                effect_element["old materials (DO NOT USE)"] = effect_element.pop("materials", [])
                effect_element["TagBlock_old materials (DO NOT USE)"] = {"unk1": 0, "unk2": 0}
                effect_element["TagBlockHeader_old materials (DO NOT USE)"] = {"name": "tbfd", "version": 0, "size": 44}

def model_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    model_def = merged_defs["hlmt"]
    root = tag_dict["Data"]

    model_header = tag_dict.get("TagBlockHeader_model")
    if model_header is not None and model_header["version"] == 0:
        model_header = tag_dict["TagBlockHeader_model"] = {"name": "tbfd", "version": 1, "size": 348}

        root["physics_model"] = root.pop("physics model", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
        max_draw_distance = root.pop("max draw distance", 0.0)
        root["disappear distance"] = max_draw_distance
        root["begin fade distance"] = max_draw_distance

def model_animation_graph_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    animation_def = merged_defs["jmad"]
    root = tag_dict["Data"]

    resources_header = root.get("StructHeader_resources")
    if resources_header is not None and resources_header["version"] == 0:
        resources_header = root["StructHeader_resources"] = {"name": "MAgr", "version": 2, "size": 80}

        root["private flags"] = root.pop("animation graph flags", 0)

    nodes_block = root.get("skeleton nodes|ABCDCC")
    nodes_header = root.get("TagBlockHeader_skeleton nodes|ABCDCC")
    if nodes_block is not None and nodes_header is not None and nodes_header["version"] == 0:
        nodes_header = root["TagBlockHeader_skeleton nodes|ABCDCC"] = {"name": "tbfd", "version": 1, "size": 32}
        for node_element in nodes_block:
            node_element["node joint flags"] = node_element.pop("Node joint flags", 0)

    animation_block = root.get("animations|ABCDCC")
    animation_header = root.get("TagBlockHeader_animations|ABCDCC")
    if animation_block is not None and animation_header is not None:
        for animation_element in animation_block:
            if animation_header["version"] == 0:
                animation_element["Data"] = animation_element.pop("animation data", 0)
                animation_element["ShortBlockIndex_1"] = animation_element.pop("next animation", -1)
                animation_element["CharInteger"] = animation_element.pop("static node flag data size", 0)
                animation_element["CharInteger_1"] = animation_element.pop("animated node flag data size", 0)
                animation_element["ShortInteger"] = animation_element.pop("movement_data size", 0)
                animation_element["ShortInteger_2"] = animation_element.pop("default_data size", 0)
                animation_element["LongInteger"] = animation_element.pop("uncompressed_data size", 0)
                animation_element["LongInteger_1"] = animation_element.pop("compressed_data size", 0)

                animation_element["StructHeader_Struct"] = {"name": "apds", "version": 0, "size": 16}

            elif animation_header["version"] == 1 or animation_header["version"] == 2 or animation_header["version"] == 3 or animation_header["version"] == 4:
                animation_element["Data"] = animation_element.pop("animation data", 0)
                animation_element["ShortBlockIndex"] = animation_element.pop("parent animation", -1)
                animation_element["ShortBlockIndex_1"] = animation_element.pop("next animation", -1)
                animation_element["StructHeader_Struct"] = animation_element.pop("StructHeader_data sizes",  {"name": "apds", "version": 0, "size": 16})

                if animation_header["version"] == 3:
                    animation_element["ShortInteger"] = animation_element.pop("ShortInteger_3", 0)
                    animation_element["ShortInteger_1"] = animation_element.pop("ShortInteger_4", 0)
                    animation_element["ShortInteger_2"] = animation_element.pop("ShortInteger_5", 0)
                    animation_element["LongInteger"] = animation_element.pop("LongInteger_1", 0)
                    animation_element["LongInteger_1"] = animation_element.pop("LongInteger_2", 0)

        animation_header = root["TagBlockHeader_animations|ABCDCC"] = {"name": "tbfd", "version": 5, "size": 124}

def new_hud_definition_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    hud_def = merged_defs["nhdt"]
    root = tag_dict["Data"]

    function_struct_field = hud_def.find(".//Block[@name='bitmap widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_5']")
    function_1_struct_field = hud_def.find(".//Block[@name='bitmap widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_6']")
    function_2_struct_field = hud_def.find(".//Block[@name='bitmap widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_7']")
    function_3_struct_field = hud_def.find(".//Block[@name='bitmap widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_8']")
    function_4_struct_field = hud_def.find(".//Block[@name='bitmap widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_9']")
    function_5_struct_field = hud_def.find(".//Block[@name='text widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_5']")
    function_6_struct_field = hud_def.find(".//Block[@name='text widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_6']")
    function_7_struct_field = hud_def.find(".//Block[@name='text widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_7']")
    function_8_struct_field = hud_def.find(".//Block[@name='text widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_8']")
    function_9_struct_field = hud_def.find(".//Block[@name='text widgets']//Block[@name='effect']//Struct[@name='StructHeader_function_9']")

    bitmap_widget_block = root.get("bitmap widgets")
    if bitmap_widget_block is not None:
        for bitmap_widget_element in bitmap_widget_block:
            effect_block = bitmap_widget_element.get("effect")
            if effect_block is not None:
                for effect_element in effect_block:
                    function_header = effect_element.get("StructHeader_function_5")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = effect_element["StructHeader_function_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_element, function_struct_field, file_endian)
                    function_1_header = effect_element.get("StructHeader_function_6")
                    if function_1_header is not None and function_1_header["version"] == 0:
                        function_1_header = effect_element["StructHeader_function_6"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_element, function_1_struct_field, file_endian)
                    function_2_header = effect_element.get("StructHeader_function_7")
                    if function_2_header is not None and function_2_header["version"] == 0:
                        function_2_header = effect_element["StructHeader_function_7"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_element, function_2_struct_field, file_endian)
                    function_3_header = effect_element.get("StructHeader_function_8")
                    if function_3_header is not None and function_3_header["version"] == 0:
                        function_3_header = effect_element["StructHeader_function_8"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_element, function_3_struct_field, file_endian)
                    function_4_header = effect_element.get("StructHeader_function_9")
                    if function_4_header is not None and function_4_header["version"] == 0:
                        function_4_header = effect_element["StructHeader_function_9"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_element, function_4_struct_field, file_endian)

    text_widget_block = root.get("text widgets")
    if text_widget_block is not None:
        for text_widget_element in text_widget_block:
            effect_1_block = text_widget_element.get("effect")
            if effect_1_block is not None:
                for effect_1_element in effect_1_block:
                    function_header = effect_1_element.get("StructHeader_function_5")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = effect_1_element["StructHeader_function_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_1_element, function_5_struct_field, file_endian)
                    function_1_header = effect_1_element.get("StructHeader_function_6")
                    if function_1_header is not None and function_1_header["version"] == 0:
                        function_1_header = effect_1_element["StructHeader_function_6"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_1_element, function_6_struct_field, file_endian)
                    function_2_header = effect_1_element.get("StructHeader_function_7")
                    if function_2_header is not None and function_2_header["version"] == 0:
                        function_2_header = effect_1_element["StructHeader_function_7"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_1_element, function_7_struct_field, file_endian)
                    function_3_header = effect_1_element.get("StructHeader_function_8")
                    if function_3_header is not None and function_3_header["version"] == 0:
                        function_3_header = effect_1_element["StructHeader_function_8"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_1_element, function_8_struct_field, file_endian)
                    function_4_header = effect_1_element.get("StructHeader_function_9")
                    if function_4_header is not None and function_4_header["version"] == 0:
                        function_4_header = effect_1_element["StructHeader_function_9"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, effect_1_element, function_9_struct_field, file_endian)

def object_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    object_def = merged_defs["obje"]
    root = tag_dict["Data"]

    function_struct_field = object_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def particle_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    particle_def = merged_defs["prt3"]
    root = tag_dict["Data"]

    function_struct_field = particle_def.find(".//Block[@name='shader parameters']//Block[@name='animation properties']//Struct[@name='StructHeader_function']")
    function_1_struct_field = particle_def.find(".//Struct[@name='StructHeader_Mapping']")
    function_2_struct_field = particle_def.find(".//Struct[@name='StructHeader_Mapping_1']")
    function_3_struct_field = particle_def.find(".//Struct[@name='StructHeader_Mapping_2']")
    function_4_struct_field = particle_def.find(".//Struct[@name='StructHeader_Mapping_3']")
    function_5_struct_field = particle_def.find(".//Struct[@name='StructHeader_Mapping_4']")
    function_6_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping']")
    function_7_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_1']")
    function_8_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_2']")
    function_9_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_3']")
    function_10_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_4']")
    function_11_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_5']")
    function_12_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_6']")
    function_13_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_7']")
    function_14_struct_field = particle_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_8']")
    function_15_struct_field = particle_def.find(".//Block[@name='Block']//Block[@name='overlays']//Struct[@name='StructHeader_function_1']")
    function_16_struct_field = particle_def.find(".//Block[@name='Block']//Block[@name='old levels of detail']//Block[@name='bitmap transform overlays']//Struct[@name='StructHeader_function_1']")
    function_17_struct_field = particle_def.find(".//Block[@name='Block']//Block[@name='old levels of detail']//Block[@name='value overlays']//Struct[@name='StructHeader_function_1']")
    function_18_struct_field = particle_def.find(".//Block[@name='Block']//Block[@name='old levels of detail']//Block[@name='color overlays']//Struct[@name='StructHeader_function_1']")

    function_1_header = root.get("StructHeader_Mapping")
    if function_1_header is not None and function_1_header["version"] == 0:
        function_1_header = root["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_1_struct_field, file_endian)

    function_2_header = root.get("StructHeader_Mapping_1")
    if function_2_header is not None and function_2_header["version"] == 0:
        function_2_header = root["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_2_struct_field, file_endian)

    function_3_header = root.get("StructHeader_Mapping_2")
    if function_3_header is not None and function_3_header["version"] == 0:
        function_3_header = root["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_3_struct_field, file_endian)

    function_4_header = root.get("StructHeader_Mapping_3")
    if function_4_header is not None and function_4_header["version"] == 0:
        function_4_header = root["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_4_struct_field, file_endian)

    function_5_header = root.get("StructHeader_Mapping_4")
    if function_5_header is not None and function_5_header["version"] == 0:
        function_5_header = root["StructHeader_Mapping_4"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_5_struct_field, file_endian)

    shader_parameters_block = root.get("shader parameters")
    if shader_parameters_block is not None:
        for shader_parameters_element in shader_parameters_block:
            animation_properties_block = shader_parameters_element.get("animation properties")
            if animation_properties_block is not None:
                for animation_property_element in animation_properties_block:
                    function_header = animation_property_element.get("StructHeader_function")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = animation_property_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, animation_property_element, function_struct_field, file_endian)

    attached_particle_systems_block = root.get("attached particle systems")
    if attached_particle_systems_block is not None:
        for attached_particle_system_element in attached_particle_systems_block:
            emitters_block = attached_particle_system_element.get("emitters")
            if emitters_block is not None:
                for emitter_element in emitters_block:
                    function_6_header = emitter_element.get("StructHeader_Mapping")
                    if function_6_header is not None and function_6_header["version"] == 0:
                        function_6_header = emitter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_6_struct_field, file_endian)
                    function_7_header = emitter_element.get("StructHeader_Mapping_1")
                    if function_7_header is not None and function_7_header["version"] == 0:
                        function_7_header = emitter_element["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_7_struct_field, file_endian)
                    function_8_header = emitter_element.get("StructHeader_Mapping_2")
                    if function_8_header is not None and function_8_header["version"] == 0:
                        function_8_header = emitter_element["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_8_struct_field, file_endian)
                    function_9_header = emitter_element.get("StructHeader_Mapping_3")
                    if function_9_header is not None and function_9_header["version"] == 0:
                        function_9_header = emitter_element["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_9_struct_field, file_endian)
                    function_10_header = emitter_element.get("StructHeader_Mapping_4")
                    if function_10_header is not None and function_10_header["version"] == 0:
                        function_10_header = emitter_element["StructHeader_Mapping_4"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_10_struct_field, file_endian)
                    function_11_header = emitter_element.get("StructHeader_Mapping_5")
                    if function_11_header is not None and function_11_header["version"] == 0:
                        function_11_header = emitter_element["StructHeader_Mapping_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_11_struct_field, file_endian)
                    function_12_header = emitter_element.get("StructHeader_Mapping_6")
                    if function_12_header is not None and function_12_header["version"] == 0:
                        function_12_header = emitter_element["StructHeader_Mapping_6"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_12_struct_field, file_endian)
                    function_13_header = emitter_element.get("StructHeader_Mapping_7")
                    if function_13_header is not None and function_13_header["version"] == 0:
                        function_13_header = emitter_element["StructHeader_Mapping_7"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_13_struct_field, file_endian)
                    function_14_header = emitter_element.get("StructHeader_Mapping_8")
                    if function_14_header is not None and function_14_header["version"] == 0:
                        function_14_header = emitter_element["StructHeader_Mapping_8"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_14_struct_field, file_endian)

    shader_postprocess_block = root.get("Block")
    if shader_postprocess_block is not None:
        for shader_postprocess_element in shader_postprocess_block:
            overlays_block = shader_postprocess_element.get("overlays")
            if overlays_block is not None:
                for overlay_element in overlays_block:
                    function_15_header = overlay_element.get("StructHeader_function_1")
                    if function_15_header is not None and function_15_header["version"] == 0:
                        function_15_header = overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, overlay_element, function_15_struct_field, file_endian)

            old_levels_of_detail_block = shader_postprocess_element.get("old levels of detail")
            if old_levels_of_detail_block is not None:
                for old_levels_of_detail_element in old_levels_of_detail_block:
                    bitmap_transform_overlays_block = old_levels_of_detail_element.get("bitmap transform overlays")
                    if bitmap_transform_overlays_block is not None:
                        for bitmap_transform_overlay_element in bitmap_transform_overlays_block:
                            function_16_header = bitmap_transform_overlay_element.get("StructHeader_function_1")
                            if function_16_header is not None and function_16_header["version"] == 0:
                                function_16_header = bitmap_transform_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, bitmap_transform_overlay_element, function_16_struct_field, file_endian)

                    value_overlays_block = old_levels_of_detail_element.get("value overlays")
                    if value_overlays_block is not None:
                        for value_overlay_element in value_overlays_block:
                            function_17_header = value_overlay_element.get("StructHeader_function_1")
                            if function_17_header is not None and function_17_header["version"] == 0:
                                function_17_header = value_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, value_overlay_element, function_17_struct_field, file_endian)

                    color_overlays_block = old_levels_of_detail_element.get("color overlays")
                    if color_overlays_block is not None:
                        for color_overlay_element in color_overlays_block:
                            function_18_header = color_overlay_element.get("StructHeader_function_1")
                            if function_18_header is not None and function_18_header["version"] == 0:
                                function_18_header = color_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, color_overlay_element, function_18_struct_field, file_endian)

def particle_model_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    particle_model_def = merged_defs["PRTM"]
    root = tag_dict["Data"]

    function_struct_field = particle_model_def.find(".//Struct[@name='StructHeader_Mapping']")
    function_1_struct_field = particle_model_def.find(".//Struct[@name='StructHeader_Mapping_1']")
    function_2_struct_field = particle_model_def.find(".//Struct[@name='StructHeader_Mapping_2']")
    function_3_struct_field = particle_model_def.find(".//Struct[@name='StructHeader_Mapping_3']")
    function_4_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping']")
    function_5_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_1']")
    function_6_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_2']")
    function_7_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_3']")
    function_8_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_4']")
    function_9_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_5']")
    function_10_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_6']")
    function_11_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_7']")
    function_12_struct_field = particle_model_def.find(".//Block[@name='attached particle systems']//Block[@name='emitters']//Struct[@name='StructHeader_Mapping_8']")

    function_header = root.get("StructHeader_Mapping")
    if function_header is not None and function_header["version"] == 0:
        function_header = root["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_struct_field, file_endian)

    function_1_header = root.get("StructHeader_Mapping_1")
    if function_1_header is not None and function_1_header["version"] == 0:
        function_1_header = root["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_1_struct_field, file_endian)

    function_2_header = root.get("StructHeader_Mapping_2")
    if function_2_header is not None and function_2_header["version"] == 0:
        function_2_header = root["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_2_struct_field, file_endian)

    function_3_header = root.get("StructHeader_Mapping_3")
    if function_3_header is not None and function_3_header["version"] == 0:
        function_3_header = root["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_3_struct_field, file_endian)

    attached_particle_systems_block = root.get("attached particle systems")
    if attached_particle_systems_block is not None:
        for attached_particle_system_element in attached_particle_systems_block:
            emitters_block = attached_particle_system_element.get("emitters")
            if emitters_block is not None:
                for emitter_element in emitters_block:
                    function_4_header = emitter_element.get("StructHeader_Mapping")
                    if function_4_header is not None and function_4_header["version"] == 0:
                        function_4_header = emitter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_4_struct_field, file_endian)
                    function_5_header = emitter_element.get("StructHeader_Mapping_1")
                    if function_5_header is not None and function_5_header["version"] == 0:
                        function_5_header = emitter_element["StructHeader_Mapping_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_5_struct_field, file_endian)
                    function_6_header = emitter_element.get("StructHeader_Mapping_2")
                    if function_6_header is not None and function_6_header["version"] == 0:
                        function_6_header = emitter_element["StructHeader_Mapping_2"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_6_struct_field, file_endian)
                    function_7_header = emitter_element.get("StructHeader_Mapping_3")
                    if function_7_header is not None and function_7_header["version"] == 0:
                        function_7_header = emitter_element["StructHeader_Mapping_3"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_7_struct_field, file_endian)
                    function_8_header = emitter_element.get("StructHeader_Mapping_4")
                    if function_8_header is not None and function_8_header["version"] == 0:
                        function_8_header = emitter_element["StructHeader_Mapping_4"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_8_struct_field, file_endian)
                    function_9_header = emitter_element.get("StructHeader_Mapping_5")
                    if function_9_header is not None and function_9_header["version"] == 0:
                        function_9_header = emitter_element["StructHeader_Mapping_5"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_9_struct_field, file_endian)
                    function_10_header = emitter_element.get("StructHeader_Mapping_6")
                    if function_10_header is not None and function_10_header["version"] == 0:
                        function_10_header = emitter_element["StructHeader_Mapping_6"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_10_struct_field, file_endian)
                    function_11_header = emitter_element.get("StructHeader_Mapping_7")
                    if function_11_header is not None and function_11_header["version"] == 0:
                        function_11_header = emitter_element["StructHeader_Mapping_7"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_11_struct_field, file_endian)
                    function_12_header = emitter_element.get("StructHeader_Mapping_8")
                    if function_12_header is not None and function_12_header["version"] == 0:
                        function_12_header = emitter_element["StructHeader_Mapping_8"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, emitter_element, function_12_struct_field, file_endian)

def particle_physics_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    particle_physics_def = merged_defs["pmov"]
    root = tag_dict["Data"]

    function_struct_field = particle_physics_def.find(".//Block[@name='movements']//Block[@name='parameters']//Struct[@name='StructHeader_Mapping']")

    movements_block = root.get("movements")
    if movements_block is not None:
        for movement_element in movements_block:
            parameters_block = movement_element.get("parameters")
            if parameters_block is not None:
                for parameter_element in parameters_block:
                    function_header = parameter_element.get("StructHeader_Mapping")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = parameter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, parameter_element, function_struct_field, file_endian)

def physics_model_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    physics_model_def = merged_defs["phmo"]
    root = tag_dict["Data"]

    rigid_bodies_block = root.get("rigid bodies")
    rigid_bodies_header = root.get("TagBlockHeader_rigid bodies")
    if rigid_bodies_block is not None and rigid_bodies_header is not None and rigid_bodies_header["version"] == 0:
        for rigid_body_element in rigid_bodies_block:
            rigid_body_element["permutattion"] = rigid_body_element.pop("permutation", 0)

        rigid_bodies_header = root["TagBlockHeader_rigid bodies"] = {"name": "tbfd", "version": 1, "size": 144}

def projectile_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    projectile_def = merged_defs["proj"]
    root = tag_dict["Data"]

    function_struct_field = projectile_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    projectile_header = tag_dict.get("TagBlockHeader_projectile")
    if projectile_header is not None and projectile_header["version"] == 0:
        projectile_header = tag_dict["TagBlockHeader_projectile"] = {"name": "tbfd","version": 1,"size": 604}

        effect_tag = root.pop("effect", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
        root["detonation effect (airborne)"] = effect_tag
        root["detonation effect (ground)"] = effect_tag

        root["guided angular velocity (upper)"] = root.pop("guided angular velocity", 0.0)

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def render_model_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    render_model_def = merged_defs["mode"]
    root = tag_dict["Data"]

    sections_block = root.get("sections")
    if sections_block is not None:
        for section_element in sections_block:
            section_data_block = section_element.get("section data")
            section_data_header = section_element.get("TagBlockHeader_section data")
            if section_data_block is not None and section_data_header is not None:
                for section_data_element in section_data_block:
                    if section_data_header["version"] == 0:
                        section_data_element["raw vertices"] = section_data_element.pop("raw vertices_1", [])
                        section_data_element["strip indices"] = section_data_element.pop("strip indices_1", [])
                        
                        subparts_block = section_data_element.get("TagBlock_subparts")
                        subparts_header = section_data_element.get("TagBlockHeader_subparts")
                        subparts_data = section_data_element.get("subparts")
                        if subparts_block is None:
                            section_data_element["TagBlock_subparts"] = {"unk1": 0, "unk2": 0}
                        if subparts_header is None:
                            section_data_element["TagBlockHeader_subparts"] = {"name": "tbfd", "version": 0, "size": 8}
                        if subparts_data is None:
                            subparts_data = section_data_element["subparts"] = []

                        parts_block = section_data_element.get("TagBlock_parts")
                        parts_header = section_data_element["TagBlockHeader_parts"] = {"name": "tbfd", "version": 0, "size": 72}
                        parts_data = section_data_element.get("parts")
                        if parts_block is None:
                            section_data_element["TagBlock_parts"] = {"unk1": 0, "unk2": 0}
                        if parts_data is None:
                            parts_data = section_data_element["parts"] = []

                        for part_idx, part_element in enumerate(parts_data):
                            part_element["first subpart index"] = part_idx
                            part_element["subpart count"] = 1

                            subparts_element = {
                            "indices_start_index": part_element["strip start index"], 
                            "indices_length": part_element["strip length"], 
                            "visibility_bounds_index": 0,
                            "part index": part_idx
                            }

                            subparts_data.append(subparts_element)

                    section_data_header = section_element["TagBlockHeader_section data"] = {"name": "tbfd", "version": 1, "size": 180}

def scenery_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    scenery_def = merged_defs["scen"]
    root = tag_dict["Data"]

    function_struct_field = scenery_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def shader_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    shader_def = merged_defs["shad"]
    root = tag_dict["Data"]

    function_struct_field = shader_def.find(".//Block[@name='parameters']//Block[@name='animation properties']//Struct[@name='StructHeader_function']")
    function_1_struct_field = shader_def.find(".//Block[@name='postprocess definition']//Block[@name='overlays']//Struct[@name='StructHeader_function_1']")
    function_2_struct_field = shader_def.find(".//Block[@name='postprocess definition']//Block[@name='old levels of detail']//Block[@name='bitmap transform overlays']//Struct[@name='StructHeader_function_1']")
    function_3_struct_field = shader_def.find(".//Block[@name='postprocess definition']//Block[@name='old levels of detail']//Block[@name='value overlays']//Struct[@name='StructHeader_function_1']")
    function_4_struct_field = shader_def.find(".//Block[@name='postprocess definition']//Block[@name='old levels of detail']//Block[@name='color overlays']//Struct[@name='StructHeader_function_1']")

    parameters_block = root.get("parameters")
    if parameters_block is not None:
        for parameter_element in parameters_block:
            animation_properties_block = parameter_element.get("animation properties")
            if animation_properties_block is not None:
                for animation_property_element in animation_properties_block:
                    function_header = animation_property_element.get("StructHeader_function")
                    if function_header is not None and function_header["version"] == 0:
                        function_header = animation_property_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, animation_property_element, function_struct_field, file_endian)

    postprocess_definition_block = root.get("postprocess definition")
    if postprocess_definition_block is not None:
        for postprocess_definition_element in postprocess_definition_block:
            overlays_block = postprocess_definition_element.get("overlays")
            if overlays_block is not None:
                for overlay_element in overlays_block:
                    function_1_header = overlay_element.get("StructHeader_function_1")
                    if function_1_header is not None and function_1_header["version"] == 0:
                        function_1_header = overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, overlay_element, function_1_struct_field, file_endian)

            old_levels_of_detail_block = postprocess_definition_element.get("old levels of detail")
            if old_levels_of_detail_block is not None:
                for old_levels_of_detail_element in old_levels_of_detail_block:
                    bitmap_transform_overlays_block = old_levels_of_detail_element.get("bitmap transform overlays")
                    if bitmap_transform_overlays_block is not None:
                        for bitmap_transform_overlay_element in bitmap_transform_overlays_block:
                            function_2_header = bitmap_transform_overlay_element.get("StructHeader_function_1")
                            if function_2_header is not None and function_2_header["version"] == 0:
                                function_2_header = bitmap_transform_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, bitmap_transform_overlay_element, function_2_struct_field, file_endian)

                    value_overlays_block = old_levels_of_detail_element.get("value overlays")
                    if value_overlays_block is not None:
                        for value_overlay_element in value_overlays_block:
                            function_3_header = value_overlay_element.get("StructHeader_function_1")
                            if function_3_header is not None and function_3_header["version"] == 0:
                                function_3_header = value_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, value_overlay_element, function_3_struct_field, file_endian)

                    color_overlays_block = old_levels_of_detail_element.get("color overlays")
                    if color_overlays_block is not None:
                        for color_overlay_element in color_overlays_block:
                            function_3_header = color_overlay_element.get("StructHeader_function_1")
                            if function_3_header is not None and function_3_header["version"] == 0:
                                function_3_header = color_overlay_element["StructHeader_function_1"] = {"name": "MAPP", "version": 1, "size": 12}
                                upgrade_function(merged_defs, color_overlay_element, function_4_struct_field, file_endian)

def sound_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_def = merged_defs["snd!"]
    root = tag_dict["Data"]

    sound_header = tag_dict.get("TagBlockHeader_sound")
    if sound_header is not None:
        if sound_header["version"] == 0:
            # This version does not transfer this data. Why? - Gen
            outer_cone_gain = root.pop("outer cone gain", 0.0)
            gain_modifier = root.pop("gain modifier", 0.0)
            gain_modifier_min = root.pop("gain modifier_1", 0.0)
            gain_modifier_max = root.pop("gain modifier_2", 0.0)

            pitch_modifier_min = root.pop("pitch modifier", 0.0)
            pitch_modifier_max = root.pop("pitch modifier_1", 0.0)
            skip_fraction_min = root.pop("skip fraction modifier", 0.0)
            skip_fraction_max = root.pop("skip fraction modifier_1", 0.0)

            # CE gain_modifier converter
            # 20 * math.log10(fraction)
            root["outer cone gain"] = outer_cone_gain
            root["gain base"] = gain_modifier 
            root["gain modifier"] = {"Min": gain_modifier_min, "Max": gain_modifier_max}
            root["pitch modifier"] = {"Min": pitch_modifier_min, "Max": pitch_modifier_max}
            root["skip fraction modifier"] = {"Min": skip_fraction_min, "Max": skip_fraction_max}

            root["StructHeader_scale"] = {"name": "snsc", "version": 0, "size": 20}

            if sound_header["version"] == 0 or sound_header["version"] == 1 or sound_header["version"] == 2 or sound_header["version"] == 3 or sound_header["version"] == 4:
                # This version does not transfer this data. Why? - Gen
                output_effect = root.pop("output effect", 0)

                root["CharEnum"] = output_effect

    function_struct_field = sound_def.find(".//Block[@name='pitch ranges']//Struct[@name='StructHeader_Struct']")
    function_1_struct_field = sound_def.find(".//Block[@name='platform parameters']//Block[@name='sound effect']//Block[@name='Block']//Block[@name='overrides']//Struct[@name='StructHeader_function value']")
    function_2_struct_field = sound_def.find(".//Block[@name='platform parameters']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='sound effects']//Block[@name='function inputs']//Struct[@name='StructHeader_function']")
    function_3_struct_field = sound_def.find(".//Block[@name='platform parameters']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='low frequency input']//Struct[@name='StructHeader_function']")
    function_4_struct_field = sound_def.find(".//Struct[@name='StructHeader_Mapping']")

    struct_header = root.get("StructHeader_Mapping")
    if struct_header is not None and struct_header["version"] == 0:
        struct_header = root["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
        upgrade_function(merged_defs, root, function_4_struct_field, file_endian)

    sound_sample_lengths = []
    pitch_ranges_block = root.get("pitch ranges")
    if pitch_ranges_block is not None:
        for pitch_range_element in pitch_ranges_block:
            struct_header = pitch_range_element.get("StructHeader_Struct")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = pitch_range_element["StructHeader_Struct"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, pitch_range_element, function_struct_field, file_endian)

            permutations_block = pitch_range_element.get("permutations")
            if permutations_block is not None:
                for permutation_element in permutations_block:
                    if sound_header["version"] == 0:
                        sample_length = 0
                        samples_data = permutation_element.get("samples")
                        if samples_data is not None:
                            sample_length = permutation_element["samples"]["length"]

                        sound_sample_lengths.append(sample_length)
                    else:
                        sample_length = 0
                        samples_data = permutation_element.get("Data")
                        if samples_data is not None:
                            sample_length = permutation_element["Data"]["length"]

                        sound_sample_lengths.append(sample_length)

    platform_parameters_block = root.get("platform parameters")
    if platform_parameters_block is not None:
        for platform_parameter_element in platform_parameters_block:
            sound_effect_block = platform_parameter_element.get("sound effect")
            if sound_effect_block is not None:
                for sound_effect_element in sound_effect_block:
                    sound_override_block = sound_effect_element.get("Block")
                    if sound_override_block is not None:
                        for sound_override_element in sound_override_block:
                            overrides_block = sound_override_element.get("overrides")
                            if overrides_block is not None:
                                for override_element in overrides_block:
                                    struct_1_header = override_element.get("StructHeader_function value")
                                    if struct_1_header is not None and struct_1_header["version"] == 0:
                                        struct_1_header = override_element["StructHeader_function value"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, override_element, function_1_struct_field, file_endian)

                    sound_effect_collection_block = sound_effect_element.get("Block_1")
                    if sound_effect_collection_block is not None:
                        for sound_effect_collection_element in sound_effect_collection_block:
                            sound_effects_block = sound_effect_collection_element.get("sound effects")
                            if sound_effects_block is not None:
                                for sound_effect_element in sound_effects_block:
                                    function_inputs_block = sound_effect_element.get("function inputs")
                                    if function_inputs_block is not None:
                                        for function_input_element in function_inputs_block:
                                            struct_2_header = function_input_element.get("StructHeader_function")
                                            if struct_2_header is not None and struct_2_header["version"] == 0:
                                                struct_2_header = function_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                                upgrade_function(merged_defs, function_input_element, function_2_struct_field, file_endian)

                            low_frequency_input_block = sound_effect_collection_element.get("low frequency input")
                            if low_frequency_input_block is not None:
                                for low_frequency_input_element in low_frequency_input_block:
                                    struct_3_header = low_frequency_input_element.get("StructHeader_function")
                                    if struct_3_header is not None and struct_3_header["version"] == 0:
                                        struct_3_header = low_frequency_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, low_frequency_input_element, function_3_struct_field, file_endian)

    sound_extra_info_block = root.get("Block")
    if sound_extra_info_block is not None:
        for sound_extra_info_element in sound_extra_info_block:
            language_permutation_info_block = sound_extra_info_element.get("language permutation info")
            language_permutation_info_header = sound_extra_info_element.get("TagBlockHeader_language permutation info")
            if language_permutation_info_block is not None and language_permutation_info_header is not None:
                for perm_idx, language_permutation_info_element in enumerate(language_permutation_info_block):
                    sample_length = sound_sample_lengths[perm_idx]
                    if language_permutation_info_header["version"] == 0:
                        skip_fraction_name = language_permutation_info_element.pop("skip fraction name", "")
                        data = language_permutation_info_element.pop("Data", {"length":0, "unk1":0, "unk2":0, "unk3":0, "unk4":0, "encoded": ""})
                        data_1 = language_permutation_info_element.pop("Data_1", {"length":0, "unk1":0, "unk2":0, "unk3":0, "unk4":0, "encoded": ""})
                        data_2 = language_permutation_info_element.pop("Data_2", {"length":0, "unk1":0, "unk2":0, "unk3":0, "unk4":0, "encoded": ""})
                        sound_permutation_marker = language_permutation_info_element.pop("Block", [])
                        compression = language_permutation_info_element.pop("compression", 0)
                        language = language_permutation_info_element.pop("language", 0)

                        raw_info_block = language_permutation_info_element.get("TagBlock_raw info block v3")
                        raw_info_header = language_permutation_info_element.get("TagBlockHeader_raw info block v3")
                        raw_info_data = language_permutation_info_element.get("raw info block v3")
                        if raw_info_block is None:
                            language_permutation_info_element["TagBlock_raw info block v3"] = {"unk1": 0, "unk2": 0}
                        if raw_info_header is None:
                            language_permutation_info_element["TagBlockHeader_raw info block v3"] = {"name": "tbfd", "version": 2, "size": 12}
                        if raw_info_data is None:
                            raw_info_data = language_permutation_info_element["raw info block v3"] = []

                        raw_info_element = {"skip fraction name": skip_fraction_name, 
                                            "Data": data, 
                                            "Data_1": data_1,
                                            "Data_2": data_2,
                                            "Block": sound_permutation_marker,
                                            "compression": compression,
                                            "language": language,
                                            "Pad": "",
                                            "Block_1": [],
                                            "LongInteger": sample_length}

                        raw_info_data.append(raw_info_element)

                    elif language_permutation_info_header["version"] == 1:
                        raw_info_data = language_permutation_info_element.pop("raw info block", [])
                        language_permutation_info_element["raw info block v3"] = raw_info_data
                        for raw_info_element in language_permutation_info_element["raw info block v3"]:
                            raw_info_element["LongInteger"] = sample_length

    sound_header = tag_dict["TagBlockHeader_sound"] = {"name": "tbfd", "version": 7, "size": 220}

def sound_cache_file_gestalt_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_cache_file_gestalt_def = merged_defs["ugh!"]
    root = tag_dict["Data"]

    function_struct_field = sound_cache_file_gestalt_def.find(".//Block[@name='lowpass cut off parameters']//Struct[@name='StructHeader_Mapping']")
    function_1_struct_field = sound_cache_file_gestalt_def.find(".//Block[@name='custom playbacks']//Block[@name='sound effect']//Block[@name='Block']//Block[@name='overrides']//Struct[@name='StructHeader_function value']")
    function_2_struct_field = sound_cache_file_gestalt_def.find(".//Block[@name='custom playbacks']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='sound effects']//Block[@name='function inputs']//Struct[@name='StructHeader_function']")
    function_3_struct_field = sound_cache_file_gestalt_def.find(".//Block[@name='custom playbacks']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='low frequency input']//Struct[@name='StructHeader_function']")

    lowpass_cut_off_parameters_block = root.get("lowpass cut off parameters")
    if lowpass_cut_off_parameters_block is not None:
        for parameter_element in lowpass_cut_off_parameters_block:
            struct_header = parameter_element.get("StructHeader_Mapping")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = parameter_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, parameter_element, function_struct_field, file_endian)

    custom_playbacks_block = root.get("custom playbacks")
    if custom_playbacks_block is not None:
        for platform_parameter_element in custom_playbacks_block:
            sound_effect_block = platform_parameter_element.get("sound effect")
            if sound_effect_block is not None:
                for sound_effect_element in sound_effect_block:
                    sound_override_block = sound_effect_element.get("Block")
                    if sound_override_block is not None:
                        for sound_override_element in sound_override_block:
                            overrides_block = sound_override_element.get("overrides")
                            if overrides_block is not None:
                                for override_element in overrides_block:
                                    struct_1_header = override_element.get("StructHeader_function value")
                                    if struct_1_header is not None and struct_1_header["version"] == 0:
                                        struct_1_header = override_element["StructHeader_function value"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, override_element, function_1_struct_field, file_endian)

                    sound_effect_collection_block = sound_effect_element.get("Block_1")
                    if sound_effect_collection_block is not None:
                        for sound_effect_collection_element in sound_effect_collection_block:
                            sound_effects_block = sound_effect_collection_element.get("sound effects")
                            if sound_effects_block is not None:
                                for sound_effect_element in sound_effects_block:
                                    function_inputs_block = sound_effect_element.get("function inputs")
                                    if function_inputs_block is not None:
                                        for function_input_element in function_inputs_block:
                                            struct_2_header = function_input_element.get("StructHeader_function")
                                            if struct_2_header is not None and struct_2_header["version"] == 0:
                                                struct_2_header = function_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                                upgrade_function(merged_defs, function_input_element, function_2_struct_field, file_endian)

                            low_frequency_input_block = sound_effect_collection_element.get("low frequency input")
                            if low_frequency_input_block is not None:
                                for low_frequency_input_element in low_frequency_input_block:
                                    struct_3_header = low_frequency_input_element.get("StructHeader_function")
                                    if struct_3_header is not None and struct_3_header["version"] == 0:
                                        struct_3_header = low_frequency_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, low_frequency_input_element, function_3_struct_field, file_endian)

def sound_classes_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_classes_def = merged_defs["sncl"]
    root = tag_dict["Data"]

    function_struct_field = sound_classes_def.find(".//Block[@name='sound classes']//Struct[@name='StructHeader_Mapping']")

    sound_classes_block = root.get("sound classes")
    if sound_classes_block is not None:
        for sound_classes_element in sound_classes_block:
            struct_header = sound_classes_element.get("StructHeader_Mapping")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = sound_classes_element["StructHeader_Mapping"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, sound_classes_element, function_struct_field, file_endian)

def sound_effect_collection_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_effect_collection_def = merged_defs["sfx+"]
    root = tag_dict["Data"]

    function_struct_field = sound_effect_collection_def.find(".//Block[@name='sound effects']//Block[@name='sound effect']//Block[@name='Block']//Block[@name='overrides']//Struct[@name='StructHeader_function value']")
    function_1_struct_field = sound_effect_collection_def.find(".//Block[@name='sound effects']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='sound effects']//Block[@name='function inputs']//Struct[@name='StructHeader_function']")
    function_2_struct_field = sound_effect_collection_def.find(".//Block[@name='sound effects']//Block[@name='sound effect']//Block[@name='Block_1']//Block[@name='low frequency input']//Struct[@name='StructHeader_function']")

    sound_effects_block = root.get("sound effects")
    if sound_effects_block is not None:
        for sound_effects_element in sound_effects_block:
            sound_effect_block = sound_effects_element.get("sound effect")
            if sound_effect_block is not None:
                for sound_effect_element in sound_effect_block:
                    sound_override_block = sound_effect_element.get("Block")
                    if sound_override_block is not None:
                        for sound_override_element in sound_override_block:
                            overrides_block = sound_override_element.get("overrides")
                            if overrides_block is not None:
                                for override_element in overrides_block:
                                    struct_1_header = override_element.get("StructHeader_function value")
                                    if struct_1_header is not None and struct_1_header["version"] == 0:
                                        struct_1_header = override_element["StructHeader_function value"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, override_element, function_struct_field, file_endian)

                    sound_effect_collection_block = sound_effect_element.get("Block_1")
                    if sound_effect_collection_block is not None:
                        for sound_effect_collection_element in sound_effect_collection_block:
                            inner_sound_effects_block = sound_effect_collection_element.get("sound effects")
                            if inner_sound_effects_block is not None:
                                for inner_sound_effect_element in inner_sound_effects_block:
                                    function_inputs_block = inner_sound_effect_element.get("function inputs")
                                    if function_inputs_block is not None:
                                        for function_input_element in function_inputs_block:
                                            struct_2_header = function_input_element.get("StructHeader_function")
                                            if struct_2_header is not None and struct_2_header["version"] == 0:
                                                struct_2_header = function_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                                upgrade_function(merged_defs, function_input_element, function_1_struct_field, file_endian)

                            low_frequency_input_block = sound_effect_collection_element.get("low frequency input")
                            if low_frequency_input_block is not None:
                                for low_frequency_input_element in low_frequency_input_block:
                                    struct_3_header = low_frequency_input_element.get("StructHeader_function")
                                    if struct_3_header is not None and struct_3_header["version"] == 0:
                                        struct_3_header = low_frequency_input_element["StructHeader_function"] = {"name": "MAPP", "version": 1, "size": 12}
                                        upgrade_function(merged_defs, low_frequency_input_element, function_2_struct_field, file_endian)

def sound_effect_template_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_effect_template_def = merged_defs["<fx>"]
    root = tag_dict["Data"]

    function_1_struct_field = sound_effect_template_def.find(".//Block[@name='template collection']//Block[@name='parameters']//Struct[@name='StructHeader_default function']")
    function_2_struct_field = sound_effect_template_def.find(".//Block[@name='additional sound inputs']//Struct[@name='StructHeader_low frequency sound']")
    
    sound_effect_template_header = tag_dict.get("TagBlockHeader_sound_effect_template")
    if sound_effect_template_header is not None and sound_effect_template_header["version"] == 0:
        sound_effect_template_header = tag_dict["TagBlockHeader_sound_effect_template"] = {"name": "tbfd", "version": 1, "size": 40}

        template_collection_block = root.get("TagBlock_template collection")
        template_collection_header = root.get("TagBlockHeader_template collection")
        template_collection_data = root.get("template collection")
        if template_collection_block is None:
            root["TagBlock_template collection"] = {"unk1": 0, "unk2": 0}
        if template_collection_header is None:
            root["TagBlockHeader_template collection"] = {"name": "tbfd", "version": 0, "size": 44}
        if template_collection_data is None:
            template_collection_data = root["template collection"] = []

        template_element = {
                            "dsp effect": root.pop("dsp effect", ""), 
                            "explanation": root.pop("explanation", {"length":0, "unk1":0, "unk2":0, "unk3":0, "unk4":0, "encoded": ""}), 
                            "flags": root.pop("flags", 0),
                            "ShortInteger": root.pop("ShortInteger", 0),
                            "ShortInteger_1": root.pop("ShortInteger_1", 0),
                            "TagBlock_parameters": root.pop("TagBlock_parameters", {"unk1": 0,"unk2": 0}),
                            "TagBlockHeader_parameters": root.pop("TagBlockHeader_parameters", {"name": "tbfd", "version": 0, "size": 40}),
                            "parameters": root.pop("parameters", [])
                            }

        template_collection_data.append(template_element)

    template_collection_block = root.get("template collection")
    if template_collection_block is not None:
        for template_element in template_collection_block:
            parameters_block = template_element.get("parameters")
            if parameters_block is not None:
                for parameter_element in parameters_block:
                    struct_1_header = parameter_element.get("StructHeader_default function")
                    if struct_1_header is not None and struct_1_header["version"] == 0:
                        struct_1_header = parameter_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                        upgrade_function(merged_defs, parameter_element, function_1_struct_field, file_endian)

    additional_sound_inputs_block = root.get("additional sound inputs")
    if additional_sound_inputs_block is not None:
        for additional_sound_input_element in additional_sound_inputs_block:
            struct_1_header = additional_sound_input_element.get("StructHeader_low frequency sound")
            if struct_1_header is not None and struct_1_header["version"] == 0:
                struct_1_header = additional_sound_input_element["StructHeader_low frequency sound"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, additional_sound_input_element, function_2_struct_field, file_endian)

def sound_looping_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_looping_def = merged_defs["lsnd"]
    root = tag_dict["Data"]

    sound_looping_header = tag_dict.get("TagBlockHeader_sound_looping")
    if sound_looping_header is not None and sound_looping_header["version"] == 0:
        sound_looping_header = tag_dict["TagBlockHeader_sound_looping"] = {"name": "tbfd", "version": 3, "size": 76}

        root["TagReference"] = root.pop("continuous damage effect", 0.0)

    tracks_block = root.get("tracks")
    tracks_header = root.get("TagBlockHeader_tracks")
    if tracks_block is not None and tracks_header is not None:
        for track_element in tracks_block:
            if tracks_header["version"] == 0:
                track_element["name"] = "reimport_me"

                # This version does not transfer this data. Why? - Gen
                gain = track_element.pop("gain", 0.0)
                track_element["gain"] = gain

                track_element["in"] = track_element.pop("start", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                track_element["loop"] = track_element.pop("loop", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                track_element["out"] = track_element.pop("end", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                track_element["alt loop"] = track_element.pop("alternate loop", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                track_element["alt out"] = track_element.pop("alternate end", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})

    detail_sounds_block = root.get("detail sounds")
    detail_sounds_header = root.get("TagBlockHeader_detail sounds")
    if detail_sounds_block is not None and detail_sounds_header is not None:
        for detail_sound_element in detail_sounds_block:
            if detail_sounds_header["version"] == 0:
                detail_sound_element["name"] = "reimport_me"

                # This version does not transfer this data. Why? - Gen
                sound_tag = detail_sound_element.pop("sound", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                random_period_bounds = detail_sound_element.pop("random period bounds", {"Min": 0.0, "Max": 0.0})
                gain = detail_sound_element.pop("gain", 0.0)
                flags = detail_sound_element.pop("flags", 0)
                yaw_bounds = detail_sound_element.pop("yaw bounds", {"Min": 0.0, "Max": 0.0})
                pitch_bounds = detail_sound_element.pop("pitch bounds", {"Min": 0.0, "Max": 0.0})
                distance_bounds = detail_sound_element.pop("distance bounds", {"Min": 0.0, "Max": 0.0})
                detail_sound_element["sound"] = sound_tag
                detail_sound_element["random period bounds"] = random_period_bounds
                detail_sound_element["Real"] = gain
                detail_sound_element["flags"] = flags
                detail_sound_element["yaw bounds"] = yaw_bounds
                detail_sound_element["pitch bounds"] = pitch_bounds
                detail_sound_element["distance bounds"] = distance_bounds

def sound_scenery_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    sound_scenery_def = merged_defs["ssce"]
    root = tag_dict["Data"]

    function_struct_field = sound_scenery_def.find(f".//Struct[@name='{"StructHeader_default function"}']")

    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

def unit_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    unit_def = merged_defs["unit"]
    root = tag_dict["Data"]

    function_struct_field = unit_def.find(f".//Struct[@name='{"StructHeader_default function"}']")
    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

    seats_block = root.get("seats")
    seat_header = root.get("TagBlockHeader_seats")
    if seats_block is not None and seat_header is not None and not seat_header["version"] == 3:
        for seat_element in seats_block:
            if seat_header["version"] == 0:
                yaw = seat_element.pop("yaw rate", 0.0)
                seat_element["yaw rate bounds"] = {"Min": yaw, "Max": yaw}

                pitch = seat_element.pop("pitch rate", 0.0)
                seat_element["pitch rate bounds"] = {"Min": pitch, "Max": pitch}

            seat_element["acceleration range"] = seat_element.pop("acceleration scale", (0.0, 0.0, 0.0))
            seat_element["StructHeader_acceleration"] = {"name": "usas", "version": 0, "size": 20}

        seat_header = root["TagBlockHeader_seats"] = {"name": "tbfd", "version": 3, "size": 192}

def vehicle_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    vehicle_def = merged_defs["vehi"]
    root = tag_dict["Data"]

    function_struct_field = vehicle_def.find(f".//Struct[@name='{"StructHeader_default function"}']")
    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

    seats_block = root.get("seats")
    seat_header = root.get("TagBlockHeader_seats")
    if seats_block is not None and seat_header is not None and not seat_header["version"] == 3:
        for seat_element in seats_block:
            if seat_header["version"] == 0:
                yaw = seat_element.pop("yaw rate", 0.0)
                seat_element["yaw rate bounds"] = {"Min": yaw, "Max": yaw}

                pitch = seat_element.pop("pitch rate", 0.0)
                seat_element["pitch rate bounds"] = {"Min": pitch, "Max": pitch}

            seat_element["acceleration range"] = seat_element.pop("acceleration scale", (0.0, 0.0, 0.0))
            seat_element["StructHeader_acceleration"] = {"name": "usas", "version": 0, "size": 20}

        seat_header = root["TagBlockHeader_seats"] = {"name": "tbfd", "version": 3, "size": 192}

def weapon_postprocess(merged_defs, tag_dict, file_endian, tag_directory):
    weapon_def = merged_defs["weap"]
    root = tag_dict["Data"]

    weapon_header = tag_dict.get("TagBlockHeader_weapon")
    if weapon_header is not None:
        if weapon_header["version"] == 0 or weapon_header["version"] == 1:
            if weapon_header["version"] == 0:
                root["weapon power-on time"] = root.pop("light power-on time", 0.0)
                root["weapon power-off time"] = root.pop("light power-on time", 0.0)
                root["weapon power-on effect"] = root.pop("light power-on effect", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
                root["weapon power-off effect"] = root.pop("light power-off effect", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})

            first_person_block = root.get("TagBlock_first person")
            first_person_header = root.get("TagBlockHeader_first person")
            first_person_data = root.get("first person")
            if first_person_block is None:
                root["TagBlock_first person"] = {"unk1": 0, "unk2": 0}
            if first_person_header is None:
                root["TagBlockHeader_first person"] = {"name": "tbfd", "version": 0, "size": 88}
            if first_person_data is None:
                first_person_data = root["first person"] = []

            fp_model = root.pop("first person model", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})
            fp_anim = root.pop("first person animations", {"group name": -1," unk1": 0," length": 0," unk2": -1," path": ""})

            first_person_spartan_element = {
                                "first person model": fp_model, 
                                "first person animations": fp_anim
                                }
            
            # Lets try to find the elite equivelent if we have spartan tags. - Gen
            spartan_path = r"objects\characters\masterchief"
            elite_path = r"objects\characters\dervish"
            elite_fp_model = fp_model.copy()
            elite_fp_anim = fp_anim.copy()
            if elite_fp_model.path.startswith(spartan_path):
                elite_fp_model_path = os.path.join(tag_directory, "%s.render_model" % elite_fp_model.path.replace(spartan_path, elite_path, 1))
                if os.path.isfile(elite_fp_model_path):
                    elite_fp_model = {"group name": "mode"," unk1": 0," length": len(elite_fp_model_path)," unk2": -1," path": elite_fp_model_path}

            if elite_fp_anim.path.startswith(spartan_path):
                elite_fp_anim_path = os.path.join(tag_directory, "%s.model_animation_graph" % elite_fp_anim.path.replace(spartan_path, elite_path, 1))
                if os.path.isfile(elite_fp_anim_path):
                    elite_fp_anim = {"group name": "jmad"," unk1": 0," length": len(elite_fp_model_path)," unk2": -1," path": elite_fp_anim_path}

            first_person_elite_element = {
                                "first person model": elite_fp_model, 
                                "first person animations": elite_fp_anim
                                }

            first_person_data.append(first_person_spartan_element)
            first_person_data.append(first_person_elite_element)

    function_struct_field = weapon_def.find(f".//Struct[@name='{"StructHeader_default function"}']")
    function_block = root.get("functions")
    if function_block is not None:
        for function_element in function_block:
            struct_header = function_element.get("StructHeader_default function")
            if struct_header is not None and struct_header["version"] == 0:
                struct_header = function_element["StructHeader_default function"] = {"name": "MAPP", "version": 1, "size": 12}
                upgrade_function(merged_defs, function_element, function_struct_field, file_endian)

postprocess_functions = {
    "obje": object_postprocess,
    "devi": device_postprocess,
    "item": item_postprocess,
    "unit": unit_postprocess,
    "hlmt": model_postprocess,
    "mode": render_model_postprocess,
    "coll": collision_model_postprocess,
    "phmo": physics_model_postprocess,
    "bitm": bitmap_postprocess,
    "colo": None,
    "unic": None,
    "bipd": biped_postprocess,
    "vehi": vehicle_postprocess,
    "scen": scenery_postprocess,
    "bloc": crate_postprocess,
    "crea": creature_postprocess,
    "phys": None,
    "cont": None,
    "weap": weapon_postprocess,
    "ligh": light_postprocess,
    "effe": effect_postprocess,
    "prt3": particle_postprocess,
    "PRTM": particle_model_postprocess,
    "pmov": particle_physics_postprocess,
    "matg": globals_postprocess,
    "snd!": sound_postprocess,
    "lsnd": sound_looping_postprocess,
    "eqip": equipment_postprocess,
    "ant!": None,
    "MGS2": light_volume_postprocess,
    "tdtl": liquid_postprocess,
    "devo": None,
    "whip": None,
    "BooM": None,
    "trak": None,
    "proj": projectile_postprocess,
    "mach": device_machine_postprocess,
    "ctrl": device_control_postprocess,
    "lifi": device_light_fixture_postprocess,
    "pphy": None,
    "ltmp": None,
    "sbsp": None,
    "scnr": None,
    "shad": shader_postprocess,
    "stem": None,
    "slit": None,
    "spas": None,
    "vrtx": None,
    "pixl": None,
    "DECR": None,
    "sky ": None,
    "wind": None,
    "snde": None,
    "lens": lens_flare_postprocess,
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
    "nhdt": new_hud_definition_postprocess,
    "hud#": None,
    "hudg": None,
    "mply": None,
    "dobc": None,
    "ssce": sound_scenery_postprocess,
    "hmt ": None,
    "wgit": None,
    "skin": None,
    "wgtz": None,
    "wigl": None,
    "sily": None,
    "goof": None,
    "foot": material_effects_postprocess,
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
    "sncl": sound_classes_postprocess,
    "mulg": None,
    "<fx>": sound_effect_template_postprocess,
    "sfx+": sound_effect_collection_postprocess,
    "gldf": chocolate_mountain_postprocess,
    "jmad": model_animation_graph_postprocess,
    "clwd": None,
    "egor": None,
    "weat": None,
    "snmx": None,
    "spk!": None,
    "ugh!": sound_cache_file_gestalt_postprocess,
    "$#!+": None,
    "mcsr": None,
    "tag+": None,
}
