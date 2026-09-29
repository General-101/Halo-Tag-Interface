import os
import sys
import json
import tag_common
from tag_interface import read_file, write_file, obfuscation_buffer_prepare
from tag_definitions import h1, h2, common
from tag_postprocessing.h1 import postprocess_functions as h1_postprocess_functions
from tag_postprocessing.h2 import postprocess_functions as h2_postprocess_functions, create_function
from tag_upgrading.h1 import upgrade_functions as h1_upgrade_functions
from tag_upgrading.h2 import upgrade_functions as h2_upgrade_functions

def get_version_args(game_version):
    engine_tag = None
    tag_defs = None
    tag_groups = None
    tag_extensions = None
    postprocess_functions = None
    is_prerelease = False
    if game_version == 19980319:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980319_defs_directory
        tag_groups = tag_common.h1_19980319_tag_groups
        tag_extensions = tag_common.h1_19980319_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19980403:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980403_defs_directory
        tag_groups = tag_common.h1_19980403_tag_groups
        tag_extensions = tag_common.h1_19980403_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19980512:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980512_defs_directory
        tag_groups = tag_common.h1_19980512_tag_groups
        tag_extensions = tag_common.h1_19980512_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19980514:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980514_defs_directory
        tag_groups = tag_common.h1_19980514_tag_groups
        tag_extensions = tag_common.h1_19980514_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19980624:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980624_defs_directory
        tag_groups = tag_common.h1_19980624_tag_groups
        tag_extensions = tag_common.h1_19980624_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19980708:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19980708_defs_directory
        tag_groups = tag_common.h1_19980708_tag_groups
        tag_extensions = tag_common.h1_19980708_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19981008:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19981008_defs_directory
        tag_groups = tag_common.h1_19981008_tag_groups
        tag_extensions = tag_common.h1_19981008_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19981022:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19981022_defs_directory
        tag_groups = tag_common.h1_19981022_tag_groups
        tag_extensions = tag_common.h1_19981022_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19990225:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19990225_defs_directory
        tag_groups = tag_common.h1_19990225_tag_groups
        tag_extensions = tag_common.h1_19990225_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19990302:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19990302_defs_directory
        tag_groups = tag_common.h1_19990302_tag_groups
        tag_extensions = tag_common.h1_19990302_tag_extensions
        postprocess_functions = None
        is_prerelease = True
    elif game_version == 19990426:
        engine_tag = tag_common.EngineTag.H1Latest.value
        tag_defs = tag_common.h1_19990426_defs_directory
        tag_groups = tag_common.h1_19990426_tag_groups
        tag_extensions = tag_common.h1_19990426_tag_extensions
        postprocess_functions = None
        is_prerelease = True

    return engine_tag, tag_defs, tag_groups, tag_extensions, postprocess_functions, is_prerelease

def import_tag(file_path, game_version=20011115):
    engine_tag, tag_defs, tag_groups, tag_extensions, postprocess_functions, is_prerelease = get_version_args(game_version)
    output_dir = os.path.join(os.path.dirname(tag_defs), "%s_merged_output" % os.path.basename(tag_defs))
    merged_defs = h1.generate_defs(tag_defs, output_dir, tag_groups, tag_extensions)

    tag_dict = read_file(merged_defs, "", file_path, engine_tag=engine_tag, tag_groups=tag_groups, tag_extensions=tag_extensions, postprocess_functions=postprocess_functions, 
                         is_prerelease=is_prerelease)
    with open(os.path.join(os.path.dirname(file_path), "%s.json" % os.path.basename(file_path).rsplit(".", 1)[0]), 'w', encoding ='utf8') as json_file:
        json.dump(tag_dict, json_file, ensure_ascii = True, indent=4)

def export_tag(file_path, game_version):
    engine_tag, tag_defs, tag_groups, tag_extensions, postprocess_functions, is_prerelease = get_version_args(game_version)

    output_dir = os.path.join(os.path.dirname(tag_defs), "%s_merged_output" % os.path.basename(tag_defs))
    merged_defs = h1.generate_defs(tag_defs, output_dir, tag_groups, tag_extensions)

    output_path = file_path.rsplit(".", 1)[0]
    with open(file_path, "r", encoding="utf8") as json_file:
        tag_dict = json.load(json_file)

        write_file(merged_defs, tag_dict, obfuscation_buffer_prepare(), output_path, engine_tag=engine_tag, tag_groups=tag_groups, tag_extensions=tag_extensions, 
                   postprocess_functions=postprocess_functions, is_prerelease=is_prerelease)

def main():
    if len(sys.argv) < 2:
        print("Drag a file onto this script.")
        return

    file_path = sys.argv[1]
    game_version = 20011115
    if len(sys.argv) >= 3:
        game_version = int(sys.argv[2])

    if not os.path.isfile(file_path):
        return print("Not a valid file path. Check that the file exists on your system.")
    if file_path.lower().endswith(".json"):
        export_tag(file_path, game_version)
    else:
        import_tag(file_path, game_version)

if __name__ == "__main__":
    try:
        main()
        input("\nPress Enter to close...")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}\n")
        input("\nPress Enter to close...")
