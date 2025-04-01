# this script is as messy as it gets but it gets the job done
# i mostly use windows so it is tailored for windows - if you're on linux then you can probably edit it to tailor it to your needs anyway

import os, os.path, zipfile, shutil
import json
path = os.path.dirname(os.path.realpath(__file__))
output_only = True


preferred_bases_directory = "imported_manual" # either this or "imported", gets modified later

mc_source_directory = f"C:/Users/{os.getlogin()}/AppData/Roaming/PrismLauncher/libraries/com/mojang/minecraft"
output_path = f"{path}/output/"

overlays_path = "/".join(f"{path}".split("\\")[:-2]) + "/.dev/biome overlays/1.21.5"
overlays = os.listdir(overlays_path)


mc_version = input("Enter Minecraft version to steal biomes from or press enter to skip:\n> "); mc_version = mc_version.strip()
if not output_only: input("Warning!! Will keep imported files after program end.")


if (mc_version != ""):
	jar = f"{mc_source_directory}/{mc_version}/minecraft-{mc_version}-client.jar"

	if not os.path.isfile(jar):
		print(f"\nCouldn't find {mc_version}, make sure the Minecraft path is correct.\n")
		quit()

	else:
		print(f"\nFound {mc_version}, importing...")

		preferred_bases_directory = "imported"

		shutil.rmtree(f"{path}/imported/") # deletes outdated data
		os.makedirs(f"{path}/imported/")
		
		jar = zipfile.ZipFile(jar, 'r') # bad practice but i dont care

		for overlay in overlays:
			try:
				jar.extract(f"data/minecraft/worldgen/biome/{overlay}", path=f"{path}/imported/")
				os.rename(f"{path}/imported/data/minecraft/worldgen/biome/{overlay}", f"{path}/imported/{overlay}")

			except FileExistsError:
				print(f"{overlay} already extracted, remove to replace")

			except:
				print(f"Couldn't extract {overlay} from JAR file")
	
		shutil.rmtree(f"{path}/imported/data")


definition_bases = os.listdir(f"{path}/{preferred_bases_directory}")
mc_version_edit = ("" + mc_version).replace(".", "_")


if not os.path.exists(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome"):
	os.makedirs(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome")
else:
	_dc_ = input(f"\nWarning!!! The output path for {mc_version} already exists. Some data in that folder may be out of date even after mixing. Wipe it first? (y/Y)\n> ")
	if (_dc_ == "Y" or _dc_ == "y"):
		shutil.rmtree(f"{output_path}/biomes_{mc_version_edit}")
		os.makedirs(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome")
		print("All files deleted.")


for overlay in overlays:
	if overlay in definition_bases:
		print(f"\nFound {overlay}, mixing...")

		_file_ = open(f"{path}/{preferred_bases_directory}/{overlay}"); file_content = _file_.read(); _file_.close()
		base = json.loads(file_content)

		_file_ = open(f"{overlays_path}/{overlay}"); file_content = _file_.read(); _file_.close()
		mixin = json.loads(file_content)

		for entry in mixin:
			if entry == "features":
				for index, step in enumerate(mixin[entry]):
					if len(step) != 0:
						base[entry][index] = step
						print(f"  Replaced feature step {index} of {overlay}")

			elif entry == "effects":
				for index, (key, value) in enumerate(mixin[entry].items()):
					base[entry][key] = value
					print(f"  Replaced effect {key} of {overlay}")

			elif entry == "spawners":
				for index, (key, value) in enumerate(mixin[entry].items()):
					base[entry][key] = value
					print(f"  Replaced spawner {key} of {overlay}")

			else:
				print(f"  Replaced {entry} of {overlay}")
				base[entry] = mixin[entry]

		if not os.path.exists(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome"):
			os.makedirs(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome")

		_file_ = open(f"{output_path}/biomes_{mc_version_edit}/data/minecraft/worldgen/biome/{overlay}", "w"); _file_.write(json.dumps(base, indent=2, sort_keys=True)); _file_.close()


if output_only:
	shutil.rmtree(f"{path}/imported/") # deletes outdated data
	os.makedirs(f"{path}/imported/")