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

current_dir = os.path.dirname(os.path.abspath(__file__))
h1_defs_directory = os.path.join(current_dir, "layouts", "h1")
h2_defs_directory = os.path.join(current_dir, "layouts", "h2")

h1_tag_groups = {
    "actr": "actor",
	"actv": "actor_variant",
	"ant!": "antenna",
	"antr": "model_animations",
	"bipd": "biped",
	"bitm": "bitmap",
	"boom": "spheroid",
	"cdmg": "continuous_damage_effect",
	"coll": "model_collision_geometry",
	"colo": "color_table",
	"cont": "contrail",
	"ctrl": "device_control",
	"deca": "decal",
	"DeLa": "ui_widget_definition",
	"devc": "input_device_defaults",
	"devi": "device",
	"dobc": "detail_object_collection",
	"effe": "effect",
	"elec": "lightning",
	"eqip": "equipment",
	"flag": "flag",
	"fog ": "fog",
	"font": "font",
	"foot": "material_effects",
	"garb": "garbage",
	"glw!": "glow",
	"grhi": "grenade_hud_interface",
	"hmt ": "hud_message_text",
	"hud#": "hud_number",
	"hudg": "hud_globals",
	"item": "item",
	"itmc": "item_collection",
	"jpt!": "damage_effect",
	"lens": "lens_flare",
	"lifi": "device_light_fixture",
	"ligh": "light",
	"lsnd": "sound_looping",
	"mach": "device_machine",
	"matg": "globals",
	"metr": "meter",
	"mgs2": "light_volume",
	"mod2": "gbxmodel",
	"mode": "model",
	"mply": "multiplayer_scenario_description",
	"ngpr": "preferences_network_game",
	"obje": "object",
	"part": "particle",
	"pctl": "particle_system",
	"phys": "physics",
	"plac": "placeholder",
	"pphy": "point_physics",
	"proj": "projectile",
	"rain": "weather_particle_system",
	"sbsp": "scenario_structure_bsp",
	"scen": "scenery",
	"scex": "shader_transparent_chicago_extended",
	"schi": "shader_transparent_chicago",
	"scnr": "scenario",
	"senv": "shader_environment",
	"sgla": "shader_transparent_glass",
	"shdr": "shader",
	"sky ": "sky",
	"smet": "shader_transparent_meter",
	"snd!": "sound",
	"snde": "sound_environment",
	"soso": "shader_model",
	"sotr": "shader_transparent_generic",
	"Soul": "ui_widget_collection",
	"spla": "shader_transparent_plasma",
	"ssce": "sound_scenery",
	"str#": "string_list",
	"swat": "shader_transparent_water",
	"tagc": "tag_collection",
	"trak": "camera_track",
	"udlg": "dialogue",
	"unhi": "unit_hud_interface",
	"unit": "unit",
	"ustr": "unicode_string_list",
	"vcky": "virtual_keyboard",
	"vehi": "vehicle",
	"weap": "weapon",
	"wind": "wind",
	"wphi": "weapon_hud_interface"
    }

h2_tag_groups = {
            "obje": "object",
            "devi": "device",
            "item": "item",
            "unit": "unit",
            "hlmt": "model",
            "DECP": "decorators",
            "mode": "render_model",
            "coll": "collision_model",
            "phmo": "physics_model",
            "bitm": "bitmap",
            "colo": "color_table",
            "unic": "multilingual_unicode_string_list",
            "bipd": "biped",
            "vehi": "vehicle",
            "scen": "scenery",
            "bloc": "crate",
            "crea": "creature",
            "phys": "physics",
            "cont": "contrail",
            "weap": "weapon",
            "ligh": "light",
            "effe": "effect",
            "prt3": "particle",
            "PRTM": "particle_model",
            "pmov": "particle_physics",
            "matg": "globals",
            "snd!": "sound",
            "lsnd": "sound_looping",
            "eqip": "equipment",
            "ant!": "antenna",
            "MGS2": "light_volume",
            "tdtl": "liquid",
            "devo": "cellular_automata",
            "whip": "cellular_automata2d",
            "BooM": "stereo_system",
            "trak": "camera_track",
            "proj": "projectile",
            "mach": "device_machine",
            "ctrl": "device_control",
            "lifi": "device_light_fixture",
            "pphy": "point_physics",
            "ltmp": "scenario_structure_lightmap",
            "sbsp": "scenario_structure_bsp",
            "scnr": "scenario",
            "shad": "shader",
            "stem": "shader_template",
            "slit": "shader_light_response",
            "spas": "shader_pass",
            "vrtx": "vertex_shader",
            "pixl": "pixel_shader",
            "DECR": "decorator_set",
            "sky ": "sky",
            "wind": "wind",
            "snde": "sound_environment",
            "lens": "lens_flare",
            "fog ": "planar_fog",
            "fpch": "patchy_fog",
            "metr": "meter",
            "deca": "decal",
            "coln": "colony",
            "jpt!": "damage_effect",
            "udlg": "dialogue",
            "itmc": "item_collection",
            "vehc": "vehicle_collection",
            "wphi": "weapon_hud_interface",
            "grhi": "grenade_hud_interface",
            "unhi": "unit_hud_interface",
            "nhdt": "new_hud_definition",
            "hud#": "hud_number",
            "hudg": "hud_globals",
            "mply": "multiplayer_scenario_description",
            "dobc": "detail_object_collection",
            "ssce": "sound_scenery",
            "hmt ": "hud_message_text",
            "wgit": "user_interface_screen_widget_definition",
            "skin": "user_interface_list_skin_definition",
            "wgtz": "user_interface_globals_definition",
            "wigl": "user_interface_shared_globals_definition",
            "sily": "text_value_pair_definition",
            "goof": "multiplayer_variant_settings_interface_definition",
            "foot": "material_effects",
            "garb": "garbage",
            "styl": "style",
            "char": "character",
            "adlg": "ai_dialogue_globals",
            "mdlg": "ai_mission_dialogue",
            "*cen": "scenario_scenery_resource",
            "*ipd": "scenario_bipeds_resource",
            "*ehi": "scenario_vehicles_resource",
            "*qip": "scenario_equipment_resource",
            "*eap": "scenario_weapons_resource",
            "*sce": "scenario_sound_scenery_resource",
            "*igh": "scenario_lights_resource",
            "dgr*": "scenario_devices_resource",
            "dec*": "scenario_decals_resource",
            "cin*": "scenario_cinematics_resource",
            "trg*": "scenario_trigger_volumes_resource",
            "clu*": "scenario_cluster_data_resource",
            "*rea": "scenario_creature_resource",
            "dc*s": "scenario_decorators_resource",
            "sslt": "scenario_structure_lighting_resource",
            "hsc*": "scenario_hs_source_file",
            "ai**": "scenario_ai_resource",
            "/**/": "scenario_comments_resource",
            "bsdt": "breakable_surface",
            "mpdt": "material_physics",
            "sncl": "sound_classes",
            "mulg": "multiplayer_globals",
            "<fx>": "sound_effect_template",
            "sfx+": "sound_effect_collection",
            "gldf": "chocolate_mountain",
            "jmad": "model_animation_graph",
            "clwd": "cloth",
            "egor": "screen_effect",
            "weat": "weather_system",
            "snmx": "sound_mix",
            "spk!": "sound_dialogue_constants",
            "ugh!": "sound_cache_file_gestalt",
            "$#!+": "cache_file_sound",
            "mcsr": "mouse_cursor_definition",
            "tag+": "tag_database"}

h1_tag_extensions = {ext: group for group, ext in h1_tag_groups.items()}
h2_tag_extensions = {ext: group for group, ext in h2_tag_groups.items()}

invader_key_conversion = {
    "Angle": "Angle",
    "ColorARGBFloat": "RealArgbColor",
    "ColorARGBInt": "ArgbColor",
    "ColorRGBFloat": "RealRgbColor",
    "Data": "Data",
    "Euler2D": "RealEulerAngles2D",
    "ID": "LongInteger",
    "Index": "ShortInteger",
    "Rectangle": "Rectangle2D",
    "Reflexive": "Block",
    "String32": "String",
    "TagID": "LongInteger",
    "TagReference": "TagReference",
    "Vector2D": "RealPoint2D",
    "Vector2DInt": "Point2D",
    "Vector3D": "RealVector3D",
    "bitfield16": "WordFlags",
    "bitfield32": "LongFlags",
    "bitfield8": "ByteFlags",
    "editor_section": "Explanation",
    "enum": "ShortEnum",
    "float": "Real",
    "int16": "ShortInteger",
    "int32": "LongInteger",
    "int8": "CharInteger",
    "pad": "Pad",
    "struct": "Struct",
    "uint16": "ShortInteger",
    "uint32": "LongInteger",
    "uint8": "CharInteger",
    "TagGroup": "Tag",
    "Address": "LongInteger",
    "Quaternion": "RealQuaternion",
    "Plane3D": "RealPlane3D",
    "Plane2D": "RealPlane2D",
    "Euler3D": "RealEulerAngles3D",
    "Matrix3x3": "Matrix3x3",
    "FileData": "Data",
    "CompressedVector3D": "LongInteger",
    "CompressedFloat": "ShortInteger",
    "BSPVertexData": "Data",
    "UTF16String": "Data",
    "RealBounds": "RealBounds",
    "AngleBounds": "AngleBounds",
    "ShortBounds": "ShortBounds",
}

field_sizes = {
    "Angle": 4,
    "AngleBounds": 8,
    "ArgbColor": 4,
    "Block": 12,
    "ByteFlags": 1,
    "CharBlockIndex": 1,
    "CharEnum": 1,
    "CharInteger": 1,
    "CustomLongBlockIndex": 4,
    "CustomShortBlockIndex": 2,
    "Data": 20,
    "LongBlockIndex": 4,
    "LongEnum": 4,
    "LongFlags": 4,
    "LongInteger": 4,
    "LongString": 256,
    "OldStringId": 32,
    "Point2D": 4,
    "Ptr": 4,
    "Real": 4,
    "RealArgbColor": 16,
    "RealBounds": 8,
    "RealEulerAngles2D": 8,
    "RealEulerAngles3D": 12,
    "RealFraction": 4,
    "RealFractionBounds": 8,
    "RealPlane2D": 12,
    "RealPlane3D": 16,
    "RealPoint2D": 8,
    "RealPoint3D": 12,
    "RealQuaternion": 16,
    "RealRgbColor": 12,
    "RealVector2D": 8,
    "RealVector3D": 12,
    "Rectangle2D": 8,
    "RgbColor": 4,
    "ShortBlockIndex": 2,
    "ShortBounds": 4,
    "ShortEnum": 2,
    "ShortInteger": 2,
    "String": 32,
    "StringId": 4,
    "Struct": 0,
    "Tag": 4,
    "TagReference": 16,
    "VertexBuffer": 32,
    "WordBlockFlags": 2,
    "WordFlags": 2,
    "Matrix3x3": 36,
}

pad_tags = {"Pad", "Skip", "UselessPad"}
