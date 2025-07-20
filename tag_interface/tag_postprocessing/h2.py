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

def upgrade_function(field_node, tag_block_fields, endian_override):
    tree = ET.parse(r"C:\Users\Steven\Documents\GitHub\Halo-Tag-Interface\tag_interface\layouts\h2\common\function_defintions.xml")
    field_node = tree.getroot()

    field_set_0 = None
    field_set_1 = None
    for layout in field_node:
        if layout.get("regolithID") == "structure:mapping_function":
            for struct_field_set in layout:
                if int(struct_field_set.attrib.get('version')) == 0:
                    field_set_0 = struct_field_set
                elif int(struct_field_set.attrib.get('version')) == 1:
                    field_set_1 = struct_field_set
            break

    function_type_result = 0
    flag_result = 0
    function_stream = io.BytesIO()
    for field_node_element in field_set_0:
        unsigned_key = field_node.get("unsigned")
        field_endian = field_node_element.get("endianOverride")
        if field_endian:
            endian_override = field_endian

        field_key = field_node_element.get("name")
        field_tag = field_node_element.tag
        if field_tag == "RgbColor":
            struct_string = '%s4B' % endian_override
            result = get_result(field_key, tag_block_fields)
            color_pad_result = get_result("%s_pad" % field_key, tag_block_fields)
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
            tag_block_value = tag_block_fields.pop(field_key, [])
            for tag_element in tag_block_value:
                write_real(function_stream, struct_string, tag_element["Value"])

        elif field_tag == "CharInteger":
            struct_string = '%sb' % endian_override
            if unsigned_key:
                struct_string = uppercase_struct_letters(struct_string)
            result = get_result(field_key, tag_block_fields)
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
            result = get_result(field_key, tag_block_fields)
            if field_key.startswith("Flags"):
                flag_result = result
            if result is not None:
                function_stream.write(struct.pack(struct_string, result))
            else:
                function_stream.write(struct.pack(struct_string, 0))

    for field_node_element in field_set_1:
        unsigned_key = field_node.get("unsigned")
        field_endian = field_node_element.get("endianOverride")
        if field_endian:
            endian_override = field_endian

        field_key = field_node_element.get("name")
        field_tag = field_node_element.tag
        if field_tag == "Block":
            tag_block = tag_block_fields[field_key] = []
            for byte in function_stream.getbuffer():
                signed_byte = byte if byte < 128 else byte - 256
                tag_block.append({"Value": signed_byte})

def biped_postprocess(tag_dict, file_endian, preserve_version):
    if not preserve_version:
        root = tag_dict["Data"]
        tag_block_version = 1
        tag_block_header = root.get("TagBlockHeader_biped")
        if tag_block_header is not None:
            tag_block_version = tag_block_header["version"]

        if tag_block_version == 0:
            root["flags_2"] = root.pop("Skip", 0)

            root["height standing"] = root.pop("standing collision height", 0.0)
            root["height crouching"] = root.pop("crouching collision height", 0.0)
            root["radius"] = root.pop("collision radius", 0.0)
            root["mass"] = root.pop("collision mass", 0.0)
            root["living material name"] = root.pop("collision global material name", "")
            root["dead material name"] = root.pop("dead collision global material name", "")

            root["StructHeader_%s" % "structure:character_physics_ground"] = {"name": "chgr", "version": 0, "size": 48}
            root["StructHeader_%s" % "structure:character_physics_flying"] = {"name": "chfl", "version": 0, "size": 44}

        function_tag_block = root.get("functions")
        if function_tag_block is not None:
            for function_element in function_tag_block:
                struct_header = function_element.get("StructHeader_%s" % "structure:mapping_function")
                if struct_header["name"] == "MAPP" and struct_header["version"] == 0:
                    struct_header = {"name": "MAPP", "version": 1, "size": 12}
                    upgrade_function(function_element, function_element, file_endian)

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
                seat_element["StructHeader_%s" % "structure:unit_seat_acceleration"] = {"name": "usas", "version": 0, "size": 20}

def bitmap_postprocess(tag_dict, file_endian, preserve_version):
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

def character_postprocess(tag_dict, file_endian, preserve_version):
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




postprocess_functions = {
    "obje": None,
    "devi": None,
    "item": None,
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
    "bloc": None,
    "crea": None,
    "phys": None,
    "cont": None,
    "weap": None,
    "ligh": None,
    "effe": None,
    "prt3": None,
    "PRTM": None,
    "pmov": None,
    "matg": None,
    "snd!": None,
    "lsnd": None,
    "eqip": None,
    "ant!": None,
    "MGS2": None,
    "tdtl": None,
    "devo": None,
    "whip": None,
    "BooM": None,
    "trak": None,
    "proj": None,
    "mach": None,
    "ctrl": None,
    "lifi": None,
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
    "jpt!": None,
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
    "garb": None,
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
    "bsdt": None,
    "mpdt": None,
    "sncl": None,
    "mulg": None,
    "<fx>": None,
    "sfx+": None,
    "gldf": None,
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
