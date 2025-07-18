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

import base64
import struct

def h2_bitmap_postprocess(tag_dict, file_endian, preserve_version):
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

h1_postprocess_functions = {
    "actr": None,
    "actv": None,
    "ant!": None,
    "antr": None,
    "bipd": None,
    "bitm": None,
    "boom": None,
    "cdmg": None,
    "coll": None,
    "colo": None,
    "cont": None,
    "ctrl": None,
    "deca": None,
    "DeLa": None,
    "devc": None,
    "devi": None,
    "dobc": None,
    "effe": None,
    "elec": None,
    "eqip": None,
    "flag": None,
    "fog ": None,
    "font": None,
    "foot": None,
    "garb": None,
    "glw!": None,
    "grhi": None,
    "hmt ": None,
    "hud#": None,
    "hudg": None,
    "item": None,
    "itmc": None,
    "jpt!": None,
    "lens": None,
    "lifi": None,
    "ligh": None,
    "lsnd": None,
    "mach": None,
    "matg": None,
    "metr": None,
    "mgs2": None,
    "mod2": None,
    "mode": None,
    "mply": None,
    "ngpr": None,
    "obje": None,
    "part": None,
    "pctl": None,
    "phys": None,
    "plac": None,
    "pphy": None,
    "proj": None,
    "rain": None,
    "sbsp": None,
    "scen": None,
    "scex": None,
    "schi": None,
    "scnr": None,
    "senv": None,
    "sgla": None,
    "shdr": None,
    "sky ": None,
    "smet": None,
    "snd!": None,
    "snde": None,
    "soso": None,
    "sotr": None,
    "Soul": None,
    "spla": None,
    "ssce": None,
    "str#": None,
    "swat": None,
    "tagc": None,
    "trak": None,
    "udlg": None,
    "unhi": None,
    "unit": None,
    "ustr": None,
    "vcky": None,
    "vehi": None,
    "weap": None,
    "wind": None,
    "wphi": None,
}

h2_postprocess_functions = {
    "obje": None,
    "devi": None,
    "item": None,
    "unit": None,
    "hlmt": None,
    "mode": None,
    "coll": None,
    "phmo": None,
    "bitm": h2_bitmap_postprocess,
    "colo": None,
    "unic": None,
    "bipd": None,
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
    "char": None,
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
