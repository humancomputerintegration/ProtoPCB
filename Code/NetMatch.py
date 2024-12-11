from sch_reader import *
from svg_edit import *

from ComponentMatch import *
from PCB_utils import *

import cv2
import os
import subprocess


class NetMatching():
	'''
	data structure of NetMatching class
	nodes - array of nodes in net, nodes struct: {ref:, pin:, footprint:}
	net - str name of net

	(set through run_cm_on_nodes)
	cm_data - component match data for each component reached by nodes of net
	
	(set through process_PCB_png_files or initialize_vars fxn)
	mask_rgb (2D array) - solder mask image
    mask_contours (array) - array of contours for solderable pads
	pcb_rgb (2D array) - image of full PCB with traces
    trace_contours (array) - array of all contours in the PCB image (connected parts)
	'''
	def __init__(self, node_arr, net):
		'''
		init function for net matching
		node_arr - array of nodes in net, nodes struct: {ref:, pin:, footprint:}
		net - str name of net
		'''
		self.nodes = node_arr
		self.net = net

		#output = os.path.dirname(__file__) + "/temp"
		
		#self.traces_file = output + "/traces.png"

		self.cm_data = {}

	def process_PCB_png_files(self, mask_file, traces_file):
		'''
		process PCB png files (for mask and traces)
		mask_file (str) - path to mask png for pcb
		traces_file (str)- path to traces png for pcb

		Sets:
		self.mask_rgb (2D array) - solder mask image
    	self.mask_contours (array) - array of contours for solderable pads
		self.pcb_rgb (2D array) - image of full PCB with traces
    	self.trace_contours (array) - array of all contours in the PCB image (connected parts)
		'''

		self.pcb_rgb = cv2.imread(traces_file)								
		self.mask_rgb = cv2.imread(mask_file)

		m_img_grey = cv2.cvtColor(self.mask_rgb, cv2.COLOR_BGR2GRAY)
		inv_m_img_grey = cv2.bitwise_not(m_img_grey)
		self.mask_contours, hierarchy = cv2.findContours(inv_m_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

		self.pad_map = gen_pad_map(self.mask_contours)

		t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
		t_inv_img_grey = cv2.bitwise_not(t_img_grey)
		self.trace_contours, trace_hierarchy = cv2.findContours(t_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

		self.trace_map = connected_pads(self.pad_map, self.trace_contours, trace_hierarchy, t_inv_img_grey)


	def initialize_pcb_vars(self, mask_rgb, mask_contours, pcb_rgb, trace_contours, pad_map, trace_map):
		"""
		initialize img and contour info from pcb directly (useful to reduce redundant processing)

		Parameters:
		mask_rgb (2D array) - solder mask image
		mask_contours (array) - array of contours for solderable pads
		pcb_rgb (2D array) - image of full PCB with traces
		trace_contours (array) - array of all contours in the PCB image (connected parts)
		pad_map (dict) - each pad with corresponding pad center
		trace_map (dict) - each trace with corresponding pads within trace

		"""

		self.mask_rgb = mask_rgb
		self.mask_contours = mask_contours
		self.pcb_rgb = pcb_rgb 
		self.trace_contours = trace_contours
		self.pad_map = pad_map
		self.trace_map = trace_map

	def run_cm_on_nodes(self, temp_dir, kicad_cli, footprints_dir):
		"""
        Runs Component Matching on each component within Net
		
		Parameters:
        temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints
        
        
        Effects:
        NetMatching object property cm_data (dict) component matching information
        
    	"""

		print(f'RUNNING COMPONENT MATCHING FOR NODES ON NET: {self.net}')
		
		# go through each component (node) represented in this net
		# make sure you don't do component matching twice (i.e., in the case of two pins from the same component being connected)
		for node in self.nodes:
			# check if component already generated for cm_data
			if node['ref'] in self.cm_data.keys():
				#this component was already in cm_data
				self.cm_data[node['ref']]['pins'].append(node['pin'])
			else:
				footprint = node['footprint']
				footprint_arr = footprint.split(":")
				fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

				if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
					
					gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
				
				cm = ComponentMatching()
				cm.pcb_board = self.pcb_board
				cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
				matches = cm.get_matches()
				matches = cm.sort_matches()
				matches = cm.add_traces_data_to_matches(matches)
				
				ref = node['ref']
				self.cm_data[node['ref']] = {'pins': [node['pin']], 'matches': matches}

	def run_cm_via_traces(self, temp_dir, kicad_cli, footprints_dir):
		"""
        Runs Component Matching on each component within Net but through a trace-centric approach (only looks at component matches for relevant traces)
		
		Parameters:
        temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints
        
        
        Effects:
        NetMatching object property cm_data (dict) component matching information

        Returns:
        net_match_array (array) - unprocessed matches for each "trace" match
        
    	"""
		self.nodes.sort(key=lambda x: x['total pins'], reverse=True)

		starting_node = self.nodes[0]

		footprint = starting_node['footprint']
		footprint_arr = footprint.split(":")
		fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

		if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
			complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
		
			gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
		
		cm = ComponentMatching()
		cm.pcb_board = self.pcb_board

		cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
		matches = cm.get_matches()
		matches = cm.sort_matches(matches)
		matches = cm.add_traces_data_to_matches(matches)

		self.cm_data[starting_node['ref']] = {'pins': [starting_node['pin']], 'matches': matches}

		
		ref = starting_node['ref']

		# make sure all pins touched within net are met
		for node in self.nodes[1:]:
			if node['ref'] == ref:
				# add pin 
				self.cm_data[node['ref']]['pins'].append(node['pin'])
			else:
				break
		
		f_matches = []
		# look at these initial component matches 
		for init_cm in self.cm_data[ref]['matches']:
			# consider first pin in array
			init_pin = self.cm_data[ref]['pins'][0]

			net_traces = init_cm.touched_traces_dict[int(init_pin)]

			# look at subsequent pins needed on this component for this net, are they within these traces?

			if len(self.cm_data[ref]['pins']) > 1:
				for subs_pin in self.cm_data[ref]['pins'][1:]:
					subs_traces = init_cm.touched_traces_dict[int(subs_pin)]
					connected_to_net_trace = False
					for subs_trace in subs_traces:
						if subs_trace in net_traces:
							connected_to_net_trace = True

					if connected_to_net_trace:
						f_matches.append(init_cm)
			else:
				f_matches.append(init_cm)


		self.cm_data[ref]['matches'] = f_matches

		#create data structure to keep track of multi-pin components
		cm_pin_dict = {}

		for node in self.nodes:
			if node['ref'] in cm_pin_dict.keys():
				cm_pin_dict[node['ref']].append(node['pin'])
			else:
				cm_pin_dict[node['ref']] = [node['pin']]

		net_match_array = []
		
		

		# now look at the rest of components
		for init_cm in self.cm_data[ref]['matches']:
			
			net_traces = []

			for i_pin in self.cm_data[ref]['pins']:
				for t_trace in init_cm.touched_traces_dict[int(init_pin)]:
					net_traces.append(t_trace)

			#loop through relevant traces

			for trace in net_traces:
				trace_node_match_arr = [{'ref': ref, 'matches': [init_cm], 'pins': cm_pin_dict[ref]}]
				touched_refs = [ref]
				for node in self.nodes[(len(self.cm_data[ref]['pins'])):]:
					
					if node['ref'] not in touched_refs:
						# run cm

						footprint = node['footprint']
						footprint_arr = footprint.split(":")
						fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

						if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
							complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])

							gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
						ignore_pads = {'front pads': [], 'back pads': []}
						if init_cm.fb == 'front':
							ignore_pads['front pads'] += init_cm.pad_list
						else:
							ignore_pads['back pads'] += init_cm.pad_list

						matches, _, __ = cm.get_matches_on_trace(trace, cm_pin_dict[node['ref']], ignore_pads=ignore_pads)
						matches = cm.sort_matches(matches)

						if len(matches) > 0:
							trace_node_match_arr.append({'ref': node['ref'],'matches': matches, 'pins': cm_pin_dict[node['ref']]})
						touched_refs.append(node['ref'])
				net_match_array.append({'traces': [trace], 'node_arr': trace_node_match_arr, 'net': self.net})

		return net_match_array

	
	def run_net_cms_from_cm(self, temp_dir, kicad_cli, footprints_dir, init_match, ref):
		"""
        Runs component matching on components touched by net but only for specific component specified

		Parameters:
        temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints
        init_match (ComponentMatch) - match to run net finding along
        ref (str) - reference of component 
        
        
        Effects:
        NetMatching object property cm_data (dict) component matching information

        Returns:
        net_match_array (array) - possible net matches for this initial component match
        
    	"""
		self.nodes.sort(key=lambda x: x['total pins'], reverse=True)

		init_pins = []

    	# make sure all pins touched within net are met
		for node in self.nodes:
			if node['ref'] == ref:
				# add pin 
				init_pins.append(node['pin'])

		# consider first pin in array
		init_pin = init_pins[0]
		if init_pin not in init_match.touched_traces_dict.keys():
			return [] #malformed initial match
		net_traces = init_match.touched_traces_dict[init_pin]

		# look at subsequent pins needed on this component for this net, are they within these traces?

		if len(init_pins) > 1:
			for subs_pin in init_pins[1:]:
				if subs_pin not in init_match.touched_traces_dict.keys():
					return []
				subs_traces = init_match.touched_traces_dict[subs_pin]
				connected_to_net_trace = False
				for subs_trace in subs_traces:
					if subs_trace in net_traces:
						connected_to_net_trace = True

				if not connected_to_net_trace:
					return [] #this match doesn't contain connections across necessary pins

		#create data structure to keep track of multi-pin components
		cm_pin_dict = {}

		for node in self.nodes:
			if node['ref'] in cm_pin_dict.keys():
				cm_pin_dict[node['ref']].append(node['pin'])
			else:
				cm_pin_dict[node['ref']] = [node['pin']]

		net_match_array = []

		net_traces = []

		for i_pin in init_pins:
			for t_trace in init_match.touched_traces_dict[i_pin]:
				if t_trace not in net_traces:
					net_traces.append(t_trace)

		# initialize component matching
		cm = ComponentMatching()
		cm.pcb_board = self.pcb_board
		#loop through relevant traces

		
		trace_node_match_arr = [{'ref': ref, 'matches': [init_match], 'pins': cm_pin_dict[ref]}]
		touched_refs = [ref]
		
		for node in self.nodes:
			
			if node['ref'] not in touched_refs:
				# run cm
				footprint = node['footprint']
				footprint_arr = footprint.split(":")
				fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

				if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])

					gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

				cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
				
				ignore_pads = {'front pads': [], 'back pads': []}
				if init_match.fb == 'front':
					ignore_pads['front pads'] = init_match.pad_list
				else:
					ignore_pads['back pads'] = init_match.pad_list

				matches = []
				for trace in net_traces:
					t_matches, _, __ = cm.get_matches_on_trace(trace, cm_pin_dict[node['ref']], ignore_pads=ignore_pads)
					matches += t_matches
				matches = cm.add_traces_data_to_matches(matches)
				matches = cm.sort_matches(matches)
				if len(matches) > 0:
					trace_node_match_arr.append({'ref': node['ref'],'matches': matches, 'pins': cm_pin_dict[node['ref']]})
				touched_refs.append(node['ref'])

			net_match_array.append({'traces': net_traces, 'node_arr': trace_node_match_arr, 'net': self.net})

		return net_match_array


	def add_cm_data(self, full_cm_data):
		'''
			Adds component match data from a larger set of component match data (i.e., when running a full circuit match)

			Parameters:
			full_cm_data (dict) - large dict of component match information (to be selectively used)

			Effects
			self.cm_data (dict) - { '<ref>': {'pins': '', 'matches': []}}
		'''

		for node in self.nodes:
			if node['ref'] in self.cm_data.keys():
				self.cm_data[node['ref']]['pins'].append(node['pin'])
			else:
				self.cm_data[node['ref']] = {'pins': [node['pin']], 'matches': full_cm_data[node['ref']]['matches']}

		
	def search_net_matches(self):
		"""
        Creates a full net match array starting from first component (i.e. one with the least matches)

        Returns:
        net_matches (array): array of the trace ID and all resulting matches relevant for this net
        
   		"""

		# sort component list by number of matches

		ref_list = list(self.cm_data.keys())
		ref_list.sort(key=lambda x: len(self.cm_data[x]['matches']))

		net_matches = []
		
		# start with first component 
		component = self.cm_data[ref_list[0]] #has all matches and pins needed for net

		pin = component['pins'][0] # start with just one pin, check for others later
		for match in component['matches']:
			# plural because multiple pads might be covered for one pin
			p_IDs = match.pad_IDs[pin]
			# go through each pad to see if it belongs to a trace that hits another nodes in net

			for p_ID in p_IDs:
				# run through all trace contours in pcb to see pads in trace
				for trace, trace_pads in self.trace_map.items():
					# check if pad is in trace
					if p_ID in trace_pads:

						#potential trace, check that other pads needed are included in this trace
						nodes_info = [{'node':ref_list[0] + '-' + pin, 'match': match, 'pads': p_IDs}]
						
						#if there is another pin for this component that touches the NET, are there any of those pads within this NET?
						if len(component['pins']) > 1:
							#look at all pins after the first one
							sub_pins_connected = True
							for subsequent_pin in component['pins'][1:]:
								sub_p_IDs = match.pad_IDs[int(subsequent_pin)]
								connection_present = False
								for sub_p_ID in sub_p_IDs:
									if sub_p_ID in trace_pads:
										connection_present = True
										nodes_info.append({'node':ref_list[0]+ '-' + subsequent_pin, 'match': match, 'pads': sub_p_IDs})

								if not connection_present:
									sub_pins_connected = False # the subsequent pins are not connected, break from looping over subsequent pins
									break 

							if not sub_pins_connected: 
								continue # the subsequent pins are not connected, go to the next trace

						# go through other components and run similar process

						refs_connected = True
						sub_ref_match_arr = []

						for subsequent_ref in ref_list[1:]:

							subsequent_component = self.cm_data[subsequent_ref]
							sub_comp_pins = subsequent_component['pins'] #pins of interest on component
							
							match_for_ref_found = False
							ref_match_arr = []
							
							for sc_match in subsequent_component['matches']:
								
								sc_pins_connected = True
								pins_info = []
								for sub_comp_pin in sub_comp_pins:
									scsp_IDs = sc_match.pad_IDs[int(sub_comp_pin)]
									
									pin_connection = False
									for scsp_ID in scsp_IDs:
										if scsp_ID in trace_pads:
											pin_connection = True
											pins_info.append({'node': subsequent_ref + '-' + sub_comp_pin, 'match': sc_match, 'pads': scsp_IDs})
									if not pin_connection:
										sc_pins_connected = False 
										break # a pin is not properly connected
								if sc_pins_connected:
									# component is properly connected
									# this is a match !
									# pins_info contains this match
									for i_pin in pins_info:
										ref_match_arr.append(i_pin)
									match_for_ref_found = True

							if not match_for_ref_found:
								refs_connected = False
								break
							else:
								sub_ref_match_arr.append(ref_match_arr)

						if refs_connected:
							nodes_array = []
							for node_info in nodes_info:
								nodes_array.append([node_info])
							for ref_match in sub_ref_match_arr:
								nodes_array.append(ref_match)
							
							net_matches.append({'trace': trace, 'net': self.net, 'nodes array': nodes_array})
		return net_matches

	def process_matches(self, net_matches):
		"""
        Processes full array of matches to create all possible combinations of net matches

        Returns:
        n_matches (array): array of the component match combinations within a net match
        
   		"""
		n_matches = []
		for n_match in net_matches:
			n_refs = len(n_match['nodes array'])

			
			trace = n_match['trace']

			indices = [0 for i in range(n_refs)]
			
			while 1:
				nodes_arr = []
				for i in range(n_refs):
					nodes_arr.append(n_match['nodes array'][i][indices[i]])

				n_match_dict = {'trace': trace, 'nodes': nodes_arr, 'net': n_match['net']}
				n_matches.append(n_match_dict)

				# find the rightmost array that has more
			    # elements left after the current element
			    # in that array
				next = n_refs-1

				while (next >=0 and (indices[next] + 1 >= len(n_match['nodes array'][next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_refs):
					indices[i] = 0

		return n_matches

	def process_trace_matches(self, net_matches):
		"""
        Processes full array of matches to create all possible combinations of net matches (handles trace-based data structure)

        Returns:
        n_matches (array): array of the component match combinations within a net match
        
   		"""
		n_matches = []
		for n_match in net_matches:

			n_refs = len(n_match['node_arr'])
			traces = n_match['traces']

			indices = [0 for i in range(n_refs)]
			
			while 1:
				nodes_arr = []
				for i in range(n_refs):
					node_ref = n_match['node_arr'][i]['ref']
					node_match = n_match['node_arr'][i]['matches'][indices[i]]
					pin_arr = n_match['node_arr'][i]['pins']
					for pin in pin_arr:
						nodes_arr.append({'node': node_ref + '-' + pin, 'match': node_match, 'pads': node_match.pad_IDs[pin]})

				n_match_dict = {'traces': traces, 'nodes': nodes_arr, 'net': n_match['net']}
				n_matches.append(n_match_dict)
				
				next = n_refs-1

				while (next >= 0 and (indices[next] + 1 >= len(n_match['node_arr'][next]['matches']))):
					next -=1

				if next < 0:
					break 

				indices[next] += 1

				for i in range(next + 1, n_refs):
					indices[i] = 0


		return n_matches

	def get_complete_matches(self, matches, num_nodes):
		'''
			Filter through matches to create array that only has *full* net matches

	        Parameters:
	        matches (array): array of valid net matches
	        num_nets (int): number of nodes found in net

	        Returns:
	        complete_matches (array): array of matches that contain *all* nodes in the net
		'''

		complete_matches = []

		for match in matches:
			if len(match['nodes']) == num_nodes:
				complete_matches.append(match)

		return complete_matches

	def identify_duplicate_match(self, net_match1, net_match2):
		'''
			Helper function for 'filter_matches'. Assess if these net matches are the same

			Parameters:
			net_match1
			net_match2
			
			Returns:
			bool - True if this is a duplicate, False otherwise
		'''

		# (1) are traces different
		if net_match1['traces'] != net_match2['traces']:
			return False
		else:
			# (2) length of nodes is different
			if len(net_match1['nodes']) != len(net_match2['nodes']):
				return False
			else:
				# (3) component nodes are the same
				for nm1_node in net_match1['nodes']:
					nm1_ID = nm1_node['node']
					nm1_match = nm1_node['match']
					nm1_pads = nm1_node['pads']

					nm1_node_not_present = True
					for nm2_node in net_match2['nodes']:
						if nm1_ID == nm2_node['node']:
							nm1_node_not_present = False

							if nm1_match.pad_IDs != nm2_node['match'].pad_IDs:
								
								return False

							if nm1_pads != nm2_node['pads']:
								
								return False

					if nm1_node_not_present:
						return False #that node is not in the second net match!

		return True

	def filter_matches(self, net_matches):
		"""
        Filters full array of net matches to make sure there are no conflicting pads OR net already represented

        Returns:
        filtered_matches (array): array of the net matches that are valid
        
   		"""

		filtered_matches = []
		for n_match in net_matches:
			duplicate_exists = False
			for f_match in filtered_matches:
				#loop through to make sure there are no duplicates
				if self.identify_duplicate_match(f_match, n_match):
					duplicate_exists = True
					break
			if duplicate_exists:
				continue

			nodes = n_match['nodes']
			cm_dict = {}
			pads_touched = []
			bad_match = False
			for node in nodes:
				ref = node['node'].split('-')[0]
				if ref in cm_dict.keys():
					if node['match'] != cm_dict[ref]:
						return False
				else:
					cm = node['match']
					pad_IDs = cm.pad_IDs.values()
					for pad_arr in pad_IDs:
						for pad in pad_arr:
							if pad in pads_touched:
								bad_match = True
							else:
								pads_touched.append(pad)
					cm_dict[ref] = cm
			if not bad_match:
				filtered_matches.append(n_match)

		return filtered_matches

	def find_wire_interventions(self, match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, ignore_traces = []):
		'''
		search for places to add a wire connection

		Parameters:
		match - Net match dict 
		missing_node_IDs - array of missing node IDs
		temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints

        Optional:
        ignore_traces (array) - additional traces (by ID) to ignore

		Returns:
		matches (array) - updated matches with intervention or empty array
		'''

		if len(missing_node_IDs) == 0:
			return []

		existing_refs = []
		existing_refs_dict = {}
		net_matches = []
		ignore_pads = {'front pads': [], 'back pads': []}
		for match_node in match['nodes']:
			[m_ref,m_pin] = match_node['node'].split('-')
			if match_node['match'].fb == 'front':
				ignore_pads['front pads'] += match_node['match'].pad_IDs[m_pin]
			else:
				ignore_pads['back pads'] += match_node['match'].pad_IDs[m_pin]
			if m_ref not in existing_refs:
				existing_refs.append(m_ref)
				if m_ref not in existing_refs_dict.keys():
					existing_refs_dict[m_ref] = [match_node['node']]
				else:
					existing_refs_dict[m_ref].append(match_node['node'])

		# for missing nodes, can they be implemented on current trace?
		num_pads_on_trace = self.pcb_board.get_num_pads_on_traces(match['traces'])
		if num_pads_on_trace > len(match['nodes']):
			#is possible that other nodes can be matched on trace
			for missing_node in missing_node_IDs:
				[ref,pin] = missing_node.split('-')
				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
													
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

					#does this ref already exist in the match?
					
					if ref in existing_refs:
						# add wire between pins of that ref
						match['incomplete'] = True
						if 'interventions' in match.keys():
							if isinstance(match['interventions'], list):
								match['interventions'].append({'add wire': [missing_node] + existing_refs_dict[ref]})
							elif isinstance(match['interventions'], dict):
								int_cpy = dict(match['interventions'].copy)
								match['interventions'] = [int_cpy, {'add wire': [missing_node] + existing_refs_dict[ref]}]
						else:
							match['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]
					else:
						# see if matches possible on trace for this missing node ID

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

						matches = []
						for m_trace in match['traces']:
							t_matches, _, __ = cm.get_matches_on_trace(m_trace, [pin], ignore_pads = ignore_pads)
							matches += t_matches
						matches = cm.sort_matches(matches)
						matches = cm.add_traces_data_to_matches(matches)

						
						for cm_match in matches:
							node_dict = {'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}
							#match_cpy = {dict(match.copy())}
							match_cpy = {key: value for key, value in match.items()}
							match_cpy['nodes'] = match['nodes'].copy()
							match_cpy['nodes'].append(node_dict)
							missing_node_IDs_cpy = missing_node_IDs.copy()
							missing_node_IDs_cpy.remove(missing_node)
							
							n_matches = self.find_wire_interventions(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir)
							
							if len(n_matches) > 0:
								net_matches += n_matches

		else:
			# find wire interventions for nodes
		
			for missing_node in missing_node_IDs:
				ref = missing_node.split('-')[0]
				pin = missing_node.split('-')[1]

				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
													
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")


				#does this ref already exist in the match?

				if ref in existing_refs:
					# add wire between pins of that ref
					match['incomplete'] = True
					if 'interventions' in match.keys():
						match['interventions'].append({'add wire': [missing_node] + existing_refs_dict[ref]})
					else:
						match['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]

				else:
					# can matches be made on a connected intervention trace?
					match_via_intervention = False
					if 'interventions' in match.keys():
						if isinstance(match['interventions'], list):
							int_index = 0
							for intervention in match['interventions']:
								if 'add wire' in intervention.keys():
									if isinstance(intervention['add wire'], dict):
										#can ignore if list
										m_missing_node = intervention['add wire']['missing node']
										[m_ref,m_pin] = m_missing_node.split('-')

										if 'cmpnt matches' in intervention['add wire'].keys():
											for m_cm in intervention['add wire']['cmpnt matches']:
												m_touched_traces = m_cm.touched_traces_dict[m_pin]

												for m_touched_trace in m_touched_traces:
													if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
														#can you find this missing ref match in this trace?
														cm = ComponentMatching()
														cm.pcb_board = self.pcb_board
														cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

														m_matches, _, __ = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pad_arr = m_cm.pad_IDs[m_pin])
														m_matches = cm.sort_matches(m_matches)
														m_matches = cm.add_traces_data_to_matches(m_matches)
														if len(m_matches) > 0:
															for m_match in m_matches:
																match_cpy = dict(match.copy())
																match_cpy['nodes'] = match['nodes'].copy()
																match_cpy['interventions'] = match['interventions'].copy()
																new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																match_cpy['interventions'][int_index] = new_intervention
																node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																match_cpy['nodes'].append(node_dict)
																missing_node_IDs_cpy = missing_node_IDs.copy()

																if m_missing_node in missing_node_IDs_cpy:
																	missing_node_IDs_cpy.remove(m_missing_node)

																if missing_node in missing_node_IDs_cpy:
																	missing_node_IDs_cpy.remove(missing_node)

																if len(missing_node_IDs_cpy) == 0:
																	match_via_intervention = True
																	net_matches.append(match_cpy)

																completed_m_matches = self.find_wire_interventions(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces = m_touched_traces)

																if len(completed_m_matches) > 0:
																	match_via_intervention = True
																	net_matches.append(completed_m_matches)
										elif 'cmpnt match' in intervention['add wire'].keys():
											m_cm = intervention['add wire']['cmpnt match']
											m_touched_traces = m_cm.touched_traces_dict[m_pin]

											for m_touched_trace in m_touched_traces:
												if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
													#can you find this missing ref match in this trace?
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

													m_matches, _, __ = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pad_arr = m_cm.pad_IDs[m_pin])
													m_matches = cm.sort_matches(m_matches)
													m_matches = cm.add_traces_data_to_matches(m_matches)
													if len(m_matches) > 0:
														for m_match in m_matches:
															match_cpy = dict(match.copy())
															match_cpy['nodes'] = match['nodes'].copy()
															match_cpy['interventions'] = match['interventions'].copy()
															new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
															match_cpy['interventions'][int_index] = new_intervention
															node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
															match_cpy['nodes'].append(node_dict)
															missing_node_IDs_cpy = missing_node_IDs.copy()
															if m_missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(m_missing_node)

															if missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(missing_node)

															if len(missing_node_IDs_cpy) == 0:
																match_via_intervention = True
																net_matches.append(match_cpy)

															completed_m_matches = self.find_wire_interventions(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces = m_touched_traces)
															if len(completed_m_matches) > 0:
																match_via_intervention = True
																net_matches.append(completed_m_matches)
													#cm_matches += matches
								int_index += 1


						elif isinstance(match['interventions'], dict):
							if 'add wire' in match['interventions'].keys():
								if isinstance(match['interventions']['add wire'], dict):
									#can ignore if list
									m_missing_node = match['interventions']['add wire']['missing node']
									[m_ref,m_pin] = m_missing_node.split('-')

									if 'cmpnt matches' in match['interventions']['add wire'].keys():
										for m_cm in match['interventions']['add wire']['cmpnt matches']:
											m_touched_traces = m_cm.touched_traces_dict[m_pin]

											for m_touched_trace in m_touched_traces:
												if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
													#can you find this missing ref match in this trace?
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

													m_matches, _, __ = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pad_arr = m_cm.pad_IDs[m_pin])
													m_matches = cm.sort_matches(m_matches)
													m_matches = cm.add_traces_data_to_matches(m_matches)
													if len(m_matches) > 0:
														for m_match in m_matches:
															match_cpy = dict(match.copy())
															match_cpy['nodes'] = match['nodes'].copy()
															new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
															match_cpy['interventions'] = new_intervention
															node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
															match_cpy['nodes'].append(node_dict)
															missing_node_IDs_cpy = missing_node_IDs.copy()
															if m_missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(m_missing_node)

															if missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(missing_node)

															if len(missing_node_IDs_cpy) == 0:
																match_via_intervention = True
																net_matches.append(match_cpy)

															completed_m_matches = self.find_wire_interventions(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces = m_touched_traces)
															if len(completed_m_matches) > 0:
																match_via_intervention = True
																net_matches.append(completed_m_matches)
									elif 'cmpnt match' in match['interventions']['add wire'].keys():
										m_cm = match['interventions']['add wire']['cmpnt match']
										m_touched_traces = m_cm.touched_traces_dict[m_pin]

										for m_touched_trace in m_touched_traces:
											if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
												#can you find this missing ref match in this trace?
												cm = ComponentMatching()
												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

												m_matches, _, __ = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pad_arr = m_cm.pad_IDs[m_pin])
												m_matches = cm.sort_matches(m_matches)
												m_matches = cm.add_traces_data_to_matches(m_matches)
												if len(m_matches) > 0:
													for m_match in m_matches:
														match_cpy = dict(match.copy())
														match_cpy['nodes'] = match['nodes'].copy()
														new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
														match_cpy['interventions'] = new_intervention
														node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
														match_cpy['nodes'].append(node_dict)
														missing_node_IDs_cpy = missing_node_IDs.copy()
														if m_missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(m_missing_node)

														if missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(missing_node)

														if len(missing_node_IDs_cpy) == 0:
															match_via_intervention = True
															net_matches.append(match_cpy)

														completed_m_matches = self.find_wire_interventions(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces = m_touched_traces)
														if len(completed_m_matches) > 0:
															match_via_intervention = True
															net_matches.append(completed_m_matches)
												#cm_matches += matches

					if not match_via_intervention:
						# search for a Component Match for that ref on other relevant traces
						cm_matches = []

						#exclude traces that are touched by other net match components
						touched_traces = match['traces'] + ignore_traces

						for match_node in match['nodes']:
							cm = match_node['match']
							touched_traces += cm.touched_traces_list

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")


						for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
							if trace_ID not in touched_traces:
								if self.pcb_board.get_num_pads_on_traces([trace_ID]) >= 1: # at least one possible match possible
									
									matches, _, __ = cm.get_matches_on_trace(trace_ID, [pin])
									matches = cm.sort_matches(matches)
									matches = cm.add_traces_data_to_matches(matches)
									cm_matches += matches
						if len(cm_matches) > 0:
							
							match['incomplete'] = True 
							if 'interventions' in match.keys():
								
								match['interventions'].append({'add wire': {'missing node': missing_node, 'cmpnt matches': cm_matches}})
							else:
								match['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt matches': cm_matches}}]
			net_matches.append(match)


		return net_matches

	def fwi_fifo(self, match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, ignore_traces = [], index = 0, search_index = 0, circuit_matching = None, cir_match = None, missing_nets = [], last_loc = []):
		'''
		Recursive strategy for finding the next valid net match for circuit (rather than exhaustive search)

		Parameters:
		match (dict) - Net match dict to search on
		missing_node_IDs (arr) - array of node_IDs (str) to search for
		temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints

        Optional:
        ignore_traces (array) - array of traces to ignore on search
        index (int) - way to keep track of search paths
        search_index (int) - skip some searching if you are going for next match
        circuit_matching (CircuitMatching obj) - to continue circuit matching search
        cir_match (CircuitMatch) - to continue circuit match search
        missing_nets (arr) - array of nets still missing

        Returns:
        CircuitMatch - completed circuit match or None
        index (int) - where the search completed
        *or*
        Incomplete Net Match dict

		'''
		


		last_loc.append({'fxn': 'fwi_fifo', 'match': match, 'missing_node_IDs': missing_node_IDs, 'ignore_traces': ignore_traces, 'index': index, 
			'circuit_matching': circuit_matching, 'cir_match': cir_match, 'missing_nets': missing_nets, 'net_matching': self})

		if len(missing_node_IDs) == 0:
			return match, index, last_loc


		
		match = self.update_traces(match.copy())

		next_index = 0

		missing_node = missing_node_IDs[0]
		[ref, pin] = missing_node.split('-')

		def continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index):
			'''
			Helper function

			'''
			print('continue_search fwi_fifo')
			next_index += 1
			if search_index != 0:
				search_index -= 1
				return None, next_index, last_loc, search_index
			else:
				if cir_match_cpy != None:


					cir_match_cpy.update_traces(cir_match_cpy.circuit_arr, self.pcb_board)

					match_cpy = self.update_traces(match_cpy)

					circuit_matching.pcb_board = self.pcb_board


					if circuit_matching.intervention_combo_valid(cir_match_cpy.circuit_arr + [match_cpy]):

						if len(missing_node_IDs_cpy) > 0:
							search_on_node, n_index, n_last_loc = self.fwi_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, cir_match_cpy, missing_nets, last_loc = last_loc)
						
							if search_on_node != None:
								if not isinstance(search_on_node, dict):
									if circuit_matching.intervention_combo_valid(search_on_node.circuit_arr):
										return search_on_node, next_index, n_last_loc, search_index
								else:
									if circuit_matching.intervention_combo_valid(cir_match_cpy.circuit_arr + [search_on_node]):
										cir_match_cpy.add_net(search_on_node)
										missing_nets_cpy = missing_nets.copy()
										missing_nets_cpy.remove(match_cpy['net'])
										cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc = n_last_loc)
										
										if cm_search != None:
											if circuit_matching.intervention_combo_valid(cm_search.circuit_arr):
												return cm_search, next_index, cm_last_loc, search_index
						elif len(missing_node_IDs_cpy) == 0:
							missing_nets_cpy = missing_nets.copy()
							missing_nets_cpy.remove(match_cpy['net'])
							cir_match_cpy.add_net(match_cpy)

							cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc = last_loc)
							
							if cm_search != None:
								if circuit_matching.intervention_combo_valid(cm_search.circuit_arr):
									return cm_search, next_index, cm_last_loc, search_index
								else:
									print('intervention combo not valid')
							else:
								print('get next mwi fifo did not return')
							
					else:
						return None, next_index, last_loc, search_index
				else:
					if len(missing_node_IDs_cpy) > 0:
						search_on_node, n_index, n_last_loc = self.fwi_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, last_loc = last_loc)
					
						if search_on_node != None:
							return search_on_node, n_index, n_last_loc, search_index

					elif len(missing_node_IDs_cpy) == 0:
						return match_cpy, next_index, last_loc, search_index
			print('returning None from continue_search')
			return None, next_index, last_loc, search_index

		def check_for_existing_matches_on_trace(cm, footprint, trace, pin_arr):
			
			if circuit_matching != None:
				if not hasattr(circuit_matching, 'cm_data'):
					circuit_matching.cm_data = {}

				if footprint in circuit_matching.cm_data.keys():
					if trace in circuit_matching.cm_data[footprint].keys():

						if len(pin_arr) > 0:
							matches = []
							for pin in pin_arr:
								if str(trace) + '-pin-' + str(pin) in circuit_matching.cm_data[footprint].keys():
									matches += circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)]
								else:
									pin_matches = cm.filter_for_matches_on_trace(circuit_matching.cm_data[footprint][trace], trace, [pin])
									circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_matches
									matches += pin_matches
						else:
							matches = circuit_matching.cm_data[footprint][trace]
					elif 'full' in circuit_matching.cm_data[footprint].keys():
						full_matches = circuit_matching.cm_data[footprint]['full']
						matches = cm.filter_for_matches_on_trace(full_matches, trace, pin_arr)
					else:
						matches = []
						if len(pin_arr) > 0:
						
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
							circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin_arr[0])] = pin_t_matches
							circuit_matching.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								circuit_matching.cm_data[footprint]['full'] = f_matches				
							matches += pin_t_matches

							if len(pin_arr) > 1:
								for pin in pin_arr[1]:
									pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
									circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
									matches += pin_t_matches
						else:
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
							circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
							circuit_matching.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								circuit_matching.cm_data[footprint]['full'] = f_matches			
							matches += pin_t_matches

				else:
					matches = []
					if len(pin_arr) > 0:
						
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
						circuit_matching.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
						circuit_matching.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							circuit_matching.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

						if len(pin_arr) > 1:
							for pin in pin_arr[1]:
								pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
								circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								matches += pin_t_matches
					else:
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
						circuit_matching.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
						circuit_matching.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							circuit_matching.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

			else:
				if hasattr(self, 'cm_data'):
					if footprint in self.cm_data.keys():
						if trace in self.cm_data[footprint].keys():
							if len(pin_arr) > 0:
								matches = []
								for pin in pin_arr:
									if str(trace) + '-pin-' + str(pin) in self.cm_data[footprint].keys():
										matches += self.cm_data[footprint][str(trace) + '-pin-' + str(pin)]
									else:
										pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint][trace], trace, [pin])
										self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_matches
										matches += pin_matches
							else:
								matches = self.cm_data[footprint][trace]
						elif 'full' in self.cm_data[footprint].keys():
							full_matches = self.cm_data[footprint]['full']
							matches = cm.filter_for_matches_on_trace(full_matches, trace, pin_arr)
						else:

							matches = []
							if len(pin_arr) > 0:
							
								pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin_arr[0])] = pin_t_matches
								self.cm_data[footprint][trace] = t_matches
								if len(f_matches) > 0:
									self.cm_data[footprint]['full'] = f_matches				
								matches += pin_t_matches

								if len(pin_arr) > 1:
									for pin in pin_arr[1]:
										pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
										self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
										matches += pin_t_matches
							else:
								pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								self.cm_data[footprint][trace] = t_matches
								if len(f_matches) > 0:
									self.cm_data[footprint]['full'] = f_matches				
								matches += pin_t_matches

					else:
						matches = []
						if len(pin_arr) > 0:
							
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
							self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
							self.cm_data[footprint][trace] = t_matches	
							if len(f_matches) > 0:
								self.cm_data[footprint]['full'] = f_matches			
							matches += pin_t_matches

							if len(pin_arr) > 1:
								for pin in pin_arr[1]:
									pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
									self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
									matches += pin_t_matches
						else:
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
							self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
							self.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								self.cm_data[footprint]['full'] = f_matches				
							matches += pin_t_matches

				else:
					self.cm_data = {}
					matches = []
					if len(pin_arr) > 0:
						
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
						self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
						self.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							self.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

						if len(pin_arr) > 1:
							for pin in pin_arr[1]:
								pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								matches += pin_t_matches
					else:
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
						self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
						self.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							self.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

			return matches

		def update_cm_data():
			if hasattr(self, 'cm_data'):
				for fp, val in self.cm_data.items():
					for id, matches in val.items():
						for match in matches:
							match.update_traces(self.pcb_board)
			if circuit_matching != None:
				circuit_matching.cm_data = self.cm_data

		update_cm_data()


		if cir_match != None and ref in cir_match.refs:

			match_cpy = dict(match.copy())
			match_cpy['incomplete'] = True
			if 'interventions' in match_cpy.keys():
				
				if isinstance(match['interventions'], list):
					match_cpy['interventions'] = match['interventions'].copy()
					add_wire = True
					for intervention in match_cpy['interventions']:
						if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
							if intervention['add wire']['missing node'] == missing_node:
								add_wire = False
								break
					if add_wire:
						match_cpy['interventions'].append({'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}})

					match_cpy['traces'] = match['traces'] + cir_match.ref_dict[ref].touched_traces_dict[pin]

				elif isinstance(match['interventions'], dict):
					int_cpy = dict(match['interventions'].copy)
					match_cpy['interventions'] = [int_cpy, {'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}}]
					match_cpy['traces'] = match['traces'] + cir_match.ref_dict[ref].touched_traces_dict[pin]

			else:
				match_cpy['interventions'] = [{'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}}]
				match_cpy['traces'] = match['traces'] + cir_match.ref_dict[ref].touched_traces_dict[pin]
			match_cpy['traces'] = list(set(match_cpy['traces']))
			
			missing_node_IDs_cpy = missing_node_IDs.copy()
			missing_node_IDs_cpy.remove(missing_node)

			cir_match_cpy = cir_match.copy()

			cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
			
			if cs_m != None:
				return cs_m, next_index, cs_last_loc
			else:
				return None, next_index, cs_last_loc
		
		elif cir_match != None and len(match['traces']) == 0:
			# need to find a whole new connection
			# search for a Component Match for that ref on other relevant traces
			cm_matches = []

			footprint = ''
			# get element footprint
			for node in self.nodes:
				if node['ref'] == ref:
					footprint = node['footprint']
					break

			if len(footprint) > 0:
				footprint_arr = footprint.split(":")
				fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
				if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])

					if complete.returncode != 0:
						print('did not return')
						fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
										
					gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

			#exclude traces that are touched by other net match components
			touched_traces = match['traces'] + ignore_traces

			for cir_ref, cir_cm in cir_match.ref_dict.items():
				touched_traces += cir_cm.touched_traces_list
			
			cm = ComponentMatching()
			cm.pcb_board = self.pcb_board
			cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

			cir_match_cpy_i = cir_match.copy()

			if circuit_matching != None:
				if not hasattr(circuit_matching, 'cm_data'):
					circuit_matching.cm_data = {}

				if footprint in circuit_matching.cm_data.keys():
					if 'full' in circuit_matching.cm_data[footprint].keys():
						matches = circuit_matching.cm_data[footprint]['full']
						matches = cm.add_traces_data_to_matches(matches)
					else:
						matches = cm.get_matches()
						matches = cm.sort_matches(matches)
						matches = cm.add_traces_data_to_matches(matches)
						circuit_matching.cm_data[footprint]['full'] = matches
				else:
					matches = cm.get_matches()
					matches = cm.sort_matches(matches)
					matches = cm.add_traces_data_to_matches(matches)
					circuit_matching.cm_data[footprint] = {'full': matches }
			else:
				matches = cm.get_matches()
				matches = cm.sort_matches(matches)
				matches = cm.add_traces_data_to_matches(matches)
				self.cm_data[footprint] = {'full': matches}

			matches = cm.filter_out_traces(matches, touched_traces, [pin])

			cm_i = 0

			if len(matches) > 0:


				while 1:
					
					cm_match = matches[cm_i]
					match_cpy = {'traces': match['traces'], 'nodes': [{'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}], 'net': match['net']}
					match_cpy['incomplete'] = True 
					
					match_cpy['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}}]
					match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
					match_cpy['traces'] = list(set(match_cpy['traces']))

					missing_node_IDs_cpy = missing_node_IDs.copy()
					missing_node_IDs_cpy.remove(missing_node)

					cir_match_cpy = cir_match_cpy_i.copy()

					cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
					
					if cs_m != None:
						return cs_m, next_index, cs_last_loc

					cm_i += 1

					if cm_i >= len(matches):
						break

			return None, next_index, last_loc


		else:
			existing_refs = []
			existing_refs_dict = {}
			net_matches = []
			ignore_pads = {'front pads': [], 'back pads': []}
			self.update_traces(match)
			for match_node in match['nodes']:
				[m_ref,m_pin] = match_node['node'].split('-')
				if match_node['match'].fb == 'front':
					ignore_pads['front pads'] += match_node['match'].pad_list
				else:
					ignore_pads['back pads'] += match_node['match'].pad_list
				if m_ref not in existing_refs:
					existing_refs.append(m_ref)
					if m_ref not in existing_refs_dict.keys():
						existing_refs_dict[m_ref] = [match_node['node']]
					else:
						existing_refs_dict[m_ref].append(match_node['node'])

			if 'interventions' in match.keys():
				if isinstance(match['interventions'], list):
					for intervention in match['interventions']:
						if 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict):
							if 'cmpnt match' in intervention['add wire'].keys():
								cm = intervention['add wire']['cmpnt match']
								m_ref = intervention['add wire']['missing node'].split('-')[0]
								existing_refs.append(m_ref)
								if m_ref not in existing_refs_dict.keys():
									existing_refs_dict[m_ref] = [intervention['add wire']['missing node']]
								else:
									existing_refs_dict[m_ref].append(intervention['add wire']['missing node'])
								if cm.fb == 'front':
									ignore_pads['front pads'] += cm.pad_list
								else:
									ignore_pads['back pads'] += cm.pad_list


			if cir_match != None:
				cir_match = cir_match.update_traces(cir_match.circuit_arr, self.pcb_board)
				ignore_pads['front pads'] += cir_match.touched_pads['front pads']
				ignore_pads['back pads'] += cir_match.touched_pads['back pads']

			# for missing nodes, can they be implemented on current trace?
			
			num_pads_on_trace = self.pcb_board.get_num_pads_on_traces(match['traces'])


			if num_pads_on_trace > len(match['nodes']):
				
				#is possible that other nodes can be matched on trace

				## fifo strategy
				missing_node = missing_node_IDs[0]

				[ref,pin] = missing_node.split('-')



				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
						if complete.returncode != 0:
							print('did not return')
							fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
							complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
										
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

					#does this ref already exist in the match?
					
					if ref in existing_refs:
						# add wire between pins of that ref
						
						match_cpy = dict(match.copy())
						match_cpy['incomplete'] = True
						if 'interventions' in match_cpy.keys():
							
							if isinstance(match['interventions'], list):
								match_cpy['interventions'] = match['interventions'].copy()
								match_cpy['interventions'].append({'add wire':[missing_node] + existing_refs_dict[ref]})
							elif isinstance(match['interventions'], dict):
								int_cpy = dict(match['interventions'].copy)
								match_cpy['interventions'] = [int_cpy, {'add wire': [missing_node] + existing_refs_dict[ref]}]
						else:
							match_cpy['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]

						existing_ref_traces = []
						for match_node in match['nodes']:
							if match_node['node'] in existing_refs_dict[ref]:
								existing_ref_traces = match_node['match'].touched_traces_dict[pin]
								break
						match_cpy['traces'] = match['traces'] + existing_ref_traces
						match_cpy['traces'] = list(set(match_cpy['traces']))

						
						missing_node_IDs_cpy = missing_node_IDs.copy()
						missing_node_IDs_cpy.remove(missing_node)

						if cir_match != None:
							cir_match_cpy = cir_match.copy()
						else:
							cir_match_cpy = None

						cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
						
						if cs_m != None:
							return cs_m, next_index, cs_last_loc


					else:
						# see if matches possible on trace for this missing node ID

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

						matches = []
						for trace in match['traces']:
							matches += check_for_existing_matches_on_trace(cm, footprint_arr[1], trace, [pin])
						matches = cm.filter_out_pads(matches, ignore_pads)

						match_located = False
						for cm_match in matches:
							node_dict = {'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}
							#match_cpy = {dict(match.copy())}
							match_cpy = {key: value for key, value in match.items()}
							match_cpy['nodes'] = match['nodes'].copy()
							match_cpy['nodes'].append(node_dict)
							match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
							match_cpy['traces'] = list(set(match_cpy['traces']))

							
							missing_node_IDs_cpy = missing_node_IDs.copy()
							missing_node_IDs_cpy.remove(missing_node)

							if cir_match != None:
								cir_match_cpy = cir_match.copy()
							else:
								cir_match_cpy = None

							cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
							
							if cs_m != None:
								match_located = True
								return cs_m, next_index, cs_last_loc

						if not match_located:
							print('match not located yet')

							# find wire interventions for nodes

							missing_node = missing_node_IDs[0]
							
							ref = missing_node.split('-')[0]
							pin = missing_node.split('-')[1]

							footprint = ''
							# get element footprint
							for node in self.nodes:
								if node['ref'] == ref:
									footprint = node['footprint']
									break

							if len(footprint) > 0:
								footprint_arr = footprint.split(":")
								fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
								if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
									complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
																
									gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")


							#does this ref already exist in the match?

							if ref in existing_refs:
								# add wire between pins of that ref
								match_cpy = dict(match.copy())
								match_cpy['incomplete'] = True
								if 'interventions' in match_cpy.keys():
									if isinstance(match['interventions'], list):
										match_cpy['interventions'] = match['interventions'].copy()
										match_cpy['interventions'].append({'add wire':[missing_node] + existing_refs_dict[ref]})
									elif isinstance(match['interventions'], dict):
										int_cpy = dict(match['interventions'].copy)
										match_cpy['interventions'] = [int_cpy, {'add wire': [missing_node] + existing_refs_dict[ref]}]
								else:
									match_cpy['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]
								match_cpy['traces'] = match['traces'] + existing_refs_dict[ref].touched_traces_dict[pin]
								match_cpy['traces'] = list(set(match_cpy['traces']))

								
								missing_node_IDs_cpy = missing_node_IDs.copy()
								missing_node_IDs_cpy.remove(missing_node)

								if cir_match != None:
									cir_match_cpy = cir_match.copy()
								else:
									cir_match_cpy = None

								cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
								
								if cs_m != None:
									return cs_m, next_index, cs_last_loc

							else:
								# can matches be made on a connected intervention trace?
								match_via_intervention = False
								if 'interventions' in match.keys():
									if isinstance(match['interventions'], list):
										int_index = 0
										for intervention in match['interventions']:
											if 'add wire' in intervention.keys():
												if isinstance(intervention['add wire'], dict):
													#can ignore if list
													m_missing_node = intervention['add wire']['missing node']
													[m_ref,m_pin] = m_missing_node.split('-')

													if 'cmpnt matches' in intervention['add wire'].keys():
														for m_cm in intervention['add wire']['cmpnt matches']:
															m_touched_traces = m_cm.touched_traces_dict[m_pin]

															for m_touched_trace in m_touched_traces:
																if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
																	#can you find this missing ref match in this trace?
																	cm = ComponentMatching()
																	cm.pcb_board = self.pcb_board
																	cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

														

																	m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
																	m_matches = cm.filter_out_pads(m_matches, ignore_pads)

																	if len(m_matches) > 0:
																		for m_match in m_matches:
																			match_cpy = dict(match.copy())
																			match_cpy['nodes'] = match['nodes'].copy()
																			match_cpy['interventions'] = match['interventions'].copy()
																			new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																			match_cpy['interventions'][int_index] = new_intervention
																			node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																			match_cpy['nodes'].append(node_dict)
																			match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
																			match_cpy['traces'] = list(set(match_cpy['traces']))

																			missing_node_IDs_cpy = missing_node_IDs.copy()

																			if m_missing_node in missing_node_IDs_cpy:
																				missing_node_IDs_cpy.remove(m_missing_node)

																			if missing_node in missing_node_IDs_cpy:
																				missing_node_IDs_cpy.remove(missing_node)

																			if cir_match != None:
																				cir_match_cpy = cir_match.copy()
																			else:
																				cir_match_cpy = None

																			cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																			
																			if cs_m != None:
																				return cs_m, next_index, cs_last_loc
																			
																		
													elif 'cmpnt match' in intervention['add wire'].keys():
														m_cm = intervention['add wire']['cmpnt match']
														m_touched_traces = m_cm.touched_traces_dict[m_pin]

														for m_touched_trace in m_touched_traces:
															if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
																#can you find this missing ref match in this trace?
																cm = ComponentMatching()
																cm.pcb_board = self.pcb_board
																cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

																
																m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
																m_matches = cm.filter_out_pads(m_matches, ignore_pads)

																if len(m_matches) > 0:
																	n_cm_i = 0
																	while 1:
																		m_match = m_matches[n_cm_i]
																		match_cpy = dict(match.copy())
																		match_cpy['nodes'] = match['nodes'].copy()
																		match_cpy['interventions'] = match['interventions'].copy()

																		new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																		match_cpy['interventions'][int_index] = new_intervention
																		node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																		match_cpy['nodes'].append(node_dict)
																		match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
																		match_cpy['traces'] = list(set(match_cpy['traces']))

																		missing_node_IDs_cpy = missing_node_IDs.copy()

																		if m_missing_node in missing_node_IDs_cpy:
																			missing_node_IDs_cpy.remove(m_missing_node)

																		if missing_node in missing_node_IDs_cpy:
																			missing_node_IDs_cpy.remove(missing_node)

																		if cir_match != None:
																			cir_match_cpy = cir_match.copy()
																		else:
																			cir_match_cpy = None

																		cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																		
																		
																		if cs_m != None:
																			return cs_m, next_index, cs_last_loc

																		n_cm_i += 1

																		if n_cm_i >= len(m_matches):
																			break

																		
											int_index += 1


									elif isinstance(match['interventions'], dict):
										if 'add wire' in match['interventions'].keys():
											if isinstance(match['interventions']['add wire'], dict):
												#can ignore if list
												m_missing_node = match['interventions']['add wire']['missing node']
												[m_ref,m_pin] = m_missing_node.split('-')

												if 'cmpnt matches' in match['interventions']['add wire'].keys():
													for m_cm in match['interventions']['add wire']['cmpnt matches']:
														m_touched_traces = m_cm.touched_traces_dict[m_pin]

														for m_touched_trace in m_touched_traces:
															if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
																#can you find this missing ref match in this trace?
																cm = ComponentMatching()
																cm.pcb_board = self.pcb_board
																cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

																
																m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
																m_matches = cm.filter_out_pads(m_matches, ignore_pads)

																if len(m_matches) > 0:
																	for m_match in m_matches:
																		match_cpy = dict(match.copy())
																		match_cpy['nodes'] = match['nodes'].copy()
																		match_cpy['interventions'] = match['interventions'].copy()
																		new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																		match_cpy['interventions'][int_index] = new_intervention
																		node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																		match_cpy['nodes'].append(node_dict)
																		match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
																		match_cpy['traces'] = list(set(match_cpy['traces']))

																		missing_node_IDs_cpy = missing_node_IDs.copy()

																		if m_missing_node in missing_node_IDs_cpy:
																			missing_node_IDs_cpy.remove(m_missing_node)

																		if missing_node in missing_node_IDs_cpy:
																			missing_node_IDs_cpy.remove(missing_node)

																		if cir_match != None:
																			cir_match_cpy = cir_match.copy()
																		else:
																			cir_match_cpy = None

																		cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																		
																		if cs_m != None:
																			return cs_m, next_index, cs_last_loc
																		
																			
												elif 'cmpnt match' in match['interventions']['add wire'].keys():
													m_cm = match['interventions']['add wire']['cmpnt match']
													m_touched_traces = m_cm.touched_traces_dict[m_pin]

													for m_touched_trace in m_touched_traces:
														if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
															#can you find this missing ref match in this trace?
															cm = ComponentMatching()
															cm.pcb_board = self.pcb_board
															cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

															
															m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
															m_matches = cm.filter_out_pads(m_matches, ignore_pads)

															if len(m_matches) > 0:
																for m_match in m_matches:
																	match_cpy = dict(match.copy())
																	match_cpy['nodes'] = match['nodes'].copy()
																	match_cpy['interventions'] = match['interventions'].copy()
																	new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																	match_cpy['interventions'][int_index] = new_intervention
																	node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																	match_cpy['nodes'].append(node_dict)
																	match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
																	match_cpy['traces'] = list(set(match_cpy['traces']))

																	missing_node_IDs_cpy = missing_node_IDs.copy()

																	if m_missing_node in missing_node_IDs_cpy:
																		missing_node_IDs_cpy.remove(m_missing_node)

																	if missing_node in missing_node_IDs_cpy:
																		missing_node_IDs_cpy.remove(missing_node)

																	if cir_match != None:
																		cir_match_cpy = cir_match.copy()
																	else:
																		cir_match_cpy = None

																	cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																	
																	if cs_m != None:
																		return cs_m, next_index, cs_last_loc
																	

								if not match_via_intervention:
									# search for a Component Match for that ref on other relevant traces
									cm_matches = []

									cm = ComponentMatching()
									cm.pcb_board = self.pcb_board
									cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

									touched_traces = match['traces'] + ignore_traces

									if cir_match != None:
										cir_match_cpy_i = cir_match.copy()
										for cir_ref, cir_cm in cir_match.ref_dict.items():
											touched_traces += cir_cm.touched_traces_list
									else:
										cir_match_cpy_i = None

									print(f'finding matches for {ref}')
									if circuit_matching != None:
										if not hasattr(circuit_matching, 'cm_data'):
											circuit_matching.cm_data = {}

										fp_key = footprint.split(':')[1]

										if fp_key in circuit_matching.cm_data.keys():
											if 'full' in circuit_matching.cm_data[fp_key].keys():
												matches = circuit_matching.cm_data[fp_key]['full']
												matches = cm.add_traces_data_to_matches(matches)
											else:
												
												matches = cm.get_matches()
												matches = cm.sort_matches(matches)
												matches = cm.add_traces_data_to_matches(matches)
												circuit_matching.cm_data[footprint]['full'] = matches
										else:
											
											matches = cm.get_matches()
											matches = cm.sort_matches(matches)
											matches = cm.add_traces_data_to_matches(matches)
											circuit_matching.cm_data[footprint] = {'full': matches }
									else:
										if hasattr(self, 'cm_data'):
											if footprint in self.cm_data.keys():
												if 'full' in self.cm_data[footprint].keys():
													matches = self.cm_data[footprint]['full']
												else:
													matches = cm.get_matches()
													matches = cm.sort_matches(matches)
													matches = cm.add_traces_data_to_matches(matches)
													self.cm_data[footprint]['full'] = matches
											else:
												matches = cm.get_matches()
												matches = cm.sort_matches(matches)
												matches = cm.add_traces_data_to_matches(matches)
												self.cm_data[footprint] = {'full': matches }
										else:
											matches = cm.get_matches()
											matches = cm.sort_matches(matches)
											matches = cm.add_traces_data_to_matches(matches)
											self.cm_data[footprint] = {'full': matches}
									

									matches = cm.filter_out_traces(matches, touched_traces, [pin])
									matches = cm.filter_out_pads(matches, ignore_pads)
									cm_i = 0


									if 'interventions' in match.keys():
										add_wire = True
										for intervention in match['interventions']:
											if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
												if intervention['add wire']['missing node'] == missing_node:
													print(intervention['add wire'])



									if len(matches) > 0:
										print(f'looping through {len(matches)} matches')
										while 1:
											
											cm_match = matches[cm_i]
											
											match_cpy = dict(match.copy())
											match_cpy['incomplete'] = True 
											if 'interventions' in match_cpy.keys():
												match_cpy['interventions'] = match['interventions'].copy()
												add_wire = True
												for intervention in match_cpy['interventions']:
													if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
														if intervention['add wire']['missing node'] == missing_node:
															add_wire = False
															break
												if add_wire:
													match_cpy['interventions'].append({'add wire': {'missing node':missing_node, 'cmpnt match': cm_match}})

											else:
												match_cpy['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}}]

											match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
											match_cpy['traces'] = list(set(match_cpy['traces']))
																	
											missing_node_IDs_cpy = missing_node_IDs.copy()
											missing_node_IDs_cpy.remove(missing_node)

											if cir_match_cpy_i != None:
												cir_match_cpy = cir_match_cpy_i.copy()
											else:
												cir_match_cpy = None

											cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
											
											if cs_m != None:
												return cs_m, next_index, cs_last_loc

											cm_i += 1

											if cm_i >= len(matches):
												break
										print(f'finished looping through {len(matches)} matches')

									return None, next_index, last_loc

			else:
				
				# find wire interventions for nodes

				missing_node = missing_node_IDs[0]

				
				ref = missing_node.split('-')[0]
				pin = missing_node.split('-')[1]

				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
						
						if complete.returncode != 0:
							print('did not return')
							fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
							complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
										
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")


				#does this ref already exist in the match?

				if ref in existing_refs:
					# add wire between pins of that ref
					match_cpy = dict(match.copy())
					match_cpy['incomplete'] = True
					if 'interventions' in match_cpy.keys():
						if isinstance(match['interventions'], list):
							match_cpy['interventions'] = match['interventions'].copy()
							match_cpy['interventions'].append({'add wire':[missing_node] + existing_refs_dict[ref]})
						elif isinstance(match['interventions'], dict):
							int_cpy = dict(match['interventions'].copy)
							match_cpy['interventions'] = [int_cpy, {'add wire': [missing_node] + existing_refs_dict[ref]}]
					else:
						match_cpy['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]
					match_cpy['traces'] = match['traces'] + existing_refs_dict[ref].touched_traces_dict[pin]
					match_cpy['traces'] = list(set(match_cpy['traces']))
																	

					
					missing_node_IDs_cpy = missing_node_IDs.copy()
					missing_node_IDs_cpy.remove(missing_node)

					if cir_match != None:
						cir_match_cpy = cir_match.copy()
					else:
						cir_match_cpy = None

					cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
					
					if cs_m != None:
						return cs_m, next_index, cs_last_loc

				else:
					# can matches be made on a connected intervention trace?
					match_via_intervention = False
					if 'interventions' in match.keys():
						if isinstance(match['interventions'], list):
							int_index = 0
							for intervention in match['interventions']:
								if 'add wire' in intervention.keys():
									if isinstance(intervention['add wire'], dict):
										#can ignore if list
										m_missing_node = intervention['add wire']['missing node']
										[m_ref,m_pin] = m_missing_node.split('-')

										if 'cmpnt matches' in intervention['add wire'].keys():
											for m_cm in intervention['add wire']['cmpnt matches']:
												m_touched_traces = m_cm.touched_traces_dict[m_pin]

												for m_touched_trace in m_touched_traces:
													if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
														#can you find this missing ref match in this trace?
														cm = ComponentMatching()
														cm.pcb_board = self.pcb_board
														cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")


														m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
														m_matches = cm.filter_out_pads(m_matches, ignore_pads)


														if len(m_matches) > 0:
															for m_match in m_matches:
																match_cpy = dict(match.copy())
																match_cpy['nodes'] = match['nodes'].copy()
																match_cpy['interventions'] = match['interventions'].copy()
																new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
																match_cpy['interventions'][int_index] = new_intervention
																node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
																match_cpy['nodes'].append(node_dict)
																match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
																match_cpy['traces'] = list(set(match_cpy['traces']))

																missing_node_IDs_cpy = missing_node_IDs.copy()

																if m_missing_node in missing_node_IDs_cpy:
																	missing_node_IDs_cpy.remove(m_missing_node)

																if missing_node in missing_node_IDs_cpy:
																	missing_node_IDs_cpy.remove(missing_node)

																if cir_match != None:
																	cir_match_cpy = cir_match.copy()
																else:
																	cir_match_cpy = None

																cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																
																if cs_m != None:
																	return cs_m, next_index, cs_last_loc
																
															
										elif 'cmpnt match' in intervention['add wire'].keys():
											m_cm = intervention['add wire']['cmpnt match']
											m_touched_traces = m_cm.touched_traces_dict[m_pin]

											for m_touched_trace in m_touched_traces:
												if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
													#can you find this missing ref match in this trace?
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")


													m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
													m_matches = cm.filter_out_pads(m_matches, ignore_pads)

													if len(m_matches) > 0:
														n_cm_i = 0
														while 1:
															m_match = m_matches[n_cm_i]
															match_cpy = dict(match.copy())
															match_cpy['nodes'] = match['nodes'].copy()
															match_cpy['interventions'] = match['interventions'].copy()

															new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
															match_cpy['interventions'][int_index] = new_intervention
															node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
															match_cpy['nodes'].append(node_dict)
															match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
															match_cpy['traces'] = list(set(match_cpy['traces']))

															missing_node_IDs_cpy = missing_node_IDs.copy()

															if m_missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(m_missing_node)

															if missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(missing_node)

															if cir_match != None:
																cir_match_cpy = cir_match.copy()
															else:
																cir_match_cpy = None

															cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
															
															if cs_m != None:
																return cs_m, next_index, cs_last_loc

															n_cm_i += 1

															if n_cm_i >= len(m_matches):
																break

															
								int_index += 1


						elif isinstance(match['interventions'], dict):
							if 'add wire' in match['interventions'].keys():
								if isinstance(match['interventions']['add wire'], dict):
									#can ignore if list
									m_missing_node = match['interventions']['add wire']['missing node']
									[m_ref,m_pin] = m_missing_node.split('-')

									if 'cmpnt matches' in match['interventions']['add wire'].keys():
										for m_cm in match['interventions']['add wire']['cmpnt matches']:
											m_touched_traces = m_cm.touched_traces_dict[m_pin]

											for m_touched_trace in m_touched_traces:
												if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
													#can you find this missing ref match in this trace?
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

													m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
													m_matches = cm.filter_out_pads(m_matches, ignore_pads)

													if len(m_matches) > 0:
														for m_match in m_matches:
															match_cpy = dict(match.copy())
															match_cpy['nodes'] = match['nodes'].copy()
															match_cpy['interventions'] = match['interventions'].copy()
															new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
															match_cpy['interventions'][int_index] = new_intervention
															node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
															match_cpy['nodes'].append(node_dict)
															match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
															match_cpy['traces'] = list(set(match_cpy['traces']))

															missing_node_IDs_cpy = missing_node_IDs.copy()

															if m_missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(m_missing_node)

															if missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(missing_node)

															if cir_match != None:
																cir_match_cpy = cir_match.copy()
															else:
																cir_match_cpy = None

															cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
															
															if cs_m != None:
																return cs_m, next_index, cs_last_loc
															
																
									elif 'cmpnt match' in match['interventions']['add wire'].keys():
										m_cm = match['interventions']['add wire']['cmpnt match']
										m_touched_traces = m_cm.touched_traces_dict[m_pin]

										for m_touched_trace in m_touched_traces:
											if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
												#can you find this missing ref match in this trace?
												cm = ComponentMatching()
												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")


												m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
												m_matches = cm.filter_out_pads(m_matches, ignore_pads)

												if len(m_matches) > 0:
													for m_match in m_matches:
														match_cpy = dict(match.copy())
														match_cpy['nodes'] = match['nodes'].copy()
														match_cpy['interventions'] = match['interventions'].copy()
														new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
														match_cpy['interventions'][int_index] = new_intervention
														node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
														match_cpy['nodes'].append(node_dict)
														match_cpy['traces'] = match['traces'] + m_match.touched_traces_dict[pin]
														match_cpy['traces'] = list(set(match_cpy['traces']))

														missing_node_IDs_cpy = missing_node_IDs.copy()

														if m_missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(m_missing_node)

														if missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(missing_node)

														if cir_match != None:
															cir_match_cpy = cir_match.copy()
														else:
															cir_match_cpy = None

														cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
														
														if cs_m != None:
															return cs_m, next_index, cs_last_loc
															

					if not match_via_intervention:
						# search for a Component Match for that ref on other relevant traces
						cm_matches = []

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

						touched_traces = match['traces'] + ignore_traces

						if cir_match != None:
							cir_match_cpy_i = cir_match.copy()
							for cir_ref, cir_cm in cir_match.ref_dict.items():
								touched_traces += cir_cm.touched_traces_list
						else:
							cir_match_cpy_i = None



						

						print(f'finding matches for {ref}')
						if circuit_matching != None:
							if not hasattr(circuit_matching, 'cm_data'):
								circuit_matching.cm_data = {}

							if footprint in circuit_matching.cm_data.keys():
								if 'full' in circuit_matching.cm_data[footprint].keys():
									matches = circuit_matching.cm_data[footprint]['full']
									matches = cm.add_traces_data_to_matches(matches)
								else:
									matches = cm.get_matches()
									matches = cm.sort_matches(matches)
									matches = cm.add_traces_data_to_matches(matches)
									circuit_matching.cm_data[footprint]['full'] = matches
							else:
								matches = cm.get_matches()
								matches = cm.sort_matches(matches)
								matches = cm.add_traces_data_to_matches(matches)
								circuit_matching.cm_data[footprint] = {'full': matches }
						else:
							if hasattr(self, 'cm_data'):
								if footprint in self.cm_data.keys():
									if 'full' in self.cm_data[footprint].keys():
										matches = self.cm_data[footprint]['full']
									else:
										matches = cm.get_matches()
										matches = cm.sort_matches(matches)
										matches = cm.add_traces_data_to_matches(matches)
										self.cm_data[footprint]['full'] = matches
								else:
									matches = cm.get_matches()
									matches = cm.sort_matches(matches)
									matches = cm.add_traces_data_to_matches(matches)
									self.cm_data[footprint] = {'full': matches }
							else:
								matches = cm.get_matches()
								matches = cm.sort_matches(matches)
								matches = cm.add_traces_data_to_matches(matches)
								self.cm_data[footprint] = {'full': matches}
						print('got matches')

						matches = cm.filter_out_traces(matches, touched_traces, [pin])

						cm_i = 0



						if len(matches) > 0:

							while 1:
								
								cm_match = matches[cm_i]
								
								match_cpy = dict(match.copy())
								match_cpy['incomplete'] = True 
								if 'interventions' in match_cpy.keys():
									match_cpy['interventions'] = match['interventions'].copy()
									add_wire = True
									for intervention in match_cpy['interventions']:
										if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
											if intervention['add wire']['missing node'] == missing_node:
												add_wire = False
												break
									if add_wire:
										match_cpy['interventions'].append({'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}})
								else:
									match_cpy['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}}]
								match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
								match_cpy['traces'] = list(set(match_cpy['traces']))

								missing_node_IDs_cpy = missing_node_IDs.copy()
								missing_node_IDs_cpy.remove(missing_node)

								if cir_match_cpy_i != None:
									cir_match_cpy = cir_match_cpy_i.copy()
								else:
									cir_match_cpy = None

								cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
								
								if cs_m != None:
									return cs_m, next_index, cs_last_loc

								cm_i += 1

								if cm_i >= len(matches):
									break

		return None, next_index, last_loc


	def trace_cut_fifo(self, match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, ignore_traces = [], index = 0, search_index = 0, circuit_matching = None, cir_match = None, missing_nets = [], last_loc = []):
		'''
		Recursive strategy for finding the next valid net match for circuit (rather than exhaustive search)

		Parameters:
		match (dict) - Net match dict to search on
		missing_node_IDs (arr) - array of node_IDs (str) to search for
		temp_dir (str) - directory where to output temp image files 
        kicad_cli (str) - path to access kicad command line interface tool
        footprints_dir (str) - path to the directory of kicad footprints

        fxnOptional:
        ignore_traces (array) - array of traces to ignore on search
        index (int) - way to keep track of search paths
        search_index (int) - skip some searching if you are going for next match
        circuit_matching (CircuitMatching obj) - to continue circuit matching search
        cir_match (CircuitMatch) - to continue circuit match search
        missing_nets (arr) - array of nets still missing

        Returns:
        CircuitMatch - completed circuit match or None
        index (int) - where the search completed
        *or*
        Incomplete Net Match dict

		'''

		last_loc.append({'fxn': 'trace_cut_fifo', 'match': match, 'missing_node_IDs': missing_node_IDs, 'ignore_traces': ignore_traces, 'index': index, 
			'circuit_matching': circuit_matching, 'cir_match': cir_match, 'missing_nets': missing_nets, 'net_matching': self})

		if len(missing_node_IDs) == 0:
			return match, index, last_loc

		next_index = 0

		if search_index is None:
			search_index = 0

		missing_node = missing_node_IDs[0]
		[ref, pin] = missing_node.split('-')

		match = self.update_traces(match.copy())
		def continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index):
			'''
			Helper function

			'''
			
			next_index += 1
			if search_index != 0:
				search_index -= 1
				return None, next_index, last_loc, search_index
			else:
				if cir_match_cpy != None:
					print('cs cir match is not None')
					if circuit_matching.intervention_combo_valid(cir_match_cpy.circuit_arr + [match_cpy]):
						print('combo was valid')
						if len(missing_node_IDs_cpy)> 0:
							print('missing node ids')
							## use fwi_fifo first... then trace cut if returns None (on exit from continue search)
							search_on_node, n_index, n_last_loc = self.fwi_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, cir_match_cpy, missing_nets, last_loc)

							if search_on_node != None:
								print('search_on_node is not None!')

								if not isinstance(search_on_node, dict):
									return search_on_node, next_index, n_last_loc, search_index
								else:
									n_cir_match.add_net(search_on_node)
									missing_nets_cpy = missing_nets.copy()
									missing_nets_cpy.remove(match_cpy['net'])

									#preserve old circuit matching board
									old_board = circuit_matching.pcb_board.copy_self()
									circuit_matching.pcb_board = self.pcb_board
									cir_match_cpy.update_traces(cir_match_cpy.circuit_arr, self.pcb_board)

									cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, n_last_loc)
									if cm_search != None:
										return cm_search, next_index, cm_last_loc, search_index
									else:
										#return old circuit matching board
										circuit_matching.pcb_board = old_board
										self.pcb_board = old_board
										cir_match_cpy.update_traces(cir_match_cpy.circuit_arr, self.pcb_board)
									
										return None, next_index, last_loc, search_index
							else:
								return None, next_index, last_loc, search_index
						elif len(missing_node_IDs_cpy) == 0:

							missing_nets_cpy = missing_nets.copy()
							missing_nets_cpy.remove(match_cpy['net'])

							cir_match_cpy.add_net(match_cpy)

							cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc)
							
							if cm_search != None:
								if circuit_matching.intervention_combo_valid(cm_search.circuit_arr):
									return cm_search, next_index, cm_last_loc, search_index


					else:
						print('combo not valid')
						return None, next_index, last_loc, search_index
					
				else:
					print('cs cir match is None')
					return None, next_index, last_loc, search_index
					

			return None, next_index, last_loc, search_index

		
		def check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node_ID, missing_node_IDs_cpy, search_index=search_index, next_index=next_index):
			'''
			Helper function

			'''
			print('check_trace_cut')

			

			next_index += 1
			if search_index != 0:
				search_index -= 1
				return None, next_index, last_loc, search_index
			else:
				if cir_match_cpy != None:
					#cm_match.visualize_match("cm", True, self.pcb_board.pcb_rgb, cm_match.coordinates)
					circuit_matching.pcb_board = self.pcb_board.copy_self()
					cir_match_cpy = cir_match_cpy.update_traces(cir_match_cpy.circuit_arr, self.pcb_board)
					match_cpy = self.update_traces(match_cpy)
					cm_match = cm_match.update_traces(self.pcb_board)

					

					interventions = circuit_matching.identify_trace_conflicts(cir_match_cpy.circuit_arr, match_cpy, cm_match, missing_node_ID)

					if interventions != {} and isinstance(interventions, dict):
						n_cir_arr = []
						for cir_match_net in cir_match_cpy.circuit_arr:
							if cir_match_net['net'] in interventions.keys():
								if 'interventions' in cir_match_net.keys():
									cir_match_net['interventions'] += interventions[cir_match_net['net']]
								else:
									cir_match_net['interventions'] = interventions[cir_match_net['net']]
							n_cir_arr.append(cir_match_net)

						if match_cpy['net'] in interventions.keys():
							if 'interventions' in match_cpy.keys():
								match_cpy['interventions'] += interventions[match_cpy['net']]
							else:
								match_cpy['interventions'] = interventions[match_cpy['net']]


						if 'interventions' in match_cpy.keys():
							add_wire = True
							for intervention in match_cpy['interventions']:
								if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
									if intervention['add wire']['missing node'] == missing_node_ID:
										add_wire = False
										break
							if add_wire:
								match_cpy['interventions'].append({'add wire': {'missing node': missing_node_ID, 'cmpnt match': cm_match}})
						else:
							match_cpy['interventions'] = [{'add wire': {'missing node': missing_node_ID, 'cmpnt match': cm_match}}]
						

						all_trace_cuts = {'front cuts': [], 'back cuts': []}
						for net, interventions_list in interventions.items():
							for intervention in interventions_list:
								for key,val in intervention.items():
									if key == 'trace cuts':
										all_trace_cuts['front cuts'] += val['front cuts']
										all_trace_cuts['back cuts'] += val['back cuts']

						
						self.pcb_board.integrate_trace_cuts(all_trace_cuts)


						n_cir_match = cir_match_cpy.update_traces(n_cir_arr, self.pcb_board)
						match_cpy = self.update_traces(match_cpy)

						missing_node_IDs_ccpy = missing_node_IDs_cpy.copy()
						missing_node_IDs_ccpy.remove(missing_node_ID)


						if len(missing_node_IDs_ccpy)> 0:
							print('missing node ids')

							## use fwi_fifo first... then trace cut if returns poorly

							search_on_node, n_index, n_last_loc = self.fwi_fifo(match_cpy, missing_node_IDs_ccpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, n_cir_match, missing_nets, last_loc)

							if search_on_node != None:
								print('search_on_node is not None!')
								if not isinstance(search_on_node, dict):
									return search_on_node, next_index, n_last_loc, search_index
								else:
									n_cir_match.add_net(search_on_node)
									missing_nets_cpy = missing_nets.copy()
									missing_nets_cpy.remove(match_cpy['net'])

									#preserve old circuit matching board
									old_board = circuit_matching.pcb_board.copy_self()
									circuit_matching.pcb_board = self.pcb_board
									cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, n_last_loc)
									if cm_search != None:
										return cm_search, next_index, cm_last_loc, search_index
									else:
										#return old circuit matching board
										circuit_matching.pcb_board = old_board
										self.pcb_board = old_board
										return None, next_index, last_loc, search_index
							else:
								#try trace cut

								

								old_board = circuit_matching.pcb_board.copy_self()
								n_search_on_node, nn_index, nn_last_loc = self.trace_cut_fifo(match_cpy, missing_node_IDs_ccpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, n_cir_match, missing_nets, last_loc)

								if n_search_on_node != None:
									print('trace cut worked - continuing')
									if not isinstance(n_search_on_node, dict):
										print('is not dict instance')
										return n_search_on_node, next_index, n_last_loc, search_index
									else:
										print('dict instance')
										n_cir_match.add_net(n_search_on_node)
										missing_nets_cpy = missing_nets.copy()
										missing_nets_cpy.remove(match_cpy['net'])

										## preserve old circuit matching board
										old_board = circuit_matching.pcb_board.copy_self()
										circuit_matching.pcb_board = self.pcb_board

										cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, n_last_loc)
										if cm_search != None:
											return cm_search, next_index, cm_last_loc, search_index
										else:
											#return old circuit matching board
											circuit_matching.pcb_board = old_board
											self.pcb_board = old_board
											return None, next_index, last_loc, search_index


								else:
									circuit_matching.pcb_board = old_board
									self.pcb_board = old_board
									return None, next_index, last_loc, search_index
						elif len(missing_node_IDs_ccpy) == 0:
							print('reached end!')

							

							missing_nets_cpy = missing_nets.copy()
							missing_nets_cpy.remove(match_cpy['net'])

							n_cir_match.add_net(match_cpy)

							## preserve old circuit matching board
							old_board = circuit_matching.pcb_board.copy_self()
							circuit_matching.pcb_board = self.pcb_board

							cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_mwi_fifo(n_cir_match.copy(), missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc)
							if cm_search != None:
								return cm_search, cm_search_index, cm_last_loc, search_index
							else:
								#return old circuit matching board
								circuit_matching.pcb_board = old_board
								self.pcb_board = old_board
								return None, next_index, last_loc, search_index

					elif interventions == {}:
						return None, next_index, last_loc, search_index


					else:
						return None, next_index, last_loc, search_index
					
				else:
					return None, next_index, last_loc, search_index	

			return None, next_index, last_loc, search_index


		def check_for_existing_matches_on_trace(cm, footprint, trace, pin_arr):
			
			if circuit_matching != None:
				if not hasattr(circuit_matching, 'cm_data'):
					circuit_matching.cm_data = {}

				if footprint in circuit_matching.cm_data.keys():

					if trace in circuit_matching.cm_data[footprint].keys():

						if len(pin_arr) > 0:
							matches = []
							for pin in pin_arr:
								if str(trace) + '-pin-' + str(pin) in circuit_matching.cm_data[footprint].keys():
									matches += circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)]
								else:
									pin_matches = cm.filter_for_matches_on_trace(circuit_matching.cm_data[footprint][trace], trace, [pin])
									circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_matches
									matches += pin_matches
						else:
							matches = circuit_matching.cm_data[footprint][trace]
					elif 'full' in circuit_matching.cm_data[footprint].keys():
						full_matches = circuit_matching.cm_data[footprint]['full']
						matches = cm.filter_for_matches_on_trace(full_matches, trace, pin_arr)
					else:
						matches = []
						if len(pin_arr) > 0:
						
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
							circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin_arr[0])] = pin_t_matches
							circuit_matching.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								circuit_matching.cm_data[footprint]['full'] = f_matches				
							matches += pin_t_matches

							if len(pin_arr) > 1:
								for pin in pin_arr[1]:
									pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
									circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
									matches += pin_t_matches
						else:
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
							circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
							circuit_matching.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								circuit_matching.cm_data[footprint]['full'] = f_matches			
							matches += pin_t_matches

				else:
					matches = []
					if len(pin_arr) > 0:
						
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
						circuit_matching.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
						circuit_matching.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							circuit_matching.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

						if len(pin_arr) > 1:
							for pin in pin_arr[1]:
								pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
								circuit_matching.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								matches += pin_t_matches
					else:
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
						circuit_matching.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
						circuit_matching.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							circuit_matching.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

			else:
				if hasattr(self, 'cm_data'):
					if footprint in self.cm_data.keys():
						if trace in self.cm_data[footprint].keys():
							if len(pin_arr) > 0:
								matches = []
								for pin in pin_arr:
									if str(trace) + '-pin-' + str(pin) in self.cm_data[footprint].keys():
										matches += self.cm_data[footprint][str(trace) + '-pin-' + str(pin)]
									else:
										pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint][trace], trace, [pin])
										self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_matches
										matches += pin_matches
							else:
								matches = self.cm_data[footprint][trace]
						elif 'full' in self.cm_data[footprint].keys():
							full_matches = self.cm_data[footprint]['full']
							matches = cm.filter_for_matches_on_trace(full_matches, trace, pin_arr)
						else:

							matches = []
							if len(pin_arr) > 0:
							
								pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin_arr[0])] = pin_t_matches
								self.cm_data[footprint][trace] = t_matches
								if len(f_matches) > 0:
									self.cm_data[footprint]['full'] = f_matches				
								matches += pin_t_matches

								if len(pin_arr) > 1:
									for pin in pin_arr[1]:
										pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
										self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
										matches += pin_t_matches
							else:
								pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								self.cm_data[footprint][trace] = t_matches
								if len(f_matches) > 0:
									self.cm_data[footprint]['full'] = f_matches				
								matches += pin_t_matches

					else:
						matches = []
						if len(pin_arr) > 0:
							
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
							self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
							self.cm_data[footprint][trace] = t_matches	
							if len(f_matches) > 0:
								self.cm_data[footprint]['full'] = f_matches			
							matches += pin_t_matches

							if len(pin_arr) > 1:
								for pin in pin_arr[1]:
									pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
									self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
									matches += pin_t_matches
						else:
							pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
							self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
							self.cm_data[footprint][trace] = t_matches
							if len(f_matches) > 0:
								self.cm_data[footprint]['full'] = f_matches				
							matches += pin_t_matches

				else:
					self.cm_data = {}
					matches = []
					if len(pin_arr) > 0:
						
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin_arr[0]])
						self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin_arr[0]): pin_t_matches}
						self.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							self.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

						if len(pin_arr) > 1:
							for pin in pin_arr[1]:
								pin_t_matches = cm.filter_for_matches_on_trace(t_matches, trace, [pin])
								self.cm_data[footprint][str(trace) + '-pin-' + str(pin)] = pin_t_matches
								matches += pin_t_matches
					else:
						pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, pin_arr)
						self.cm_data[footprint] = {str(trace) + '-pin-' + str(pin): pin_t_matches}
						self.cm_data[footprint][trace] = t_matches
						if len(f_matches) > 0:
							self.cm_data[footprint]['full'] = f_matches				
						matches += pin_t_matches

			return matches

		def update_cm_data():
			if hasattr(self, 'cm_data'):
				for fp, val in self.cm_data.items():
					for id, matches in val.items():
						for match in matches:
							match.update_traces(self.pcb_board)
			if circuit_matching != None:
				circuit_matching.cm_data = self.cm_data

		update_cm_data()

		if cir_match != None and ref in cir_match.refs:
			
			match_cpy = dict(match.copy())
			match_cpy['incomplete'] = True
			if 'interventions' in match_cpy.keys():
				
				if isinstance(match['interventions'], list):
					match_cpy['interventions'] = match['interventions'].copy()
					add_wire = True
					for intervention in match_cpy['interventions']:
						if isinstance(intervention, dict) and 'add wire' in intervention.keys() and isinstance(intervention['add wire'], dict) and 'missing node' in intervention['add wire'].keys():
							if intervention['add wire']['missing node'] == missing_node:
								add_wire = False
								break
					if add_wire:
						match_cpy['interventions'].append({'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}})

				elif isinstance(match['interventions'], dict):
					int_cpy = dict(match['interventions'].copy)
					match_cpy['interventions'] = [int_cpy, {'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}}]
			else:
				match_cpy['interventions'] = [{'add wire': {'missing node':missing_node, 'cmpnt match': cir_match.ref_dict[ref]}}]
			match_cpy['traces'] = match['traces'] + cir_match.ref_dict[ref].touched_traces_dict[pin]
			match_cpy['traces'] = list(set(match_cpy['traces']))

			missing_node_IDs_cpy = missing_node_IDs.copy()
			missing_node_IDs_cpy.remove(missing_node)

			cir_match_cpy = cir_match.copy()

			cs_m = None

			if cs_m != None:
				return cs_m, next_index, cs_last_loc
			else:
				print('could not continue on search... try trace cutting?')

				match_cpy = dict(match.copy())

				missing_node_IDs_cpy = missing_node_IDs.copy()
				cir_match_cpy = cir_match.copy()

				cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cir_match.ref_dict[ref], missing_node, missing_node_IDs_cpy, search_index, next_index)

				if cs_m != None:
					
					return cs_m, next_index, cs_last_loc
				else:
					return None, next_index, last_loc
				#return None, next_index, cs_last_loc
			

		
		
		elif cir_match != None and len(match['traces']) == 0:
			
			# need to find a whole new connection
			# search for a Component Match for that ref on other relevant traces
			cm_matches = []

			footprint = ''
			# get element footprint
			for node in self.nodes:
				if node['ref'] == ref:
					footprint = node['footprint']
					break

			if len(footprint) > 0:
				footprint_arr = footprint.split(":")
				fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
				if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])							
					
					if complete.returncode != 0:
						print('did not return')
						fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
					
					gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

			
			cm = ComponentMatching()
			cm.pcb_board = self.pcb_board
			cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

			cir_match_cpy_i = cir_match.copy()

			ignore_pads = {'front pads': [], 'back pads': []}
			ignore_pads['front pads'] += cir_match.touched_pads['front pads']
			ignore_pads['back pads'] += cir_match.touched_pads['back pads']


			for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
				if self.pcb_board.get_num_pads_on_traces([trace_ID]) >= 1: # at least one possible match possible

					matches = check_for_existing_matches_on_trace(cm, footprint, trace_ID, [pin])

					matches = cm.filter_out_pads(matches, ignore_pads)

					cir_match = cir_match_cpy_i.copy()

					cm_i = 0

					if len(matches) > 0:


						while 1:
							
							cm_match = matches[cm_i]
							
							match_cpy = {'traces': [trace_ID], 'nodes': [{'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}], 'net': match['net']}
							match_cpy['incomplete'] = True 
							
							match_cpy['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}}]

							missing_node_IDs_cpy = missing_node_IDs.copy()
							missing_node_IDs_cpy.remove(missing_node)

							cir_match_cpy = cir_match.copy()

							cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
							
							if cs_m != None:
								return cs_m, next_index, cs_last_loc
							else:
								print('try trace cutting')
								match_cpy = {'traces': [trace_ID], 'nodes': [{'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}], 'net': match['net']}
								
								missing_node_IDs_cpy = missing_node_IDs.copy()

								cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
								if cs_m != None:
									if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
										return cs_m, next_index, cs_last_loc

							cm_i += 1

							if cm_i >= len(matches):
								break
			return None, next_index, last_loc
			
		
		else:


			existing_refs = []
			existing_refs_dict = {}
			net_matches = []
			ignore_pads = {'front pads': [], 'back pads': []}
			for match_node in match['nodes']:
				[m_ref,m_pin] = match_node['node'].split('-')
				if match_node['match'].fb == 'front':
					ignore_pads['front pads'] += match_node['match'].pad_IDs[m_pin]
				else:
					ignore_pads['back pads'] += match_node['match'].pad_IDs[m_pin]
				if m_ref not in existing_refs:
					existing_refs.append(m_ref)
					if m_ref not in existing_refs_dict.keys():
						existing_refs_dict[m_ref] = [match_node['node']]
					else:
						existing_refs_dict[m_ref].append(match_node['node'])

			if 'interventions' in match.keys():
				if isinstance(match['interventions'], list):
					for intervention in match['interventions']:
						if 'add wire' in intervention.keys():
							if 'cmpnt match' in intervention['add wire']:
								cm = intervention['add wire']['cmpnt match']
								[m_ref,m_pin] = intervention['add wire']['missing node'].split('-')

								if cm.fb == 'front':
									ignore_pads['front pads'] += cm.pad_IDs[m_pin]
								else:
									ignore_pads['back pads'] += cm.pad_IDs[m_pin]
								
								if m_ref not in existing_refs:
									existing_refs.append(m_ref)

								if m_ref not in existing_refs_dict.keys():
									existing_refs_dict[m_ref] = [intervention['add wire']['missing node']]
								else:
									existing_refs_dict[m_ref].append(intervention['add wire']['missing node'])


				elif isinstance(match['interventions'], dict):
					if 'add wire' in match['interventions'].keys():
						if 'cmpnt match' in match['interventions']['add wire']:
							cm = match['interventions']['add wire']['cmpnt match']
							[m_ref,m_pin] = match['interventions']['add wire']['missing node'].split('-')

							if cm.fb == 'front':
								ignore_pads['front pads'] += cm.pad_IDs[m_pin]
							else:
								ignore_pads['back pads'] += cm.pad_IDs[m_pin]
							
							if m_ref not in existing_refs:
								existing_refs.append(m_ref)

							if m_ref not in existing_refs_dict.keys():
								existing_refs_dict[m_ref] = [match['interventions']['add wire']['missing node']]
							else:
								existing_refs_dict[m_ref].append(match['interventions']['add wire']['missing node'])

			if cir_match != None:
				ignore_pads['front pads'] += cir_match.touched_pads['front pads']
				ignore_pads['back pads'] += cir_match.touched_pads['back pads']

			# for missing nodes, can they be implemented on current trace?
			
			num_pads_on_trace = self.pcb_board.get_num_pads_on_traces(match['traces'])


			if num_pads_on_trace > len(match['nodes']):
				
				#is possible that other nodes can be matched on trace

				## fifo strategy
				missing_node = missing_node_IDs[0]

				[ref,pin] = missing_node.split('-')


				
				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
													
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

					#does this ref already exist in the match?
					
					if ref in existing_refs:
						# add wire between pins of that ref
						
						match_cpy = dict(match.copy())
						match_cpy['incomplete'] = True
						if 'interventions' in match_cpy.keys():
							
							if isinstance(match['interventions'], list):
								match_cpy['interventions'] = match['interventions'].copy()
								if missing_node not in existing_refs_dict[ref]:
									match_cpy['interventions'].append({'add wire':[missing_node] + existing_refs_dict[ref]})
							elif isinstance(match['interventions'], dict):
								int_cpy = dict(match['interventions'].copy)
								match_cpy['interventions'] = [int_cpy, {'add wire': [missing_node] + existing_refs_dict[ref]}]
						else:
							match_cpy['interventions'] = [{'add wire': [missing_node] + existing_refs_dict[ref]}]

						
						missing_node_IDs_cpy = missing_node_IDs.copy()
						missing_node_IDs_cpy.remove(missing_node)

						if cir_match != None:
							cir_match_cpy = cir_match.copy()
						else:
							cir_match_cpy = None
						cs_m = None
						if cs_m != None:
							return cs_m, next_index, cs_last_loc
						else:
							return None, next_index, last_loc


					else:
						# see if matches possible on trace for this missing node ID

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

						matches = []
						for trace in match['traces']:
							matches += check_for_existing_matches_on_trace(cm, footprint_arr[1], trace, [pin])

						matches = cm.filter_out_pads(matches, ignore_pads)
						

						match_located = False
						for cm_match in matches:
							node_dict = {'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}
							match_cpy = dict(match.copy())
							match_cpy = {key: value for key, value in match.items()}
							match_cpy['nodes'] = match['nodes'].copy()
							match_cpy['nodes'].append(node_dict)
							match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
							match_cpy['traces'] = list(set(match_cpy['traces']))
							
							missing_node_IDs_cpy = missing_node_IDs.copy()
							missing_node_IDs_cpy.remove(missing_node)

							if cir_match != None:
								cir_match_cpy = cir_match.copy()
							else:
								cir_match_cpy = None

							print('first continue search')
							cs_m = None
							#cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
							
							if cs_m != None:
								print('contineu search valid')
								return cs_m, next_index, cs_last_loc
							else:
								print('trying trace cutting')
								match_cpy = dict(match.copy())
								match_cpy = {key: value for key, value in match.items()}
								match_cpy['nodes'] = match['nodes'].copy()

								missing_node_IDs_cpy = missing_node_IDs.copy()
								if cir_match != None:
									cir_match_cpy = cir_match.copy()
								else:
									cir_match_cpy = None

								cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
								if cs_m != None:
									return cs_m, next_index, cs_last_loc

			match = self.update_traces(match)

			ignore_pads = {'front pads': [], 'back pads': []}
			for match_node in match['nodes']:
				[m_ref,m_pin] = match_node['node'].split('-')
				if match_node['match'].fb == 'front':
					ignore_pads['front pads'] += match_node['match'].pad_IDs[m_pin]
				else:
					ignore_pads['back pads'] += match_node['match'].pad_IDs[m_pin]
				if m_ref not in existing_refs:
					existing_refs.append(m_ref)
					if m_ref not in existing_refs_dict.keys():
						existing_refs_dict[m_ref] = [match_node['node']]
					else:
						existing_refs_dict[m_ref].append(match_node['node'])

			if cir_match != None:
				cir_match = cir_match.update_traces(cir_match.circuit_arr, self.pcb_board)
				ignore_pads['front pads'] += cir_match.touched_pads['front pads']
				ignore_pads['back pads'] += cir_match.touched_pads['back pads']


			# find wire interventions for nodes

			missing_node = missing_node_IDs[0]

			
			ref = missing_node.split('-')[0]
			pin = missing_node.split('-')[1]

			footprint = ''
			# get element footprint
			for node in self.nodes:
				if node['ref'] == ref:
					footprint = node['footprint']
					break

			if len(footprint) > 0:
				footprint_arr = footprint.split(":")
				fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
				if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
												
					gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")


			#does this ref already exist in the match?

			if ref in existing_refs:
				# add wire between pins of that ref
				print('ref in existing_refs')
				
			else:
				print('looking in interventions')
				match = self.update_traces(match)
				
				# can matches be made on a connected intervention trace?
				match_via_intervention = False
				
				if 'interventions' in match.keys():
					if isinstance(match['interventions'], list):
						int_index = 0
						for intervention in match['interventions']:
							if 'add wire' in intervention.keys():
								if isinstance(intervention['add wire'], dict):
									#can ignore if list
									m_missing_node = intervention['add wire']['missing node']
									[m_ref,m_pin] = m_missing_node.split('-')

									if 'cmpnt matches' in intervention['add wire'].keys():
										for m_cm in intervention['add wire']['cmpnt matches']:
											m_touched_traces = m_cm.touched_traces_dict[m_pin]

											for m_touched_trace in m_touched_traces:
												if len(self.trace_map[m_touched_trace]) > 1: #needs to hold more than one
													#can you find this missing ref match in this trace?
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

													
													m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
													m_matches = cm.filter_out_pads(m_matches, m_cm.pad_IDs[m_pin])

													
													cm.add_traces_data_to_matches(m_matches)

													if len(m_matches) > 0:
														for m_match in m_matches:
															match_cpy = dict(match.copy())
															match_cpy['nodes'] = match['nodes'].copy()
															match_cpy['interventions'] = match['interventions'].copy()
															new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
															match_cpy['interventions'][int_index] = new_intervention
															node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
															match_cpy['nodes'].append(node_dict)
															missing_node_IDs_cpy = missing_node_IDs.copy()

															if m_missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(m_missing_node)

															if missing_node in missing_node_IDs_cpy:
																missing_node_IDs_cpy.remove(missing_node)

															cir_match_cpy = cir_match.copy()

															cs_m = None
															
															if cs_m != None:
																return cs_m, next_index, cs_last_loc
															else:
																print('trying trace cutting')
																match_cpy = dict(match.copy())
																match_cpy = {key: value for key, value in match.items()}
																match_cpy['nodes'] = match['nodes'].copy()

																missing_node_IDs_cpy = missing_node_IDs.copy()
																cir_match_cpy = cir_match.copy()

																cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, m_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
																if cs_m != None:
																	
																	return cs_m, next_index, cs_last_loc
																else:
																	
																	return None, next_index, last_loc
															
														
									elif 'cmpnt match' in intervention['add wire'].keys():
										m_cm = intervention['add wire']['cmpnt match'].update_traces(self.pcb_board)
										m_touched_traces = m_cm.touched_traces_dict[m_pin]



										for m_touched_trace in m_touched_traces:
											
											if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
												#can you find this missing ref match in this trace?
												cm = ComponentMatching()
												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

												m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
												m_matches = cm.filter_out_pads(m_matches, ignore_pads)
												
												
												cm.add_traces_data_to_matches(m_matches)
												if len(m_matches) > 0:
													n_cm_i = 0
													while 1:
														
														m_match = m_matches[n_cm_i]
														match_cpy = dict(match.copy())
														match_cpy['nodes'] = match['nodes'].copy()
														match_cpy['interventions'] = match['interventions'].copy()

														new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
														match_cpy['interventions'][int_index] = new_intervention
														node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
														match_cpy['nodes'].append(node_dict)
														missing_node_IDs_cpy = missing_node_IDs.copy()

														if m_missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(m_missing_node)

														if missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(missing_node)

														if cir_match != None:
															cir_match_cpy = cir_match.copy()
														else:
															cir_match_cpy = None
														cs_m = None
														if cs_m != None:
															return cs_m, next_index, cs_last_loc
														
														n_cm_i += 1

														if n_cm_i >= len(m_matches):
															break

													n_cm_i = 0
													while 1:
														m_match = m_matches[n_cm_i]
														
														match_cpy = dict(match.copy())
														match_cpy = {key: value for key, value in match.items()}
														match_cpy['nodes'] = match['nodes'].copy()

														missing_node_IDs_cpy = missing_node_IDs.copy()
														
														if cir_match != None:
															cir_match_cpy = cir_match.copy()
														else:
															cir_match_cpy = None

														cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, m_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
														if cs_m != None:
															if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
																return cs_m, next_index, cs_last_loc

														n_cm_i += 1

														if n_cm_i >= len(m_matches):
															break

														
							int_index += 1


					elif isinstance(match['interventions'], dict):
						if 'add wire' in match['interventions'].keys():
							if isinstance(match['interventions']['add wire'], dict):
								#can ignore if list
								m_missing_node = match['interventions']['add wire']['missing node']
								[m_ref,m_pin] = m_missing_node.split('-')

								if 'cmpnt matches' in match['interventions']['add wire'].keys():
									for m_cm in match['interventions']['add wire']['cmpnt matches']:
										m_touched_traces = m_cm.touched_traces_dict[m_pin]

										for m_touched_trace in m_touched_traces:
											if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
												#can you find this missing ref match in this trace?
												cm = ComponentMatching()
												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

												m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
												m_matches = cm.filter_out_pads(m_matches, ignore_pads)
												#m_matches = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pads=ignore_pads)
												cm.add_traces_data_to_matches(m_matches)
												if len(m_matches) > 0:
													for m_match in m_matches:
														match_cpy = dict(match.copy())
														match_cpy['nodes'] = match['nodes'].copy()
														match_cpy['interventions'] = match['interventions'].copy()
														new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
														match_cpy['interventions'][int_index] = new_intervention
														node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
														match_cpy['nodes'].append(node_dict)
														missing_node_IDs_cpy = missing_node_IDs.copy()

														if m_missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(m_missing_node)

														if missing_node in missing_node_IDs_cpy:
															missing_node_IDs_cpy.remove(missing_node)

														if cir_match != None:
															cir_match_cpy = cir_match.copy()
														else:
															cir_match_cpy = None

														cs_m = None
														#cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
														if cs_m != None:
															return cs_m, next_index, cs_last_loc

													for m_match in m_matches:
														print('trying trace cutting')
														match_cpy = dict(match.copy())
														match_cpy = {key: value for key, value in match.items()}
														match_cpy['nodes'] = match['nodes'].copy()

														missing_node_IDs_cpy = missing_node_IDs.copy()
														cir_match_cpy = cir_match.copy()

														cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, m_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
														if cs_m != None:
															if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
																return cs_m, next_index, cs_last_loc

														
															
								elif 'cmpnt match' in match['interventions']['add wire'].keys():
									m_cm = match['interventions']['add wire']['cmpnt match']
									m_touched_traces = m_cm.touched_traces_dict[m_pin]

									for m_touched_trace in m_touched_traces:
										if self.pcb_board.get_num_pads_on_traces([m_touched_trace]) > 1: #needs to hold more than one
											#can you find this missing ref match in this trace?
											cm = ComponentMatching()
											cm.pcb_board = self.pcb_board
											cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

											m_matches = check_for_existing_matches_on_trace(cm, footprint_arr[1], m_touched_trace, [pin])
											m_matches = cm.filter_out_pads(m_matches, ignore_pads)
											#m_matches = cm.get_matches_on_trace(m_touched_trace, [pin], ignore_pads=ignore_pads)
											cm.add_traces_data_to_matches(m_matches)
											if len(m_matches) > 0:
												for m_match in m_matches:
													match_cpy = dict(match.copy())
													match_cpy['nodes'] = match['nodes'].copy()
													match_cpy['interventions'] = match['interventions'].copy()
													new_intervention = {'add wire': {'missing node': m_missing_node, 'cmpnt match': m_cm}}
													match_cpy['interventions'][int_index] = new_intervention
													node_dict = {'node': missing_node, 'match': m_match, 'pads': m_match.pad_IDs[pin]}
													match_cpy['nodes'].append(node_dict)
													missing_node_IDs_cpy = missing_node_IDs.copy()

													if m_missing_node in missing_node_IDs_cpy:
														missing_node_IDs_cpy.remove(m_missing_node)

													if missing_node in missing_node_IDs_cpy:
														missing_node_IDs_cpy.remove(missing_node)

													if cir_match != None:
														cir_match_cpy = cir_match.copy()
													else:
														cir_match_cpy = None

													cs_m = None
													#cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
													if cs_m != None:
														return cs_m, next_index, cs_last_loc

												for m_match in m_matches:
													print('trying trace cutting')
													match_cpy = dict(match.copy())
													match_cpy = {key: value for key, value in match.items()}
													match_cpy['nodes'] = match['nodes'].copy()

													missing_node_IDs_cpy = missing_node_IDs.copy()
													cir_match_cpy = cir_match.copy()

													cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, m_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
													if cs_m != None:
														if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
															return cs_m, next_index, cs_last_loc
														
				

				if not match_via_intervention:
					print('not match via intervention')
					# search for a Component Match for that ref on other relevant traces
					cm_matches = []

					#exclude traces that are touched by other net match components
					touched_traces = match['traces'] + ignore_traces

					for match_node in match['nodes']:
						cm = match_node['match']
						touched_traces += cm.touched_traces_list

					

					cm = ComponentMatching()
					cm.pcb_board = self.pcb_board
					cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")


					if cir_match != None:
						cir_match_cpy_i = cir_match.copy()
						for cir_ref, cir_cm in cir_match.ref_dict.items():
							touched_traces += cir_cm.touched_traces_list
					else:
						cir_match_cpy_i = None

					print(f'finding matches for {ref}')
					if circuit_matching != None:
						if not hasattr(circuit_matching, 'cm_data'):
							circuit_matching.cm_data = {}

						if footprint in circuit_matching.cm_data.keys():
							if 'full' in circuit_matching.cm_data[footprint].keys():
								matches = circuit_matching.cm_data[footprint]['full']
								matches = cm.add_traces_data_to_matches(matches)
							else:
								matches = cm.get_matches()
								matches = cm.sort_matches(matches)
								matches = cm.add_traces_data_to_matches(matches)
								circuit_matching.cm_data[footprint]['full'] = matches
						else:
							matches = cm.get_matches()
							matches = cm.sort_matches(matches)
							matches = cm.add_traces_data_to_matches(matches)
							circuit_matching.cm_data[footprint] = {'full': matches }
					else:
						if hasattr(self, 'cm_data'):
							if footprint in self.cm_data.keys():
								if 'full' in self.cm_data[footprint].keys():
									matches = self.cm_data[footprint]['full']
								else:
									matches = cm.get_matches()
									matches = cm.sort_matches(matches)
									matches = cm.add_traces_data_to_matches(matches)
									self.cm_data[footprint]['full'] = matches
							else:
								matches = cm.get_matches()
								matches = cm.sort_matches(matches)
								matches = cm.add_traces_data_to_matches(matches)
								self.cm_data[footprint] = {'full': matches }
						else:
							matches = cm.get_matches()
							matches = cm.sort_matches(matches)
							matches = cm.add_traces_data_to_matches(matches)
							self.cm_data[footprint] = {'full': matches}

					print(f'got matches {len(matches)}')

					matches = cm.filter_out_pads(matches, ignore_pads)

					uf_matches = matches
					
					matches = cm.filter_out_traces(matches, touched_traces, [pin])



					cm_i = 0

					if len(matches) > 0:


						while 1:
							
							cm_match = matches[cm_i]
							
							
							match_cpy = dict(match.copy())
							match_cpy['incomplete'] = True 
							if 'interventions' in match_cpy.keys():
								match_cpy['interventions'] = match['interventions'].copy()
								match_cpy['interventions'].append({'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}})
							else:
								match_cpy['interventions'] = [{'add wire': {'missing node': missing_node, 'cmpnt match': cm_match}}]
							match_cpy['traces'] = match['traces'] + cm_match.touched_traces_dict[pin]
							match_cpy['traces'] = list(set(match_cpy['traces']))

							missing_node_IDs_cpy = missing_node_IDs.copy()
							missing_node_IDs_cpy.remove(missing_node)

							if cir_match != None:
								cir_match_cpy = cir_match.copy()
							else:
								cir_match_cpy = None
								
							#cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
							cs_m = None
							if cs_m != None:
								return cs_m, next_index, cs_last_loc
							else:
								print('try trace cutting with these loop')
								match_cpy = dict(match.copy())
								match_cpy = {key: value for key, value in match.items()}
								match_cpy['nodes'] = match['nodes'].copy()

								missing_node_IDs_cpy = missing_node_IDs.copy()
								
								if cir_match != None:
									cir_match_cpy = cir_match.copy()
								else:
									cir_match_cpy = None

								cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
								if cs_m != None:
									if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
										return cs_m, next_index, cs_last_loc

							cm_i += 1

							if cm_i >= len(matches):
								break

						cm_i = 0
						matches = uf_matches
						last_loc_copy = last_loc.copy()
						while 1:

							cm_match = matches[cm_i]
							last_loc = last_loc_copy.copy()
							
							print('trying trace cutting')
							match_cpy = dict(match.copy())
							match_cpy = {key: value for key, value in match.items()}
							match_cpy['nodes'] = match['nodes'].copy()

							if 'interventions' in match.keys():
								match_cpy['interventions'] = match['interventions'].copy()

							missing_node_IDs_cpy = missing_node_IDs.copy()
							if cir_match != None:
								cir_match_cpy = cir_match.copy()
							else:
								cir_match_cpy = None

							cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
							if cs_m != None:
								if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
									return cs_m, next_index, cs_last_loc

							cm_i += 1

							if cm_i >= len(matches):
								break
					else:

						cm_i = 0
						matches = uf_matches

						if cir_match != None:
							i_cir_match = cir_match.copy()
						else:
							i_cir_match = None

						while len(matches) > 0:
							cm_match = matches[cm_i]
							
							print('trying trace cutting')
							match_cpy = dict(match.copy())
							match_cpy = {key: value for key, value in match.items()}
							match_cpy['nodes'] = match['nodes'].copy()

							if 'interventions' in match.keys():
								match_cpy['interventions'] = match['interventions'].copy()


							missing_node_IDs_cpy = missing_node_IDs.copy()

							if i_cir_match != None:
								cir_match_cpy = i_cir_match.copy()
							else:
								cir_match_cpy = None

							

							cs_m, next_index, cs_last_loc, search_index = check_trace_cut(cir_match_cpy, match_cpy, cm_match, missing_node, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)

							if cs_m != None:
								if circuit_matching.intervention_combo_valid(cs_m.circuit_arr):
									return cs_m, next_index, cs_last_loc

							


							cm_i += 1

							if cm_i >= len(matches):
								break


		return None, next_index, last_loc

	def update_traces(self, net):

		net['traces'] = []

		net_connections_dict = {}
		node_dict = {}

		for node in net['nodes']:
			#updated touched_traces_list
			#update touched_traces_dict
			[n_ref, n_pin] = node['node'].split('-')
			node['match'].touched_traces_dict = {}
			node['match'].touched_traces_list = []

			for pin, pads in node['match'].pad_IDs.items():
				for pad in pads:
					for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
						if node['match'].fb == 'front':
							if pad in trace_info['front pads']:
								if pin in node['match'].touched_traces_dict.keys():
									node['match'].touched_traces_dict[pin].append(trace_ID)
								else:
									node['match'].touched_traces_dict[pin] = [trace_ID]
								node['match'].touched_traces_list.append(trace_ID)
								break
						else:
							if pad in trace_info['back pads']:
								if pin in node['match'].touched_traces_dict.keys():
									node['match'].touched_traces_dict[pin].append(trace_ID)
								else:
									node['match'].touched_traces_dict[pin] = [trace_ID]
								node['match'].touched_traces_list.append(trace_ID)
								break
			n_traces = node['match'].touched_traces_dict[n_pin]

			for n_trace in n_traces:
				if n_trace not in net['traces']:
					net['traces'].append(n_trace)
				if n_trace not in net_connections_dict.keys():
					net_connections_dict[n_trace] = [node['node']]
				else:
					net_connections_dict[n_trace].append(node['node'])

			if n_ref not in node_dict.keys():
				node_dict[n_ref] = node['match']
		if 'interventions' in net.keys():
			if isinstance(net['interventions'], list):
				for intervention in net['interventions']:
					if 'add wire' in intervention.keys():
						wire_info = intervention['add wire']
						if isinstance(wire_info, dict):
							missing_node = wire_info['missing node']
							pin = missing_node.split('-')[1]

							if 'cmpnt match' in wire_info.keys():
								cmpnt_match = wire_info['cmpnt match']
								cmpnt_match.touched_traces_dict = {}
								cmpnt_match.touched_traces_list = []

								for cm_pin, pads in cmpnt_match.pad_IDs.items():
									for pad in pads:
										for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
											if cmpnt_match.fb == 'front':
												if pad in trace_info['front pads']:
													if cm_pin in cmpnt_match.touched_traces_dict.keys():
														cmpnt_match.touched_traces_dict[cm_pin].append(trace_ID)
													else:
														cmpnt_match.touched_traces_dict[cm_pin] = [trace_ID]
													cmpnt_match.touched_traces_list.append(trace_ID)
													break
											else:
												if pad in trace_info['back pads']:
													if cm_pin in cmpnt_match.touched_traces_dict.keys():
														cmpnt_match.touched_traces_dict[cm_pin].append(trace_ID)
													else:
														cmpnt_match.touched_traces_dict[cm_pin] = [trace_ID]
													cmpnt_match.touched_traces_list.append(trace_ID)
													break

								n_traces = cmpnt_match.touched_traces_dict[pin]

								for n_trace in n_traces:
									if n_trace not in net['traces']:
										net['traces'].append(n_trace)
									if n_trace not in net_connections_dict.keys():
										net_connections_dict[n_trace] = [missing_node]
									else:
										if missing_node not in net_connections_dict[n_trace]:
											net_connections_dict[n_trace].append(missing_node)

								if missing_node.split('-')[0] not in node_dict.keys():
									node_dict[missing_node.split('-')[0]] = cmpnt_match

						elif isinstance(wire_info, list):

							for missing_node in wire_info:
								[ref, pin] = missing_node.split('-')

								for node in net['nodes']:
									if ref == node['node'].split('-')[0]:

										n_traces = node['match'].touched_traces_dict[pin]

										for n_trace in n_traces:
											if n_trace not in net['traces']:
												net['traces'].append(n_trace)
											if n_trace not in net_connections_dict.keys():
												net_connections_dict[n_trace] = [missing_node]
											else:
												net_connections_dict[n_trace].append(missing_node)

										if ref not in node_dict.keys():
											node_dict[ref] = node['match']
										break

			elif isinstance(net['interventions'], dict):
				if 'add wire' in net['interventions'].keys():
					wire_info = net['interventions']['add wire']
					missing_node = wire_info['missing node']
					pin = missing_node.split('-')[1]

					if 'cmpnt match' in wire_info.keys():
						cmpnt_match = wire_info['cmpnt match']
						cmpnt_match.touched_traces_dict = {}
						cmpnt_match.touched_traces_list = []

						for cm_pin, pads in cmpnt_match.pad_IDs.items():
							for pad in pads:
								for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
									if cmpnt_match.fb == 'front':
										if pad in trace_info['front pads']:
											if cm_pin in cmpnt_match.touched_traces_dict.keys():
												cmpnt_match.touched_traces_dict[cm_pin].append(trace_ID)
											else:
												cmpnt_match.touched_traces_dict[cm_pin] = [trace_ID]
											cmpnt_match.touched_traces_list.append(trace_ID)
											break
									else:
										if pad in trace_info['back pads']:
											if cm_pin in cmpnt_match.touched_traces_dict.keys():
												cmpnt_match.touched_traces_dict[cm_pin].append(trace_ID)
											else:
												cmpnt_match.touched_traces_dict[cm_pin] = [trace_ID]
											cmpnt_match.touched_traces_list.append(trace_ID)
											break

						n_traces = cmpnt_match.touched_traces_dict[pin]

						for n_trace in n_traces:
							if n_trace not in net['traces']:
								net['traces'].append(n_trace)
							if n_trace not in net_connections_dict.keys():
								net_connections_dict[n_trace] = [missing_node]
							else:
								net_connections_dict[n_trace].append(missing_node)

						if missing_node.split('-')[0] not in node_dict.keys():
							node_dict[missing_node.split('-')[0]] = cmpnt_match

		#check:is net properly connected still?
		if len(list(net_connections_dict.keys())) > 1:
			connected_traces = []
			connected_nodes_checked = []
			unconnected_nodes = []

			for trace, connected_nodes in net_connections_dict.items():
				if len(connected_traces) == 0:
					connected_traces.append(trace)
					connected_nodes_checked += connected_nodes
				else:
					connection_made = False
					for connected_node in connected_nodes:
						if connected_node in connected_nodes_checked:
							connection_made = True
							break

					if connection_made:
						for connected_node in connected_nodes:
							if connected_node not in connected_nodes_checked:
								connected_nodes_checked.append(connected_node)
						connected_traces.append(trace)
					else:
						unconnected_nodes += connected_nodes

			unconnected_nodes_cpy = unconnected_nodes.copy()
			for unconnected_node in unconnected_nodes_cpy:
				if unconnected_node in connected_nodes_checked:
					unconnected_nodes.remove(unconnected_node)


			if len(unconnected_nodes) > 0:
				for unconnected_node in unconnected_nodes:
					if 'interventions' in net.keys():
						if isinstance(net['interventions'], list):

							add_wire = True
							for n_intervention in net['interventions']:
								if isinstance(n_intervention, dict) and 'add wire' in n_intervention.keys() and isinstance(n_intervention['add wire'], dict) and 'missing node' in n_intervention['add wire'].keys():
									if n_intervention['add wire']['missing node'] == unconnected_node:
										add_wire = False
										break

							if add_wire:
								net['interventions'].append({'add wire': {'missing node': unconnected_node, 'cmpnt match': node_dict[unconnected_node.split('-')[0]]}})


						elif isinstance(net['interventions'], dict):
							net['interventions'] = [net['interventions'], {'add wire': {'missing_node': unconnected_node, 'cmpnt match': node_dict[unconnected_node.split('-')[0]]}}]
					else:
						net['interventions'] = [{'add wire': {'missing node': unconnected_node, 'cmpnt match': node_dict[unconnected_node.split('-')[0]]}}]

		return net


	def get_matches_fifo(self, match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, ignore_traces = [], index = 0, search_index = 0, circuit_matching = None, cir_match = None, missing_nets = [], last_loc = []):
		'''
			finds matches via a fifo strategy
		'''

		last_loc.append({'fxn': 'get_matches_fifo', 'match': match, 'missing_node_IDs': missing_node_IDs, 'ignore_traces': ignore_traces, 'index': index, 
			'circuit_matching': circuit_matching, 'cir_match': cir_match, 'missing_nets': missing_nets, 'net_matching': self})
		
		print('get_matches_fifo')

		
		if len(missing_node_IDs) == 0:
			return match, index, last_loc

		next_index = 0

		missing_node = missing_node_IDs[0]
		[ref, pin] = missing_node.split('-')

		def continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index):
			'''
			Helper function

			'''
			print('continue_search in get_matches_fifo')
			
			if search_index != 0:
				search_index -= 1
				return None, next_index, last_loc, search_index
			else:
				if cir_match_cpy != None:
					print('cir_match_copy is not None')


					if circuit_matching.net_combination_valid(cir_match_cpy.circuit_arr + [match_cpy]):
						if len(missing_node_IDs_cpy) > 0:

							
							search_on_node, n_index, n_last_loc = self.get_matches_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, cir_match_cpy, missing_nets, last_loc)
						
							if search_on_node != None:
								if not isinstance(search_on_node, dict):
									print('search_on_node not instance of dict')
									if circuit_matching.net_combination_valid(search_on_node.circuit_arr):
										return search_on_node, next_index, n_last_loc, search_index
								else:
									print('search_on_node is instance of dict')
									if circuit_matching.net_combination_valid(cir_match_cpy.circuit_arr + [search_on_node]):
										cir_match_cpy.add_net(search_on_node)
										missing_nets_cpy = missing_nets.copy()
										missing_nets_cpy.remove(match_cpy['net'])
										cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_match_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, n_last_loc)
										if cm_search != None:
											if circuit_matching.net_combination_valid(cm_search.circuit_arr):
												return cm_search, next_index, cm_last_loc, search_index
							else:
								return None, next_index, last_loc, search_index

						elif len(missing_node_IDs_cpy) == 0:
							print('missing_node_IDs_cpy is empty')
							missing_nets_cpy = missing_nets.copy()
							missing_nets_cpy.remove(match_cpy['net'])
							cir_match_cpy.add_net(match_cpy)



							cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_match_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc)
							
							if cm_search != None:
								if circuit_matching.net_combination_valid(cm_search.circuit_arr):
									
									return cm_search, next_index, cm_last_loc, search_index
							else:
								return None, next_index, last_loc, search_index
					else:
						return None, next_index, last_loc, search_index
				else:

					if len(missing_node_IDs_cpy) > 0:
							
						search_on_node, n_index, n_last_loc = self.get_matches_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index)
					
						if search_on_node != None:
							return search_on_node, n_index, n_last_loc, search_index

					elif len(missing_node_IDs_cpy) == 0:
						
						return match_cpy, next_index, last_loc, search_index


			return None, next_index, last_loc, search_index

		def check_for_existing_matches_on_trace(trace_ID, footprint, cm, pin=''):
			print(f'check_for_existing_matches_on_trace {trace_ID}, {footprint} {pin}')
			trace_matches_in_dict = False
			pin_trace_matches_in_dict = False
			full_matches_in_dict = False

			if hasattr(self, 'cm_data'):
				if footprint in self.cm_data.keys():
					if trace_ID in self.cm_data[footprint].keys():
						trace_matches_in_dict = True

					if 'full' in self.cm_data[footprint].keys():
						full_matches_in_dict = True

					if len(pin) > 0:
						if str(trace_ID) + '-pin-' + str(pin) in self.cm_data[footprint].keys():
							pin_trace_matches_in_dict = True

			if trace_matches_in_dict:

				if pin_trace_matches_in_dict:
					return self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)]
				elif len(pin) > 0:

					pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint][trace_ID], trace_ID, [pin])
					print(f'pin pt len of orig matches on trace: {len(self.cm_data[footprint][trace_ID])}, len of pin matches {len(pin_matches)}')
					self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] = pin_matches
					return pin_matches
				else:
					return self.cm_data[footprint][trace_ID]
			else:
				if full_matches_in_dict:
					print(f'full_matches: {len(self.cm_data[footprint]["full"])}')
					if len(pin)> 0:
						pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint]['full'], trace_ID, [pin])
						self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] = pin_matches
						return pin_matches
					else:
						return cm.filter_for_matches_on_trace(self.cm_data[footprint]['full'], trace_ID)
					

				else:

					return None


		if cir_match != None and ref in cir_match.refs:

			match_cpy = dict(match.copy())
			match_cpy['nodes'] = match['nodes'].copy()
			#are there traces in common?
			cm_in_cir= cir_match.ref_dict[ref]
			cm_in_cir_traces = cm_in_cir.touched_traces_dict[pin]

			is_connected = False
			for trace in match['traces']:
				if trace in cm_in_cir_traces:
					#connected!
					is_connected = True
					node_dict = {'node': missing_node, 'match': cm_in_cir, 'pads': cm_in_cir.pad_IDs[pin]}
					match_cpy['nodes'].append(node_dict)
					break
			
			if not is_connected:
				print('nodes not connected')
				return None, next_index, last_loc

			missing_node_IDs_cpy = missing_node_IDs.copy()
			missing_node_IDs_cpy.remove(missing_node)

			cir_match_cpy = cir_match.copy()

			cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
			if cs_m != None:
				return cs_m, next_index, cs_last_loc
			else:
				return None, next_index, cs_last_loc
		
		else:
			existing_refs = []
			existing_refs_dict = {}
			net_matches = []
			ignore_pads = {'front pads': [], 'back pads': []}
			for match_node in match['nodes']:
				[m_ref,m_pin] = match_node['node'].split('-')

				if match_node['match'].fb == 'front':
					ignore_pads['front pads'] += match_node['match'].pad_list
				else:
					ignore_pads['back pads'] += match_node['match'].pad_list
				if m_ref not in existing_refs:
					existing_refs.append(m_ref)
					if m_ref not in existing_refs_dict.keys():
						existing_refs_dict[m_ref] = [match_node['node']]
					else:
						existing_refs_dict[m_ref].append(match_node['node'])

			if cir_match != None:
				ignore_pads['front pads'] += cir_match.touched_pads['front pads']
				ignore_pads['back pads'] += cir_match.touched_pads['back pads']

			# for missing nodes, can they be implemented on current trace?
			
			num_pads_on_trace = self.pcb_board.get_num_pads_on_traces(match['traces'])


			if num_pads_on_trace >= len(match['nodes']) + len(missing_node_IDs):
				#is possible that other nodes can be matched on trace

				## fifo strategy
				missing_node = missing_node_IDs[0]

				[ref,pin] = missing_node.split('-')

				footprint = ''
				# get element footprint
				for node in self.nodes:
					if node['ref'] == ref:
						footprint = node['footprint']
						break

				if len(footprint) > 0:
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
						
						if complete.returncode != 0:
							print('did not return')
							fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
							complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
										
						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

					#does this ref already exist in the match?
					
					if ref in existing_refs:
						
						match_cpy = dict(match.copy())
						match_cpy['nodes'] = match['nodes'].copy()
						#are there traces in common?
						cm_in_cir= cir_match.ref_dict[ref]
						cm_in_cir_traces = cm_in_cir.touched_traces_dict[pin]

						is_connected = False
						for trace in match['traces']:
							if trace in cm_in_cir_traces:
								#connected!
								is_connected = True
								node_dict = {'node': missing_node, 'match': cm_in_cir, 'pads': cm_in_cir.pad_IDs[pin]}
								match_cpy['nodes'].append(node_dict)
								break
						
						if not is_connected:
							return None, next_index, last_loc
						
						missing_node_IDs_cpy = missing_node_IDs.copy()
						missing_node_IDs_cpy.remove(missing_node)

						cir_match_cpy = cir_match.copy()

						cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
						if cs_m != None:
							return cs_m, next_index, cs_last_loc

					else:
						# see if matches possible on trace for this missing node ID

						cm = ComponentMatching()
						cm.pcb_board = self.pcb_board
						cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
						matches = []
						print(f'component searching on {match["traces"]}')
						for trace in match['traces']:
							print(f'searching on trace {trace}')
							dict_t_matches = check_for_existing_matches_on_trace(trace, footprint_arr[1], cm, pin)
							if dict_t_matches != None:
								print('was in stored matches')
								matches += dict_t_matches
							else:
								pin_t_matches, t_matches, f_matches = cm.get_matches_on_trace(trace, [pin])
								print(f'len of pin matches {len(pin_t_matches)}, len of t_matches {len(t_matches)}, len of f_matches {len(f_matches)}')
								self.save_cm_data(trace, footprint_arr[1], t_matches, pin=pin, pin_t_matches=pin_t_matches, full_matches=f_matches)
								matches += pin_t_matches

						print(f'found {len(matches)} for {missing_node} on {match["traces"]}')
						matches = cm.filter_out_pads(matches, ignore_pads)
						matches = cm.sort_matches(matches)

						print(f'filtered pads to {len(matches)}')

						last_loc_copy = last_loc.copy()

						if len(matches) > 0:
							index = 0
							for cm_match in matches:
								last_loc = last_loc_copy.copy()
								index += 1
								node_dict = {'node': missing_node, 'match': cm_match, 'pads': cm_match.pad_IDs[pin]}
								match_cpy = dict(match.copy())
								match_cpy['nodes'] = match['nodes'].copy()
								match_cpy['nodes'].append(node_dict)

								match_cpy['traces'] = list(set(match_cpy['traces'] + cm_match.touched_traces_dict[pin]))
								
								missing_node_IDs_cpy = missing_node_IDs.copy()
								missing_node_IDs_cpy.remove(missing_node)


								if cir_match != None:
									cir_match_cpy = cir_match.copy()

									cs_m, next_index, cs_last_loc, search_index = continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
									if cs_m != None:
										return cs_m, next_index, cs_last_loc
									else:
										print('continue search was None')
								else:
									cs_m, next_index, cs_last_loc, search_index = continue_search(None, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index)
									if cs_m != None:
										return cs_m, next_index, cs_last_loc

							return None, next_index, last_loc
						else:
							print('no matches on those traces')
							return None, next_index, last_loc
			else:
				return None, next_index, last_loc
		return None, next_index, last_loc


	def get_connected_net_fifo(self, match, missing_node_IDs, unconnected_nodes, temp_dir, kicad_cli, footprints_dir, ignore_traces = [], index = 0, search_index = 0, circuit_matching = None, cir_match = None, missing_nets = [], last_loc = []):
		'''
			finds matches via a fifo strategy
		'''

		last_loc.append({'fxn': 'get_connected_net_fifo', 'match': match, 'missing_node_IDs': missing_node_IDs, 'unconnected_nodes': unconnected_nodes, 'ignore_traces': ignore_traces, 'index': index, 
			'circuit_matching': circuit_matching, 'cir_match': cir_match, 'missing_nets': missing_nets, 'net_matching': self})
		
		print('get_connected_net_fifo')
		print(missing_node_IDs)
		
		if len(missing_node_IDs) == 0:
			return match, index, last_loc

		next_index = 0

		def continue_search(cir_match_cpy, match_cpy, missing_node_IDs_cpy, search_index=search_index, next_index=next_index):
			'''
			Helper function

			'''
			print('continue_search in get_matches_fifo')
			print(search_index)
			next_index += 1
			if search_index != 0:
				search_index -= 1
				return None, next_index, last_loc, search_index
			else:
				if cir_match_cpy != None:
					print('cir_match_copy is not None')


					if circuit_matching.net_combination_valid(cir_match_cpy.circuit_arr + [match_cpy]):
						if len(missing_node_IDs_cpy) > 0:
							search_on_node, n_index, n_last_loc = self.get_matches_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index, circuit_matching, cir_match_cpy, missing_nets, last_loc)
						
							if search_on_node != None:
								if not isinstance(search_on_node, dict):
									print('search_on_node not instance of dict')
									if circuit_matching.net_combination_valid(search_on_node.circuit_arr):
										return search_on_node, next_index, n_last_loc, search_index
								else:
									print('search_on_node is instance of dict')
									if circuit_matching.net_combination_valid(cir_match_cpy.circuit_arr + [search_on_node]):
										cir_match_cpy.add_net(search_on_node)
										missing_nets_cpy = missing_nets.copy()
										missing_nets_cpy.remove(match_cpy['net'])
										cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_match_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, n_last_loc)
										if cm_search != None:
											if circuit_matching.net_combination_valid(cm_search.circuit_arr):
												return cm_search, next_index, cm_last_loc, search_index
							else:
								return None, next_index, last_loc, search_index

						elif len(missing_node_IDs_cpy) == 0:
							print('missing_node_IDs_cpy is empty')
							missing_nets_cpy = missing_nets.copy()
							missing_nets_cpy.remove(match_cpy['net'])
							cir_match_cpy.add_net(match_cpy)

							cm_search, cm_search_index, cm_last_loc = circuit_matching.get_next_match_fifo(cir_match_cpy, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, next_index, search_index, last_loc)
							
							if cm_search != None:
								if circuit_matching.net_combination_valid(cm_search.circuit_arr):
									return cm_search, next_index, cm_last_loc, search_index
							else:
								return None, next_index, last_loc, search_index
					else:
						return None, next_index, last_loc, search_index
				else:
					print('cir_match_copy is  None')

					if len(missing_node_IDs_cpy) > 0:
							
						search_on_node, n_index, n_last_loc = self.get_matches_fifo(match_cpy, missing_node_IDs_cpy, temp_dir, kicad_cli, footprints_dir, ignore_traces, next_index, search_index)
					
						if search_on_node != None:
							return search_on_node, n_index, n_last_loc, search_index

					elif len(missing_node_IDs_cpy) == 0:
						
						return match_cpy, next_index, last_loc, search_index


			return None, next_index, last_loc, search_index

		def check_for_existing_matches_on_trace(trace_ID, footprint, cm, pin=''):
			print(f'check_for_existing_matches_on_trace {trace_ID}, {footprint} {pin}')
			trace_matches_in_dict = False
			pin_trace_matches_in_dict = False
			full_matches_in_dict = False
			if hasattr(self, 'cm_data'):
				if footprint in self.cm_data.keys():
					if trace_ID in self.cm_data[footprint].keys():
						trace_matches_in_dict = True

					if 'full' in self.cm_data[footprint].keys():
						full_matches_in_dict = True

					if len(pin) > 0:
						if str(trace_ID) + '-pin-' + str(pin) in self.cm_data[footprint].keys():
							pin_trace_matches_in_dict = True

			if trace_matches_in_dict:

				if pin_trace_matches_in_dict:
					return self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)]
				elif len(pin) > 0:

					pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint][trace_ID], trace_ID, [pin])
					print(f'pin pt len of orig matches on trace: {len(self.cm_data[footprint][trace_ID])}, len of pin matches {len(pin_matches)}')
					self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] = pin_matches
					return pin_matches
				else:
					return self.cm_data[footprint][trace_ID]
			else:
				if full_matches_in_dict:
					print(f'full_matches: {len(self.cm_data[footprint]["full"])}')
					if len(pin)> 0:
						pin_matches = cm.filter_for_matches_on_trace(self.cm_data[footprint]['full'], trace_ID, [pin])
						self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] = pin_matches
					else:
						return cm.filter_for_matches_on_trace(self.cm_data[footprint]['full'], trace_ID)
					

				else:

					return None


		traces_to_connect = []
		nodes_needed = missing_node_IDs.copy()
		for node in unconnected_nodes:
			cm = cir_m.ref_dict[node['ref']]
			traces_to_connect += cm.touched_traces_dict[node['pin']]
			if node['ref'] + '-' + node['pin'] in nodes_needed:
				nodes_needed.remove(node['ref'] + '-' + node['pin'])

		if nodes_needed > 0:
			print('find nodes needed')



		



	def save_cm_data(self, trace_ID, footprint, matches, pin='', pin_t_matches = [], full_matches = []):

		if hasattr(self, 'cm_data'):
			if footprint in self.cm_data.keys():
				if trace_ID not in self.cm_data[footprint].keys():
					self.cm_data[footprint][trace_ID] = matches

				if len(pin) > 0 and str(trace_ID) + '-pin-' + str(pin) not in self.cm_data[footprint].keys():
					self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] = pin_t_matches

				if 'full' not in self.cm_data[footprint].keys():
					if len(full_matches) > 0:
						self.cm_data[footprint]['full'] = full_matches	
			else:
				self.cm_data[footprint] = {trace_ID: matches}
				if len(pin) > 0:
					self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] =  pin_t_matches

				if len(full_matches) > 0:
					self.cm_data[footprint]['full'] = full_matches	

		else:
			self.cm_data = {footprint: {trace_ID: matches}}
			if len(pin) > 0:
				self.cm_data[footprint][str(trace_ID) + '-pin-' + str(pin)] =  pin_t_matches
			if len(full_matches) > 0:
				self.cm_data[footprint]['full'] = full_matches	

	def visualize_net_matches(self, net_matches, wait=True):
		"""
        Quick visualization method for checking net matches 
        
   		"""

		for match in net_matches:
			if not self.pcb_board.double_sided:
				m_img_rgb = self.pcb_board.pcb_rgb.copy()
			else:
				m_img_rgb = self.pcb_board.pcb_rgb.copy()
				mb_img_rgb = self.pcb_board.pcb_rgb_back.copy()

			traces = match['traces']
			nodes = match['nodes']

			for node in nodes:
				
				cm = node['match']
				pad_IDs = cm.pad_IDs.values()
				
				for pad in node['pads']:
					if cm.fb == 'front':
						cv2.drawContours(m_img_rgb, self.pcb_board.mask_contours, pad, (0, 255,0), -1)
					else:
						cv2.drawContours(mb_img_rgb, self.pcb_board.mask_back_contours, pad, (0, 255,0), -1)

				for contour in cm.fp_contours:
					if cm.fb == 'front':
						cv2.drawContours(m_img_rgb, [contour], 0, (0, 0, 255), 3, offset=cm.coordinates)
					else:
						cv2.drawContours(mb_img_rgb, [contour], 0, (0, 0, 255), 3, offset=cm.coordinates)

			if 'interventions' in match.keys():
				if not self.pcb_board.double_sided:
					cpy_m_img_rgb = m_img_rgb.copy()
				else:
					cpy_m_img_rgb = m_img_rgb.copy()
					cpy_mb_img_rgb = mb_img_rgb.copy()

				if isinstance(match['interventions'], list):
					for intervention in match['interventions']:
						if 'add wire' in intervention.keys():
							wire_info = intervention['add wire']
							if isinstance(wire_info, dict):
								missing_node = wire_info['missing node']
								pin = missing_node.split('-')[1]
								if 'cmpnt matches' in wire_info.keys():
									for cmpnt_match in wire_info['cmpnt matches']:
										#cpy_m_img_rgb = m_img_rgb.copy()
										pad_IDs = cmpnt_match.pad_IDs[pin]
										for pad_ID in pad_IDs:
											if cmpnt_match.fb == 'front':
												cv2.drawContours(cpy_m_img_rgb, self.pcb_board.mask_contours, pad_ID, (0, 255, 255), -1)
											else:
												cv2.drawContours(cpy_mb_img_rgb, self.pcb_board.mask_back_contours, pad_ID, (0, 255, 255), -1)
											
								elif 'cmpnt match' in wire_info.keys():
									cmpnt_match = wire_info['cmpnt match']
									#cpy_m_img_rgb = m_img_rgb.copy()
									pad_IDs = cmpnt_match.pad_IDs[pin]
									for pad_ID in pad_IDs:
										if cmpnt_match.fb == 'front':
											cv2.drawContours(cpy_m_img_rgb, self.pcb_board.mask_contours, pad_ID, (0, 255, 255), -1)
										else:
											cv2.drawContours(cpy_mb_img_rgb, self.pcb_board.mask_back_contours, pad_ID, (0, 255, 255), -1)
										
							elif isinstance(wire_info, list):

								for missing_node in wire_info:
									[ref, pin] = missing_node.split('-')
									#cpy_m_img_rgb = m_img_rgb.copy()
									cm = None
									for node in nodes:
										if ref == node['node'].split('-')[0]:
											
											cm = node['match']
											pad_IDs = cm.pad_IDs[pin]
											for pad_ID in pad_IDs:
												if cm.fb == 'front':
													cv2.drawContours(cpy_m_img_rgb, self.pcb_board.mask_contours, pad_ID, (0, 255, 255), -1)
												else:
													cv2.drawContours(cpy_mb_img_rgb, self.pcb_board.mask_back_contours, pad_ID, (0, 255, 255), -1)
												
					if not self.pcb_board.double_sided:	
						cv2.imshow(match['net'], cpy_m_img_rgb)
						if wait:
							key = cv2.waitKeyEx(0)
					else:
						cv2.imshow(match['net'] + '-front', cpy_m_img_rgb)
						cv2.imshow(match['net'] + '-back', cpy_mb_img_rgb)
						if wait:
							key = cv2.waitKeyEx(0)


				elif isinstance(match['interventions'], dict):
					if 'add wire' in match['interventions'].keys():
						wire_info = match['interventions']['add wire']
						missing_node = wire_info['missing node']
						pin = missing_node.split('-')[1]
						if 'cmpnt matches' in wire_info.keys():
							for cmpnt_match in wire_info['cmpnt matches']:
								cpy_m_img_rgb = m_img_rgb.copy()
								pad_IDs = cmpnt_match.pad_IDs[pin]
								for pad_ID in pad_IDs:
									if cmpnt_match.fb == 'front':
										cv2.drawContours(cpy_m_img_rgb, self.pcb_board.mask_contours, pad_ID, (0, 255, 255), -1)
									else:
										cv2.drawContours(cpy_mb_img_rgb, self.pcb_board.mask_back_contours, pad_ID, (0, 255, 255), -1)
								if not self.pcb_board.double_sided:	
									cv2.imshow(match['net'], cpy_m_img_rgb)
									key = cv2.waitKeyEx(0)
								else:
									cv2.imshow(match['net'] + '-front', cpy_m_img_rgb)
									cv2.imshow(match['net'] + '-back', cpy_mb_img_rgb)
									key = cv2.waitKeyEx(0)
						elif 'cmpnt match' in wire_info.keys():
							cmpnt_match = wire_info['cmpnt match']
							cpy_m_img_rgb = m_img_rgb.copy()
							pad_IDs = cmpnt_match.pad_IDs[pin]
							for pad_ID in pad_IDs:
								if cmpnt_match.fb == 'front':
									cv2.drawContours(cpy_m_img_rgb, self.pcb_board.mask_contours, pad_ID, (0, 255, 255), -1)
								else:
									cv2.drawContours(cpy_mb_img_rgb, self.pcb_board.mask_back_contours, pad_ID, (0, 255, 255), -1)
							if not self.pcb_board.double_sided:	
								cv2.imshow(match['net'], cpy_m_img_rgb)
								if wait:
									key = cv2.waitKeyEx(0)
							else:
								cv2.imshow(match['net'] + '-front', cpy_m_img_rgb)
								cv2.imshow(match['net'] + '-back', cpy_mb_img_rgb)
								if wait:
									key = cv2.waitKeyEx(0)
			else:
				if not self.pcb_board.double_sided:	
					cv2.imshow(match['net'], m_img_rgb)
					if wait:
						key = cv2.waitKeyEx(0)
				else:
					cv2.imshow(match['net'] + '-front', m_img_rgb)
					cv2.imshow(match['net'] + '-back', mb_img_rgb)
					if wait:
						key = cv2.waitKeyEx(0)

			
			
			






