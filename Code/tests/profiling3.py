import unittest

import os
import sys

parent_directory = os.path.abspath('..')
sys.path.append(parent_directory)

current_directory = os.getcwd()

from ComponentMatch import *

from NetMatch import *

from CircuitMatch import *

from sch_reader import *

from Objectifier import Objectifier



def get_num_components():
	print('get_num_components')

	net_arr = get_connections(filename_net)
	sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

	print(sorted_refs)

	# look at netlist


def get_num_nets():
	print('get_num_nets')

	# look at netlist


def get_num_solder_pads():
	print('get_num_solder_pads')

	# count # of pads via front pad map & back pad map


def get_full_matches():
	temp_dir = parent_directory + "/temp"
	kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
	footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
	
	filename_net = current_directory + '/testfiles/Adafruit LSM9DS1 Rev C.net'

	
	
	'''
	pcb_file = current_directory + '/testfiles/UNO-TH_Rev3e.kicad_pcb'
	mask_file_png = current_directory + '/testfiles/23_test_pcb_mask.png'
	maskb_file_png = current_directory + '/testfiles/23_test_pcb_mask_back.png'
	pcb_file_png = current_directory + '/testfiles/23_test_pcb_traces.png'
	pcbb_file_png = current_directory + '/testfiles/23_test_pcb_traces_back.png'
	drill_file = current_directory + '/testfiles/23_test_drill.drl'
	'''
	

	
	#PCB 3
	pcb_file = current_directory + '/testfiles/Adafruit LSM9DS1 Rev C.kicad_pcb'
	mask_file_png = current_directory + '/testfiles/24_test_pcb_mask.png'
	maskb_file_png = current_directory + '/testfiles/24_test_pcb_mask_back.png'
	pcb_file_png = current_directory + '/testfiles/24_test_pcb_traces.png'
	pcbb_file_png = current_directory + '/testfiles/24_test_pcb_traces_back.png'
	drill_file = current_directory + '/testfiles/Adafruit LSM9DS1 Rev C.drl'
	

	net_arr = get_connections(filename_net)
	sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

	pcb = PCB_Board(pcb_file)
	pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)

	cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
	cir_m.pcb_board = pcb

	valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)

	if valid_match != None:
		print('match found')
	else:
		print('match not found')

		missing_nets = []
		missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
		for missing_net_arr in missing_nets_arr:
			missing_nets.append(missing_net_arr['name'])

		print(cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr))
		valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo(cir_m.current_best_match['match'], missing_nets, temp_dir, kicad_cli, footprints_dir)

		if valid_match != None:
			print('match found')
			cir_m.visualize_matches([valid_match.circuit_arr])
		else:
			print('match not found')
			if cir_m.current_best_match != None:
				print(cir_m.current_best_match.nets)
				print(len(cir_m.current_best_match.nets))
				print(len(cir_m.net_arr))


get_full_matches()



