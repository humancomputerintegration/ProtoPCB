'''exploratory page for different matching pathways'''

import os
from sch_reader import *
from CircuitMatch import *

current_directory = os.getcwd()

def run_circuit_match_on_dir(png_dir, filename_net):
	'''
		run circuit matching across all pngs in a directory
		
		Parameters:
		png_dir (str) - png directory
	'''
	temp_dir = current_directory + "/temp"
	kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
	footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
	
	net_arr = get_connections(filename_net)
	sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

	projects = os.listdir(png_dir)

	for project in projects:
		print(project)
		if project == '.DS_Store':
			continue

		if project == '#backup':
			continue
		
		mask_file_png = png_dir + '/' + project + '/' + project + '-f-mask.png'
		pcb_file_png = png_dir + '/' + project + '/' + project + '-f-traces.png'


		cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
		cir_m.process_PCB_png_files(mask_file_png, pcb_file_png)
		
		valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
		full_circuit_matches = cir_m.get_full_matches(valid_matches, len(net_arr))

		if len(full_circuit_matches) > 0:
			print("VALID MATCHES FOUND")
			print(len(full_circuit_matches))
			print(project)
			cir_m.visualize_matches(full_circuit_matches)


filename_net = current_directory + '/tests/testfiles/2_test_net.net'
png_dir = current_directory + '/pcb_library/png_images'
run_circuit_match_on_dir(png_dir, filename_net)





