# Halo-Tag-Interface
Python script for parsing and writing Halo 1 and Halo 2 tag files

## Usage
tag_interface.py has some example functions on running on a single file or a directory. All you have to worry about in most instances is setting:
read_path - Absolute path to a valid Halo 1 or Halo 2 tag file.
output_path - Absolute path to a location to write the result of the script.
engine_tag - Set it to the engine you're working with. Either EngineTag.H1.value or EngineTag.H2Latest.value
file_endian - Set the endian of the file. Halo 1 is generally big endian while Halo 2 is little endian though this may not apply to all fields within. Definitions may define an override through the attribute "endian_override"

Once you've configured your variables just run the script through "python tag_interface.py"

The intermediate file is a JSON file containing all the values in the file as keys. You can modify it there before sending the file back out.

Halo 1 currently is capable of importing and exporting game files while maintaining matching file hashes. Halo 2 may still have some mismatches but should be functional otherwise.

## Credits

 * Discord user num0005
   * For creating the Halo 2 tag definitions used in this project and Pytolith that was used as reference
   * [Pytolith](https://github.com/num0005/Pytolith)

 * The Invader team/aerocatia/Snowy
   * For creating the Halo 1 tag definitions used in this project
   * [Invader](https://github.com/SnowyMouse/invader)

 * Discord user zeddikins
   * For developing the tooling for dumping tag definitions for various Halo games

 * Discord user modulus32
   * For contributing to the understanding of the Halo tag checksum code