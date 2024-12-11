"""
	Holds circuit matching module
"""
from ComponentMatch import *
from NetMatch import *

from sch_reader import *
from svg_edit import *

from PCB_utils import *

import cv2
import os
import subprocess

class CircuitMatch():
	'''
		Represents a circuit match and includes relevant details of the match for future analysis

		Properties include
		component_matches (array) - array of component matches in circuit
		nets (array) - array of nets 
		touched_traces (array) - touched traces of this circuit match
		touched_pads (array) - touched pads by this circuit match
		refs (array) - array of components (as refs)
		ref_dict (dict) - component matches by ref keys
		interventions_net_arr (array) - interventions that need to be made
	'''

	def __init__(self, circuit_arr):
		"""
		init for component match 

		Parameters:
		circuit_arr (array) - array of net matches that complete the circuit
		"""
		self.circuit_arr = circuit_arr
		self.touched_traces = []
		self.nets = []
		self.refs = []
		self.component_matches = []
		self.touched_pads = {'front pads': [], 'back pads': []}
		self.ref_dict = {}
		self.interventions_net_arr = []
		for net in circuit_arr:
			self.touched_traces += net['traces']
			self.nets.append(net['net'])

			for node in net['nodes']:
				ref = node['node'].split('-')[0]
				self.refs.append(ref)
				self.ref_dict[ref] = node['match']
				if node['match'] not in self.component_matches:
					self.component_matches.append(node['match'])
					if hasattr(node['match'], 'touched_traces_list'):
						self.touched_traces += node['match'].touched_traces_list
						if node['match'].fb == 'front':
							self.touched_pads['front pads'] += node['match'].pad_list
						else:
							self.touched_pads['back pads'] += node['match'].pad_list

			if 'interventions' in net.keys():
				self.interventions_net_arr.append(net)
				if isinstance(net['interventions'], list):
					for intervention in net['interventions']:
						if 'add wire' in intervention.keys():
							if isinstance(intervention['add wire'], list):
								missing_node = intervention['add wire'][0]
								[ref, pin] = missing_node.split('-')
								cm = self.ref_dict[ref]
								self.touched_traces += cm.touched_traces_dict[pin]
							elif isinstance(intervention['add wire'], dict):
								if 'cmpnt match' in intervention['add wire'].keys():
									missing_node = intervention['add wire']['missing node']
									[ref, pin] = missing_node.split('-')
									cm = intervention['add wire']['cmpnt match']
									self.refs.append(ref)
									self.ref_dict[ref] = cm
									self.touched_traces += cm.touched_traces_dict[pin]

									if cm.fb == 'front':
										self.touched_pads['front pads'] += cm.pad_list
									else:
										self.touched_pads['back pads'] += cm.pad_list



				elif isinstance(net['interventions'], dict):
					if 'add wire' in net['interventions'].keys():
						if isinstance(net['interventions']['add wire'], list):
							missing_node = net['interventions']['add wire'][0]
							[ref, pin] = missing_node.split('-')
							cm = self.ref_dict[ref]
							self.touched_traces += cm.touched_traces_dict[pin]
						elif isinstance(net['interventions']['add wire'], dict):
							if 'cmpnt match' in net['interventions']['add wire'].keys():
								missing_node = net['interventions']['add wire']['missing node']
								[ref, pin] = missing_node.split('-')
								cm = net['interventions']['add wire']['cmpnt match']
								self.refs.append(ref)
								self.ref_dict[ref] = cm
								self.touched_traces += cm.touched_traces_dict[pin]
								
								if cm.fb == 'front':
									self.touched_pads['front pads'] += cm.pad_list
								else:
									self.touched_pads['back pads'] += cm.pad_list

	def add_net(self, net_dict):
		'''
			Function for adding a new net to the circuit and updated values
			Also checks if there are any issues before adding

			Parameters:
			net_dict - Net dict with values to add to circuit
		'''


		self.circuit_arr.append(net_dict)
		self.touched_traces += net_dict['traces']
		self.nets.append(net_dict['net'])

		for node in net_dict['nodes']:
			ref = node['node'].split('-')[0]
			self.refs.append(ref)
			self.ref_dict[ref] = node['match']
			if node['match'] not in self.component_matches:
				self.component_matches.append(node['match'])
				if hasattr(node['match'], 'touched_traces_list'):
					self.touched_traces += node['match'].touched_traces_list
					if node['match'].fb == 'front':
						self.touched_pads['front pads'] += node['match'].pad_list
					else:
						self.touched_pads['back pads'] += node['match'].pad_list

		if 'interventions' in net_dict.keys():
				self.interventions_net_arr.append(net_dict)
				if isinstance(net_dict['interventions'], list):
					for intervention in net_dict['interventions']:
						if 'add wire' in intervention.keys():
							if isinstance(intervention['add wire'], list):
								missing_node = intervention['add wire'][0]
								[ref, pin] = missing_node.split('-')
								cm = self.ref_dict[ref]
								self.touched_traces += cm.touched_traces_dict[pin]
								if cm.fb == 'front': 
									self.touched_pads['front pads'] += cm.pad_list
								else:
									self.touched_pads['back_pads'] += cm.pad_list
							elif isinstance(intervention['add wire'], dict):
								if 'cmpnt match' in intervention['add wire'].keys():
									missing_node = intervention['add wire']['missing node']
									[ref, pin] = missing_node.split('-')
									cm = intervention['add wire']['cmpnt match']
									self.refs.append(ref)
									self.ref_dict[ref] = cm
									self.touched_traces += cm.touched_traces_dict[pin]
									if cm.fb == 'front':
										self.touched_pads['front pads'] += cm.pad_list
									else:
										self.touched_pads['back pads'] += cm.pad_list

				elif isinstance(net_dict['interventions'], dict):
					if 'add wire' in net_dict['interventions'].keys():
						if isinstance(net_dict['interventions']['add wire'], list):
							missing_node = net_dict['interventions']['add wire'][0]
							[ref, pin] = missing_node.split('-')
							cm = self.ref_dict[ref]
							self.touched_traces += cm.touched_traces_dict[pin]
						elif isinstance(net_dict['interventions']['add wire'], dict):
							if 'cmpnt match' in net_dict['interventions']['add wire'].keys():
								missing_node = net_dict['interventions']['add wire']['missing node']
								[ref, pin] = missing_node.split('-')
								cm = net_dict['interventions']['add wire']['cmpnt match']
								self.refs.append(ref)
								self.ref_dict[ref] = cm
								self.touched_traces += cm.touched_traces_dict[pin]
								if cm.fb == 'front':
									self.touched_pads['front pads'] += cm.pad_list
								else:
									self.touched_pads['back pads'] += cm.pad_list

	def copy(self):
		return CircuitMatch(self.circuit_arr.copy())

	def update(self, circuit_arr):
		return CircuitMatch(circuit_arr)

	def update_traces(self, circuit_arr, pcb_board):
		new_circuit_arr = []

		

		for net in circuit_arr:
			#update net traces
			#update node info
			#update interventions info

			net['traces'] = []

			net_connections_dict = {}
			node_dict = {}

			for node in net['nodes']:
				[n_ref, n_pin] = node['node'].split('-')
				node['match'].touched_traces_dict = {}
				node['match'].touched_traces_list = []

				

				for pin, pads in node['match'].pad_IDs.items():
					for pad in pads:
						for trace_ID, trace_info in pcb_board.board_connections_dict.items():
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

				#temp = self.pcb_board.pcb_rgb.copy()
				#cv2.dr

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
											for trace_ID, trace_info in pcb_board.board_connections_dict.items():
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
									for trace_ID, trace_info in pcb_board.board_connections_dict.items():
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

			new_circuit_arr.append(net)
			
		return CircuitMatch(new_circuit_arr)

	def get_interventions_count(self):
		total = 0
		for net in self.interventions_net_arr:
			for intervention in net['interventions']:
				if 'add wire' in intervention.keys():
					if isinstance(intervention['add wire'], list):
						total += 1
					else:
						total += 1

				elif 'trace cuts' in intervention.keys():
					print(f"front cuts: {len(intervention['trace cuts']['front cuts'])}")
					total += len(intervention['trace cuts']['front cuts'])
					print(f"back cuts: {len(intervention['trace cuts']['back cuts'])}")
					total += len(intervention['trace cuts']['back cuts'])

		print(f'total: {total}')

		return total

	def get_all_trace_cuts(self):
		trace_cuts = {'front cuts': [], 'back cuts': []}

		for net in self.interventions_net_arr:
			for intervention in net['interventions']:
				if isinstance(intervention, dict):
					if 'trace cuts' in intervention.keys():
						trace_cuts['front cuts'] += intervention['trace cuts']['front cuts']
						trace_cuts['back cuts'] += intervention['trace cuts']['back cuts']

		if len(trace_cuts['front cuts']) + len(trace_cuts['back cuts']) > 0:
			return trace_cuts
		else:
			return None

	def to_json(self):


		m_cpy = self.copy()
		json_cpy = m_cpy.circuit_arr.copy()

		n_json_cpy = []

		for net in json_cpy:
			n_net = {'traces': net['traces'], 'net': net['net']}
			nodes = net['nodes'].copy()
			n_nodes = []
			for node in nodes:

				m_to_json = node['match'].copy().to_json()

				n_node = {'node': node['node'], 'match': m_to_json, 'pads': node['pads']}

				n_nodes.append(n_node)

			n_net['nodes'] = n_nodes


			if 'interventions' in net.keys():
				interventions = net['interventions'].copy()

				n_interventions = []

				for intervention in interventions:

					n_intervention = {}

					if 'trace cuts' in intervention.keys():
						f_cuts = intervention['trace cuts']['front cuts'].copy()
						b_cuts = intervention['trace cuts']['back cuts'].copy()

						n_f_cuts = []
						for f_cut in f_cuts:
							str_fp_cnt = '//'.join(str(elem) for elem in f_cut)
							n_f_cuts.append(str_fp_cnt)

						n_b_cuts = []
						for b_cut in b_cuts:
							str_fp_cnt = '//'.join(str(elem) for elem in b_cut)
							n_b_cuts.append(str_fp_cnt)
						
						n_intervention = {'trace cuts': {'front cuts': n_f_cuts, 'back cuts': n_b_cuts}}

					if 'add wire' in intervention.keys():
						if isinstance(intervention['add wire'], dict):
							if 'cmpnt match' in intervention['add wire'].keys():
					
								n_intervention = {'add wire': {'missing node': intervention['add wire']['missing node'], 'cmpnt match': intervention['add wire']['cmpnt match'].to_json()}}
					n_interventions.append(n_intervention)


				n_net['interventions'] = n_interventions
			n_json_cpy.append(n_net)


		return n_json_cpy










class CircuitMatching():
	'''
		Represents a process of circuit matching and related info

		mask_rgb (2D array) - solder mask image
		mask_contours (array) - array of contours for solderable pads
		
		pcb_rgb (2D array) - image of full PCB with traces
		trace_contours (array) - array of all contours in the PCB image (connected parts)

		pad_map (dict) - each pad with corresponding pad center
		trace_map (dict) - each trace with corresponding pads within trace

		cm_data (dict) - component match data for all components
	'''

	def __init__(self, sorted_refs, footprints_dict, net_arr):
		'''
		init function for net matching
		sorted_refs - ordered list of the components based on pin #
		footprints_dict - dictionary of footprints to the refs in the netlist
		net_arr - array of nets found in netlist
		'''
		self.sorted_refs = sorted_refs
		self.footprints_dict = footprints_dict
		self.net_arr = net_arr
		self.cm_data = {}

	def fill_cm_data(self, temp_dir, kicad_cli, footprints_dir):
		'''
		fill out cm_data dict by performing component matching across every component in net
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		
		Effects:
		CircuitMatching object property cm_data (dict) component matching information
		'''

		for fp, refs in self.footprints_dict.items():
			footprint_arr = fp.split(":")
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
			matches = cm.get_matches()

			sorted_matches = cm.sort_matches(matches)
			matches = cm.add_traces_data_to_matches(sorted_matches)

			for ref in refs:
				self.cm_data[ref] = {'matches': matches}

	def generate_components_file(self, file):

		data = self.cm_data.copy()

		for key,val in data.items():
			n_matches = []
			for match in val['matches']:
				n_matches.append(match.to_json())
			val['matches'] = n_matches

		with open(file, 'w') as f:
			json.dump(data, f)

	def load_component_matches_from_file(self, file):

		with open(file, 'r') as f:
			data = json.load(f)

		cm_data = {}

		for key,val in data.items():
			cm_arr = []
			for match in val['matches']:
				cm = ComponentMatch(0.00, [], [], (0,0), 0)

				for c_key,c_val in match.items():

					if c_key == 'fp_contours':
						c_val = c_val.replace('\n\n ', '*')
						c_val = c_val.replace('   ', ' ')
						c_val = c_val.replace('  ', ' ')
						c_val = c_val.replace('[ ', '[')
						c_val = c_val.replace(' ', ',')
						res = c_val.split('//')

						n_arr = []
						for elem in res:
							
							elem_s = elem[1: -1]
							n_elem = elem_s.split('*')

							a_elem = []
							for i_elem in n_elem:
								i_elem_s = i_elem[2:-2]
								pt = i_elem_s.split(',')
								n_pt = [[int(pt[0]), int(pt[1])]]
								a_elem.append(n_pt)
							n_arr.append(a_elem)

						arr_size = len(n_arr[0])

						for l_arr in n_arr:
							arr_size = min(len(l_arr), arr_size)

						nn_arr = []
						for l_arr in n_arr:
							l_arr = l_arr[0:arr_size]
							nn_arr.append(l_arr)


						cm.fp_contours = tuple(np.array(nn_arr, dtype=np.int32))
					else:
						setattr(cm, c_key, c_val) 
				cm_arr.append(cm)
			val['matches'] = cm_arr

			for f_key, f_val in self.footprints_dict.items():
				if key in f_val:
					fp = f_key.split(':')[1]
					cm_data[f_key] = {'full': cm_arr}
					cm_data[fp] = {'full': cm_arr}
					break

		return data, cm_data


	def save_matches(self, file, matches):

		data = {'id': 'save_matches', 'matches': []}

		for match in matches:
			cir_match = CircuitMatch(match)
			data['matches'].append(cir_match.to_json())
			
		with open(file, 'w') as f:
			json.dump(data, f)

	def load_matches(self, file, matches):

		with open(file, 'r') as f:
			data = json.load(f)

		for match in data['matches']:
			for net in match:
				for key,val in net.items():

					if key == 'nodes':

						cm = ComponentMatch(0.00, [], [], (0,0), 0)

						for node in val:

							for c_key,c_val in node['match'].items():

								if c_key == 'fp_contours':
									c_val = c_val.replace('\n\n ', '*')
									c_val = c_val.replace('   ', ' ')
									c_val = c_val.replace('  ', ' ')
									c_val = c_val.replace('[ ', '[')
									c_val = c_val.replace(' ', ',')
									res = c_val.split('//')

									n_arr = []
									for elem in res:
										
										elem_s = elem[1: -1]
										n_elem = elem_s.split('*')

										a_elem = []
										for i_elem in n_elem:
											i_elem_s = i_elem[2:-2]
											pt = i_elem_s.split(',')
											n_pt = [[int(pt[0]), int(pt[1])]]
											a_elem.append(n_pt)
										n_arr.append(a_elem)

									arr_size = len(n_arr[0])

									for l_arr in n_arr:
										arr_size = min(len(l_arr), arr_size)

									nn_arr = []
									for l_arr in n_arr:
										l_arr = l_arr[0:arr_size]
										nn_arr.append(l_arr)


									cm.fp_contours = tuple(np.array(nn_arr, dtype=np.int32))
								else:
									setattr(cm, c_key, c_val) 

							node['match'] = cm

					if key == 'interventions':
						for intervention in val:

							if 'trace cuts' in intervention.keys():
								f_cuts = intervention['trace cuts']['front cuts']
								b_cuts = intervention['trace cuts']['back cuts']

							if 'add wire' in intervention.keys():
								if isinstance(intervention['add wire'], dict):
									if 'cmpnt match' in intervention['add wire'].keys():
										cm = ComponentMatch(0.00, [], [], (0,0), 0)

										for c_key, c_val in intervention['add wire']['cmpnt match'].items():

											if c_key == 'fp_contours':
												c_val = c_val.replace('\n\n ', '*')
												c_val = c_val.replace('   ', ' ')
												c_val = c_val.replace('  ', ' ')
												c_val = c_val.replace('[ ', '[')
												c_val = c_val.replace(' ', ',')
												res = c_val.split('//')

												n_arr = []
												for elem in res:
													
													elem_s = elem[1: -1]
													n_elem = elem_s.split('*')

													a_elem = []
													for i_elem in n_elem:
														i_elem_s = i_elem[2:-2]
														pt = i_elem_s.split(',')
														n_pt = [[int(pt[0]), int(pt[1])]]
														a_elem.append(n_pt)
													n_arr.append(a_elem)

												arr_size = len(n_arr[0])

												for l_arr in n_arr:
													arr_size = min(len(l_arr), arr_size)

												nn_arr = []
												for l_arr in n_arr:
													l_arr = l_arr[0:arr_size]
													nn_arr.append(l_arr)


												cm.fp_contours = tuple(np.array(nn_arr, dtype=np.int32))
											else:
												setattr(cm, c_key, c_val) 

										intervention['add wire']['cmpnt match'] = cm
							

		return data['matches']



	def run_cm_via_traces(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Runs Component Matching on each component within Circuit but through a trace-centric approach (only looks at component matches for relevant traces)
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		
		Effects:
		Circuit object property cm_data (dict) component matching information
		'''

		starting_node_ref = self.sorted_refs[0]
		footprint = ''
		
		for fp, refs in self.footprints_dict.items():
			if starting_node_ref in refs:
				footprint = fp
				break

		footprint_arr = footprint.split(":")
		fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

		if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
			complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
		
			gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
		
		cm = ComponentMatching()
		cm.pcb_board = self.pcb_board
		cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
		matches = cm.get_matches()
		matches = cm.add_traces_data_to_matches(matches)
		matches = cm.sort_matches(matches)

		print(f'found {len(matches)} for {starting_node_ref}')

		init_net_matches_arr = []

		num_starting_nets = 0
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
			if contains_ref:
				num_starting_nets +=1


		for init_cm in matches:
			cm_ordered_nm_arr = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
						break

				if contains_ref:
					nm = NetMatching(net['node arr'], net['name'])
					nm.pcb_board = self.pcb_board
					t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
					
					p_net_arr = nm.process_trace_matches(t_net_arr)
					f_net_arr = nm.filter_matches(p_net_arr)
					full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
					cm_ordered_nm_arr.append(full_match_net_arr)
			init_net_matches_arr.append(cm_ordered_nm_arr)

		# remove for missing nets

		f_init_net_matches_arr = []

		for n_init_match in init_net_matches_arr:
			
			missing_net = False
			for net in n_init_match:
				if len(net) == 0:
					missing_net = True
					break
			if not missing_net:
				f_init_net_matches_arr.append(n_init_match)


		v_init_net_matches_arr = []

		for n_init_match_arr in f_init_net_matches_arr:

			n_nets = len(n_init_match_arr)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(n_init_match_arr[i]) > 0):
						net_combination.append(n_init_match_arr[i][indices[i]])

				if self.net_combination_valid(net_combination):
					valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(n_init_match_arr[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			v_init_net_matches_arr += valid_net_combinations

		full_valid_net_combos = []
		#continue on across any other nets not hit
		for v_init_match_arr in v_init_net_matches_arr:

			touched_refs = [self.sorted_refs[0]]

			if len(v_init_match_arr) > 0:
				#keep going

				missing_net = False

				valid_combos_last_ref = [v_init_match_arr]
				#loop through the rest of refs
				for ref in self.sorted_refs[1:]:

					#build off these sequentially
					
					valid_combos_last_net = valid_combos_last_ref

					for net in self.net_arr:
						contains_ref = False
						contains_touched_ref = False
						
						for node in net['node arr']:
							if(node['ref'] == ref):
								contains_ref = True
							if node['ref'] in touched_refs:
								contains_touched_ref = True
						
						if contains_ref and not contains_touched_ref:
							
							# try to run nm on existing match
							match_for_net_found = False
							#build off these sequentially
							valid_combos_last_net = valid_combos_last_ref

							for node in net['node arr']:
								if node['ref'] != ref:
									i_ref = node['ref']
									valid_combos_net_added = []
									#loop through nets in this current net combo
									for valid_combo in valid_combos_last_net:

										for v_net in valid_combo:

											contains_i_ref = False
											i_match = None
											for m_node in v_net['nodes']:
												if i_ref == m_node['node'].split('-')[0]:
													contains_i_ref = True
													i_match = m_node['match']
													break

											if contains_i_ref:
												
												nm = NetMatching(net['node arr'], net['name'])
												
												nm.pcb_board = self.pcb_board
												t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, i_match, i_ref)
												
												p_net_arr = nm.process_trace_matches(t_net_arr)
												f_net_arr = nm.filter_matches(p_net_arr)
												
												full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
												
												if(len(full_match_net_arr) > 0):
													
													temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)

													if len(temp_arr) > 0:
														valid_combos_net_added += temp_arr
														match_for_net_found = True
												break # break from looping through nets

									if match_for_net_found:
										valid_combos_last_net = valid_combos_net_added
										break

							if not match_for_net_found:
								nm = NetMatching(net['node arr'], net['name'])
								
								nm.pcb_board = self.pcb_board
								nm.nodes.sort(key=lambda x: x['total pins'], reverse=True)

								#create data structure to keep track of multi-pin components
								cm_pin_dict = {}

								for node in nm.nodes:
									if node['ref'] in cm_pin_dict.keys():
										cm_pin_dict[node['ref']].append(node['pin'])
									else:
										cm_pin_dict[node['ref']] = [node['pin']]

								valid_combos_net_added = []
								for valid_combo in valid_combos_last_net:
									touched_traces = []
									for v_net in valid_combo:
										for m_node in v_net['nodes']:
											touched_traces += m_node['match'].touched_traces_list

									for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
										if trace_ID not in touched_traces:
											if self.pcb_board.get_num_pads_on_traces([trace_ID]) > len(net['node arr']):
												starting_node = nm.nodes[0]
												footprint = starting_node['footprint']
												footprint_arr = footprint.split(":")
												fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

												if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
													complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
												
													gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
												
												cm = ComponentMatching()

												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
												matches,_,__ = cm.get_matches_on_trace(trace_ID, cm_pin_dict[starting_node['ref']])
												matches = cm.add_traces_data_to_matches(matches)
												matches = cm.sort_matches(matches)

												for init_match in matches:
													t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_match, starting_node['ref'])
													p_net_arr = nm.process_trace_matches(t_net_arr)
													f_net_arr = nm.filter_matches(p_net_arr)
													full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))

													if len(full_match_net_arr) > 0:
														temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)
														if(len(temp_arr) > 0):
															valid_combos_net_added += temp_arr
															match_for_net_found = True
								if match_for_net_found:
									valid_combos_last_net = valid_combos_net_added

							if not match_for_net_found:
								# net not found !
								missing_net = True
								break

					touched_refs.append(ref)
					if missing_net:
						break
					else:
						valid_combos_last_ref = valid_combos_last_net
				full_valid_net_combos += valid_combos_last_ref

		return full_valid_net_combos
	
	def run_cm_via_traces_queue(self, temp_dir, kicad_cli, footprints_dir, queue):
		'''
		Runs Component Matching on each component within Circuit but through a trace-centric approach (only looks at component matches for relevant traces)
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		
		Effects:
		Circuit object property cm_data (dict) component matching information
		'''

		starting_node_ref = self.sorted_refs[0]
		footprint = ''
		
		for fp, refs in self.footprints_dict.items():
			if starting_node_ref in refs:
				footprint = fp
				break

		starting_pins = []
		for net in self.net_arr:
			for node in net['node arr']:
				if starting_node_ref == node['ref']:
					starting_pins.append(node['pin'])

		footprint_arr = footprint.split(":")
		fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

		if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
			complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
			queue.put_nowait('circuit matching - gen first fp ')
			gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
		
		cm = ComponentMatching()
		
		cm.pcb_board = self.pcb_board
		cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
		
		queue.put_nowait('circuit matching - finding matches for first component')
		print(f'circuit matching - finding matches for first component {footprint_arr[1]}')
		matches = cm.get_matches()
		matches = cm.add_traces_data_to_matches(matches)
		matches = cm.sort_matches(matches)

		print('circuit matching - initial component matches found')

		init_net_matches_arr = []

		num_starting_nets = 0
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
			if contains_ref:
				num_starting_nets +=1

		print(f'circuit matching - found {len(matches)} component matches for {starting_node_ref}')
		print(f'circuit matching - searching for nets connected to {starting_node_ref}')

		for init_cm in matches:
			cm_ordered_nm_arr = []
			for net in self.net_arr:

				contains_ref = False
				for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
						break

				if contains_ref:
					print(f"circuit matching - searching for {net['name']}")
					nm = NetMatching(net['node arr'], net['name'])

					nm.pcb_board = self.pcb_board
					t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
					p_net_arr = nm.process_trace_matches(t_net_arr)
					f_net_arr = nm.filter_matches(p_net_arr)
					full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
					cm_ordered_nm_arr.append(full_match_net_arr)
			init_net_matches_arr.append(cm_ordered_nm_arr)

		# remove for missing nets

		f_init_net_matches_arr = []

		for n_init_match in init_net_matches_arr:
			missing_net = False
			for net in n_init_match:
				if len(net) == 0:
					missing_net = True
					break
			if not missing_net:
				f_init_net_matches_arr.append(n_init_match)

		
		v_init_net_matches_arr = []

		for n_init_match_arr in f_init_net_matches_arr:

			n_nets = len(n_init_match_arr)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(n_init_match_arr[i]) > 0):
						net_combination.append(n_init_match_arr[i][indices[i]])

				if self.net_combination_valid(net_combination):
					valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(n_init_match_arr[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			v_init_net_matches_arr += valid_net_combinations

		print(f"circuit matching - found {len(v_init_net_matches_arr)} matches for circuit surrounding {starting_node_ref}")
		full_valid_net_combos = []


		#continue on across any other nets not hit
		for v_init_match_arr in v_init_net_matches_arr:
			print(f"circuit matching - searching from match for circuit surrounding {starting_node_ref}")
					
			touched_refs = [self.sorted_refs[0]]

			if len(v_init_match_arr) > 0:
				#keep going

				missing_net = False

				valid_combos_last_ref = [v_init_match_arr]
				#loop through the rest of refs
				for ref in self.sorted_refs[1:]:
					#build off these sequentially
					
					valid_combos_last_net = valid_combos_last_ref

					for net in self.net_arr:
						contains_ref = False
						contains_touched_ref = False
						
						for node in net['node arr']:
							if(node['ref'] == ref):
								contains_ref = True
							if node['ref'] in touched_refs:
								contains_touched_ref = True
						
						if contains_ref and not contains_touched_ref:
							print(f"circuit matching - searching for {ref} matches in {net['name']}")

							# try to run nm on existing match
							match_for_net_found = False
							#build off these sequentially
							valid_combos_last_net = valid_combos_last_ref

							for node in net['node arr']:
								if node['ref'] != ref:
									i_ref = node['ref']
									print(f'looking at {i_ref} in {net["name"]}')
									valid_combos_net_added = []

									#loop through nets in this current net combo
									for valid_combo in valid_combos_last_net:
										for v_net in valid_combo:
											contains_i_ref = False
											i_match = None
											for m_node in v_net['nodes']:
												if i_ref == m_node['node'].split('-')[0]:
													contains_i_ref = True
													i_match = m_node['match']
													break

											if contains_i_ref:

												print(f'looking to make a connection via {i_ref} in {v_net["net"]}')
												nm = NetMatching(net['node arr'], net['name'])
												
												nm.pcb_board = self.pcb_board
												t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, i_match, i_ref)
												
												p_net_arr = nm.process_trace_matches(t_net_arr)
												f_net_arr = nm.filter_matches(p_net_arr)
												
												full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
												print(f'found {len(full_match_net_arr)} matches on existing {i_ref} via {v_net["net"]}')
												if(len(full_match_net_arr) > 0):
													
													temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)
													print(f'validated combos for {i_ref} matches')
													if len(temp_arr) > 0:
														valid_combos_net_added += temp_arr
														match_for_net_found = True
												break # break from looping through nets

									if match_for_net_found:
										valid_combos_last_net = valid_combos_net_added
										break

							if not match_for_net_found:
								print('searching for net elsewhere')

								nm.pcb_board = self.pcb_board
								nm.nodes.sort(key=lambda x: x['total pins'], reverse=True)

								#create data structure to keep track of multi-pin components
								cm_pin_dict = {}

								for node in nm.nodes:
									if node['ref'] in cm_pin_dict.keys():
										cm_pin_dict[node['ref']].append(node['pin'])
									else:
										cm_pin_dict[node['ref']] = [node['pin']]

								valid_combos_net_added = []
								for valid_combo in valid_combos_last_net:
									touched_traces = []
									for v_net in valid_combo:
										for m_node in v_net['nodes']:
											touched_traces += m_node['match'].touched_traces_list

									for trace_ID, trace_pads in self.trace_map.items():
										if trace_ID not in touched_traces:
											if len(trace_pads) > len(net['node arr']):
												starting_node = nm.nodes[0]
												footprint = starting_node['footprint']
												footprint_arr = footprint.split(":")
												fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

												if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
													complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
												
													gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
												print(f'searching for {starting_node["ref"]}')
												cm = ComponentMatching()
												
												cm.pcb_board = self.pcb_board
												cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
												matches,_,__ = cm.get_matches_on_trace(trace_ID, cm_pin_dict[starting_node['ref']])
												matches = cm.sort_matches(matches)
											
												print(f'found {len(matches)} searching for {starting_node["ref"]}')
												for init_match in matches:
													t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_match, starting_node['ref'])
													p_net_arr = nm.process_trace_matches(t_net_arr)
													f_net_arr = nm.filter_matches(p_net_arr)
													full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))

													print(f'found {len(full_match_net_arr)} searching for {net["name"]}')
													if len(full_match_net_arr) > 0:
														temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)
														if(len(temp_arr) > 0):
															valid_combos_net_added += temp_arr
															match_for_net_found = True
								if match_for_net_found:
									valid_combos_last_net = valid_combos_net_added

							if not match_for_net_found:
								# net not found !
								missing_net = True
								break

					touched_refs.append(ref)
					if missing_net:
						break
					else:
						valid_combos_last_ref = valid_combos_last_net
				full_valid_net_combos += valid_combos_last_ref

		return full_valid_net_combos

	def get_matches_fifo(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Finds *first* possible match. Useful for speed.
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		Returns:
		match - Array of net matches
		'''

		def check_for_component_matches(ref):
			if ref in self.cm_dict.keys():
				return self.cm_dict[ref]['matches']
			else:
				return None


		self.current_best_match = None

		starting_node_ref = self.sorted_refs[0]
		footprint = ''
		
		matches = check_for_component_matches(starting_node_ref)

		if matches is None:
			for fp, refs in self.footprints_dict.items():
				if starting_node_ref in refs:
					footprint = fp
					break

			footprint_arr = footprint.split(":")
			fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

			if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
				complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
				print(complete)
				if complete.returncode != 0:
					print('did not return')
					fp_parent_file = temp_dir + "/Footprint Libraries/KiCad.pretty"
					complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
				
				gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
			
			cm = ComponentMatching()
			cm.pcb_board = self.pcb_board
			cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

			try:
				matches = cm.get_matches()
			except:
				print('except hit')
				cm.fp_file = temp_dir + "/Footprint Libraries/KiCad.pretty/" + footprint_arr[1] + ".kicad_mod"
				matches = cm.get_matches()

			matches = cm.add_traces_data_to_matches(matches)
			matches = cm.sort_matches(matches)

		if hasattr(self, 'cm_dict'):
			if starting_node_ref not in self.cm_dict.keys():
				self.cm_dict[starting_node_ref] = matches
		else:
			self.cm_dict = {starting_node_ref: matches}

		print(f'found {len(matches)} for {starting_node_ref}')

		# get a net to start on that contains this component
		starting_net = {}
		starting_net_pins = []

		nets_with_starting_ref = []
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if node['ref'] == starting_node_ref:
					contains_ref = True
			if contains_ref:
				if starting_net == {}:
					starting_net = net
					nets_with_starting_ref.append(net['name'])
				else:
					nets_with_starting_ref.append(net['name'])

		## quick verification - if pins are connected on starting ref, do these matches satisfy?

		def all_pins_connected_search(next_pin, not_connected_pins, checked_pins, connected_pins_dict):
			n_checked_pins = checked_pins.copy()

			if next_pin not in n_checked_pins:
				n_checked_pins.append(next_pin)
			else:
				return not_connected_pins, checked_pins

			n_not_connected_pins = not_connected_pins.copy()
			if next_pin in n_not_connected_pins:
				n_not_connected_pins.remove(next_pin)

			if len(n_not_connected_pins) == 0:
				return n_not_connected_pins, n_checked_pins

			if len(n_checked_pins) == len(connected_pins_dict.keys()):
				return n_not_connected_pins, n_checked_pins

			if len(connected_pins_dict[next_pin]) == 0:
				return n_not_connected_pins, n_checked_pins
			else:
				for n_next_pin in connected_pins_dict[next_pin]:
					n_not_connected_pins, n_checked_pins = all_pins_connected_search(n_next_pin, n_not_connected_pins, n_checked_pins, connected_pins_dict)

					if len(n_not_connected_pins) == 0:
						return n_not_connected_pins, n_checked_pins

					if len(n_checked_pins) == len(connected_pins_dict.keys()):
						return n_not_connected_pins, n_checked_pins

				return n_not_connected_pins, n_checked_pins


		nets_to_check = []
		for net in self.net_arr:
			if net['name'] in nets_with_starting_ref:
				pins_connected_on_net = []
				for node in net['node arr']:
					if node['ref'] == starting_node_ref:
						pins_connected_on_net.append(node['pin'])
				if len(pins_connected_on_net) > 1 and len(pins_connected_on_net) == len(net['node arr']):
					nets_to_check.append(pins_connected_on_net)

		if len(nets_to_check) > 0:
			f_matches = []
			for match in matches:
				all_nets_satisfied = True
				for pins_combination in nets_to_check:
					touched_traces_dict = {}
					for pin in pins_combination:
						touched_traces_dict[pin] = match.touched_traces_dict[pin]

					connected_pins_dict = {}
					for pin in pins_combination:
						connected_pins_dict[pin] = []
						for pin_trace in touched_traces_dict[pin]:
							for ttd_pin, ttd_traces in touched_traces_dict.items():
								if pin_trace in ttd_traces:
									connected_pins_dict[pin].append(ttd_pin)

					not_connected_pins = pins_combination.copy()
					not_connected_pins.remove(pins_combination[0])
					checked_pins = []
					next_pin = pins_combination[0]


					not_connected_pins, checked_pins = all_pins_connected_search(next_pin, not_connected_pins, checked_pins, connected_pins_dict)

					if len(not_connected_pins) > 0:
						all_nets_satisfied = False
						break

				if all_nets_satisfied:
					f_matches.append(match)

			matches = f_matches
			print(f'filtered to {len(matches)}')

		for node in starting_net['node arr']:
			if node['ref'] == starting_node_ref:
				starting_net_pins.append(node['pin'])

		print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_node_ref}')

		nm = NetMatching(starting_net['node arr'], starting_net['name'])
		nm.pcb_board = self.pcb_board

		if hasattr(self, 'cm_data'):
			nm.cm_data = self.cm_data

		def locate_other_nets(cir_m, index=0, last_loc=[]):
			
			#approach this by looking at sorted refs

			starting_ref = ''
			for ref in self.sorted_refs[1:]:
				if ref not in cir_m.refs:
					starting_ref = ref
					break

			if starting_ref == '':
				print('all components are accounted for, validating matches on missing nets')
				#all refs are accounted for - are they properly connected?
				missing_net_arr = self.get_missing_nets(cir_m.circuit_arr)

				for missing_net in missing_net_arr:
					print(f'checking on {missing_net["name"]}')
					net_touched_traces = []
					all_nodes_connected = True
					net_match_nodes_arr = []

					for node in missing_net['node arr']:
						ref = node['ref']
						pin = node['pin']

						node_cm = cir_m.ref_dict[ref]

						node_cm_traces = node_cm.touched_traces_dict[pin]

						if len(net_touched_traces) == 0:
							net_touched_traces += node_cm_traces
							net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
						else:
							connected = False
							for n_cm_trace in node_cm_traces:
								if n_cm_trace in net_touched_traces:
									connected = True
									break

							if connected:
								for n_cm_trace in node_cm_traces:
									if n_cm_trace not in net_touched_traces:
										net_touched_traces.append(n_cm_trace)
								net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
							else:
								all_nodes_connected = False
								break


					if all_nodes_connected:
						#create a net for them
						net_dict = {'traces': net_touched_traces, 'nodes': net_match_nodes_arr, 'net': missing_net['name']}
						cir_m.add_net(net_dict)
					else:
						print('nodes were not connected!')
						return None, index, last_loc

				if self.net_combination_valid(cir_m.circuit_arr.copy()):
					print('exit locate_other_nets')
					return cir_m, index, last_loc
				else:
					print('exit locate_other_nets - None')
					return None, index, last_loc


			else:
				print(f'component match search for {starting_ref}')
				#use starting ref to run search

				# get a net to start on that contains this component
				starting_net = {}
				starting_net_pins = []

				nets_with_starting_ref = []
				for net in self.net_arr:
					contains_ref = False
					for node in net['node arr']:
						if node['ref'] == starting_ref:
							contains_ref = True
					if contains_ref:
						if starting_net == {}:
							starting_net = net
							nets_with_starting_ref.append(net['name'])
						else:
							nets_with_starting_ref.append(net['name'])

				for node in starting_net['node arr']:
					if node['ref'] == starting_ref:
						starting_net_pins.append(node['pin'])

				print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_ref}')

				n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, nets_with_starting_ref, temp_dir, kicad_cli, footprints_dir, last_loc = [])

				if n_cir_m != None:
					#seek out next nets
					nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

					if nn_cir_m != None:
						return nn_cir_m, nn_index, nn_last_loc
					else:
						return None, nn_index, nn_last_loc # here you could return a partial
				else:
					return None, n_index, last_loc

		def recursive_search_on_circuit(n_last_loc, n_search_index):
			

			orig_n_search_index = n_search_index

			while 1:

				if len(n_last_loc) > 1:
					last_step = n_last_loc[-2:-1][0]

					if last_step['fxn'] == 'get_matches_fifo':
						nm = last_step['net_matching']
						i_n_last_loc = n_last_loc.copy()
						nn_match, nn_index, nn_last_loc = nm.get_matches_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

						n_last_loc = i_n_last_loc

						if nn_match != None:
							if not isinstance(nn_match, dict):
								return nn_match, n_search_index, nn_last_loc
							else:
								cir_m = CircuitMatch([nn_match])
								missing_nets_cpy = last_step['missing_nets'].copy()
								cm_search, cm_search_index, cm_last_loc = self.get_next_match_fifo(cir_m, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir)
								
								if cm_search != None:
									return cm_search, cm_search_index, cm_last_loc

							
							n_search_index = nn_index - 1

							if len(nn_last_loc) > len(n_last_loc):

								t_last_loc = nn_last_loc[len(n_last_loc):].copy()
								ff_match, n_search_index, ff_last_loc = recursive_search_on_circuit(t_last_loc, t_last_loc[-1]['index'])
								
								if ff_match != None:
									print('within recursive_search_on_circuit (2)')
									return ff_match, n_search_index, ff_last_loc
								else:
									r_last_loc = n_last_loc.pop()
									n_search_index = last_step['index'] - 1

						else:
							r_last_loc = n_last_loc.pop()

							n_search_index = r_last_loc['index'] - 1
					elif last_step['fxn'] == 'get_next_match_fifo' and last_step['missing_nets'] == []:
						return None, n_search_index, n_last_loc
					else:
						r_last_loc = n_last_loc.pop()
						n_search_index = r_last_loc['index'] - 1

				else:
					break

				n_search_index += 1


			return None, orig_n_search_index, n_last_loc

		def add_nm_cm_data(nm):
			if not hasattr(nm, 'cm_data'):
				nm.cm_data = {}
			if not hasattr(self, 'cm_data'):
				self.cm_data = {}

			for key, val in nm.cm_data.items():
				if key in self.cm_data.keys():
					for trace_ID_key, match_vals in nm.cm_data[key].items():
						if trace_ID_key not in self.cm_data[key].keys():
							self.cm_data[key][trace_ID_key] = match_vals
				else:
					self.cm_data[key] = val

		# try to find matches on this net
		for init_cm_match in matches:
			print(f'looking on new component match for {starting_net["name"]}')

			if len(starting_net_pins) > 1: # multiple pins for same net
				print(f'component match has multiple pins for this net')
				# do they lie on the same trace for this match?
				touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]

				is_connected = True
				for starting_net_pin in starting_net_pins:
					s_touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]
					s_is_connected = False
					for s_touched_trace in s_touched_traces:
						if s_touched_trace in touched_traces:
							s_is_connected = True
							break
					if not s_is_connected:
						is_connected = False
						break

				if is_connected: # create a net match on these nets
					match_node_arr = []
					for node in starting_net['node arr']:
						if node['ref'] == starting_node_ref:
							node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': init_cm_match, 'pads': init_cm_match.pad_IDs[node['pin']]}
							match_node_arr.append(node_dict)
					
					net_match = {'traces': touched_traces, 'nodes': match_node_arr, 'net': starting_net['name']}
					cir_m = CircuitMatch([net_match])

					missing_nets = nets_with_starting_ref.copy()
					missing_nets.remove(starting_net['name'])

					n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = [])

					add_nm_cm_data(nm)
					if n_cir_m != None:
						#seek out next nets

						nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

						if nn_cir_m != None:
							return nn_cir_m, nn_index, nn_last_loc
						else:
							return None, nn_index, nn_last_loc # here you could return a partial
					else:
						starting_net_search_index = 1
						while 1:
							print(f'%Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
							
							net_match, nm_index, nm_last_loc = nm.get_matches_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
							add_nm_cm_data(nm)

							if net_match != None:
								print(f'a net match was found at {starting_net_search_index}')
								cir_m = CircuitMatch([net_match])

								n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
								add_nm_cm_data(nm)

								if n_cir_m != None:
									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										other_net_search_index = 0
										while 1:

											nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
											if nnn_cir_m != None:
												nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
												if nnnn_cir_m != None:
													return nnnn_cir_m, nnnn_index, nnnn_last_loc
												else:
													other_net_search_index += 1
											else:
												break
										starting_net_search_index += 1
								else:
									starting_net_search_index += 1

							else:
								break
			else:

				print(f'looking at traces for {starting_node_ref}-{starting_net_pins[0]}')
				
				touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]
				
				#try to find net matches on touched traces:
				
				incomplete_match_node_arr = []
				missing_node_IDs = []
				for node in starting_net['node arr']:
					if node['ref'] == starting_node_ref:
						node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': init_cm_match, 'pads': init_cm_match.pad_IDs[node['pin']]}
						incomplete_match_node_arr.append(node_dict)
					else:
						missing_node_IDs.append(node['ref'] + '-' + node['pin'])

				incomplete_net_match = {'traces': touched_traces, 'nodes': incomplete_match_node_arr, 'net': starting_net['name']}
				
				starting_net_search_index = 0

				print(f'looking for {missing_node_IDs}')
				nm_last_loc = []
				n_last_loc = []
				net_match, nm_index, nm_last_loc = nm.get_matches_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, last_loc=[])
				add_nm_cm_data(nm)


				if net_match != None:
					cir_m = CircuitMatch([net_match])
					
					missing_nets = nets_with_starting_ref.copy()

					missing_nets.remove(starting_net['name'])
					
					n_last_loc = []

					n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = nm_last_loc)
					add_nm_cm_data(nm)

					if n_cir_m != None:
						#seek out next nets
						
						nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)
						if nn_cir_m != None:
							return nn_cir_m, nn_index, nn_last_loc
						else:
							other_net_search_index = 0
							while 1:
								nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
								if nnn_cir_m != None:
									nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
									if nnnn_cir_m != None:
										return nnnn_cir_m, nnnn_index, nnnn_last_loc
									else:
										#return None, nnnn_index, nnnn_last_loc
										other_net_search_index = nnn_index + 1
										nn_last_loc = nnn_last_loc.copy()
								else:
									break
							
					else:
						starting_net_search_index = 1
						while 1:
							if len(missing_node_IDs) == 0:
								break

							print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
							nm_last_loc = []

							net_match, nm_index, nm_last_loc = nm.get_matches_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index, last_loc=[])
							add_nm_cm_data(nm)


							if net_match != None:
								print(f'a net match was found at {starting_net_search_index}')
								cir_m = CircuitMatch([net_match])

								n_last_loc = []

								n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = nm_last_loc)

								if n_cir_m != None:
									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)
									
									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										
										other_net_search_index = nn_last_loc[-1]['index']
										while 1:
											nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
											if nnn_cir_m != None:
												nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)

												if nnnn_cir_m != None:
													return nnnn_cir_m, nnnn_index, nnnn_last_loc
												else:
													#other_net_search_index += 1
													nn_last_loc = nnn_last_loc
													other_net_search_index = nnn_index + 1

											else:
												break
										starting_net_search_index += 1
										
								else:
									starting_net_search_index += 1

							else:
								break

		return None, -1, []

	def get_next_net_fifo(self, cir_m, missing_net, m_net_node_arr, missing_nets, temp_dir, kicad_cli, footprints_dir, index = 0, search_index = None, last_loc = []):
		'''
		Recursive strategy for finding the next match with needed net possible

		Parameters:
		cir_m (Circuit Match) - initial circuit match to start search on
		missing_net (str) - str of net that needs to be found on circuit
		m_net_node_arr (arr) - arr of nodes that need to be found for net
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints

		Optional:
		index (int) - way to keep track of search paths
		search_index (int) - skip some searching if you are going for next match

		Returns:
		CircuitMatch - completed circuit match or None
		index (int) - where the search completed

		'''
		print('get_next_net_fifo')

		def recursive_search_on_nodes(r_last_loc, missing_node_IDs, next_index):
			print('recursive_search_on_nodes')
			# need to fix
			n_last_loc = r_last_loc.copy()
			n_search_index = 1

			while 1:
				if len(n_last_loc) > 0:
					last_step = n_last_loc[-1]

					if last_step['fxn'] == 'get_matches_fifo':
						ls_missing_node_IDs = last_step['missing_node_IDs']
						if ls_missing_node_IDs[0] in missing_node_IDs:
							nm = last_step['net_matching']

							nm_match, nm_index, nm_last_loc = nm.get_matches_fifo(last_step['match'],last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], n_search_index, last_step['circuit_matching'], last_step['cir_match'], last_step['missing_nets'], n_last_loc[:-1])
							
							if nm_match != None:
								return nm_match, nm_index, nm_last_loc

							else:
								s_last_step = n_last_loc.pop()
								n_search_index = last_step['index'] - 1
						else:
							s_last_step = n_last_loc.pop()
							n_search_index = last_step['index'] - 1

					else:
						s_last_step = n_last_loc.pop()
						n_search_index = last_step['index'] - 1
				else:
					break
				n_search_index += 1


			# go to next match before missing nodes

			n_last_loc = r_last_loc.copy()
			n_search_index = 1

			while 1:
				if len(n_last_loc) > 1:
					last_step = n_last_loc[-1]
					prior_step = n_last_loc[-2:-1]

					if last_step['fxn'] == 'get_matches_fifo':
						ls_missing_node_IDs = last_step['missing_node_IDs']
						if ls_missing_node_IDs[0] in missing_node_IDs:
							
							if prior_step['fxn'] == 'get_matches_fifo':
								nm = prior_step['net_matching']

								nm_match, nm_index, nm_last_loc = nm.get_matches_fifo(prior_step['match'],prior_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, prior_step['ignore_traces'], prior_step['index'], n_search_index, prior_step['circuit_matching'], prior_step['cir_match'], prior_step['missing_nets'], n_last_loc[:-2])
							
								if nm_match != None:
									return nm_match, nm_index, nm_last_loc

								else:
									s_last_step = n_last_loc.pop()
									n_search_index = prior_step['index'] - 1

							else:

								if len(n_last_loc) > 3:
									nm_last_step = n_last_loc[-3:-2]
									nm_prior_step = n_last_loc[-4:-3]

									if nm_prior_step['fxn'] == 'get_matches_fifo':
										nm = prior_step['net_matching']

									nm_match, nm_index, nm_last_loc = nm.get_matches_fifo(nm_prior_step['match'],nm_prior_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, nm_prior_step['ignore_traces'], nm_prior_step['index'], nm_last_step['index'], nm_prior_step['circuit_matching'], nm_prior_step['cir_match'], nm_prior_step['missing_nets'], n_last_loc[:-4])
								
									if nm_match != None:
										return nm_match, nm_index, nm_last_loc

									else:
										s_last_step = n_last_loc.pop()
										n_search_index = prior_step['index'] - 1
								else:

									s_last_step = n_last_loc.pop()
									n_search_index = prior_step['index'] - 1
						else:
							
							s_last_step = n_last_loc.pop()
							n_search_index = prior_step['index'] - 1

				else:
					break
				n_search_index += 1

			#go to next initial component match

			return None, next_index, r_last_loc



		if search_index != None:
			print(search_index)

		next_index = index

		last_loc.append({'fxn': 'get_next_net_fifo', 'cir_m': cir_m, 'missing_net': missing_net, 'm_net_node_arr': m_net_node_arr, 'missing_nets': missing_nets, 'index': index})
		
		net_node_IDs = []
		needed_refs = []
		for node in m_net_node_arr:
			node_ID = node['ref'] + '-' + node['pin']
			net_node_IDs.append(node_ID)
			if node['ref'] not in needed_refs:
				needed_refs.append(node['ref'])

		nm = NetMatching(m_net_node_arr, missing_net)
		nm.pcb_board = self.pcb_board
		nm.cm_data = self.cm_data

		missing_node_IDs = []
		for net_node_ID in net_node_IDs:
			missing_node_IDs.append(net_node_ID)

		incomplete_match_node_arr = []
		traces = []

		unconnected_nodes_refs = []

		for node in m_net_node_arr:
			if node['ref'] in cir_m.refs:
				node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': cir_m.ref_dict[node['ref']], 'pads': cir_m.ref_dict[node['ref']].pad_IDs[node['pin']]}
				traces_ref = cir_m.ref_dict[node['ref']].touched_traces_dict[node['pin']]
				
				mutual_traces = False
				for trace in traces_ref:
					if trace in traces:
						mutual_traces = True
						break


				if len(traces) == 0 or mutual_traces:
					for trace_ref in traces_ref:
						if trace_ref not in traces:
							traces.append(trace_ref)
					incomplete_match_node_arr.append(node_dict)
					missing_node_IDs.remove(node['ref'] + '-' + node['pin'])
				else:
					unconnected_nodes_refs.append(node)

				
		unconnected_nodes_refs_cpy = unconnected_nodes_refs.copy()

		while 1:
			unconnected_nodes_refs_cpy = unconnected_nodes_refs.copy()
			for unconnected_node in unconnected_nodes_refs_cpy:

				node_dict = {'node': unconnected_node['ref'] + '-' + unconnected_node['pin'], 'match': cir_m.ref_dict[unconnected_node['ref']], 'pads': cir_m.ref_dict[unconnected_node['ref']].pad_IDs[unconnected_node['pin']]}
				traces_ref = cir_m.ref_dict[unconnected_node['ref']].touched_traces_dict[unconnected_node['pin']]

				for trace in traces_ref:
					if trace in traces:
						unconnected_nodes_refs.remove(unconnected_node)
						incomplete_match_node_arr.append(node_dict)
						if node['ref'] + '-' + node['pin'] in missing_node_IDs:
							missing_node_IDs.remove(node['ref'] + '-' + node['pin'])
						traces = set(traces + traces_ref)
						break
			if len(unconnected_nodes_refs_cpy) > len(unconnected_nodes_refs):
				if len(unconnected_nodes_refs) == 0:
					break
				else:
					continue
			else:
				break #couldn't decrease the # of unconnected nodes

		incomplete_net_match = {'traces': traces, 'nodes': incomplete_match_node_arr, 'net': missing_net}
		
		if len(unconnected_nodes_refs) > 0:

			if len(unconnected_nodes_refs) == len(missing_node_IDs):
				return None, next_index, last_loc


			updated_match = None

			if updated_match != None:
				print('found somethign!')
			else:
				print('did not find things')



		if len(missing_node_IDs) == 0:
			complete_nm_arr = nm.get_complete_matches([incomplete_net_match], len(m_net_node_arr))
			
			if len(complete_nm_arr) > 0:

				n_cir_m = cir_m.copy()
				n_cir_m.add_net(complete_nm_arr[0])

				missing_nets_cpy = missing_nets.copy()
				missing_nets_cpy.remove(missing_net)

				if len(missing_nets_cpy) > 0:
					nn_cir_m, nn_index, nn_last_loc = self.get_next_match_fifo(n_cir_m, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, index = next_index, search_index = search_index, last_loc=last_loc)
					if nn_cir_m != None:
						return nn_cir_m, nn_index, nn_last_loc
					else:
						return None, nn_index, nn_last_loc
				else:
					if self.net_combination_valid(n_cir_m.circuit_arr):
						return n_cir_m, next_index, last_loc
					else:
						return None, next_index, last_loc

		if search_index is not None:
			updated_match, n_index, n_last_loc = nm.get_matches_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, search_index = search_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets, last_loc = last_loc)
			
			
		else:
			updated_match, n_index, n_last_loc = nm.get_matches_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets, last_loc = last_loc)

			
		
		f_updated_matches = []

		if updated_match != None:
			return updated_match, n_index, n_last_loc
		else:
			return None, n_index, n_last_loc

	def get_next_match_fifo(self, init_cm, missing_nets, temp_dir, kicad_cli, footprints_dir, index = 0, search_index = None, last_loc = []):
		'''
		Recursive strategy for finding the first match possible (rather than exhaustive search)

		Parameters:
		init_cm (Circuit Match) - initial circuit match to start search on
		missing_nets (array) - array of nets that need to be found on circuit
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints

		Optional:
		index (int) - way to keep track of search paths
		search_index (int) - skip some searching if you are going for next match

		Returns:
		CircuitMatch - completed circuit match or None
		index (int) - where the search completed

		'''
		print('get_next_match_fifo')
		last_loc.append({'fxn': 'get_next_match_fifo', 'init_cm': init_cm, 'missing_nets': missing_nets, 'index': index})

		if self.current_best_match != None:
			if len(self.current_best_match['match'].nets) < len(init_cm.nets):
				self.current_best_match = {'match': init_cm, 'missing nets': missing_nets}
		else:
			self.current_best_match = {'match': init_cm, 'missing nets': missing_nets}

		i = index

		if len(missing_nets) == 0:
			if self.net_combination_valid(init_cm.circuit_arr):
				return init_cm, index, last_loc
			else:
				return None, index, last_loc

		missing_net = missing_nets[0]

		m_net_node_arr = []

		for net in self.net_arr:
			if net['name'] == missing_net:
				m_net_node_arr = net['node arr']
				break

		match_v = []
		match, n_index, n_last_loc = self.get_next_net_fifo(init_cm.copy(), missing_net, m_net_node_arr, missing_nets, temp_dir, kicad_cli, footprints_dir, index = i, last_loc=last_loc)
		

		if match != None:
			if self.net_combination_valid(match.circuit_arr):
				return match, n_index, n_last_loc
			
		
		else:
			return None, n_index, n_last_loc
	
	def get_matches_with_interventions(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Finds matches with interventions needed (add wire or cut trace)
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		Returns:
		matches (array) - Array of net matches (with interventions)
		'''

		starting_node_ref = self.sorted_refs[0]
		footprint = ''
		
		for fp, refs in self.footprints_dict.items():
			if starting_node_ref in refs:
				footprint = fp
				break

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
		if len(matches) ==  0:
			return [] #not possible to match starting component on board
		matches = cm.add_traces_data_to_matches(matches)

		init_net_matches_arr = []

		num_starting_nets = 0
		starting_nets = []
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if(node['ref'] == starting_node_ref):
					contains_ref = True
			if contains_ref:
				starting_nets.append(net['name'])
				num_starting_nets +=1

		for init_cm in matches:
			cm_ordered_nm_arr = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
						break

				if contains_ref:
					nm = NetMatching(net['node arr'], net['name'])
					nm.pcb_board = self.pcb_board
					
					t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
					p_net_arr = nm.process_trace_matches(t_net_arr)
					f_net_arr = nm.filter_matches(p_net_arr)
					full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
					cm_ordered_nm_arr.append(full_match_net_arr)
			init_net_matches_arr.append(cm_ordered_nm_arr)

		# remove for missing nets
		f_init_net_matches_arr = []

		for n_init_match in init_net_matches_arr:
			missing_net = False
			for net in n_init_match:
				if len(net) == 0:
					missing_net = True
					break
			if not missing_net:
				f_init_net_matches_arr.append(n_init_match)

		#create net combos across first component

		v_init_net_matches_arr = []

		for n_init_match_arr in f_init_net_matches_arr:

			n_nets = len(n_init_match_arr)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(n_init_match_arr[i]) > 0):
						net_combination.append(n_init_match_arr[i][indices[i]])

				if self.net_combination_valid(net_combination):
					valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(n_init_match_arr[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			full_valid_n_combos = self.get_full_matches(valid_net_combinations, num_starting_nets)
			#v_init_net_matches_arr += valid_net_combinations
			v_init_net_matches_arr += full_valid_n_combos

		if len(v_init_net_matches_arr) == 0:
			# can't satisfy all nets on the first ref
			
			#look at init_net_matches_arr to see where an intervention can be made

			#first, does init net matches_arr have matches?
			
			has_matches = False
			for cm_i_arr in init_net_matches_arr:
				for net_i_arr in cm_i_arr:
					if net_i_arr != []:
						has_matches = True
						break

			if (not has_matches) and len(f_init_net_matches_arr) == 0:
				#there are no net matches to begin with! find some with interventions
				for init_cm in matches:
					cm_ordered_nm_arr = []
					for net in self.net_arr:

						contains_ref = False
						for node in net['node arr']:
							if(node['ref'] == starting_node_ref):
								contains_ref = True
								break

						if contains_ref:
							nm = NetMatching(net['node arr'], net['name'])
							nm.pcb_board = self.pcb_board
							t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
							p_net_arr = nm.process_trace_matches(t_net_arr)
							f_net_arr = nm.filter_matches(p_net_arr)
							full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
							if len(full_match_net_arr) == 0:
								net_nodes = []
								for node in net['node arr']:
									net_nodes.append(node['ref'] + '-' + node['pin'])

								for f_net in f_net_arr:
									#get missing nodes

									missing_nodes = net_nodes.copy()
									for node in f_net['nodes']:
										if node['node'] in missing_nodes:
											missing_nodes.remove(node['node'])

									#find wire interventions on this net
									full_match_net_arr += nm.find_wire_interventions(f_net, missing_nodes, temp_dir, kicad_cli, footprints_dir)

							if len(full_match_net_arr) > 0:
								cm_ordered_nm_arr.append(full_match_net_arr)
								break
						if len(cm_ordered_nm_arr) > 0:
							break
					f_init_net_matches_arr.append(cm_ordered_nm_arr)
				init_net_matches_arr = f_init_net_matches_arr
			
			#if init net matches arr has matches then continue
			init_matches_missing_arr = []
			match_index = 0

			for n_init_match in init_net_matches_arr:
				missing_nets = 0
				for net in n_init_match:
					if len(net) == 0:
						missing_nets += 1
				init_matches_missing_arr.append((match_index,missing_nets))
				match_index += 1

			init_matches_missing_arr.sort(key=lambda x: x[1])

			#get the one with least nets missing
			match_index = init_matches_missing_arr[0][0]
			n_init_match = init_net_matches_arr[match_index]

			#determine missing nets
			covered_nets = []
			for net in n_init_match:
				if len(net) != 0:
					covered_nets.append(net[0]['net'])
			missing_nets = []
			for net in starting_nets:
				if net not in covered_nets:
					missing_nets.append(net)

			# remove missing nets
			f_n_init_match = []
			for net in n_init_match:
				if len(net) != 0:
					f_n_init_match.append(net)

			# create valid combos on existing nets
			valid_net_combinations = []

			n_nets = len(f_n_init_match)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(f_n_init_match[i]) > 0):
						net_combination.append(f_n_init_match[i][indices[i]])

				if self.net_combination_valid(net_combination):
					if len(net_combination) > 0:
						valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(f_n_init_match[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			cir_m_arr = []
			for v_combo in valid_net_combinations:
				cir_m = CircuitMatch(v_combo)
				cir_m_arr.append(cir_m)

			m_net_cir_m_arr = []
			for missing_net in missing_nets:
				m_net_node_arr = []

				for net in self.net_arr:
					if net['name'] == missing_net:
						m_net_node_arr = net['node arr']
						break

				net_node_IDs = []
				needed_refs = []
				for node in m_net_node_arr:
					node_ID = node['ref'] + '-' + node['pin']
					net_node_IDs.append(node_ID)
					if node['ref'] not in needed_refs:
						needed_refs.append(node['ref'])

				if len(m_net_cir_m_arr) > 0:
					cir_m_arr += m_net_cir_m_arr
					

				m_net_cir_m_arr = []

				for cir_m in cir_m_arr:

					nm = NetMatching(m_net_node_arr, missing_net)
					nm.pcb_board = self.pcb_board

					missing_node_IDs = []
					for net_node_ID in net_node_IDs:
						missing_node_IDs.append(net_node_ID)

					incomplete_match_node_arr = []
					ignore_pads = {'front pads': [], 'back pads': []}

					traces = []
					for node in m_net_node_arr:
						if node['ref'] in cir_m.refs:
							node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': cir_m.ref_dict[node['ref']], 'pads': cir_m.ref_dict[node['ref']].pad_IDs[node['pin']]}
							traces_ref = cir_m.ref_dict[node['ref']].touched_traces_dict[node['pin']]
							
							if node_dict['match'].fb == 'front':
								ignore_pads['front pads'] += node_dict['pads']
							else:
								ignore_pads['back pads'] += node_dict['pads']

							mutual_traces = False
							for trace in traces_ref:
								if trace in traces:
									mutual_traces = True
									break

							if len(traces) == 0 or mutual_traces:
								for trace_ref in traces_ref:
									if trace_ref not in traces:
										traces.append(trace_ref)
								incomplete_match_node_arr.append(node_dict)
								missing_node_IDs.remove(node['ref'] + '-' + node['pin'])

					incomplete_net_match = {'traces': traces, 'nodes': incomplete_match_node_arr, 'net': missing_net}

					updated_matches = nm.find_wire_interventions(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir)

					f_updated_matches = []

					for updated_match in updated_matches:
						net_node_IDs_cpy = net_node_IDs.copy()
						for node in updated_match['nodes']:
							if node['node'] in net_node_IDs_cpy:
								net_node_IDs_cpy.remove(node['node'])
						if 'interventions' in updated_match.keys():
							if isinstance(updated_match['interventions'], list):
								for intervention in updated_match['interventions']:
									if 'add wire' in intervention.keys():
										if isinstance(intervention['add wire'], list):
											if intervention['add wire'][0] in net_node_IDs_cpy:
												net_node_IDs_cpy.remove(intervention['add wire'][0])
										elif isinstance(intervention['add wire'], dict):
											if intervention['add wire']['missing node'] in net_node_IDs_cpy:
												net_node_IDs_cpy.remove(intervention['add wire']['missing node'])
							elif isinstance(updated_match['interventions'], dict):
								if 'add wire' in updated_match['interventions'].keys():
										if isinstance(updated_match['interventions']['add wire'], list):
											if updated_match['interventions']['add wire'][0] in net_node_IDs_cpy:
												net_node_IDs_cpy.remove(updated_match['interventions']['add wire'][0])
										elif isinstance(updated_match['interventions']['add wire'], dict):
											if updated_match['interventions']['add wire']['missing node'] in net_node_IDs_cpy:
												net_node_IDs_cpy.remove(updated_match['interventions']['add wire']['missing node'])
						if len(net_node_IDs_cpy) == 0:
							f_updated_matches.append(updated_match)


					if len(f_updated_matches) > 0:
						for updated_match in f_updated_matches:
							new_cir_m = CircuitMatch(cir_m.circuit_arr + [updated_match])
							m_net_cir_m_arr.append(new_cir_m)

			cir_m_arr += m_net_cir_m_arr
			interventions_cir_m_arr = []
			cir_m_arr = self.get_full_matches(cir_m_arr, len(starting_nets))
			for cir_m in cir_m_arr:
				interventions_cir_m_arr += self.get_valid_intervention_combos(CircuitMatch(cir_m))

			if len(interventions_cir_m_arr) > 0:
				v_init_net_matches_arr = interventions_cir_m_arr

		if len(v_init_net_matches_arr) == 0:
			return [] # further interventions need to be made
		else:
			#continue on across any other nets not hit
			full_valid_net_combos = []
			for v_init_match_arr in v_init_net_matches_arr:

				touched_refs = [self.sorted_refs[0]]

				if len(v_init_match_arr) > 0:
					#keep going

					missing_net = False

					valid_combos_last_ref = [v_init_match_arr]
					#loop through the rest of refs
					for ref in self.sorted_refs[1:]:

						#build off these sequentially
						
						valid_combos_last_net = valid_combos_last_ref
						for net in self.net_arr:
							contains_ref = False
							contains_touched_ref = False
							
							for node in net['node arr']:
								if(node['ref'] == ref):
									contains_ref = True
								if node['ref'] in touched_refs:
									contains_touched_ref = True
							
							if contains_ref and not contains_touched_ref:
								
								# try to run nm on existing match
								match_for_net_found = False
								#build off these sequentially
								valid_combos_last_net = valid_combos_last_ref

								for node in net['node arr']:
									if node['ref'] != ref:
										i_ref = node['ref']
										valid_combos_net_added = []
										#loop through nets in this current net combo
										for valid_combo in valid_combos_last_net:

											for v_net in valid_combo:

												contains_i_ref = False
												i_match = None
												for m_node in v_net['nodes']:
													if i_ref == m_node['node'].split('-')[0]:
														contains_i_ref = True
														i_match = m_node['match']
														break

												# additional check for "intervention" components
												if not contains_i_ref:
													if 'interventions' in v_net.keys():
														if isinstance(v_net['interventions'], dict):
															if 'add wire' in v_net['interventions'].keys():
																if isinstance(v_net['interventions']['add wire'], dict):
																	if i_ref == v_net['interventions']['add wire']['missing node'].split('-')[0]:
																		contains_i_ref = True
																		i_match = v_net['interventions']['add wire']['cmpnt match']
														elif isinstance(v_net['interventions'], list):
															for intervention in v_net['interventions']:
																if 'add wire' in intervention.keys():
																	if isinstance(intervention['add wire'], dict):
																		if i_ref == intervention['add wire']['missing node'].split('-')[0]:
																			contains_i_ref = True
																			i_match = intervention['add wire']['cmpnt match']
																			break


												if contains_i_ref:
													nm = NetMatching(net['node arr'], net['name'])
													nm.pcb_board = self.pcb_board
													t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, i_match, i_ref)
													
													p_net_arr = nm.process_trace_matches(t_net_arr)
													f_net_arr = nm.filter_matches(p_net_arr)
													
													full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))

													if(len(full_match_net_arr) > 0):
														
														temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)

														if len(temp_arr) > 0:
															valid_combos_net_added += temp_arr
															match_for_net_found = True
													break # break from looping through nets

										if match_for_net_found:
											valid_combos_last_net = valid_combos_net_added
											break

								if not match_for_net_found:
									nm = NetMatching(net['node arr'], net['name'])
									nm.pcb_board = self.pcb_board
									nm.nodes.sort(key=lambda x: x['total pins'], reverse=True)

									#create data structure to keep track of multi-pin components
									cm_pin_dict = {}

									for node in nm.nodes:
										if node['ref'] in cm_pin_dict.keys():
											cm_pin_dict[node['ref']].append(node['pin'])
										else:
											cm_pin_dict[node['ref']] = [node['pin']]

									valid_combos_net_added = []
									for valid_combo in valid_combos_last_net:
										touched_traces = []
										for v_net in valid_combo:
											for m_node in v_net['nodes']:
												touched_traces += m_node['match'].touched_traces_list

										for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
											if trace_ID not in touched_traces:
												if self.pcb_board.get_num_pads_on_traces([trace_ID]) > len(net['node arr']):
													starting_node = nm.nodes[0]
													footprint = starting_node['footprint']
													footprint_arr = footprint.split(":")
													fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

													if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
														complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
													
														gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
													
													cm = ComponentMatching()
													cm.pcb_board = self.pcb_board
													cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
													matches, _, __ = cm.get_matches_on_trace(trace_ID, cm_pin_dict[starting_node['ref']])
													matches = cm.add_traces_data_to_matches(matches)
													matches = cm.sort_matches(matches)

													for init_match in matches:
														t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_match, starting_node['ref'])
														p_net_arr = nm.process_trace_matches(t_net_arr)
														f_net_arr = nm.filter_matches(p_net_arr)
														full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))

														if len(full_match_net_arr) > 0:
															temp_arr = self.gen_valid_combos([valid_combo], full_match_net_arr)
															if(len(temp_arr) > 0):
																valid_combos_net_added += temp_arr
																match_for_net_found = True
									if match_for_net_found:
										valid_combos_last_net = valid_combos_net_added

								if not match_for_net_found:
									# net not found !
									missing_net = True
									break

						touched_refs.append(ref)
						if missing_net:
							break
						else:
							valid_combos_last_ref = valid_combos_last_net
					full_valid_net_combos += valid_combos_last_ref

			return full_valid_net_combos

	def get_mwi_fifo_all(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Finds *first* possible match with interventions needed (add wire or cut trace). Gives *all* matches using this method. Useful for speed.
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		Returns:
		matches (array) - Array of net matches (with interventions)
		'''

		starting_node_ref = self.sorted_refs[0]
		footprint = ''
		
		for fp, refs in self.footprints_dict.items():
			if starting_node_ref in refs:
				footprint = fp
				break

		footprint_arr = footprint.split(":")
		fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

		if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
			complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
		
			gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
		
		cm = ComponentMatching()
		cm.pcb_board = self.pcb_board
		cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
		matches = cm.get_matches()
		matches = cm.add_traces_data_to_matches(matches)
		matches = cm.sort_matches(matches)

		init_net_matches_arr = []

		num_starting_nets = 0
		starting_nets = []
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if(node['ref'] == starting_node_ref):
					contains_ref = True
			if contains_ref:
				starting_nets.append(net['name'])
				num_starting_nets +=1

		for init_cm in matches:
			cm_ordered_nm_arr = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
						break

				if contains_ref:
					nm = NetMatching(net['node arr'], net['name'])
					nm.pcb_board = self.pcb_board
					t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
					p_net_arr = nm.process_trace_matches(t_net_arr)
					f_net_arr = nm.filter_matches(p_net_arr)
					full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
					cm_ordered_nm_arr.append(full_match_net_arr)
			init_net_matches_arr.append(cm_ordered_nm_arr)

		# remove for missing nets
		f_init_net_matches_arr = []

		for n_init_match in init_net_matches_arr:
			missing_net = False
			for net in n_init_match:
				if len(net) == 0:
					missing_net = True
					break
			if not missing_net:
				f_init_net_matches_arr.append(n_init_match)

		#create net combos across first component

		v_init_net_matches_arr = []

		for n_init_match_arr in f_init_net_matches_arr:

			n_nets = len(n_init_match_arr)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(n_init_match_arr[i]) > 0):
						net_combination.append(n_init_match_arr[i][indices[i]])

				if self.net_combination_valid(net_combination):
					valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(n_init_match_arr[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			full_valid_n_combos = self.get_full_matches(valid_net_combinations, num_starting_nets)
			#v_init_net_matches_arr += valid_net_combinations
			v_init_net_matches_arr += full_valid_n_combos

		def recursive_search_on_loc(n_last_loc, n_search_index):
				
				fifo_matches = []
				while 1:
					if len(n_last_loc) > 1:
						last_step = n_last_loc[-2:-1][0]

						if last_step['fxn'] == 'fwi_fifo':
							nm = last_step['net_matching']
							i_n_last_loc = n_last_loc.copy()
							nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

							n_last_loc = i_n_last_loc

							if nn_mwi != None:
								fifo_matches.append(nn_mwi)
								
								n_search_index = nn_index - 1

								if len(nn_last_loc) > len(n_last_loc):

									t_last_loc = nn_last_loc[len(n_last_loc):].copy()
									ff_matches = recursive_search_on_loc(t_last_loc, t_last_loc[-1]['index'])
									fifo_matches += ff_matches

							else:
								r_last_loc = n_last_loc.pop()
								n_search_index = last_step['index'] - 1
						elif last_step['fxn'] == 'get_next_mwi_fifo' and last_step['missing_nets'] == []:
							return fifo_matches
						else:
							r_last_loc = n_last_loc.pop()
							n_search_index = r_last_loc['index'] - 1

					else:
						break

					n_search_index += 1


				return fifo_matches

		if len(v_init_net_matches_arr) == 0:
			# can't satisfy all nets on the first ref
			
			#look at init_net_matches_arr to see where an intervention can be made

			#first, does init net matches_arr have matches?
			
			has_matches = False
			for cm_i_arr in init_net_matches_arr:
				for net_i_arr in cm_i_arr:
					if net_i_arr != []:
						has_matches = True
						break

			if (not has_matches) and len(f_init_net_matches_arr) == 0:
				for init_cm in matches:
					cm_ordered_nm_arr = []
					for net in self.net_arr:

						contains_ref = False
						for node in net['node arr']:
							if(node['ref'] == starting_node_ref):
								contains_ref = True
								break

						if contains_ref:
							nm = NetMatching(net['node arr'], net['name'])
							nm.pcb_board = self.pcb_board
							t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
							p_net_arr = nm.process_trace_matches(t_net_arr)
							f_net_arr = nm.filter_matches(p_net_arr)
							full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
							if len(full_match_net_arr) == 0:
								net_nodes = []
								for node in net['node arr']:
									net_nodes.append(node['ref'] + '-' + node['pin'])

								for f_net in f_net_arr:
									#get missing nodes

									missing_nodes = net_nodes.copy()
									for node in f_net['nodes']:
										if node['node'] in missing_nodes:
											missing_nodes.remove(node['node'])

									#find wire interventions on this net
									full_match_net_arr += nm.find_wire_interventions(f_net, missing_nodes, temp_dir, kicad_cli, footprints_dir)

							if len(full_match_net_arr) > 0:
								cm_ordered_nm_arr.append(full_match_net_arr)
								break
						if len(cm_ordered_nm_arr) > 0:
							break
					f_init_net_matches_arr.append(cm_ordered_nm_arr)
				init_net_matches_arr = f_init_net_matches_arr

			#if init net matches arr has matches then continue
			init_matches_missing_arr = []
			match_index = 0

			for n_init_match in init_net_matches_arr:
				missing_nets = 0
				for net in n_init_match:
					if len(net) == 0:
						missing_nets += 1
				init_matches_missing_arr.append((match_index,missing_nets))
				match_index += 1

			init_matches_missing_arr.sort(key=lambda x: x[1])

			#get the one with least nets missing
			match_index = init_matches_missing_arr[0][0]
			n_init_match = init_net_matches_arr[match_index]

			#determine missing nets
			covered_nets = []
			for net in n_init_match:
				if len(net) != 0:
					covered_nets.append(net[0]['net'])

			missing_nets = []
			for net in starting_nets:
				if net not in covered_nets:
					missing_nets.append(net)

			# remove missing nets
			f_n_init_match = []
			for net in n_init_match:
				if len(net) != 0:
					f_n_init_match.append(net)

			# create valid combos on existing nets
			valid_net_combinations = []

			n_nets = len(f_n_init_match)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(f_n_init_match[i]) > 0):
						net_combination.append(f_n_init_match[i][indices[i]])

				if self.net_combination_valid(net_combination):
					if len(net_combination) > 0:
						valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(f_n_init_match[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			cir_m_arr = []

			for v_combo in valid_net_combinations:
				cir_m = CircuitMatch(v_combo)
				cir_m_arr.append(cir_m)

			s_cir_m_arr = []


			for cir_m in cir_m_arr:
				temp_arr = self.get_valid_intervention_combos(cir_m)
				for temp_cir in temp_arr:
					s_cir_m_arr.append(CircuitMatch(temp_cir))
			
			fifo_matches = []
			
			for cir_m in s_cir_m_arr:
				n_mwi, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)

				if n_mwi != None:
					fifo_matches.append(n_mwi)
					n_search_index = n_last_loc[-1]['index']

					while 1:
						if len(n_last_loc) > 1:
							last_step = n_last_loc[-2:-1][0]

							if last_step['fxn'] == 'fwi_fifo':
								nm = last_step['net_matching']
								i_n_last_loc = n_last_loc.copy()
								
								nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

								n_last_loc = i_n_last_loc

								if nn_mwi != None:

									fifo_matches.append(nn_mwi)
									n_search_index = nn_index - 1

									if len(nn_last_loc) > len(n_last_loc):
										t_last_loc = nn_last_loc[len(n_last_loc):].copy()

										ff_matches = recursive_search_on_loc(t_last_loc, t_last_loc[-1]['index'])
										fifo_matches += ff_matches

								else:
									r_last_loc = n_last_loc.pop()
									n_search_index = last_step['index'] - 1
							else:
								r_last_loc = n_last_loc.pop()
								n_search_index = r_last_loc['index'] - 1

						else:
							break

						n_search_index += 1
			
			fifo_matches = self.filter_duplicates(fifo_matches)

			v_init_net_matches_arr += fifo_matches

		if len(v_init_net_matches_arr) == 0:
			return [] # further interventions need to be made
		else:
			#continue on across any other nets not hit
			fifo_matches = []

			for cir_m in v_init_net_matches_arr:
				missing_nets_arr = self.get_missing_nets(cir_m.circuit_arr)
				missing_nets = []
				for m_net_arr in missing_nets_arr:
					missing_nets.append(m_net_arr['name'])

				n_mwi, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)

				if n_mwi != None:
					fifo_matches.append(n_mwi)
					n_search_index = n_last_loc[-1]['index']

					fifo_matches += recursive_search_on_loc(n_last_loc, n_search_index)

			fifo_matches = self.filter_duplicates(fifo_matches)

			return fifo_matches

	def get_mwi_fifo(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Finds *first* possible match with interventions needed (add wire or cut trace). Useful for speed.
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		Returns:
		matches (array) - Array of net matches (with interventions)
		'''

		starting_node_ref = self.sorted_refs[0]

		#check if this ref already has matches found for it
		if hasattr(self, 'cm_dict') and starting_node_ref in self.cm_dict.keys():
			matches = self.cm_dict[starting_node_ref]

		else:
			footprint = ''
			
			for fp, refs in self.footprints_dict.items():
				if starting_node_ref in refs:
					footprint = fp
					break

			footprint_arr = footprint.split(":")
			fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

			if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
				complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
			
				gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")
			
			cm = ComponentMatching()
			cm.pcb_board = self.pcb_board
			cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")
			matches = cm.get_matches()
			matches = cm.add_traces_data_to_matches(matches)
			matches = cm.sort_matches(matches)


		print(f'found {len(matches)} for {starting_node_ref}')

		init_net_matches_arr = []

		num_starting_nets = 0
		starting_nets = []
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if(node['ref'] == starting_node_ref):
					contains_ref = True
			if contains_ref:
				starting_nets.append(net['name'])
				num_starting_nets +=1

		for init_cm in matches:
			cm_ordered_nm_arr = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if(node['ref'] == starting_node_ref):
						contains_ref = True
						break

				if contains_ref:
					nm = NetMatching(net['node arr'], net['name'])
					nm.pcb_board = self.pcb_board
					t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
					p_net_arr = nm.process_trace_matches(t_net_arr)
					f_net_arr = nm.filter_matches(p_net_arr)
					full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
					cm_ordered_nm_arr.append(full_match_net_arr)
			init_net_matches_arr.append(cm_ordered_nm_arr)

		# remove for missing nets
		f_init_net_matches_arr = []

		for n_init_match in init_net_matches_arr:
			missing_net = False
			for net in n_init_match:
				if len(net) == 0:
					missing_net = True
					break
			if not missing_net:
				f_init_net_matches_arr.append(n_init_match)

		#create net combos across first component

		v_init_net_matches_arr = []

		for n_init_match_arr in f_init_net_matches_arr:

			n_nets = len(n_init_match_arr)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(n_init_match_arr[i]) > 0):
						net_combination.append(n_init_match_arr[i][indices[i]])

				if self.net_combination_valid(net_combination):
					valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(n_init_match_arr[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			full_valid_n_combos = self.get_full_matches(valid_net_combinations, num_starting_nets)
            
			v_init_net_matches_arr += full_valid_n_combos

		def recursive_search_on_loc(n_last_loc, n_search_index):
				
				fifo_matches = []
				while 1:
					if len(n_last_loc) > 1:
						last_step = n_last_loc[-2:-1][0]

						if last_step['fxn'] == 'fwi_fifo':
							nm = last_step['net_matching']
							i_n_last_loc = n_last_loc.copy()
							nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

							n_last_loc = i_n_last_loc

							if nn_mwi != None:
								fifo_matches.append(nn_mwi)
								
								n_search_index = nn_index - 1

								if len(nn_last_loc) > len(n_last_loc):

									t_last_loc = nn_last_loc[len(n_last_loc):].copy()
									ff_matches = recursive_search_on_loc(t_last_loc, t_last_loc[-1]['index'])
									fifo_matches += ff_matches

							else:
								r_last_loc = n_last_loc.pop()
								n_search_index = last_step['index'] - 1
						elif last_step['fxn'] == 'get_next_mwi_fifo' and last_step['missing_nets'] == []:
							return fifo_matches
						else:
							r_last_loc = n_last_loc.pop()
							n_search_index = r_last_loc['index'] - 1

					else:
						break

					n_search_index += 1


				return fifo_matches

		if len(v_init_net_matches_arr) > 0:
			print(f'found initial matches for nets on {starting_node_ref} - {len(v_init_net_matches_arr)}')
		if len(v_init_net_matches_arr) == 0:
			# can't satisfy all nets on the first ref
			
			#look at init_net_matches_arr to see where an intervention can be made

			#first, does init net matches_arr have matches?
			
			has_matches = False
			for cm_i_arr in init_net_matches_arr:
				for net_i_arr in cm_i_arr:
					if net_i_arr != []:
						has_matches = True
						break

			if (not has_matches) and len(f_init_net_matches_arr) == 0:
				for init_cm in matches:
					cm_ordered_nm_arr = []
					for net in self.net_arr:

						contains_ref = False
						for node in net['node arr']:
							if(node['ref'] == starting_node_ref):
								contains_ref = True
								break

						if contains_ref:
							nm = NetMatching(net['node arr'], net['name'])
							nm.pcb_board = self.pcb_board
							t_net_arr = nm.run_net_cms_from_cm(temp_dir, kicad_cli, footprints_dir, init_cm, starting_node_ref)
							p_net_arr = nm.process_trace_matches(t_net_arr)
							f_net_arr = nm.filter_matches(p_net_arr)
							full_match_net_arr = nm.get_complete_matches(f_net_arr, len(net['node arr']))
							if len(full_match_net_arr) == 0:
								net_nodes = []
								for node in net['node arr']:
									net_nodes.append(node['ref'] + '-' + node['pin'])

								for f_net in f_net_arr:
									#get missing nodes

									missing_nodes = net_nodes.copy()
									for node in f_net['nodes']:
										if node['node'] in missing_nodes:
											missing_nodes.remove(node['node'])

									#find wire interventions on this net
									full_match_net_arr += nm.find_wire_interventions(f_net, missing_nodes, temp_dir, kicad_cli, footprints_dir)

							if len(full_match_net_arr) > 0:
								cm_ordered_nm_arr.append(full_match_net_arr)
								break
						if len(cm_ordered_nm_arr) > 0:
							break
					f_init_net_matches_arr.append(cm_ordered_nm_arr)
				init_net_matches_arr = f_init_net_matches_arr

			#if init net matches arr has matches then continue
			init_matches_missing_arr = []
			match_index = 0

			for n_init_match in init_net_matches_arr:
				missing_nets = 0
				for net in n_init_match:
					if len(net) == 0:
						missing_nets += 1
				init_matches_missing_arr.append((match_index,missing_nets))
				match_index += 1

			init_matches_missing_arr.sort(key=lambda x: x[1])

			#get the one with least nets missing
			match_index = init_matches_missing_arr[0][0]
			n_init_match = init_net_matches_arr[match_index]

			#determine missing nets
			covered_nets = []
			for net in n_init_match:
				if len(net) != 0:
					covered_nets.append(net[0]['net'])

			missing_nets = []
			for net in starting_nets:
				if net not in covered_nets:
					missing_nets.append(net)

			print(f'starting search off match with {covered_nets} covered and {missing_nets} still missing')

			# remove missing nets
			f_n_init_match = []
			for net in n_init_match:
				if len(net) != 0:
					f_n_init_match.append(net)

			# create valid combos on existing nets
			valid_net_combinations = []

			n_nets = len(f_n_init_match)

			indices = [0 for i in range(n_nets)]

			valid_net_combinations = []

			while 1:

				net_combination = []
				for i in range(n_nets):

					if (len(f_n_init_match[i]) > 0):
						net_combination.append(f_n_init_match[i][indices[i]])

				if self.net_combination_valid(net_combination):
					if len(net_combination) > 0:
						valid_net_combinations.append(net_combination)

				# find the rightmost array that has more
				# elements left after the current element
				# in that array
				next = n_nets-1

				while (next >=0 and (indices[next] + 1 >= len(f_n_init_match[next]))):
					next-=1

				if next < 0:
					break

				indices[next] += 1

				for i in range(next + 1, n_nets):
					indices[i] = 0

			cir_m_arr = []

			for v_combo in valid_net_combinations:
				cir_m = CircuitMatch(v_combo)
				cir_m_arr.append(cir_m)



			s_cir_m_arr = []


			for cir_m in cir_m_arr:
				temp_arr = self.get_valid_intervention_combos(cir_m)
				for temp_cir in temp_arr:
					s_cir_m_arr.append(CircuitMatch(temp_cir))
			
			
			fifo_matches = []

			print(f'searching on {len(s_cir_m_arr)} initial circuits')
			
			for cir_m in s_cir_m_arr:
				print('start search')
				n_mwi, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
				print('finished search')
				if n_mwi != None:
					fifo_matches.append(n_mwi)
					n_search_index = n_last_loc[-1]['index']
					
					while 1:
						if len(n_last_loc) > 1:
							last_step = n_last_loc[-2:-1][0]

							if last_step['fxn'] == 'fwi_fifo':
								nm = last_step['net_matching']
								i_n_last_loc = n_last_loc.copy()
								
								nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

								n_last_loc = i_n_last_loc

								if nn_mwi != None:

									fifo_matches.append(nn_mwi)
									n_search_index = nn_index - 1

									if len(nn_last_loc) > len(n_last_loc):
										t_last_loc = nn_last_loc[len(n_last_loc):].copy()

										ff_matches = recursive_search_on_loc(t_last_loc, t_last_loc[-1]['index'])
										fifo_matches += ff_matches

								else:
									r_last_loc = n_last_loc.pop()
									n_search_index = last_step['index'] - 1
							else:
								r_last_loc = n_last_loc.pop()
								n_search_index = r_last_loc['index'] - 1

						else:
							break

						n_search_index += 1
					
			#return fifo_matches

			fifo_matches = self.filter_duplicates(fifo_matches)
			print(f'found {len(fifo_matches)} initial circuits')
			v_init_net_matches_arr += fifo_matches

		if len(v_init_net_matches_arr) == 0:
			return [] # further interventions need to be made
		else:
			#continue on across any other nets not hit
			print(f'searching on next {len(v_init_net_matches_arr)} circuits')
			fifo_matches = []

			for cir_m in v_init_net_matches_arr:
				missing_nets_arr = self.get_missing_nets(cir_m.circuit_arr)
				missing_nets = []
				for m_net_arr in missing_nets_arr:
					missing_nets.append(m_net_arr['name'])

				n_mwi, n_index, n_last_loc = self.get_next_mwi_fifo(CircuitMatch(cir_m.circuit_arr), missing_nets, temp_dir, kicad_cli, footprints_dir)

				if n_mwi != None:
					fifo_matches.append(n_mwi)
					break
					#n_search_index = n_last_loc[-1]['index']

					#fifo_matches += recursive_search_on_loc(n_last_loc, n_search_index)

			#fifo_matches = self.filter_duplicates(fifo_matches)

			return fifo_matches

	def get_mwi_fifo2(self, temp_dir, kicad_cli, footprints_dir):
		'''
		Finds *first* possible match with interventions needed (add wire or cut trace). Useful for speed.
		
		Parameters:
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints
		
		Returns:
		matches (array) - Array of net matches (with interventions)
		'''



		starting_node_ref = self.sorted_refs[0]
		matches = []

		footprint = ''

			
		for fp, refs in self.footprints_dict.items():
			if starting_node_ref in refs:
				footprint = fp
				break

		#check if this ref already has matches found for it

		fp_key = footprint.split(':')[1]
		if hasattr(self, 'cm_data') and footprint in self.cm_data.keys():
			matches = self.cm_data[footprint]['full']
		elif hasattr(self, 'cm_data') and fp_key in self.cm_data.keys():
			if 'full' in self.cm_data[fp_key].keys():
				matches = self.cm_data[fp_key]['full']
		else:

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
			
			if hasattr(self, 'cm_data'):
				if footprint in self.cm_data.keys():
					matches = self.cm_data[footprint]['full']
				else:
					matches = cm.get_matches()
					matches = cm.add_traces_data_to_matches(matches)
					matches = cm.sort_matches(matches)
					self.cm_data[footprint] = {'full': matches}
			else:
				matches = cm.get_matches()
				matches = cm.add_traces_data_to_matches(matches)
				matches = cm.sort_matches(matches)
				self.cm_data[footprint] = {'full': matches}

		print(f'*found {len(matches)} for {starting_node_ref}')

		# get a net to start on that contains this component
		starting_net = {}
		starting_net_pins = []

		nets_with_starting_ref = []
		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if node['ref'] == starting_node_ref:
					contains_ref = True
			if contains_ref:
				if starting_net == {}:
					starting_net = net
					nets_with_starting_ref.append(net['name'])
				else:
					nets_with_starting_ref.append(net['name'])

					
		##initial verification - are pins of this component not connected on the same trace?

		for node in starting_net['node arr']:
			if node['ref'] == starting_node_ref:
				starting_net_pins.append(node['pin'])

		print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_node_ref}')

		nm = NetMatching(starting_net['node arr'], starting_net['name'])
		nm.pcb_board = self.pcb_board
		nm.cm_data = self.cm_data
													
		def locate_other_nets(cir_m, index=0, last_loc=[]):
			print('locating other nets')
			#approach this by looking at sorted refs

			starting_ref = ''
			for ref in self.sorted_refs[1:]:
				if ref not in cir_m.refs:
					starting_ref = ref
					break

			if starting_ref == '':
				print('all components are accounted for, validating matches on missing nets')
				#all refs are accounted for - are they properly connected?
				missing_net_arr = self.get_missing_nets(cir_m.circuit_arr)

				for missing_net in missing_net_arr:
					print(f'checking on {missing_net["name"]}')
					net_touched_traces = []
					all_nodes_connected = True
					net_match_nodes_arr = []

					for node in missing_net['node arr']:
						ref = node['ref']
						pin = node['pin']

						node_cm = cir_m.ref_dict[ref]
						node_cm_traces = node_cm.touched_traces_dict[pin]

						if len(net_touched_traces) == 0:
							net_touched_traces += node_cm_traces
							net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
						else:
							connected = False
							for n_cm_trace in node_cm_traces:
								if n_cm_trace in net_touched_traces:
									connected = True
									break

							if connected:
								for n_cm_trace in node_cm_traces:
									if n_cm_trace not in net_touched_traces:
										net_touched_traces.append(n_cm_trace)
								net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
							else:
								all_nodes_connected = False
								break


					if all_nodes_connected:
						#create a net for them
						net_dict = {'traces': net_touched_traces, 'nodes': net_match_nodes_arr, 'net': missing_net['name']}
						cir_m.add_net(net_dict)
					else:
						print('nodes were not connected!')
						missing_nets = []
						for missing_net_arr_i in missing_net_arr:
							missing_nets.append(missing_net_arr_i['name'])

						n_old_pcb_board = self.pcb_board.copy_self()

						n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = last_loc)
						
						if n_cir_m != None:
							#seek out next nets
							nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

							if nn_cir_m != None:
								return nn_cir_m, nn_index, nn_last_loc
							else:
								return None, nn_index, nn_last_loc # here you could return a partial
						else:
							self.pcb_board = n_old_pcb_board
							return None, n_index, last_loc

				if self.net_combination_valid(cir_m.circuit_arr):
					return cir_m, index, last_loc
				else:
					return None, index, last_loc


			else:
				print(f'component match search for {starting_ref}')
				#use starting ref to run search

				# get a net to start on that contains this component
				starting_net = {}
				starting_net_pins = []

				nets_with_starting_ref = []
				for net in self.net_arr:
					contains_ref = False
					for node in net['node arr']:
						if node['ref'] == starting_ref:
							contains_ref = True
					if contains_ref:
						if starting_net == {}:
							starting_net = net
							nets_with_starting_ref.append(net['name'])
						else:
							nets_with_starting_ref.append(net['name'])
				
				for node in starting_net['node arr']:
					if node['ref'] == starting_ref:
						starting_net_pins.append(node['pin'])

				print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_ref}')

				n_old_pcb_board = self.pcb_board.copy_self()

				n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, nets_with_starting_ref, temp_dir, kicad_cli, footprints_dir, last_loc = [])
				print('in locate other nets, return from get_next_mwi_fifo (2)')
						
				if n_cir_m != None:
					#seek out next nets
					nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

					if nn_cir_m != None:
						return nn_cir_m, nn_index, nn_last_loc
					else:
						return None, nn_index, nn_last_loc # here you could return a partial
				else:
					self.pcb_board = n_old_pcb_board
					return None, n_index, last_loc

		def recursive_search_on_circuit(n_last_loc, n_search_index):
			quit()	
			
			while 1:
				print('recursive_search_on_circuit')
				if len(n_last_loc) > 1:
					last_step = n_last_loc[-2:-1][0]

					if last_step['fxn'] == 'fwi_fifo':
						nm = last_step['net_matching']
						i_n_last_loc = n_last_loc.copy()
						nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = [])

						n_last_loc = i_n_last_loc

						if nn_mwi != None:
							return nn_mwi, nn_index, nn_last_loc

						else:
							r_last_loc = n_last_loc.pop()
							n_search_index = last_step['index'] - 1
					elif last_step['fxn'] == 'get_next_mwi_fifo' and last_step['missing_nets'] == []:
						return None, n_search_index, n_last_loc
					else:
						r_last_loc = n_last_loc.pop()
						n_search_index = r_last_loc['index'] - 1

				else:
					break

				n_search_index += 1


			return None, n_search_index, n_last_loc

		def add_nm_cm_data(nm):
			if not hasattr(nm, 'cm_data'):
				nm.cm_data = {}
			if not hasattr(self, 'cm_data'):
				self.cm_data = {}

			for key, val in nm.cm_data.items():
				if key in self.cm_data.keys():
					for trace_ID_key, match_vals in nm.cm_data[key].items():
						if trace_ID_key not in self.cm_data[key].keys():
							self.cm_data[key][trace_ID_key] = match_vals
				else:
					self.cm_data[key] = val

		# try to find matches on this net
		for init_cm_match in matches:
			print(f'looking on new component match for {starting_net["name"]}')
			
			if len(starting_net_pins) > 1: # multiple pins for same net
				print(f'component match has multiple pins for this net')
				# do they lie on the same trace for this match?
				touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]

				is_connected = True
				for starting_net_pin in starting_net_pins:
					s_touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]
					s_is_connected = False
					for s_touched_trace in s_touched_traces:
						if s_touched_trace in touched_traces:
							s_is_connected = True
							break
					if not s_is_connected:
						is_connected = False
						break

				if is_connected: # create a net match on these nets
					print(f'component match pins properly connected')
					match_node_arr = []
					for node in starting_net['node arr']:
						if node['ref'] == starting_node_ref:
							node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': init_cm_match, 'pads': init_cm_match.pad_IDs[node['pin']]}
							match_node_arr.append(node_dict)
					
					net_match = {'traces': touched_traces, 'nodes': match_node_arr, 'net': starting_net['name']}
					cir_m = CircuitMatch([net_match])

					missing_nets = nets_with_starting_ref.copy()
					missing_nets.remove(starting_net['name'])

					n_old_pcb_board = self.pcb_board.copy_self()

					n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = [])
					add_nm_cm_data(nm)

					if n_cir_m != None:
						#seek out next nets

						nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

						if nn_cir_m != None:
							return nn_cir_m, nn_index, nn_last_loc
						else:
							return None, nn_index, nn_last_loc # here you could return a partial
					else:
						self.pcb_board = n_old_pcb_board
						nm.pcb_board = n_old_pcb_board
						starting_net_search_index = 1
						while 1:
							print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
							
							net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
							add_nm_cm_data(nm)

							if net_match != None:
								print(f'a net match was found at {starting_net_search_index}')
								cir_m = CircuitMatch([net_match])

								n_old_pcb_board = self.pcb_board.copy_self()

								n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
								
								if n_cir_m != None:
									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)
									

									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										other_net_search_index = 0
										while 1:
											nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
											add_nm_cm_data(nm)

											if nnn_cir_m != None:
												nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
												
												if nnnn_cir_m != None:
													return nnnn_cir_m, nnnn_index, nnnn_last_loc
												else:
													other_net_search_index = nnn_index
											else:
												break
										starting_net_search_index += 1
								else:
									self.pcb_board = n_old_pcb_board
									nm.pcb_board = n_old_pcb_board
									starting_net_search_index += 1

							else:
								break
				else:
					print(f'component match pins are not properly connected - find if intervention possible')



			else:
				print(f'looking at traces for {starting_node_ref}-{starting_net_pins[0]}')
				touched_traces = init_cm_match.touched_traces_dict[starting_net_pins[0]]
				print(f'looking at {len(touched_traces)} traces for {starting_node_ref}-{starting_net_pins[0]}')
				
				#try to find net matches on touched traces:
			
				incomplete_match_node_arr = []
				missing_node_IDs = []
				for node in starting_net['node arr']:
					if node['ref'] == starting_node_ref:
						node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': init_cm_match, 'pads': init_cm_match.pad_IDs[node['pin']]}
						incomplete_match_node_arr.append(node_dict)
					else:
						missing_node_IDs.append(node['ref'] + '-' + node['pin'])

				incomplete_net_match = {'traces': touched_traces, 'nodes': incomplete_match_node_arr, 'net': starting_net['name']}
				
				starting_net_search_index = 0

				print(f'looking for {missing_node_IDs}')
				
				net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir)
				add_nm_cm_data(nm)
				

				if net_match != None:
					cir_m = CircuitMatch([net_match])

					missing_nets = nets_with_starting_ref.copy()

					missing_nets.remove(starting_net['name'])
					
					print(f'continuing search on {missing_nets}')

					old_pcb_board = self.pcb_board.copy_self()


					n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = nm_last_loc)
					
					if n_cir_m != None:
						#seek out next nets

						n_old_pcb_board = self.pcb_board.copy_self()
						nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

						if nn_cir_m != None:
							return nn_cir_m, nn_index, nn_last_loc
						else:
							self.pcb_board = n_old_pcb_board
							nm.pcb_board = n_old_pcb_board

							starting_net_search_index = 1
							while 1:

								if hasattr(self.pcb_board, 'pcb_rgb_original'):
									self.pcb_board.revert_original()
									nm.pcb_board = self.pcb_board
									incomplete_net_match = nm.update_traces(incomplete_net_match)
								print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
								
								net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
								add_nm_cm_data(nm)

								if net_match != None:
									print(f'a net match was found at {starting_net_search_index}')
									cir_m = CircuitMatch([net_match])

									n_old_pcb_board = self.pcb_board.copy_self()

									n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
									
									if n_cir_m != None:
										nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

										if nn_cir_m != None:
											return nn_cir_m, nn_index, nn_last_loc
										else:
											other_net_search_index = 0
											while 1:
												nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
												if nnn_cir_m != None:
													nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
													if nnnn_cir_m != None:
														return nnnn_cir_m, nnnn_index, nnnn_last_loc
													else:
														other_net_search_index += 1
												else:
													break
											starting_net_search_index += 1
									else:
										self.pcb_board = n_old_pcb_board
										nm.pcb_board = n_old_pcb_board
										starting_net_search_index += 1

								else:
									break
							print('reached end of search')
							return None, nn_index, nn_last_loc
					else:
						self.pcb_board = old_pcb_board
						nm.pcb_board = old_pcb_board
						incomplete_net_match = nm.update_traces(incomplete_net_match)

						starting_net_search_index = 1
						while 1:
							print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
							
							net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
							add_nm_cm_data(nm)

							if net_match != None:
								print(f'a net match was found at {starting_net_search_index}')
								cir_m = CircuitMatch([net_match])

								n_old_pcb_board = self.pcb_board.copy_self()

								n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
								
								if n_cir_m != None:
									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										other_net_search_index = 0
										while 1:
											nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
											if nnn_cir_m != None:
												nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
												if nnnn_cir_m != None:
													return nnnn_cir_m, nnnn_index, nnnn_last_loc
												else:
													other_net_search_index += 1
											else:
												break
									starting_net_search_index += 1
								else:
									self.pcb_board = n_old_pcb_board
									nm.pcb_board = n_old_pcb_board
									starting_net_search_index += 1

							else:
								break

						return None, n_index, n_last_loc


	def get_next_net_mwi_fifo(self, cir_m, missing_net, m_net_node_arr, missing_nets, temp_dir, kicad_cli, footprints_dir, index = 0, search_index = None, last_loc = []):
		'''
		Recursive strategy for finding the next match with needed net possible (rather than exhaustive search)

		Parameters:
		cir_m (Circuit Match) - initial circuit match to start search on
		missing_net (str) - str of net that needs to be found on circuit
		m_net_node_arr (arr) - arr of nodes that need to be found for net
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints

		Optional:
		index (int) - way to keep track of search paths
		search_index (int) - skip some searching if you are going for next match

		Returns:
		CircuitMatch - completed circuit match or None
		index (int) - where the search completed

		'''


		
		next_index = index

		last_loc.append({'fxn': 'get_next_net_mwi_fifo', 'cir_m': cir_m, 'missing_net': missing_net, 'm_net_node_arr': m_net_node_arr, 'missing_nets': missing_nets, 'index': index})

		print('>>>>>get_next_net_mwi_fifo')
		
		
		net_node_IDs = []
		needed_refs = []
		for node in m_net_node_arr:
			node_ID = node['ref'] + '-' + node['pin']
			net_node_IDs.append(node_ID)
			if node['ref'] not in needed_refs:
				needed_refs.append(node['ref'])

		def add_nm_cm_data(nm):
			if not hasattr(nm, 'cm_data'):
				nm.cm_data = {}
			if not hasattr(self, 'cm_data'):
				self.cm_data = {}

			
			for key, val in nm.cm_data.items():
				if key in self.cm_data.keys():
					for trace_ID_key, match_vals in nm.cm_data[key].items():
						if trace_ID_key not in self.cm_data[key].keys():
							self.cm_data[key][trace_ID_key] = match_vals
				else:
					self.cm_data[key] = val


		nm = NetMatching(m_net_node_arr, missing_net)
		nm.pcb_board = self.pcb_board
		nm.cm_data = self.cm_data
		
		missing_node_IDs = []
		for net_node_ID in net_node_IDs:
			missing_node_IDs.append(net_node_ID)

		incomplete_match_node_arr = []
		traces = []

		m_net_node_arr.sort(key=lambda x: x['total pins'], reverse=True)

		for node in m_net_node_arr:
			if node['ref'] in cir_m.refs:
				
				node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': cir_m.ref_dict[node['ref']], 'pads': cir_m.ref_dict[node['ref']].pad_IDs[node['pin']]}
				traces_ref = cir_m.ref_dict[node['ref']].touched_traces_dict[node['pin']]
				
				mutual_traces = False
				for trace in traces_ref:
					if trace in traces:
						mutual_traces = True
						break

				if len(traces) == 0 or mutual_traces:
					traces += traces_ref
					incomplete_match_node_arr.append(node_dict)
					missing_node_IDs.remove(node['ref'] + '-' + node['pin'])


		incomplete_net_match = {'traces': traces, 'nodes': incomplete_match_node_arr, 'net': missing_net}

		if len(missing_node_IDs) == 0:
			complete_nm_arr = nm.get_complete_matches([incomplete_net_match], len(m_net_node_arr))
			
			if len(complete_nm_arr) > 0:

				n_cir_m = cir_m.copy()
				n_cir_m.add_net(complete_nm_arr[0])

				missing_nets_cpy = missing_nets.copy()
				missing_nets_cpy.remove(missing_net)

				if len(missing_nets_cpy) > 0:
					nn_old_pcb_board = self.pcb_board.copy_self()
					nn_cir_m, nn_index, nn_last_loc = self.get_next_mwi_fifo(n_cir_m, missing_nets_cpy, temp_dir, kicad_cli, footprints_dir, index = next_index, search_index = search_index, last_loc=last_loc)
					
					if nn_cir_m != None:
						return nn_cir_m, nn_index, nn_last_loc
					else:
						self.pcb_board = nn_old_pcb_board
						nm.pcb_board = nn_old_pcb_board

						return None, nn_index, nn_last_loc
				else:
					return n_cir_m, next_index, last_loc

		if search_index is not None:

			updated_match, n_index, n_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, search_index = search_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets, last_loc = last_loc.copy())
			add_nm_cm_data(nm)
		else:
			
			updated_match, n_index, n_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets, last_loc = last_loc.copy())
			add_nm_cm_data(nm)
		
		f_updated_matches = []

		if updated_match != None:
			
			return updated_match, n_index, n_last_loc
		else:

			old_pcb_board = self.pcb_board.copy_self()


			tc_match, tc_index, tc_last_loc = nm.trace_cut_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, search_index = search_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets, last_loc = last_loc.copy())

			if tc_match != None:
				self.pcb_board = nm.pcb_board



				if self.intervention_combo_valid(tc_match.circuit_arr):
					print('was a valid match')
					return tc_match, tc_index, tc_last_loc
				else:
					print('was an invalid match')
					self.pcb_board = old_pcb_board
					nm.pcb_board = old_pcb_board
					incomplete_net_match = nm.update_traces(incomplete_net_match)
					cir_m.update_traces(cir_m.circuit_arr, self.pcb_board)
					n_search_index = tc_index

					while 1:
						old_pcb_board = self.pcb_board.copy_self()

						tc_match, tc_index, tc_last_loc = nm.trace_cut_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=next_index, search_index = n_search_index, circuit_matching=self, cir_match=cir_m.copy(), missing_nets = missing_nets)

						if tc_match != None:
							if self.intervention_combo_valid(tc_match.circuit_arr):
								return tc_match, tc_index, tc_last_loc
							else:
								self.pcb_board = old_pcb_board
								nm.pcb_board = old_pcb_board
								incomplete_net_match = nm.update_traces(incomplete_net_match)
								n_search_index += 1

						else:
							self.pcb_board = old_pcb_board
							nm.pcb_board = old_pcb_board
							break

						


					return None, n_index, n_last_loc
			else:
				self.pcb_board = old_pcb_board
				nm.pcb_board = old_pcb_board


				cir_m.update_traces(cir_m.circuit_arr, old_pcb_board)

				return None, n_index, n_last_loc

	

	def get_next_mwi_fifo(self, init_cm, missing_nets, temp_dir, kicad_cli, footprints_dir, index = 0, search_index = None, last_loc = []):
		'''
		Recursive strategy for finding the first match possible (rather than exhaustive search)

		Parameters:
		init_cm (Circuit Match) - initial circuit match to start search on
		missing_nets (array) - array of nets that need to be found on circuit
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints

		Optional:
		index (int) - way to keep track of search paths
		search_index (int) - skip some searching if you are going for next match

		Returns:
		CircuitMatch - completed circuit match or None
		index (int) - where the search completed

		'''
		
		
		last_loc.append({'fxn': 'get_next_mwi_fifo', 'init_cm': init_cm, 'missing_nets': missing_nets, 'index': index})
		
		print('>>>>>>>get_next_mwi_fifo')

		if search_index != None:
			print(f'search index: {search_index}')


		i = index

		if hasattr(self, 'current_best_match') and self.current_best_match != None:
			if len(self.current_best_match['match'].nets) < len(init_cm.nets):
				if len(missing_nets) > 0:
					self.current_best_match = {'match': init_cm, 'missing nets': missing_nets}
		else:
			if len(missing_nets) > 0:
				self.current_best_match = {'match': init_cm, 'missing nets': missing_nets}


		if len(missing_nets) == 0:
			
			if self.intervention_combo_valid(init_cm.circuit_arr):
				

				self.get_cuts_overlay(init_cm.interventions_net_arr)

				
				return init_cm, index, last_loc
			else:
				
				
				return None, index, last_loc

		missing_net = missing_nets[0]

		m_net_node_arr = []

		for net in self.net_arr:
			if net['name'] == missing_net:
				m_net_node_arr = net['node arr']
				break

		mwi_v = []

		
		mwi, n_index, n_last_loc = self.get_next_net_mwi_fifo(init_cm.copy(), missing_net, m_net_node_arr, missing_nets, temp_dir, kicad_cli, footprints_dir, index = i, last_loc=last_loc)
		
		if mwi != None:
			if self.intervention_combo_valid(mwi.circuit_arr):
				return mwi, n_index, n_last_loc
			else:
				print('intervention combo not valid')

				

				return None, n_index, n_last_loc



		else:
			return None, n_index, n_last_loc

	def get_next_mwi_fifo_from_match(self, init_cm, temp_dir, kicad_cli, footprints_dir, index=0, last_loc=[]):
		'''
		Recursive strategy for finding the first match possible (rather than exhaustive search) - using a starting match

		Parameters:
		init_cm (Circuit Match) - initial circuit match to start search on
		
		Optional:
		index (int) - way to keep track of search paths
		last_loc (arr) - last location pathways

		Returns:
		CircuitMatch - completed circuit match or None
		index (int) - where the search completed
		last_loc (arr) - arr of steps

		'''
		
		last_loc.append({'fxn': 'get_next_mwi_fifo_from_match', 'init_cm': init_cm, 'index': index})
		
		i = index

		starting_ref = ''
		for ref in self.sorted_refs:
			if ref not in init_cm.refs:
				starting_ref = ref
				break

		if starting_ref == '':
			print('all components are accounted for, validating matches on missing nets')
			#all refs are accounted for - are they properly connected?
			missing_net_arr = self.get_missing_nets(init_cm.circuit_arr)

			for missing_net in missing_net_arr:
				print(f'checking on {missing_net["name"]}')
				net_touched_traces = []
				init_trace = None
				all_nodes_connected = True
				net_match_nodes_arr = []

				for node in missing_net['node arr']:
					ref = node['ref']
					pin = node['pin']

					node_cm = init_cm.ref_dict[ref]
					node_cm_traces = node_cm.touched_traces_dict[pin]

					if len(net_touched_traces) == 0:
						init_trace = node_cm_traces[0]
						net_touched_traces += node_cm_traces
						net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
					else:
						connected = False
						for n_cm_trace in node_cm_traces:
							if n_cm_trace in net_touched_traces:
								connected = True
								break

						if connected:
							net_touched_traces += node_cm_traces
							net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
						else:
							all_nodes_connected = False
							break


				if all_nodes_connected:
					#create a net for them
					net_dict = {'trace': init_trace, 'nodes': net_match_nodes_arr, 'net': missing_net['name']}
					init_cm.add_net(net_dict)
				else:
					print('nodes were not connected!')
					missing_nets = []
					for missing_net_arr_i in missing_net_arr:
						missing_nets.append(missing_net_arr_i['name'])

					n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(init_cm, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = [])

					if n_cir_m != None:
						#seek out next nets
						nn_cir_m, nn_index, nn_last_loc = self.get_next_mwi_fifo_from_match(n_cir_m, n_index, n_last_loc)

						if nn_cir_m != None:
							return nn_cir_m, nn_index, nn_last_loc
						else:
							return None, nn_index, nn_last_loc # here you could return a partial
					else:
						return None, n_index, last_loc

			return init_cm, index, last_loc


		else:
			print(f'component match search for {starting_ref}')
			#use starting ref to run search

			# get a net to start on that contains this component
			starting_net = {}
			starting_net_pins = []

			nets_with_starting_ref = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if node['ref'] == starting_ref:
						contains_ref = True
				if contains_ref:
					if starting_net == {}:
						starting_net = net
						nets_with_starting_ref.append(net['name'])
					else:
						nets_with_starting_ref.append(net['name'])

			for node in starting_net['node arr']:
				if node['ref'] == starting_ref:
					starting_net_pins.append(node['pin'])

			print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_ref}')

			n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(init_cm, nets_with_starting_ref, temp_dir, kicad_cli, footprints_dir, last_loc = [])

			if n_cir_m != None:
				#seek out next nets
				nn_cir_m, nn_index, nn_last_loc = self.get_next_mwi_fifo_from_match(n_cir_m, n_index, n_last_loc)

				if nn_cir_m != None:
					return nn_cir_m, nn_index, nn_last_loc
				else:
					return None, nn_index, nn_last_loc # here you could return a partial
			else:
				return None, n_index, last_loc


	def find_wire_interventions(self, match, missing_nets, temp_dir, kicad_cli, footprints_dir):
		'''
		Search for places to add a wire connection to satisfy missing nets

		Parameters:
		match (array) - valid net match combo
		missing_node_IDs - array of missing node IDs
		temp_dir (str) - directory where to output temp image files 
		kicad_cli (str) - path to access kicad command line interface tool
		footprints_dir (str) - path to the directory of kicad footprints

		Returns:
		matches_wi - array of circuit match interventions (empty if none)
		'''
		matches_wi = []

		#get the refs already covered by the current match
		cir_match = CircuitMatch(match)
		match_refs = cir_match.refs

		#identify which nets are already known
		missing_nets_known_refs_dict = {}

		for i in range(len(missing_nets)):
			missing_nets_known_refs_dict[i] = 0

		missing_net_ID = 0
		for missing_net in missing_nets:
			for node in missing_net['node arr']:
				missing_net_ref = node['ref']
				if missing_net_ref in match_refs:
					missing_nets_known_refs_dict[missing_net_ID] += 1
			missing_net_ID += 1

		missing_net_IDs = list(range(len(missing_nets)))
		missing_net_IDs.sort(key=lambda x: missing_nets_known_refs_dict[x], reverse = True)
		

		# start with the net with most known refs
		starting_net = missing_nets[missing_net_IDs[0]]
		num_known_refs = missing_nets_known_refs_dict[missing_net_IDs[0]]

		# get missing refs and exisitng refs
		missing_refs = []
		existing_refs = []
		for node in starting_net['node arr']:
			if node['ref'] not in match_refs:
				missing_refs.append(node['ref'])
			else:
				existing_refs.append(node['ref'])

		n_starting_net = {}
		if(len(missing_refs) == 0):
			#all refs accounted for.
			# create wire intervention

			#do nodes fall on an existing trace?
			trace_dict = {}
			for node in starting_net['node arr']:
				node_ID = node['ref'] + '-' + node['pin']
				cm = cir_match.ref_dict[node['ref']]
				touched_traces = cm.touched_traces_dict[node['pin']]

				for touched_trace in touched_traces:
					if touched_trace in trace_dict.keys():
						trace_dict[touched_trace].append(node_ID)
					else:
						trace_dict[touched_trace] = [node_ID]

			trace_IDs = list(trace_dict.keys())
			trace_IDs.sort(key = lambda x: len(trace_dict[x]), reverse = True)

			if len(trace_dict[trace_IDs[0]]) == 1: #there is no best trace to start from, just connect them all
				#create net object
				
				n_starting_net['net'] = starting_net['name']
				n_starting_net['incomplete'] = True

				#populate net object with node found on trace
				node_ID = trace_dict[trace_IDs[0]][0]
				[ref, pin] = node_ID.split('-')
				match = cir_match.ref_dict[ref]
				node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
				n_starting_net['nodes'] = [node_dict]
				n_starting_net['traces'] = match.touched_traces_dict[pin]

				n_starting_net['interventions'] = []
				for trace_ID, trace_nodes in trace_dict.items():
					if trace_ID != trace_IDs[0]:
						ref = trace_nodes[0].split('-')[0]
						n_starting_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})
			else:
				n_starting_net['net'] = starting_net['name']
				n_starting_net['incomplete'] = True

				#populate net object with node found on trace
				n_starting_net['nodes'] = []
				node_touched_traces = []
				for node_ID in trace_dict[trace_IDs[0]]:
					[ref, pin] = node_ID.split('-')
					match = cir_match.ref_dict[ref]
					m_traces = match.touched_traces_dict[pin]
					for m_trace in m_traces:
						if m_trace not in node_touched_traces:
							node_touched_traces.append(m_trace)
					node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
					n_starting_net['nodes'].append(node_dict)

				n_starting_net['traces'] = node_touched_traces

			if self.intervention_combo_valid(cir_match.circuit_arr + [n_starting_net]):
				cir_match.add_net(n_starting_net)
				matches_wi.append(cir_match)

		elif len(existing_refs) > 0:
			#existing refs to search on for missing refs
			trace_dict = {}
			for existing_ref in existing_refs:
				#is there an existing trace between these existing refs? if not add wire
				for node in starting_net['node arr']:
					if node['ref'] == existing_ref:
						node_ID = node['ref'] + '-' + node['pin']
						cm = cir_match.ref_dict[node['ref']]
						touched_traces = cm.touched_traces_dict[node['pin']]
						for touched_trace in touched_traces:
							if touched_trace in trace_dict.keys():
								trace_dict[touched_trace].append(node_ID)
							else:
								trace_dict[touched_trace] = [node_ID]
			if len(trace_dict.keys()) == 1:
				#only one trace used
				#so add this as a net match (interventions still needed for missing ref)
				
				n_starting_net['net'] = starting_net['name']
				n_starting_net['incomplete'] = True
				n_starting_net['interventions'] = []
				
				n_starting_net['nodes'] = []
				node_touched_traces = []
				for node_ID in trace_dict[list(trace_dict.keys())[0]]:
					[ref, pin] = node_ID.split('-')
					match = cir_match.ref_dict[ref]
					m_traces = match.touched_traces_dict[pin]
					for m_trace in m_traces:
						if m_trace not in node_touched_traces:
							node_touched_traces.append(m_trace)
					node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
					n_starting_net['nodes'].append(node_dict)
				n_starting_net['traces'] = node_touched_traces
			else:
				trace_IDs = list(trace_dict.keys())
				trace_IDs.sort(key = lambda x: len(trace_dict[x]), reverse = True)

				if len(trace_dict[trace_IDs[0]]) == 1: #there is no best trace to start from, just connect them all
					#create net object
					
					n_starting_net['net'] = starting_net['name']
					n_starting_net['incomplete'] = True

					#populate net object with node found on trace
					node_ID = trace_dict[trace_IDs[0]][0]
					[ref, pin] = node_ID.split('-')
					match = cir_match.ref_dict[ref]
					m_traces = match.touched_traces_dict[pin]
					node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
					n_starting_net['nodes'] = [node_dict]

					node_touched_traces = []
					n_starting_net['interventions'] = []
					for trace_ID, trace_nodes in trace_dict.items():
						if trace_ID not in m_traces:
							node_touched_traces.append(trace_ID)
							ref = trace_nodes[0].split('-')[0]
							n_starting_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})
					n_starting_net['traces'] = node_touched_traces

				else: # work from trace with the most nodes
					#create net object
					n_starting_net['net'] = starting_net['name']
					n_starting_net['incomplete'] = True

					#populate net object with node found on trace
					n_starting_net['nodes'] = []
					for node_ID in trace_dict[trace_IDs[0]]:
						[ref, pin] = node_ID.split('-')
						match = cir_match.ref_dict[ref]
						node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
						n_starting_net['nodes'].append(node_dict)

					node_touched_traces = []
					n_starting_net['interventions'] = []
					for trace_ID, trace_nodes in trace_dict.items():
						if trace_ID not in m_traces:
							node_touched_traces.append(trace_ID)
							ref = trace_nodes[0].split('-')[0]
							n_starting_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})
					n_starting_net['traces'] = node_touched_traces

			#now turn to missing refs
			missing_node_IDs = []
			for missing_ref in missing_refs:
				for node in starting_net['node arr']:
					if node['ref'] == missing_ref:
						missing_node_IDs.append(node['ref'] + '-' + node['pin'])

			nm = NetMatching(starting_net['node arr'], starting_net['name'])
			nm.pcb_board = self.pcb_board
			n_starting_net_matches = nm.find_wire_interventions(n_starting_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)
			if len(n_starting_net_matches) == 0:
				return []
			elif len(n_starting_net_matches) == 1:
				n_starting_net = n_starting_net_matches[0]
				cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [n_starting_net]))
				if len(cir_matches) == 1:
					if self.intervention_combo_valid(cir_matches[0]):
						cir_match = CircuitMatch(cir_matches[0])
						matches_wi.append(cir_match)
				elif len(cir_matches) > 1:
					for ind_cir_match in cir_matches:
						if self.intervention_combo_valid(ind_cir_match):
							cir_match = CircuitMatch(ind_cir_match)
							matches_wi.append(cir_match)
				else:
					return []
			else:
				for ind_n_starting_net_match in n_starting_net_matches:
					#temporary need to fix
					cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [ind_n_starting_net_match]))
					if len(cir_matches) == 1:
						if self.intervention_combo_valid(cir_matches[0]):
							cir_match = CircuitMatch(cir_matches[0])
							matches_wi.append(cir_match)
					elif len(cir_matches) > 1:
						for ind_cir_match in cir_matches:
							if self.intervention_combo_valid(ind_cir_match):
								cir_match = CircuitMatch(ind_cir_match)
								matches_wi.append(cir_match)


		else:
			#find wire intervention with net matching to connect all missing refs
			traces_for_search = []
			for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
				if self.pcb_board.get_num_pads_on_traces([trace_ID]) >= 1 and (trace_ID not in cir_match.touched_traces):
					traces_for_search.append(trace_ID)

			missing_node_IDs = []
			for missing_ref in missing_refs[1:]:
				for node in starting_net['node arr']:
					if node['ref'] == missing_ref:
						missing_node_IDs.append(node['ref'] + '-' + node['pin'])

			missing_ref = missing_refs[0]
			footprint = ''
			pins = []
			for node in starting_net['node arr']:
				if node['ref'] == missing_ref:
					footprint = node['footprint']
					pins.append(node['pin'])
			cm = ComponentMatching()
			cm.pcb_board = self.pcb_board
			
			footprint_arr = footprint.split(":")
			fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

			if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
				complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])

				gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

			cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

			all_matches = []

			nm = NetMatching(starting_net['node arr'], starting_net['name'])
			nm.pcb_board = self.pcb_board
			
			for trace in traces_for_search:
				matches, _ , __ = cm.get_matches_on_trace(trace, pins)
				matches = cm.sort_matches(matches)
				all_matches += matches
			if len(all_matches) == 0:
				return []
			elif len(all_matches) == 1:
				# only one way to place intervention
				match = all_matches[0]
				n_starting_net['traces'] = match.touched_traces_dict[pins[0]]
				n_starting_net['net'] = missing_net['name']
				node_dict = {'node': missing_ref + '-' + pins[0], 'match': match, 'pads': match.pad_IDs[int(pins[0])]}
				n_starting_net['nodes'] = [node_dict]
				if len(pins) > 1:
					for pin in pins[1:]:
						missing_node_IDs.append(missing_ref + '-' + pin)
				n_starting_net = nm.find_wire_interventions(n_starting_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)
				
				cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [n_starting_net]))
				if len(cir_matches) == 1:
					if self.intervention_combo_valid(cir_matches[0]):
						cir_match = CircuitMatch(cir_matches[0])
						matches_wi.append(cir_match)
				elif len(cir_matches) > 1:
					for ind_cir_match in cir_matches:
						if self.intervention_combo_valid(ind_cir_match):
							cir_match = CircuitMatch(ind_cir_match)
							matches_wi.append(cir_match)
				else:
					return []
			elif len(all_matches) > 1:
				all_matches = cm.sort_matches(all_matches)
				for match in all_matches:
					n_starting_net['traces'] = match.touched_traces_dict[pins[0]]
					n_starting_net['net'] = starting_net['name']
					node_dict = {'node': missing_ref + '-' + pins[0], 'match': match, 'pads': match.pad_IDs[int(pins[0])]}
					n_starting_net['nodes'] = [node_dict]
					if len(pins) > 1:
						for pin in pins[1:]:
							missing_node_IDs.append(missing_ref + '-' + pin)
					n_starting_net = nm.find_wire_interventions(n_starting_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)
					
					cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [n_starting_net]))
					if len(cir_matches) == 1:
						if self.intervention_combo_valid(cir_matches[0]):
							cir_match = CircuitMatch(cir_matches[0])
							matches_wi.append(cir_match)
					elif len(cir_matches) > 1:
						for ind_cir_match in cir_matches:
							if self.intervention_combo_valid(ind_cir_match):
								cir_match = CircuitMatch(ind_cir_match)
								matches_wi.append(cir_match)

		if len(missing_nets) == 1:
			return matches_wi

		#loop across existing matches_wi
		init_matches_wi = matches_wi.copy()

		cir_match_wi_arr = []
		for cir_match in init_matches_wi:

			match_refs = cir_match.refs

			init_matches_wi += cir_match_wi_arr
			cir_match_wi_arr = []

			for missing_net_ID in missing_net_IDs[1:]:
				missing_net = missing_nets[missing_net_ID]

				# get missing refs and exisitng refs
				missing_refs = []
				existing_refs = []

				for node in missing_net['node arr']:
					if node['ref'] not in match_refs:
						missing_refs.append(node['ref'])
					else:
						existing_refs.append(node['ref'])

				n_missing_net = {}
				if(len(missing_refs) == 0):
					#all refs accounted for.
					# create wire intervention

					#do nodes fall on an existing trace?
					trace_dict = {}
					for node in missing_net['node arr']:
						node_ID = node['ref'] + '-' + node['pin']
						cm = cir_match.ref_dict[node['ref']]
						touched_traces = cm.touched_traces_dict[node['pin']]
						for touched_trace in touched_traces:
							if touched_trace in trace_dict.keys():
								trace_dict[touched_trace].append(node_ID)
							else:
								trace_dict[touched_trace] = [node_ID]

					if len(trace_dict.keys()) == 1:
						#only one trace used
						#so add this as a net match
						n_missing_net['traces'] = [list(trace_dict.keys())[0]]
						n_missing_net['net'] = missing_net['name']
						
						for node_ID in trace_dict[list(trace_dict.keys())[0]]:

							[ref, pin] = node_ID.split('-')
							match = cir_match.ref_dict[ref]
							node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
							n_missing_net['nodes'] = [node_dict]
					else:
						trace_IDs = list(trace_dict.keys())
						trace_IDs.sort(key = lambda x: len(trace_dict[x]), reverse = True)

						if len(trace_dict[trace_IDs[0]]) == 1: #there is no best trace to start from, just connect them all
							#create net object
							n_missing_net['traces'] = [trace_IDs[0]]
							n_missing_net['net'] = missing_net['name']
							n_missing_net['incomplete'] = True

							#populate net object with node found on trace
							node_ID = trace_dict[trace_IDs[0]][0]
							[ref, pin] = node_ID.split('-')
							match = cir_match.ref_dict[ref]
							node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
							n_missing_net['nodes'] = [node_dict]

							n_missing_net['interventions'] = []
							for trace_ID, trace_nodes in trace_dict.items():
								if trace_ID != trace_IDs[0]:
									ref = trace_nodes[0].split('-')[0]
									n_missing_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})
						else: # work from trace with the most nodes
							#create net object
							n_missing_net['traces'] = [trace_IDs[0]]
							n_missing_net['net'] = missing_net['name']
							n_missing_net['incomplete'] = True

							#populate net object with node found on trace
							n_missing_net['nodes'] = []
							for node_ID in trace_dict[trace_IDs[0]]:
								[ref, pin] = node_ID.split('-')
								match = cir_match.ref_dict[ref]
								node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
								n_missing_net['nodes'].append(node_dict)

							n_missing_net['interventions'] = []
							for trace_ID, trace_nodes in trace_dict.items():
								if trace_ID != trace_IDs[0]:
									ref = trace_nodes[0].split('-')[0]
									n_missing_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})

					if n_missing_net != {} and (self.intervention_combo_valid(cir_match.circuit_arr + [n_missing_net])):
						new_cir_m = CircuitMatch(cir_match.circuit_arr + [n_missing_net])
						cir_match_wi_arr.append(new_cir_m)
				elif len(existing_refs) >= 1:
					# have some place to start the net on

					trace_dict = {}
					for existing_ref in existing_refs:
						#is there an existing trace between these existing refs? if not add wire
						for node in missing_net['node arr']:
							if node['ref'] == existing_ref:
								node_ID = node['ref'] + '-' + node['pin']
								cm = cir_match.ref_dict[node['ref']]
								touched_traces = cm.touched_traces_dict[node['pin']]
								for touched_trace in touched_traces:
									if touched_trace in trace_dict.keys():
										trace_dict[touched_trace].append(node_ID)
									else:
										trace_dict[touched_trace] = [node_ID]

					if len(trace_dict.keys()) == 1:
						#only one trace used
						#so add this as a net match (interventions still needed for missing ref)
						n_missing_net['traces'] = [list(trace_dict.keys())[0]]
						n_missing_net['net'] = missing_net['name']
						n_missing_net['incomplete'] = True
						#n_missing_net['interventions'] = []
						
						for node_ID in trace_dict[list(trace_dict.keys())[0]]:
							[ref, pin] = node_ID.split('-')
							match = cir_match.ref_dict[ref]
							node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
							n_missing_net['nodes'] = [node_dict]
					else:
						trace_IDs = list(trace_dict.keys())
						trace_IDs.sort(key = lambda x: len(trace_dict[x]), reverse = True)

						if len(trace_dict[trace_IDs[0]]) == 1: #there is no best trace to start from, just connect them all
							#create net object
							n_missing_net['traces'] = [trace_IDs[0]]
							n_missing_net['net'] = missing_net['name']
							n_missing_net['incomplete'] = True

							#populate net object with node found on trace
							node_ID = trace_dict[trace_IDs[0]][0]
							[ref, pin] = node_ID.split('-')
							match = cir_match.ref_dict[ref]
							node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
							n_missing_net['nodes'] = [node_dict]

							n_missing_net['interventions'] = []
							for trace_ID, trace_nodes in trace_dict.items():
								if trace_ID != trace_IDs[0]:
									ref = trace_nodes[0].split('-')[0]
									n_missing_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})
						else: # work from trace with the most nodes
							#create net object
							n_missing_net['traces'] = [trace_IDs[0]]
							n_missing_net['net'] = missing_net['name']
							n_missing_net['incomplete'] = True

							#populate net object with node found on trace
							n_missing_net['nodes'] = []
							for node_ID in trace_dict[trace_IDs[0]]:
								[ref, pin] = node_ID.split('-')
								match = cir_match.ref_dict[ref]
								node_dict = {'node': node_ID, 'match': match, 'pads': match.pad_IDs[pin]}
								n_missing_net['nodes'].append(node_dict)

							n_missing_net['interventions'] = []
							for trace_ID, trace_nodes in trace_dict.items():
								if trace_ID != trace_IDs[0]:
									ref = trace_nodes[0].split('-')[0]
									n_missing_net['interventions'].append({'add wire': {'missing node': trace_nodes[0], 'cmpnt match': cir_match.ref_dict[ref]}})

					#now turn to missing refs
					missing_node_IDs = []
					for missing_ref in missing_refs:
						for node in missing_net['node arr']:
							if node['ref'] == missing_ref:
								missing_node_IDs.append(node['ref'] + '-' + node['pin'])

					nm = NetMatching(missing_net['node arr'], missing_net['name'])
					nm.pcb_board = self.pcb_board
					n_missing_nets = nm.find_wire_interventions(n_missing_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)

					if len(n_missing_nets) == 1:
						cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + n_missing_nets))

						if len(cir_matches) == 1:
							if self.intervention_combo_valid(cir_matches[0]):
								new_cir_match = CircuitMatch(cir_matches[0])
								cir_match_wi_arr.append(new_cir_match)


						elif len(cir_matches) > 1:
							for ind_cir_match in cir_matches:
								if self.intervention_combo_valid(ind_cir_match):
									new_cir_match = CircuitMatch(ind_cir_match)
									cir_match_wi_arr.append(new_cir_match)

						else:
							return []
					elif len(n_missing_nets) > 1:
						for ind_n_missing_net in n_missing_nets:
							cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [ind_n_missing_net]))
							if len(cir_matches) == 1:
								if self.intervention_combo_valid(cir_matches[0]):
									new_cir_match = CircuitMatch(cir_matches[0])
									cir_match_wi_arr.append(new_cir_match)
							elif len(cir_matches) > 1:
								for ind_cir_match in cir_matches:
									if self.intervention_combo_valid(ind_cir_match):
										new_cir_match = CircuitMatch(ind_cir_match)
										cir_match_wi_arr.append(new_cir_match)
							else:
								return []

				else:
					#need to fully construct net across all missing refs
					traces_for_search = []
					for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
						if (self.pcb_board.get_num_pads_on_traces([trace_ID]) >= 1) and (trace_ID not in cir_match.touched_traces):
							traces_for_search.append(trace_ID)

					missing_node_IDs = []
					for missing_ref in missing_refs[1:]:
						for node in missing_net['node arr']:
							if node['ref'] == missing_ref:
								missing_node_IDs.append(node['ref'] + '-' + node['pin'])

					missing_ref = missing_refs[0]
					footprint = ''
					pins = []
					for node in missing_net['node arr']:
						if node['ref'] == missing_ref:
							footprint = node['footprint']
							pins.append(node['pin'])
					# run cm
					cm = ComponentMatching()
					cm.pcb_board = self.pcb_board
													
					footprint_arr = footprint.split(":")
					fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"

					if not os.path.isfile(temp_dir + "/" + footprint_arr[1] + ".png"):
						complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", temp_dir, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])

						gen_footprint_PNG(temp_dir + "/" + footprint_arr[1] + ".svg")

					cm.initialize_fp_from_file(temp_dir + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod")

					all_matches = []

					nm = NetMatching(missing_net['node arr'], missing_net['name'])
					nm.pcb_board = self.pcb_board
						
					for trace in traces_for_search:
						matches, _, __ = cm.get_matches_on_trace(trace, pins)
						matches = cm.sort_matches(matches)
						all_matches += matches
					
					if len(all_matches) == 0:
						return []
					elif len(all_matches) == 1:
						# only one way to place intervention
						match = all_matches[0]
						n_missing_net['traces'] = match.touched_traces_dict[int(pins[0])]
						n_missing_net['net'] = missing_net['name']
						node_dict = {'node': missing_ref + '-' + pins[0], 'match': match, 'pads': match.pad_IDs[int(pins[0])]}
						n_missing_net['nodes'] = [node_dict]
						if len(pins) > 1:
							for pin in pins[1:]:
								missing_node_IDs.append(missing_ref + '-' + pin)
						n_missing_nets = nm.find_wire_interventions(n_missing_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)
						
						for ind_n_missing_net in n_missing_nets:
							cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [ind_n_missing_net]))
							if len(cir_matches) == 1:
								if self.intervention_combo_valid(cir_matches[0]):
									new_cir_match = CircuitMatch(cir_matches[0])
									cir_match_wi_arr.append(new_cir_match)
							elif len(cir_matches) > 1:
								for ind_cir_match in cir_matches:
									if self.intervention_combo_valid(ind_cir_match):
										new_cir_match = CircuitMatch(ind_cir_match)
										cir_match_wi_arr.append(new_cir_match)
					elif len(all_matches) > 1:
						all_matches = cm.sort_matches(all_matches)
						for match in all_matches:
							n_missing_net['traces'] = match.touched_traces_dict[int(pins[0])]
							n_missing_net['net'] = missing_net['name']
							node_dict = {'node': missing_ref + '-' + pins[0], 'match': match, 'pads': match.pad_IDs[int(pins[0])]}
							n_missing_net['nodes'] = [node_dict]
							if len(pins) > 1:
								for pin in pins[1:]:
									missing_node_IDs.append(missing_ref + '-' + pin)
							n_missing_nets = nm.find_wire_interventions(n_missing_net, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, cir_match.touched_traces)
							
							for ind_n_missing_net in n_missing_nets:
								cir_matches = self.get_valid_intervention_combos(CircuitMatch(cir_match.circuit_arr + [ind_n_missing_net]))

								if len(cir_matches) == 1:
									if self.intervention_combo_valid(cir_matches[0]):
										new_cir_match = CircuitMatch(cir_matches[0])
										cir_match_wi_arr.append(new_cir_match)
								elif len(cir_matches) > 1:
									for ind_cir_match in cir_matches:
										if self.intervention_combo_valid(ind_cir_match):
											new_cir_match = CircuitMatch(ind_cir_match)
											cir_match_wi_arr.append(new_cir_match)

		init_matches_wi += cir_match_wi_arr

		matches_wi = init_matches_wi
		return matches_wi

	def get_valid_intervention_combos(self, cir_m):
		'''
			Helper function for 'get_matches_with_interventions'. Goes through net matches with interventions and returns CircuitMatch combos that don't conflict.

			Parameters:
			cir_m (Circuit Match object): object with multiple interventions to run through
		'''

		def length_interventions_dict(net_dict):
			if isinstance(net_dict['interventions'], dict):
				interventions_dict = net_dict['interventions']
				if 'add wire' in interventions_dict.keys():
					if isinstance(interventions_dict['add wire'], dict):
						if 'cmpnt matches' in interventions_dict['add wire'].keys():
							return len(interventions_dict['add wire']['cmpnt matches'])
						elif 'cmpnt match' in interventions_dict['add wire'].keys():
							return 1
						else:
							return 0
					else:
						return 1
				else:
					return 0
			else:
				return 1

		def length_intervention_matches(intervention):
			if 'add wire' in intervention.keys():
				if isinstance(intervention['add wire'], dict):
					if 'cmpnt matches' in intervention['add wire'].keys():
						return len(intervention['add wire']['cmpnt matches'])
					elif 'cmpnt match' in intervention['add wire'].keys():
						return 1
					else:
						return 0
				else:
					return 1
			else:
				return 0

		cir_net_arr = []
		cir_net_interventions_arr = []
		for net in cir_m.circuit_arr:
			if 'interventions' in net.keys():
				cir_net_interventions_arr.append(net)
			else:
				cir_net_arr.append(net)
		n_nets = len(cir_net_interventions_arr)


		indices = [0 for i in range(n_nets)]

		interventions_valid = []
		while 1:
			nodes_arr = []
			int_arr_nets = []
			for i in range(n_nets):
				if isinstance(cir_net_interventions_arr[i]['interventions'], dict):
					
					interventions_dict = dict(cir_net_interventions_arr[i]['interventions'].copy())
					if 'add wire' in interventions_dict.keys():
						if isinstance(interventions_dict['add wire'], dict):
							if 'cmpnt matches' in interventions_dict['add wire'].keys():
								cmpnt_matches_arr = interventions_dict['add wire']['cmpnt matches']
								cmpnt_match = cmpnt_matches_arr[indices[i]]
								
								n_interventions_dict = {'add wire': {'missing node': interventions_dict['add wire']['missing node'], 'cmpnt match': cmpnt_match}}
								
								net_cpy = dict(cir_net_interventions_arr[i].copy())
								net_cpy['interventions'] = n_interventions_dict
								nodes_arr.append(net_cpy)
							elif 'cmpnt match' in interventions_dict['add wire'].keys():
								net_cpy = dict(cir_net_interventions_arr[i].copy())
								nodes_arr.append(net_cpy)
						elif isinstance(interventions_dict['add wire'], list):
							net_cpy = dict(cir_net_interventions_arr[i].copy())
							nodes_arr.append(net_cpy)

				elif isinstance(cir_net_interventions_arr[i]['interventions'], list):
					interventions_arr = cir_net_interventions_arr[i]['interventions'].copy()

					n_interventions = len(interventions_arr)
					intervention_indices = [0 for x in range(n_interventions)]
					next_intervention = n_interventions - 1

					combos_interventions_arr = []
					while 1:
						net_cpy = dict(cir_net_interventions_arr[i].copy())
						net_cpy['interventions'] = [{} for x in range(n_interventions)]
						for j in range(n_interventions):
							intervention = interventions_arr[j]
							if 'add wire' in intervention.keys():
								if isinstance(intervention['add wire'], dict):
									if 'cmpnt matches' in intervention['add wire'].keys():
										cmpnt_matches_arr = intervention['add wire']['cmpnt matches']
										cmpnt_match = cmpnt_matches_arr[intervention_indices[j]]
										
										n_interventions_dict = {'add wire': {'missing node': intervention['add wire']['missing node'], 'cmpnt match': cmpnt_match}}
										
										net_cpy['interventions'][j] = n_interventions_dict
									elif 'cmpnt match' in intervention['add wire'].keys():
										n_interventions_dict = {'add wire': {'missing node': intervention['add wire']['missing node'], 'cmpnt match': intervention['add wire']['cmpnt match']}}
										net_cpy['interventions'][j] = n_interventions_dict
								elif isinstance(intervention['add wire'], list):
									n_interventions_dict = {'add wire': intervention['add wire']}
									net_cpy['interventions'][j] = n_interventions_dict
						if net_cpy['interventions'] != [{}]:
							combos_interventions_arr.append(net_cpy)

						next_intervention = n_interventions -1

						while (next_intervention >= 0 and (intervention_indices[next_intervention] + 1 >= length_intervention_matches(cir_net_interventions_arr[i]['interventions'][next_intervention]))):
							next_intervention -= 1

						if next_intervention < 0:
							break

						intervention_indices[next_intervention] += 1
						for y in range(next_intervention + 1, n_interventions):
							intervention_indices[y] = 0
					if len(combos_interventions_arr) > 0:
						int_arr_nets.append(combos_interventions_arr)


			int_arr_net_combos = []

			n_int_arr_combos = len(int_arr_nets)
			int_arr_indices = [0 for x in range(n_int_arr_combos)]
			next_int_arr = n_int_arr_combos - 1

			while 1:
				int_arr_net_combo = []
				for k in range(n_int_arr_combos):
					int_arr_net_combo.append(int_arr_nets[k][int_arr_indices[k]])
				if len(int_arr_net_combo) > 0:
					int_arr_net_combos.append(int_arr_net_combo)

				next_int_arr = n_int_arr_combos -1

				while (next_int_arr >= 0 and (int_arr_indices[next_int_arr] + 1 >= len(int_arr_nets[next_int_arr]))):
					next_int_arr -= 1

				if next_int_arr < 0:
					break

				int_arr_indices[next_int_arr] += 1

				for i in range(next_int_arr + 1, n_int_arr_combos):
					int_arr_indices[i] = 0

			if len(int_arr_net_combos) > 0:
				for int_arr_net_combo in int_arr_net_combos:
					if self.intervention_combo_valid(cir_net_arr + nodes_arr + int_arr_net_combo):
						interventions_valid.append(cir_net_arr + nodes_arr + int_arr_net_combo)
					

			else:
				if self.intervention_combo_valid(cir_net_arr + nodes_arr):
					interventions_valid.append(cir_net_arr + nodes_arr)
			
			next = n_nets-1

			while (next >=0 and (indices[next] + 1 >= length_interventions_dict(cir_net_interventions_arr[next]))):
				next-=1

			if next < 0:
				break

			indices[next] += 1

			for i in range(next + 1, n_nets):
				indices[i] = 0

		
		return interventions_valid



	def intervention_combo_valid(self, net_combination):
		"""
		Helper function for interventions. Verifies that (1) traces are different, (2) component matches for same component are the same, (3) pads are not intersecting, (4) any connected trace is different, 

		Parameters:
		net_combination (array): array of nets 

		Returns:
		(bool) if this is a valid combination returns True or if one of the conditions is not met returns False

		"""
		#verify that (1) traces are different, (2) component matches for same component are the same, (3) pads are not intersecting, (4) any connected trace is different, 

		touched_traces = []
		cm_dict = {}
		pads_touched = {'front pads': [], 'back pads': []}

		for net in net_combination:

			nodes_touched = []

			if 'interventions' in net.keys():
				#(1) traces are different
				
				for trace in net['traces']:
					if trace in touched_traces:
						
						return False
					else:
						
						
						touched_traces.append(trace)

				## check on interventions side
				interventions_dict = net['interventions']
				if isinstance(interventions_dict, list):
					for intervention in interventions_dict:
						if 'add wire' in intervention.keys():
							if isinstance(intervention['add wire'], dict):
								if 'cmpnt match' in intervention['add wire'].keys():
									missing_node_ID = intervention['add wire']['missing node']
									[ref, pin] = missing_node_ID.split('-')
									
									cm = intervention['add wire']['cmpnt match']

									if pin not in cm.touched_traces_dict.keys():
										#note: this case needs to be resolved via via handling // board manager should solve this but keepin gnote in case
										
										return False

									cm_touched_traces = cm.touched_traces_dict[pin]
									
									if ref in cm_dict.keys():
										if cm != cm_dict[ref]:
											if cm.pad_IDs != cm_dict[ref].pad_IDs:
												
												return False
									else:
										
										for cm_pin, pad_arr in cm.pad_IDs.items():
											for pad in pad_arr:
												if cm.fb == 'front':
													if pad in pads_touched['front pads']:

														
														
														return False
													else:
														
														pads_touched['front pads'].append(pad)
												else:
													if pad in pads_touched['back pads']:
														return False
													else:
														pads_touched['back pads'].append(pad)
										
										cm_dict[ref] = cm
							
				elif isinstance(interventions_dict, dict):
					if 'add wire' in interventions_dict.keys():
						if isinstance(interventions_dict['add wire'], dict):
							if 'cmpnt match' in interventions_dict['add wire'].keys():
								missing_node_ID = interventions_dict['add wire']['missing node']
								[ref, pin] = missing_node_ID.split('-')
								cm = interventions_dict['add wire']['cmpnt match']
								cm_touched_traces = cm.touched_traces_dict[pin]
								
								#(2) component matches are the same across component
								if ref in cm_dict.keys():
									if cm != cm_dict[ref]:
										if cm.pad_IDs != cm_dict[ref].pad_IDs:
											return False
								else:
									#(3) pads are not intersecting
									for pin, pad_arr in cm.pad_IDs.items():
										for pad in pad_arr:
											if cm.fb == 'front':
												if pad in pads_touched['front pads']:
													return False
												else:
													pads_touched['front pads'].append(pad)
											else:
												if pad in pads_touched['back pads']:
													
													return False
												else:
													pads_touched['back pads'].append(pad)
											
									cm_dict[ref] = cm
						

				#(2) component matches are the same across component
				for node in net['nodes']:
					ref = node['node'].split('-')[0]
					if ref in cm_dict.keys():
						if node['match'] != cm_dict[ref]:
							if node['match'].pad_IDs != cm_dict[ref].pad_IDs:
								
								return False
							else:
								#they are the same so adjust node to hold same componentMatch
								node['match'] = cm_dict[ref]
					else:
						#(3) pads are not intersecting
						for pin, pad_arr in node['match'].pad_IDs.items():
							for pad in pad_arr:
								if node['match'].fb == 'front':
									if pad in pads_touched['front pads']:
										return False
									else:
										pads_touched['front pads'].append(pad)
								else:
									if pad in pads_touched['back pads']:
										return False
									else:
										pads_touched['back pads'].append(pad)

						cm_dict[ref] = node['match']

					#(4)touched traces (multi pads for a pin connection) are all different
					
					for pad in node['pads']:
						for trace_ID in self.pcb_board.board_connections_dict.keys():
							if node['match'].fb == 'front':
								if pad in self.pcb_board.board_connections_dict[trace_ID]['front pads']:
									if trace_ID not in net['traces']:
										if trace_ID in touched_traces:
											#see if it's not a valid trace (i.e., used via intervention)

											if isinstance(net['interventions'], list):
												found_trace = False
												for intervention in net['interventions']:
													if 'add wire' in intervention.keys():
														if isinstance(intervention['add wire'], list):
															for m_node in intervention['add wire']:
																[m_ref, m_pin] = m_node.split('-')
																if m_ref in cm_dict.keys():
																	m_cm = cm_dict[m_ref]
																	m_t_traces = m_cm.touched_traces_dict[m_pin]
																	if trace_ID in m_t_traces:
																		found_trace = True
																		break
															if found_trace:
																break
														elif isinstance(intervention['add wire'], dict):
															m_node = intervention['add wire']['missing node']
															[m_ref, m_pin] = m_node.split('-')
															if m_ref in cm_dict.keys():
																m_cm = cm_dict[m_ref]
																m_t_traces = m_cm.touched_traces_dict[m_pin]
																if trace_ID in m_t_traces:
																	found_trace = True
																	break
														elif isinstance(intervention['add wire'], type('string')):
															nodes = intervention['add wire'].split('--')
															for node in nodes:

																[m_ref, m_pin] = node.split('-')
																if m_ref in cm_dict.keys():
																	m_cm = cm_dict[m_ref]
																	
																	m_t_traces = m_cm.touched_traces_dict[m_pin]
																	if trace_ID in m_t_traces:
																		found_trace = True
																		break
																else:
																	print('wasnt in cm dict')
																	
												if not found_trace:
													
													return False
											elif isinstance(net['interventions'], dict):
												if 'add wire' in net['interventions'].keys():
													if isinstance(net['interventions']['add wire'], list):
														m_node = net['interventions']['add wire'][0]
														[m_ref, m_pin] = m_node.split('-')
														if m_ref in cm_dict.keys():
															m_cm = cm_dict[m_ref]
															m_t_traces = m_cm.touched_traces_dict[m_pin]
															if trace_ID not in m_t_traces:
																return False
													elif isinstance(net['interventions']['add wire'], dict):
														m_node = net['interventions']['add wire']['missing node']
														[m_ref, m_pin] = m_node.split('-')
														if m_ref in cm_dict.keys():
															m_cm = cm_dict[m_ref]
															m_t_traces = m_cm.touched_traces_dict[m_pin]
															if trace_ID not in m_t_traces:
																
																return False
											else:
												return False
										else:
											touched_traces.append(trace_ID)
							else:
								if pad in self.pcb_board.board_connections_dict[trace_ID]['back pads']:
									if trace_ID not in net['traces']:
										if trace_ID in touched_traces:
											#see if it's not a valid trace (i.e., used via intervention)

											if isinstance(net['interventions'], list):
												found_trace = False
												for intervention in net['interventions']:
													if 'add wire' in intervention.keys():
														if isinstance(intervention['add wire'], list):
															for m_node in intervention['add wire']:
																[m_ref, m_pin] = m_node.split('-')
																if m_ref in cm_dict.keys():
																	m_cm = cm_dict[m_ref]
																	m_t_traces = m_cm.touched_traces_dict[m_pin]
																	if trace_ID in m_t_traces:
																		found_trace = True
																		break
															if found_trace:
																break
														elif isinstance(intervention['add wire'], dict):
															m_node = intervention['add wire']['missing node']
															[m_ref, m_pin] = m_node.split('-')
															if m_ref in cm_dict.keys():
																m_cm = cm_dict[m_ref]
																m_t_traces = m_cm.touched_traces_dict[m_pin]
																if trace_ID in m_t_traces:
																	found_trace = True
																	break
												if not found_trace:
													return False
											elif isinstance(net['interventions'], dict):
												if 'add wire' in net['interventions'].keys():
													if isinstance(net['interventions']['add wire'], list):
														m_node = net['interventions']['add wire'][0]
														[m_ref, m_pin] = m_node.split('-')
														if m_ref in cm_dict.keys():
															m_cm = cm_dict[m_ref]
															m_t_traces = m_cm.touched_traces_dict[m_pin]
															if trace_ID not in m_t_traces:
																return False
													elif isinstance(net['interventions']['add wire'], dict):
														m_node = net['interventions']['add wire']['missing node']
														[m_ref, m_pin] = m_node.split('-')
														if m_ref in cm_dict.keys():
															m_cm = cm_dict[m_ref]
															m_t_traces = m_cm.touched_traces_dict[m_pin]
															if trace_ID not in m_t_traces:
																return False
											else:
												
												return False
										else:
											touched_traces.append(trace_ID)

			else:
				
				#(1) traces are different
				for trace in net['traces']:
					if trace in touched_traces:
						return False
					else:
						touched_traces.append(trace)


				#(2) component matches are the same across component
				for node in net['nodes']:
					ref = node['node'].split('-')[0]
					if ref in cm_dict.keys():
						if node['match'] != cm_dict[ref]:
							if node['match'].pad_IDs != cm_dict[ref].pad_IDs:
								return False
							else:
								#they are the same so adjust node to hold same componentMatch
								node['match'] = cm_dict[ref]
					else:
						#(3) pads are not intersecting
						for pin, pad_arr in node['match'].pad_IDs.items():
							
							for pad in pad_arr:
								if node['match'].fb == 'front':
									if pad in pads_touched['front pads']:
										
										return False
									else:
										pads_touched['front pads'].append(pad)
								else:
									if pad in pads_touched['back pads']:
										
										return False
									else:
										pads_touched['back pads'].append(pad)

						cm_dict[ref] = node['match']

					#(4)touched traces (multi pads for a pin connection) are all different
					
					for pad in node['pads']:
						for trace_ID in self.pcb_board.board_connections_dict.keys():
							if node['match'].fb == 'front':
								if pad in self.pcb_board.board_connections_dict[trace_ID]['front pads']:
									if trace_ID not in net['traces']:
										if trace_ID in touched_traces:
											
											return False
										else:
											touched_traces.append(trace_ID)
							else:
								if pad in self.pcb_board.board_connections_dict[trace_ID]['back pads']:
									if trace_ID not in net['traces']:
										if trace_ID in touched_traces:
											
											return False
										else:
											touched_traces.append(trace_ID)


		return True

	def identify_trace_conflicts(self, net_combination, incomplete_net, cm_match, missing_node):
		"""
		Helper function for creating cut interventions. 
		Parameters:
		net_combination (array): array of nets
		incomplete_net (dict): net dict
		cm_match (match): trying to match
		missing_node(str): ID of node for cm match

		Returns:
		(bool) if this is a valid combination returns True or if one of the conditions is not met returns False

		"""
		#verify that (1) traces are different, (2) component matches for same component are the same, (3) pads are not intersecting, (4) any connected trace is different, 


		touched_traces = []
		cm_dict = {}
		pads_touched = []

		traces_dict = {}

		print('identify_trace_conflicts')

		def cut_to_isolate_node_from_trace(missing_node, cmpnt_match, trace_ID):
			print('cut_to_isolate_node_from_trace')
			
			[ref, pin] = missing_node.split('-')

			temp = self.pcb_board.pcb_rgb.copy()
			h, w = temp.shape[:2]
			line_width = int(math.sqrt(h*w)/240)

			if self.pcb_board.double_sided:
				temp_b = self.pcb_board.pcb_rgb_back.copy()
			

			trace_img_zeros = np.zeros(self.pcb_board.pcb_rgb.shape[:2], np.uint8)
			trace_img = trace_img_zeros.copy()

			if self.pcb_board.double_sided:
				trace_img_b = trace_img_zeros.copy()

			f_traces = self.pcb_board.board_connections_dict[trace_ID]['front traces']
			b_traces = self.pcb_board.board_connections_dict[trace_ID]['back traces']

			for f_trace in f_traces:
				cv2.drawContours(trace_img, self.pcb_board.trace_contours, f_trace, (255, 255, 255), -1)

				#check for inner contours

				if self.pcb_board.trace_hierarchy[0][f_trace][2] != -1:
					inner_cnt = self.pcb_board.trace_hierarchy[0][f_trace][2]
					cv2.drawContours(trace_img, self.pcb_board.trace_contours, inner_cnt, (0, 0, 0), -1)

					while self.pcb_board.trace_hierarchy[0][inner_cnt][0] != -1:
						inner_cnt = self.pcb_board.trace_hierarchy[0][inner_cnt][0]
						cv2.drawContours(trace_img, self.pcb_board.trace_contours, inner_cnt, (0, 0, 0), -1)



			for b_trace in b_traces:
				cv2.drawContours(trace_img_b, self.pcb_board.trace_back_contours, b_trace, (255, 255, 255), -1)

				# check for inner contours

				if self.pcb_board.trace_back_hierarchy[0][b_trace][2] != -1:
					inner_cnt = self.pcb_board.trace_back_hierarchy[0][b_trace][2]
					cv2.drawContours(trace_img_b, self.pcb_board.trace_back_contours, inner_cnt, (0, 0, 0), -1)

					while self.pcb_board.trace_back_hierarchy[0][inner_cnt][0] != -1:
						inner_cnt = self.pcb_board.trace_back_hierarchy[0][inner_cnt][0]
						cv2.drawContours(trace_img_b, self.pcb_board.trace_back_contours, inner_cnt, (0, 0, 0), -1)

			pad_img = trace_img_zeros.copy()
			for pad in cmpnt_match.pad_IDs[pin]:
				if cmpnt_match.fb == 'front':
					cv2.drawContours(pad_img, self.pcb_board.mask_contours, pad, (255,255,255), line_width)
					cv2.drawContours(pad_img, self.pcb_board.mask_contours, pad, (0, 0, 0), -1)
				else:
					cv2.drawContours(pad_img, self.pcb_board.mask_back_contours, pad, (255,255,255), line_width)
					cv2.drawContours(pad_img, self.pcb_board.mask_back_contours, pad, (0, 0, 0), -1)
				
			if cmpnt_match.fb == 'front':
				cuts_img = cv2.bitwise_and(trace_img, pad_img)
			else:
				cuts_img = cv2.bitwise_and(trace_img_b, pad_img)


			cuts = {'front cuts': [], 'back cuts': []}

			int_contours, int_hierarchy = cv2.findContours(cuts_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
			
			if cmpnt_match.fb == 'front':
				for int_cnt in int_contours:
					M = cv2.moments(int_cnt)
					if M['m00'] != 0:
						cuts['front cuts'].append(int_cnt)
			else:
				for int_cnt in int_contours:
					M = cv2.moments(int_cnt)
					if M['m00'] != 0:
						cuts['back cuts'].append(int_cnt)

			if cmpnt_match.fb == 'front':
				temp1 = self.pcb_board.pcb_rgb.copy()
			else:
				temp1 = self.pcb_board.pcb_rgb_back.copy()

			for int_contour in int_contours:
				cv2.drawContours(temp1, [int_contour], 0, (0, 0, 255), -1)


			if 'holes' in self.pcb_board.board_connections_dict[trace_ID].keys():
				for hole in self.pcb_board.board_connections_dict[trace_ID]['holes']:
					if hasattr(hole, 'isThroughHole') and hole.isThroughHole:
						
						# is the cmpnt pad in question on a through hole?
						for pad in cmpnt_match.pad_IDs[pin]:
							if cmpnt_match.fb == 'front':
								within_pad = cv2.pointPolygonTest(self.pcb_board.mask_contours[pad], hole.coordinates, False)
							else:
								within_pad = cv2.pointPolygonTest(self.pcb_board.mask_back_contours[pad], hole.coordinates, False)

							if within_pad == 1:
								#make sure to create cuts on the other side too
								pad_img = trace_img_zeros.copy()

								if cmpnt_match.fb == 'front':
									cv2.drawContours(pad_img, self.pcb_board.mask_contours, pad, (255,255,255), line_width)
									cv2.drawContours(pad_img, self.pcb_board.mask_contours, pad, (0, 0, 0), -1)
									cuts_img = cv2.bitwise_and(trace_img_b, pad_img) # note these are flipped
									int_contours, int_hierarchy = cv2.findContours(cuts_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

									for int_cnt in int_contours:
										M = cv2.moments(int_cnt)
										if M['m00'] != 0:
											cuts['back cuts'].append(int_cnt)
									
								else:
									cv2.drawContours(pad_img, self.pcb_board.mask_back_contours, pad, (255,255,255), line_width)
									cv2.drawContours(pad_img, self.pcb_board.mask_back_contours, pad, (0, 0, 0), -1)
									cuts_img = cv2.bitwise_and(trace_img, pad_img)
									int_contours, int_hierarchy = cv2.findContours(cuts_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
									
									for int_cnt in int_contours:
										M = cv2.moments(int_cnt)
										if M['m00'] != 0:
											cuts['front cuts'].append(int_cnt)

			return cuts		


		all_interventions = {}
		for net in net_combination + [incomplete_net]:
			#(1) traces are different

			for net_trace in net['traces']:
				if net_trace in touched_traces:

					num_nodes_on_trace = 0
					
					for trace_net in traces_dict[net_trace]:
						for node in trace_net['nodes']:
							[ref, pin] = node['node'].split('-')
							if net_trace in node['match'].touched_traces_dict[pin]:
								num_nodes_on_trace += 1
						if 'interventions' in trace_net.keys():
							for intervention in trace_net['interventions']:
								for key, val in intervention.items():
									if key == 'add wire':
										if isinstance(val, dict):
											[ref, pin] = val['missing node'].split('-')
											if net_trace in val['cmpnt match'].touched_traces_dict[pin]:
												num_nodes_on_trace += 1

					if num_nodes_on_trace < len(net['nodes']) + 1:
						print('do cuts on existing nets')

						
						


						for trace_net in traces_dict[net_trace]:

							
							front_cuts = []
							back_cuts = []
							for node in trace_net['nodes']:

								cuts = cut_to_isolate_node_from_trace(node['node'], node['match'], net_trace)
								
								front_cuts += cuts['front cuts']
								back_cuts += cuts['back cuts']

							if 'interventions' in trace_net.keys():
								if isinstance(trace_net['interventions'], list):
									for intervention in trace_net['interventions']:
										if 'add wire' in intervention.keys():

											if isinstance(intervention['add wire'], dict):
												node = intervention['add wire']['missing node']
												cmpnt_match = intervention['add wire']['cmpnt match']
												cuts = cut_to_isolate_node_from_trace(node, cmpnt_match, net_trace)
										
												front_cuts += cuts['front cuts']
												back_cuts += cuts['back cuts']

								elif isinstance(trace_net['interventions'], dict):
									if 'add wire' in trace_net['interventions'].keys():
										node = trace_net['interventions']['add wire']['missing node']
										cmpnt_match = trace_net['interventions']['add wire']['cmpnt match']
										cuts = cut_to_isolate_node_from_trace(node, cmpnt_match, net_trace)
								
										front_cuts += cuts['front cuts']
										back_cuts += cuts['back cuts']

							interventions = []
							if len(front_cuts) > 0 or len(back_cuts) > 0:
								interventions.append({'trace cuts': {'front cuts': front_cuts, 'back cuts': back_cuts}})
							#check to see if I need to add wires
							if len(trace_net['nodes']) > 1:
								#add wire interventions
								for node in trace_net['nodes'][1:]:
									add_wire = True
									for intervention in interventions:
										if intervention == {'add wire': [trace_net['nodes'][0]['node'], node['node']]}:
											add_wire = False
											break
									if 'interventions' in trace_net.keys():
										for intervention in trace_net['interventions']:
											if intervention == {'add wire': [trace_net['nodes'][0]['node'], node['node']]}:
												add_wire = False
												
												break

									if add_wire:
										interventions.append({'add wire': [trace_net['nodes'][0]['node'], node['node']]})
										

							if trace_net['net'] not in all_interventions.keys():
								all_interventions[trace_net['net']] = interventions
							else:
								all_interventions[trace_net['net']] += interventions

					else:
						print('do cuts on new net and cmpnt match')

						all_interventions = {}
						front_cuts = []
						back_cuts = []
						for node in net['nodes']:
							cuts = cut_to_isolate_node_from_trace(node['node'], node['match'], net_trace)
							front_cuts += cuts['front cuts']
							back_cuts += cuts['back cuts']

						cuts = cut_to_isolate_node_from_trace(missing_node, cm_match, net_trace)
						front_cuts += cuts['front cuts']
						back_cuts += cuts['back cuts']

						interventions = []
						if len(front_cuts) > 0 or len(back_cuts) > 0:
							interventions.append({'trace cuts': {'front cuts': front_cuts, 'back cuts': back_cuts}})
						if len(net['nodes']) > 1:
							for node in net['nodes'][1:]:
								[ref,pin] = node['node'].split('-')
								touched_traces = node['match'].touched_traces_dict[pin]
								if net_trace not in touched_traces:
									interventions.append({'add wire': [net['nodes'][0]['node'], node['node']]})


						if net['net'] not in all_interventions.keys():
							all_interventions[net['net']] = interventions
						else:
							all_interventions[net['net']] += interventions

						

				else:
					touched_traces.append(net_trace)
					if net_trace in traces_dict.keys():
						traces_dict[net_trace].append(net)
					else:
						traces_dict[net_trace] = [net]


		
		for trace_ID in list(set(cm_match.touched_traces_list)):
			if trace_ID in touched_traces:
				
				front_cuts = []
				back_cuts = []
				interventions = []
				

				cuts = cut_to_isolate_node_from_trace(missing_node, cm_match, trace_ID)
				front_cuts += cuts['front cuts']
				back_cuts += cuts['back cuts']
				
				if len(front_cuts) > 0 or len(back_cuts) > 0:
					interventions.append({'trace cuts': {'front cuts': front_cuts, 'back cuts': back_cuts}})

				if incomplete_net['net'] not in all_interventions.keys():
					if len(interventions) > 0:
						all_interventions[incomplete_net['net']] = interventions
				else:
					all_interventions[incomplete_net['net']] += interventions


		return all_interventions

	def recursive_search_from_match(self, n_last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir):
		

		starting_ref_index = 0

		def locate_other_nets(cir_m, index=0, last_loc=[]):
			
			#approach this by looking at sorted refs

			starting_ref = ''
			for ref in self.sorted_refs[1:]:
				if ref not in cir_m.refs:
					starting_ref = ref
					break

			if starting_ref == '':
				print('all components are accounted for, validating matches on missing nets')
				#all refs are accounted for - are they properly connected?
				missing_net_arr = self.get_missing_nets(cir_m.circuit_arr)

				for missing_net in missing_net_arr:
					print(f'checking on {missing_net["name"]}')
					net_touched_traces = []
					all_nodes_connected = True
					net_match_nodes_arr = []

					for node in missing_net['node arr']:
						ref = node['ref']
						pin = node['pin']

						node_cm = cir_m.ref_dict[ref]

						node_cm_traces = node_cm.touched_traces_dict[pin]

						if len(net_touched_traces) == 0:
							net_touched_traces += node_cm_traces
							net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
						else:
							connected = False
							for n_cm_trace in node_cm_traces:
								if n_cm_trace in net_touched_traces:
									connected = True
									break

							if connected:
								for n_cm_trace in node_cm_traces:
									if n_cm_trace not in net_touched_traces:
										net_touched_traces.append(n_cm_trace)
								net_match_nodes_arr.append({'node': ref + '-' + pin, 'match': node_cm, 'pads': node_cm.pad_IDs[pin]})
							else:
								all_nodes_connected = False
								break


					if all_nodes_connected:
						#create a net for them
						net_dict = {'traces': net_touched_traces, 'nodes': net_match_nodes_arr, 'net': missing_net['name']}
						
						cir_m.add_net(net_dict)
					else:
						print('nodes were not connected!')

						
						missing_nets = []
						for missing_net_arr_i in missing_net_arr:
							missing_nets.append(missing_net_arr_i['name'])

						n_old_pcb_board = self.pcb_board.copy_self()

						n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = last_loc)
						
						if n_cir_m != None:
							#seek out next nets
							nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

							if nn_cir_m != None:
								temp = self.pcb_board.pcb_rgb.copy()
								return nn_cir_m, nn_index, nn_last_loc
							else:
								return None, nn_index, nn_last_loc # here you could return a partial
						else:
							self.pcb_board = n_old_pcb_board
							temp = self.pcb_board.pcb_rgb.copy()
							return None, n_index, last_loc
						

				if self.intervention_combo_valid(cir_m.circuit_arr.copy()):
					print('exit locate_other_nets')
					return cir_m, index, last_loc
				else:
					print('exit locate_other_nets - None')
					return None, index, last_loc


			else:
				print(f'component match search for {starting_ref}')
				#use starting ref to run search

				# get a net to start on that contains this component
				starting_net = {}
				starting_net_pins = []

				nets_with_starting_ref = []
				for net in self.net_arr:
					contains_ref = False
					for node in net['node arr']:
						if node['ref'] == starting_ref:
							contains_ref = True
					if contains_ref:
						if starting_net == {}:
							starting_net = net
							nets_with_starting_ref.append(net['name'])
						else:
							nets_with_starting_ref.append(net['name'])

				for node in starting_net['node arr']:
					if node['ref'] == starting_ref:
						starting_net_pins.append(node['pin'])

				print(f'searching for {len(nets_with_starting_ref)} nets connected to {starting_ref}')

				n_cir_m, n_index, n_last_loc = self.get_next_match_fifo(cir_m, nets_with_starting_ref, temp_dir, kicad_cli, footprints_dir, last_loc = [])

				if n_cir_m != None:
					#seek out next nets
					nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

					if nn_cir_m != None:
						return nn_cir_m, nn_index, nn_last_loc
					else:
						return None, nn_index, nn_last_loc # here you could return a partial
				else:
					return None, n_index, last_loc

		def get_nets_with_starting_ref():
			starting_node_ref = self.sorted_refs[0]

			nets_with_starting_ref = []
			for net in self.net_arr:
				contains_ref = False
				for node in net['node arr']:
					if node['ref'] == starting_node_ref:
						contains_ref = True
				if contains_ref:
					nets_with_starting_ref.append(net['name'])


			return nets_with_starting_ref

		def add_nm_cm_data(nm):
			if not hasattr(nm, 'cm_data'):
				nm.cm_data = {}
			if not hasattr(self, 'cm_data'):
				self.cm_data = {}

			for key, val in nm.cm_data.items():
				if key in self.cm_data.keys():
					for trace_ID_key, match_vals in nm.cm_data[key].items():
						if trace_ID_key not in self.cm_data[key].keys():
							self.cm_data[key][trace_ID_key] = match_vals
				else:
					self.cm_data[key] = val

		n_search_index = n_last_loc[-1]['index']

		while 1:
			if len(n_last_loc) > 1:
				last_step = n_last_loc[-2:-1][0]
				

				if last_step['fxn'] == 'fwi_fifo':
					nm = last_step['net_matching']
					i_n_last_loc = n_last_loc.copy()
					last_step['match'] = nm.update_traces(last_step['match'])

					if last_step['cir_match'] != None:
						trace_cuts = last_step['cir_match'].get_all_trace_cuts()
						if trace_cuts != None:
							nm.pcb_board.revert_original()
							nm.pcb_board.integrate_trace_cuts(trace_cuts)
							self.pcb_board = nm.pcb_board

					if last_step['circuit_matching'] != None:
						last_step['circuit_matching'].pcb_board = nm.pcb_board
						last_step['cir_match'] = last_step['cir_match'].update_traces(last_step['cir_match'].circuit_arr, nm.pcb_board)
					else:
						n_search_index = n_last_loc[-1]['index'] + 1

					nn_mwi, nn_index, nn_last_loc = nm.fwi_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = n_last_loc[:-2])

					n_last_loc = i_n_last_loc

					if nn_mwi != None:
						
						if isinstance(nn_mwi, dict):
							
							cir_m = CircuitMatch([nn_mwi])

							missing_nets = get_nets_with_starting_ref().copy()

							missing_nets.remove(nn_mwi['net'])
							
							

							old_pcb_board = self.pcb_board.copy_self()

							n_search_index = 0

							n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, index=nn_index, search_index = n_search_index, last_loc = nn_last_loc)
							
							if n_cir_m != None:
								
								nn_cir_m, nn_lon_index, nn_lon_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

								if nn_cir_m != None:
									
									return nn_cir_m, nn_lon_index, nn_lon_last_loc
								else:
									self.pcb_board = old_pcb_board

									starting_net_search_index = nn_index


									incomplete_net_match = last_step['match']

									while 1:
										if hasattr(self.pcb_board, 'pcb_rgb_original'):
											self.pcb_board.revert_original()
											nm.pcb_board = self.pcb_board
											incomplete_net_match = nm.update_traces(incomplete_net_match)

										net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, index=last_step['index'], search_index=starting_net_search_index, last_loc=[])

										if net_match != None:
											cir_m = CircuitMatch([net_match])

											n_old_pcb_board = self.pcb_board.copy_self()

											n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, index = nm_index, search_index = 0, last_loc = nm_last_loc)
									
											if n_cir_m != None:
												nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

												if nn_cir_m != None:
													return nn_cir_m, nn_index, nn_last_loc
												else:
													self.pcb_board = old_pcb_board
													nm.pcb_board = old_pcb_board
													starting_net_search_index = nm_index
											else:
												self.pcb_board = old_pcb_board
												nm.pcb_board = old_pcb_board
												starting_net_search_index = nm_index
										else:
											break

									r_last_loc = n_last_loc.pop()
									n_search_index = last_step['index'] - 1
							else:
								self.pcb_board = old_pcb_board
								starting_net_search_index = n_search_index # should this be nn_index?

								incomplete_net_match = last_step['match']
								
								n_search_index = nn_index - 1


						else:
							return nn_mwi, nn_index, nn_last_loc

					else:
						#try to see if trace cut will work
						old_pcb_board = nm.pcb_board.copy_self()

						if n_last_loc[-1]['fxn'] == 'trace_cut_fifo':
							r_last_loc = n_last_loc.pop()
							n_search_index = last_step['index'] - 1

						else:
							n_search_index = 0

							nnn_mwi, nnn_index, nnn_last_loc = nm.trace_cut_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], nn_index, search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = nn_last_loc)

							if nnn_mwi != None:
								if len(nnn_mwi.nets) == len(self.net_arr):
									return nnn_mwi, nnn_index, nnn_last_loc
								else:
									i_n_last_loc = nnn_last_loc.copy()
									

									nnn_mwi, nnn_index, nnn_last_loc = locate_other_nets(nnn_mwi, nnn_index, nnn_last_loc)


									if nnn_mwi != None:
										return nnn_mwi, nnn_index, nnn_last_loc
									else:
										self.pcb_board = old_pcb_board
										nm.pcb_board = old_pcb_board
										r_last_loc = n_last_loc.pop()
										n_search_index = last_step['index'] - 1

							else:
								nm.pcb_board = old_pcb_board
								self.pcb_board = old_pcb_board
								r_last_loc = n_last_loc.pop()
								n_search_index = last_step['index'] - 1

				elif last_step['fxn'] == 'get_next_mwi_fifo' and last_step['missing_nets'] == []:

					if len(last_step['init_cm'].nets) == len(self.net_arr):
						print('exited early')
						return None, n_search_index, n_last_loc
					else:
						
						r_last_loc = n_last_loc.pop()
						n_search_index = last_step['index'] - 1
						if n_search_index < 0:
							n_search_index = 0
				elif last_step['fxn'] == 'trace_cut_fifo':
					nm = last_step['net_matching']
					nm.pcb_board.revert_original()

					trace_cuts = last_step['cir_match'].get_all_trace_cuts()
					if trace_cuts != None:
						nm.pcb_board.integrate_trace_cuts(trace_cuts)

					self.pcb_board = nm.pcb_board
					
					i_n_last_loc = n_last_loc.copy()

					old_pcb_board = nm.pcb_board.copy_self()

					nn_mwi, nn_index, nn_last_loc = nm.trace_cut_fifo(last_step['match'], last_step['missing_node_IDs'], temp_dir, kicad_cli, footprints_dir, last_step['ignore_traces'], last_step['index'], search_index = n_search_index, circuit_matching = last_step['circuit_matching'], cir_match = last_step['cir_match'], missing_nets = last_step['missing_nets'], last_loc = n_last_loc[:-2])

					n_last_loc = i_n_last_loc

					if nn_mwi != None:
						if len(nn_mwi.nets) == len(self.net_arr):
							return nn_mwi, nn_index, nn_last_loc
						else:
							i_n_last_loc = nn_last_loc.copy()
							nnn_mwi, nnn_index, nnn_last_loc = locate_other_nets(nn_mwi, nn_index, nn_last_loc)
							nn_last_loc = i_n_last_loc

							if nnn_mwi != None:
								
								return nnn_mwi, nnn_index, nnn_last_loc
							else:
								print('locate other nets failed')
								self.pcb_board = old_pcb_board
								nm.pcb_board = old_pcb_board
								
					else:
						self.pcb_board = old_pcb_board
						nm.pcb_board = old_pcb_board
						r_last_loc = n_last_loc.pop()
						n_search_index = r_last_loc['index'] - 1

				else:
					r_last_loc = n_last_loc.pop()
					n_search_index = r_last_loc['index'] #- 1

			else:

				starting_node_ref = self.sorted_refs[0]

				if n_last_loc[0]['fxn'] == 'get_next_mwi_fifo':
					init_cm = n_last_loc[0]['init_cm'].ref_dict[starting_node_ref]

				else: 
					init_cm = n_last_loc[0]['match']['nodes'][0]['match']
				

				footprint = ''
			
				for fp, refs in self.footprints_dict.items():
					if starting_node_ref in refs:
						footprint = fp
						break

				matches = []

				if isinstance(self.cm_data[footprint], dict):
					if 'full' in self.cm_data[footprint].keys():
						matches = self.cm_data[footprint]['full']

				elif isinstance(self.cm_data[footprint], list):
					matches = self.cm_data[footprint]

				for match in matches:
					if match.pad_IDs == init_cm.pad_IDs:
						break
					starting_ref_index += 1

				starting_ref_index += 1

				if starting_ref_index < len(self.cm_data[footprint]):

					nets_with_starting_ref = get_nets_with_starting_ref()
					starting_net_name = nets_with_starting_ref[0]

					starting_net = {}

					for net in self.net_arr:
						if net['name'] == starting_net_name:
							starting_net = net
							break

					starting_net_pins = []

					for node in starting_net['node arr']:
						if node['ref'] == starting_node_ref:
							starting_net_pins.append(node['pin'])
					nm = NetMatching(starting_net['node arr'], starting_net['name'])
					nm.pcb_board = self.pcb_board
					nm.cm_data = self.cm_data

					for i in range(starting_ref_index, len(matches)):
						

						new_cm = matches[i]
						
						if len(starting_net_pins) > 1: # multiple pins for same net
							print(f'component match has multiple pins for this net')
							
							# do they lie on the same trace for this match?
							touched_traces = new_cm.touched_traces_dict[starting_net_pins[0]]

							is_connected = True
							for starting_net_pin in starting_net_pins:
								s_touched_traces = new_cm.touched_traces_dict[starting_net_pins[0]]
								s_is_connected = False
								for s_touched_trace in s_touched_traces:
									if s_touched_trace in touched_traces:
										s_is_connected = True
										break
								if not s_is_connected:
									is_connected = False
									break

							if is_connected: # create a net match on these nets
								print(f'component match pins properly connected')
								match_node_arr = []
								for node in starting_net['node arr']:
									if node['ref'] == starting_node_ref:
										node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': new_cm, 'pads': new_cm.pad_IDs[node['pin']]}
										match_node_arr.append(node_dict)
					
								net_match = {'traces': touched_traces, 'nodes': match_node_arr, 'net': starting_net['name']}
								cir_m = CircuitMatch([net_match])

								missing_nets = nets_with_starting_ref.copy()
								missing_nets.remove(starting_net['name'])

								n_old_pcb_board = self.pcb_board.copy_self()

								n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = [])
								add_nm_cm_data(nm)

								if n_cir_m != None:
									#seek out next nets

									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										return None, nn_index, nn_last_loc # here you could return a partial
								else:
									self.pcb_board = n_old_pcb_board
									nm.pcb_board = n_old_pcb_board
									
									starting_net_search_index = 1

									while 1:
										print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
										
										net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
										add_nm_cm_data(nm)

										if net_match != None:
											print(f'a net match was found at {starting_net_search_index}')
											cir_m = CircuitMatch([net_match])

											n_old_pcb_board = self.pcb_board.copy_self()

											n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
											
											if n_cir_m != None:
												nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)
												

												if nn_cir_m != None:
													return nn_cir_m, nn_index, nn_last_loc
												else:
													other_net_search_index = 0
													while 1:
														nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
														add_nm_cm_data(nm)

														if nnn_cir_m != None:
															nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
															
															if nnnn_cir_m != None:
																return nnnn_cir_m, nnnn_index, nnnn_last_loc
															else:
																other_net_search_index = nnn_index
														else:
															break
													starting_net_search_index += 1
											else:
												self.pcb_board = n_old_pcb_board
												nm.pcb_board = n_old_pcb_board
												starting_net_search_index += 1

										else:
											break
						else:
							print(f'looking at traces for {starting_node_ref}-{starting_net_pins[0]}')
							
							touched_traces = new_cm.touched_traces_dict[starting_net_pins[0]]
							print(f'looking at {len(touched_traces)} traces for {starting_node_ref}-{starting_net_pins[0]}')
							
							#try to find net matches on touched traces:
						
							incomplete_match_node_arr = []
							missing_node_IDs = []
							for node in starting_net['node arr']:
								if node['ref'] == starting_node_ref:
									node_dict = {'node': node['ref'] + '-' + node['pin'], 'match': new_cm, 'pads': new_cm.pad_IDs[node['pin']]}
									incomplete_match_node_arr.append(node_dict)
								else:
									missing_node_IDs.append(node['ref'] + '-' + node['pin'])

							incomplete_net_match = {'traces': touched_traces, 'nodes': incomplete_match_node_arr, 'net': starting_net['name']}
							
							starting_net_search_index = 0

							print(f'looking for {missing_node_IDs}')
				
							net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir)
							add_nm_cm_data(nm)

							
							

							if net_match != None:
								cir_m = CircuitMatch([net_match])

								missing_nets = nets_with_starting_ref.copy()

								missing_nets.remove(starting_net['name'])
								
								print(f'continuing search on {missing_nets}')

								old_pcb_board = self.pcb_board.copy_self()


								n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir, last_loc = nm_last_loc)
								
								if n_cir_m != None:
									#seek out next nets

									n_old_pcb_board = self.pcb_board.copy_self()


									nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

									if nn_cir_m != None:
										return nn_cir_m, nn_index, nn_last_loc
									else:
										self.pcb_board = n_old_pcb_board
										nm.pcb_board = n_old_pcb_board



										starting_net_search_index = 1
										while 1:

											if hasattr(self.pcb_board, 'pcb_rgb_original'):
												self.pcb_board.revert_original()
												nm.pcb_board = self.pcb_board
												incomplete_net_match = nm.update_traces(incomplete_net_match)

											

											print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
											
											net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
											add_nm_cm_data(nm)

											if net_match != None:
												print(f'a net match was found at {starting_net_search_index}')
												cir_m = CircuitMatch([net_match])

												n_old_pcb_board = self.pcb_board.copy_self()

												n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
												
												if n_cir_m != None:
													nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

													if nn_cir_m != None:
														return nn_cir_m, nn_index, nn_last_loc
													else:
														other_net_search_index = 0
														while 1:
															nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
															if nnn_cir_m != None:
																nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
																if nnnn_cir_m != None:
																	return nnnn_cir_m, nnnn_index, nnnn_last_loc
																else:
																	other_net_search_index += 1
															else:
																break
														starting_net_search_index += 1
												else:
													self.pcb_board = n_old_pcb_board
													nm.pcb_board = n_old_pcb_board
													starting_net_search_index += 1

											else:
												break
										print('reached end of search')
										return None, nn_index, nn_last_loc
								else:
									self.pcb_board = old_pcb_board
									nm.pcb_board = old_pcb_board
									incomplete_net_match = nm.update_traces(incomplete_net_match)

									starting_net_search_index = 1
									while 1:
										print(f'Looking at next match ({starting_net_search_index}) for {starting_net["name"]}')
										
										net_match, nm_index, nm_last_loc = nm.fwi_fifo(incomplete_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir, index=nm_index, search_index=starting_net_search_index)
										add_nm_cm_data(nm)

										if net_match != None:
											print(f'a net match was found at {starting_net_search_index}')
											cir_m = CircuitMatch([net_match])

											n_old_pcb_board = self.pcb_board.copy_self()

											n_cir_m, n_index, n_last_loc = self.get_next_mwi_fifo(cir_m, missing_nets, temp_dir, kicad_cli, footprints_dir)
											if n_cir_m != None:
												nn_cir_m, nn_index, nn_last_loc = locate_other_nets(n_cir_m, n_index, n_last_loc)

												if nn_cir_m != None:
													return nn_cir_m, nn_index, nn_last_loc
												else:
													other_net_search_index = 0
													while 1:
														nnn_cir_m, nnn_index, nnn_last_loc = recursive_search_on_circuit(nn_last_loc, other_net_search_index)
														if nnn_cir_m != None:
															nnnn_cir_m, nnnn_index, nnnn_last_loc = locate_other_nets(nnn_cir_m, nnn_index, nnn_last_loc)
															if nnnn_cir_m != None:
																return nnnn_cir_m, nnnn_index, nnnn_last_loc
															else:
																other_net_search_index += 1
														else:
															break
												starting_net_search_index += 1
											else:
												self.pcb_board = n_old_pcb_board
												nm.pcb_board = n_old_pcb_board
												starting_net_search_index += 1

										else:
											break
							else:
								print(f'component match pins are not properly connected - find if intervention possible')
				break

			n_search_index += 1


		return None, n_search_index, n_last_loc

	def net_combination_valid(self, net_combination):
		"""
		Helper function. Verifies that (1) traces are different, (2) component matches for same component are the same, (3) pads are not intersecting, (4) any connected trace is different, 

		Parameters:
		net_combination (array): array of nets 

		Returns:
		(bool) if this is a valid combination returns True or if one of the conditions is not met returns False

		"""
		#verify that (1) traces are different, (2) component matches for same component are the same, (3) pads are not intersecting, (4) any connected trace is different, 

		touched_traces = []
		cm_dict = {}
		pads_touched = {'front pads': [], 'back pads': []}

		print('net_combination_valid')

		for net in net_combination:
			
			#(1) traces are different

			for trace in net['traces']:
				if trace in touched_traces:
					return False
				else:
					touched_traces.append(trace)


			#(2) component matches are the same across component
			for node in net['nodes']:
				ref = node['node'].split('-')[0]
				if ref in cm_dict.keys():
					if node['match'] != cm_dict[ref]:
						if node['match'].pad_IDs != cm_dict[ref].pad_IDs:
							return False
						else:
							#they are the same so adjust node to hold same componentMatch
							node['match'] = cm_dict[ref]
				else:
					#(3) pads are not intersecting
					for pin, pad_arr in node['match'].pad_IDs.items():
						for pad in pad_arr:
							if node['match'].fb == 'front':
								if pad in pads_touched['front pads']:
									return False
								else:
									pads_touched['front pads'].append(pad)
							else:
								if pad in pads_touched['back pads']:
									return False
								else:
									pads_touched['back pads'].append(pad)

					cm_dict[ref] = node['match']

				#(4)touched traces (multi pads for a pin connection) are all different
				
				for pad in node['pads']:

					for trace_ID in self.pcb_board.board_connections_dict.keys():
						if node['match'].fb == 'front':
							if pad in self.pcb_board.board_connections_dict[trace_ID]['front pads']:
								if trace_ID not in net['traces']:
									if trace_ID in touched_traces:


										for f_trace in self.pcb_board.board_connections_dict[trace_ID]['front traces']:
											cv2.drawContours(temp, self.pcb_board.trace_contours, f_trace, (255, 255, 0), 3)

										return False
									else:
										touched_traces.append(trace_ID)
						else:
							if pad in self.pcb_board.board_connections_dict[trace_ID]['back pads']:
								if trace_ID not in net['traces']:
									if trace_ID in touched_traces:
										return False
									else:
										touched_traces.append(trace_ID)

		return True

	def gen_valid_combos(self, valid_net_combinations, net_matches):
		"""
		Helper function. Adds new nets to valid net combos to generate new (validated) net combos

		Parameters:
		valid_net_combinations (array): array of correct net combinations
		net_matches (array): array of nets to potentially add to valid net combos

		Returns:
		g_valid_combos (array): updated array combining all new combos that have been validated

		"""

		g_valid_combos = []
		for valid_net_combo in valid_net_combinations:
			for net_match in net_matches:
				temp_combo = valid_net_combo.copy()
				temp_combo.append(net_match)
				if self.net_combination_valid(temp_combo):
					g_valid_combos.append(temp_combo)
		return g_valid_combos



	def find_circuit_matches(self):
		'''
			Find matches for the specified circuit. Loops through nets and creates match combinations. Then verifies that these are valid combos.

			Returns:
			(array) valid matches

		'''

		net_matches_arr = []

		for net in self.net_arr:
			contains_ref = False
			for node in net['node arr']:
				if(node['ref'] == self.sorted_refs[0]):
					contains_ref = True
					break

			if contains_ref:
				nm = NetMatching(net['node arr'], net['name'])
				nm.pcb_board = self.pcb_board
				nm.add_cm_data(self.cm_data)
				unprocessed_net_matches = nm.search_net_matches()
				processed_net_matches = nm.process_matches(unprocessed_net_matches)
				filtered_net_matches = nm.filter_matches(processed_net_matches)
				net_matches_arr.append(filtered_net_matches)

		n_nets = len(net_matches_arr)
		
		indices = [0 for i in range(n_nets)]

		valid_net_combinations = []

		while 1:

			net_combination = []
			for i in range(n_nets):
				
				if (len(net_matches_arr[i]) > 0):
					net_combination.append(net_matches_arr[i][indices[i]])
					

			if self.net_combination_valid(net_combination):
				valid_net_combinations.append(net_combination)


			# find the rightmost array that has more
			# elements left after the current element
			# in that array
			next = n_nets-1

			while (next >=0 and (indices[next] + 1 >= len(net_matches_arr[next]))):
				next-=1

			if next < 0:
				break

			indices[next] += 1

			for i in range(next + 1, n_nets):
				indices[i] = 0


		if len(valid_net_combinations) == 0 or len(valid_net_combinations[0]) == 0:
			return []
		
		#moving on to the other components now
		touched_refs = [self.sorted_refs[0]]

		for ref in self.sorted_refs[1:]:
			for net in self.net_arr:
				contains_ref = False
				contains_touched_ref = False
				
				for node in net['node arr']:
					if(node['ref'] == ref):
						contains_ref = True
					if node['ref'] in touched_refs:
						contains_touched_ref = True
				
				if contains_ref and not contains_touched_ref:
					nm = NetMatching(net['node arr'], net['name'])
					nm.pcb_board = self.pcb_board
					nm.add_cm_data(self.cm_data)
					unprocessed_net_matches = nm.search_net_matches()
					processed_net_matches = nm.process_matches(unprocessed_net_matches)
					filtered_net_matches = nm.filter_matches(processed_net_matches)
					
					valid_net_combinations = self.gen_valid_combos(valid_net_combinations, filtered_net_matches)
					
			touched_refs.append(ref)


		
		return valid_net_combinations

	def get_full_matches(self, matches, num_nets):
		"""
		Filters through matches to create array that only has *full* circuit matches

		Parameters:
		matches (array): array of valid net combinations
		num_nets (int): number of nets found in circuit

		Returns:
		full_matches (array): array of matches that contain *all* nets in the circuit

		"""
		full_matches = []

		for match in matches:
			if isinstance(match, CircuitMatch):
				match = match.circuit_arr
			if len(match) == num_nets:
				full_matches.append(match)

		return full_matches

	def get_missing_nets(self, valid_match):
		'''
		returns which nets are missing from a match

		Parameters:
		valid_match (array): array of valid net combos

		Returns:
		missing_nets (array): array of the nets that are missing
		'''

		v_match_nets = []

		for net in valid_match:
			v_match_nets.append(net['net'])

		missing_nets = []

		for net in self.net_arr:
			if net['name'] not in v_match_nets:
				missing_nets.append(net)

		return missing_nets

	def filter_duplicates(self, matches):
		'''
			Removes duplicate circuit matches

			Parameters:
			matches(array) - matches to filter for duplicates on
		'''
		f_matches = []
		for match in matches:
			if isinstance(match, CircuitMatch):
				cir_match = match
			else:
				cir_match = CircuitMatch(match)
			is_duplicate = False
			for f_match in f_matches:

				if isinstance(f_match, CircuitMatch):
					f_cir_match = f_match
				else:
					f_cir_match = CircuitMatch(f_match)

				if match == f_match:
					is_duplicate = True
					break

				if cir_match.nets != f_cir_match.nets:
					continue

				if cir_match.touched_traces != f_cir_match.touched_traces:
					continue

				if cir_match.touched_pads != f_cir_match.touched_pads:
					continue

				same_ref_matches = True
				for ref in cir_match.refs:
					if cir_match.ref_dict[ref].pad_IDs != f_cir_match.ref_dict[ref].pad_IDs:
						same_ref_matches = False
						break

				if not same_ref_matches:
					continue
				else: # check interventions
					if len(cir_match.interventions_net_arr) != len(f_cir_match.interventions_net_arr):
						continue

					missing_net = False
					different_interventions = False
					for cir_match_intervention in cir_match.interventions_net_arr:
						f_cir_net = []
						#get corresponding net in f_cir_match
						for f_cir_match_intervention in f_cir_match.interventions_net_arr:
							if cir_match_intervention['net'] == f_cir_match_intervention['net']:
								f_cir_net = f_cir_match_intervention
								break

						if len(f_cir_net) == 0:
							missing_net = True 
							break

						if len(f_cir_net['nodes']) != len(cir_match_intervention['nodes']):
							different_interventions = True
							break

						#compare intervention nets
						if isinstance(f_cir_net['interventions'], dict) and isinstance(cir_match_intervention['interventions'], dict):
							if 'add wire' in f_cir_net['interventions'].keys() and 'add wire' in cir_match_intervention['interventions'].keys():
								if isinstance(f_cir_net['interventions']['add wire'], dict) and isinstance(cir_match_intervention['interventions']['add wire'], dict):
									if 'cmpnt match' in f_cir_net['interventions']['add wire'].keys() and 'cmpnt match' in cir_match_intervention['interventions']['add wire'].keys():
										if f_cir_net['interventions']['add wire']['missing node'] != cir_match_intervention['interventions']['add wire']['missing node']:
											different_interventions = True
											break
										if f_cir_net['interventions']['add wire']['cmpnt match'].pad_IDs != cir_match_intervention['interventions']['add wire']['cmpnt match'].pad_IDs:
											different_interventions = True
											break
								elif isinstance(f_cir_net['interventions']['add wire'], list) and isinstance(cir_match_intervention['interventions']['add wire'], list):
									if f_cir_net['interventions']['add wire'] != cir_match_intervention['interventions']['add wire']:
										different_interventions = True
										break
								else:
									different_interventions = True
									break

						elif isinstance(f_cir_net['interventions'], list) and isinstance(cir_match_intervention['interventions'], list):
							if len(f_cir_net['interventions']) != len(cir_match_intervention['interventions']):
								different_interventions = True
								break


							for cm_intervention in cir_match_intervention['interventions']:
								for fcm_intervention in f_cir_net['interventions']:
									if 'add wire' in cm_intervention.keys() and 'add wire' in fcm_intervention.keys():
										if isinstance(cm_intervention['add wire'], dict) and isinstance(fcm_intervention['add wire'], dict):
											if cm_intervention['add wire']['missing node'] == fcm_intervention['add wire']['missing node']:
												if cm_intervention['add wire']['cmpnt match'].pad_IDs != fcm_intervention['add wire']['cmpnt match'].pad_IDs:
													different_interventions = True
													break
								if different_interventions:
									break

						else:
							different_interventions = True
							break

					if missing_net:
						continue

					if different_interventions:
						continue
					else:
						is_duplicate = True


					if is_duplicate:
						break

			if not is_duplicate:
				f_matches.append(match)

		return f_matches


	def visualize_matches(self, matches, title="match", wait=True):

		h, w = self.pcb_board.pcb_rgb.shape[:2]
		line_width = int(math.sqrt(h*w)/240)

		for match in matches:
			temp = self.pcb_board.pcb_rgb.copy()

			if self.pcb_board.double_sided:
				temp_b = self.pcb_board.pcb_rgb_back.copy()

			interventions_drawn = 0

			for net in match:
				traces = net['traces']
				for trace_ID in traces:
					f_traces = self.pcb_board.board_connections_dict[trace_ID]['front traces']

					for f_trace in f_traces:

						cv2.drawContours(temp, self.pcb_board.trace_contours, f_trace, (255,0,0), -1)

					if self.pcb_board.double_sided:
						b_traces = self.pcb_board.board_connections_dict[trace_ID]['back traces']

						for b_trace in b_traces:
							cv2.drawContours(temp_b, self.pcb_board.trace_back_contours, b_trace, (255,0,0), -1)


				for node in net['nodes']:
					fp_contours = node['match'].fp_contours
					if node['match'].fb == 'front':
						for fp_cnt in fp_contours:
							cv2.drawContours(temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
						temp = cv2.putText(temp, node['node'], node['match'].coordinates, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1, cv2.LINE_AA)
					else:
						for fp_cnt in fp_contours:
							cv2.drawContours(temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
					

				if 'interventions' in net.keys():
					if isinstance(net['interventions'], list):
						for intervention in net['interventions']:
							if 'add wire' in intervention.keys():
								if isinstance(intervention['add wire'], dict):
									match = intervention['add wire']['cmpnt match']
									missing_node = intervention['add wire']['missing node']
									pin = missing_node.split('-')[1]
									pad_IDs = match.pad_IDs[pin]
									interventions_drawn = min(255,interventions_drawn + 50)

									if match.fb == 'front':
										for pad_ID in pad_IDs:
											cv2.drawContours(temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
									else:
										for pad_ID in pad_IDs:
											cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
									
									for node in net['nodes']:
										if node['match'].fb == 'front':
											for pad in node['pads']:
												cv2.drawContours(temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
										else:
											for pad in node['pads']:
												cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)

								elif isinstance(intervention['add wire'], list):
									missing_node = intervention['add wire'][0] # first node
									[ref, pin] = missing_node.split('-')
									cm = None
									interventions_drawn = min(255,interventions_drawn + 50)
									for node in net['nodes']:
										if ref == node['node'].split('-')[0]:
											cm = node['match']
											pad_IDs = cm.pad_IDs[pin]
											if cm.fb == 'front':
												for pad_ID in pad_IDs:
													cv2.drawContours(temp, self.pcb_board.mask_contours, pad_ID, (0, 255,interventions_drawn), -1)
											else:
												for pad_ID in pad_IDs:
													cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255,interventions_drawn), -1)
											
											break

									for o_missing_node in intervention['add wire'][1:]:
										o_ref = o_missing_node.split('-')[0]
										o_pin = o_missing_node.split('-')[1]

										cm = None
										for node in net['nodes']:
											if o_ref == node['node'].split('-')[0]:
												cm = node['match']
												break

										if cm != None:

											pad_IDs = cm.pad_IDs[o_pin]
										else:
											pad_IDs = []

										for pad_ID in pad_IDs:
											if cm.fb == 'front':
												cv2.drawContours(temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), line_width)
											else:
												cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), line_width)
											

					elif isinstance(net['interventions'], dict):
						if 'add wire' in net['interventions'].keys():
							match = net['interventions']['add wire']['cmpnt match']
							missing_node = net['interventions']['add wire']['missing node']
							pin = missing_node.split('-')[1]
							pad_IDs = match.pad_IDs[pin]
							interventions_drawn = min(255,interventions_drawn + 50)
							for pad_ID in pad_IDs:
								if match.fb == 'front':
									cv2.drawContours(temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
								else:
									cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
								
							for node in net['nodes']:
								for pad in node['pads']:
									if node['match'].fb == 'front':
										cv2.drawContours(temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
									else:
										cv2.drawContours(temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)
									

			if self.pcb_board.double_sided:
				cv2.imshow(title + '-front', temp)
				cv2.imshow(title + '-back', temp_b)
				if wait:
					key= cv2.waitKeyEx(0)
			else:
				cv2.imshow(title,temp)
				if wait:
					key=cv2.waitKeyEx(0)

			
	def get_transparent_overlay(self, match):
		'''
			Used for gui displays, returns an image that is transparent with circuit highlighted

			Returns:
			pcb_view_img (2D array): image of match with pads & traces colored in (transparent)

		'''

		alpha_temp = np.zeros(self.pcb_board.pcb_rgb.shape[:3], np.uint8)
		colored_temp = alpha_temp.copy()

		if self.pcb_board.double_sided:
			colored_temp_b = colored_temp.copy()

		h, w = self.pcb_board.pcb_rgb.shape[:2]
		line_width = int(math.sqrt(h*w)/240)

		interventions_drawn = 0

		## draw traces first 

		for net in match:
			for trace_ID in net['traces']:
				for f_trace in self.pcb_board.board_connections_dict[trace_ID]['front traces']:
					if self.pcb_board.trace_hierarchy[0][f_trace][2] != -1: # there's inner traces to not color in
						cv2.drawContours(colored_temp, self.pcb_board.trace_contours, f_trace, (255,0,0), -1)
						
						first_child = self.pcb_board.trace_hierarchy[0][f_trace][2]
						while 1:
							
							cv2.drawContours(colored_temp, self.pcb_board.trace_contours, first_child, (0,0,0), -1)
							if self.pcb_board.trace_hierarchy[0][first_child][0] == -1:
								break 
							else:
								first_child = self.pcb_board.trace_hierarchy[0][first_child][0]
					else:
						cv2.drawContours(colored_temp, self.pcb_board.trace_contours, f_trace, (255,0,0), -1)

				if self.pcb_board.double_sided:
					for b_trace in self.pcb_board.board_connections_dict[trace_ID]['back traces']:
						if self.pcb_board.trace_back_hierarchy[0][b_trace][2] != -1: # there's inner traces to not color in
							cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, b_trace, (255,0,0), -1)

							first_child = self.pcb_board.trace_back_hierarchy[0][b_trace][2]
							while 1:
								cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, first_child, (0,0,0), -1)
								if self.pcb_board.trace_back_hierarchy[0][first_child][0] == -1:
									break 
								else:
									first_child = self.pcb_board.trace_back_hierarchy[0][first_child][0]
						else:
							cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, b_trace, (255,0,0), -1)



		## draw pads next

		for net in match:
			for node in net['nodes']:
				fp_contours = node['match'].fp_contours
				
				if node['match'].fb == 'front':
					for fp_cnt in fp_contours:
						cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
				else:
					for fp_cnt in fp_contours:
						cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
				

			if 'interventions' in net.keys():
				if isinstance(net['interventions'], list):
					for intervention in net['interventions']:
						if 'add wire' in intervention.keys():
							if isinstance(intervention['add wire'], dict):
								match = intervention['add wire']['cmpnt match']

								fp_contours = match.fp_contours
				
								for fp_cnt in fp_contours:
									if match.fb == 'front':
										cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
									else:
										cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
									

								missing_node = intervention['add wire']['missing node']
								pin = missing_node.split('-')[1]
								pad_IDs = match.pad_IDs[pin]
								interventions_drawn = min(255,interventions_drawn + 50)
								for pad_ID in pad_IDs:
									if match.fb == 'front':
										cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
									else:
										cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
									
								for node in net['nodes']:
									for pad in node['pads']:
										if node['match'].fb == 'front':
											cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
										else:
											cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)
										
							elif isinstance(intervention['add wire'], list):
								missing_node = intervention['add wire'][0] # first node
								[ref, pin] = missing_node.split('-')
								cm = None
								interventions_drawn = min(255,interventions_drawn + 50)
								for node in net['nodes']:
									if ref == node['node'].split('-')[0]:
										cm = node['match']
										fp_contours = cm.fp_contours
				
										for fp_cnt in fp_contours:
											if cm.fb == 'front':
												cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=cm.coordinates)
											else:
												cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=cm.coordinates)
											
										pad_IDs = cm.pad_IDs[pin]
										for pad_ID in pad_IDs:
											if cm.fb == 'front':
												cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255,interventions_drawn), -1)
											else:
												cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255,interventions_drawn), -1)
											
										break

								if cm == None:
									print(net)

								for o_missing_node in intervention['add wire'][1:]:
									

									o_pin = o_missing_node.split('-')[1]
									pad_IDs = cm.pad_IDs[o_pin]
									for pad_ID in pad_IDs:
										if cm.fb == 'front':
											cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), line_width)
										else:
											cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), line_width)
										
				elif isinstance(net['interventions'], dict):
					if 'add wire' in net['interventions'].keys():
						match = net['interventions']['add wire']['cmpnt match']

						fp_contours = match.fp_contours
						for fp_cnt in fp_contours:
							if match.fb == 'front':
								cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
							else:
								cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
							

						missing_node = net['interventions']['add wire']['missing node']
						pin = missing_node.split('-')[1]
						pad_IDs = match.pad_IDs[pin]
						interventions_drawn = min(255,interventions_drawn + 50)
						for pad_ID in pad_IDs:
							if match.fb == 'front':
								cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
							else:
								cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
							
						for node in net['nodes']:
							for pad in node['pads']:
								if match.fb == 'front':
									cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
								else:
									cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)
								

		alpha = np.sum(colored_temp, axis=-1) > 0
		alpha = np.uint8(alpha * 255)
		overlay_img = np.dstack((colored_temp, alpha))

		if self.pcb_board.double_sided:
			alpha_b = np.sum(colored_temp_b, axis=-1) > 0
			alpha_b = np.uint8(alpha_b * 255)
			overlay_img_b = np.dstack((colored_temp_b, alpha_b))
			return overlay_img, overlay_img_b

		else:
		
			return overlay_img


	def get_nets_transparent_overlay(self, match):

		alpha_temp = np.zeros(self.pcb_board.pcb_rgb.shape[:3], np.uint8)
		colored_temp = alpha_temp.copy()

		colored_temp_b = alpha_temp.copy()

		net_view_dict = {}

		h, w = self.pcb_board.pcb_rgb.shape[:2]
		line_width = int(math.sqrt(h*w)/240)


		## draw traces first 

		for net in match:
			colored_temp = alpha_temp.copy()
			colored_temp_b = alpha_temp.copy()
			trace_IDs = net['traces']
			for trace_ID in trace_IDs:
				f_traces = self.pcb_board.board_connections_dict[trace_ID]['front traces']

				for f_trace in f_traces:
					if self.pcb_board.trace_hierarchy[0][f_trace][2] != -1: # there's inner traces to not color in
						cv2.drawContours(colored_temp, self.pcb_board.trace_contours, f_trace, (255,0,0), -1)

						first_child = self.pcb_board.trace_hierarchy[0][f_trace][2]
						while 1:
							cv2.drawContours(colored_temp, self.pcb_board.trace_contours, first_child, (0,0,0), -1)
							if self.pcb_board.trace_hierarchy[0][first_child][0] == -1:
								break 
							else:
								first_child = self.pcb_board.trace_hierarchy[0][first_child][0]
					else:
						cv2.drawContours(colored_temp, self.pcb_board.trace_contours, f_trace, (255,0,0), -1)

				if self.pcb_board.double_sided:
					b_traces = self.pcb_board.board_connections_dict[trace_ID]['back traces']

					for b_trace in b_traces:
						if self.pcb_board.trace_back_hierarchy[0][b_trace][2] != -1: # there's inner traces to not color in
							cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, b_trace, (255,0,0), -1)

							first_child = self.pcb_board.trace_back_hierarchy[0][b_trace][2]
							while 1:
								cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, first_child, (0,0,0), -1)
								if self.pcb_board.trace_back_hierarchy[0][first_child][0] == -1:
									break 
								else:
									first_child = self.pcb_board.trace_back_hierarchy[0][first_child][0]
						else:
							cv2.drawContours(colored_temp_b, self.pcb_board.trace_back_contours, b_trace, (255,0,0), -1)


			for node in net['nodes']:
				fp_contours = node['match'].fp_contours
				
				for fp_cnt in fp_contours:
					if node['match'].fb == 'front':
						cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
					else:
						cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=node['match'].coordinates)
					


			interventions_drawn = 0
			
			if 'interventions' in net.keys():
				if isinstance(net['interventions'], list):
					for intervention in net['interventions']:
						if 'add wire' in intervention.keys():
							if isinstance(intervention['add wire'], dict):
								match = intervention['add wire']['cmpnt match']
								fp_contours = match.fp_contours
				
								for fp_cnt in fp_contours:
									if match.fb == 'front':
										cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
									else:
										cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
									
								missing_node = intervention['add wire']['missing node']
								pin = missing_node.split('-')[1]
								pad_IDs = match.pad_IDs[pin]
								interventions_drawn = min(255,interventions_drawn + 50)
								for pad_ID in pad_IDs:
									if match.fb == 'front':
										cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
									else:
										cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
									
								for node in net['nodes']:
									for pad in node['pads']:
										if node['match'].fb == 'front':
											cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
										else:
											cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)
										
							elif isinstance(intervention['add wire'], list):
								missing_node = intervention['add wire'][0] # first node
								[ref, pin] = missing_node.split('-')
								cm = None
								interventions_drawn = min(255,interventions_drawn + 50)
								for node in net['nodes']:
									if ref == node['node'].split('-')[0]:
										cm = node['match']
										pad_IDs = cm.pad_IDs[pin]
										for pad_ID in pad_IDs:
											if cm.fb == 'front':
												cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255,interventions_drawn), -1)
											else:
												cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255,interventions_drawn), -1)
											
										fp_contours = cm.fp_contours
				
										for fp_cnt in fp_contours:
											if cm.fb == 'front':
												cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=cm.coordinates)
											else:
												cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=cm.coordinates)
											
										break

								for o_missing_node in intervention['add wire'][1:]:
									o_pin = o_missing_node.split('-')[1]
									pad_IDs = cm.pad_IDs[o_pin]
									for pad_ID in pad_IDs:
										if cm.fb == 'front':
											cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), line_width)
										else:
											cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), line_width)
										
				elif isinstance(net['interventions'], dict):
					if 'add wire' in net['interventions'].keys():
						match = net['interventions']['add wire']['cmpnt match']
						fp_contours = match.fp_contours
						for fp_cnt in fp_contours:
							if match.fb == 'front':
								cv2.drawContours(colored_temp, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
							else:
								cv2.drawContours(colored_temp_b, [fp_cnt], 0, (0, 0, 255), line_width, offset=match.coordinates)
							
						missing_node = net['interventions']['add wire']['missing node']
						pin = missing_node.split('-')[1]
						pad_IDs = match.pad_IDs[pin]
						interventions_drawn = min(255,interventions_drawn + 50)
						for pad_ID in pad_IDs:
							if match.fb == 'front':
								cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad_ID, (0, 255, interventions_drawn), -1)
							else:
								cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad_ID, (0, 255, interventions_drawn), -1)
							
						for node in net['nodes']:
							for pad in node['pads']:
								if node['match'].fb == 'front':
									cv2.drawContours(colored_temp, self.pcb_board.mask_contours, pad, (0, 255, interventions_drawn), line_width)
								else:
									cv2.drawContours(colored_temp_b, self.pcb_board.mask_back_contours, pad, (0, 255, interventions_drawn), line_width)
								

			alpha = np.sum(colored_temp, axis=-1) > 0
			alpha = np.uint8(alpha * 255)
			overlay_img = np.dstack((colored_temp, alpha))

			if self.pcb_board.double_sided:
				alpha_b = np.sum(colored_temp_b, axis=-1) > 0
				alpha_b = np.uint8(alpha_b * 255)
				overlay_img_b = np.dstack((colored_temp_b, alpha_b))

				net_view_dict[net['net'] + ' View'] = [overlay_img, overlay_img_b]
			else:
				net_view_dict[net['net'] + ' View'] = overlay_img

		
		return net_view_dict









	def get_cuts_overlay(self, interventions):
		print('get_cuts_overlay')

		
		alpha_temp = np.zeros(self.pcb_board.pcb_rgb.shape[:3], np.uint8)
		temp = alpha_temp.copy()

		#temp = self.pcb_board.pcb_rgb.copy()



		if self.pcb_board.double_sided:
			temp_b = alpha_temp.copy()

		j = 0
		for intervention_net in interventions:
			for intervention in intervention_net['interventions']:

				if 'trace cuts' in intervention.keys():

					i = 0

					for f_cut in intervention['trace cuts']['front cuts']:
						
						cv2.drawContours(temp, [f_cut], 0, (255,255,0), -1)

						M = cv2.moments(f_cut)

						if M['m00'] == 0:
							continue
							M['m00'] = 1

						cx = int(M['m10']/M['m00'])
						cy = int(M['m01']/M['m00'])



						cv2.circle(temp, (cx,cy), 30, (255, 0,0), 10)


					i = 0
					for b_cut in intervention['trace cuts']['back cuts']:
						cv2.drawContours(temp_b, [b_cut], 0, (255, 255, 0), -1)

						M = cv2.moments(b_cut)

						if M['m00'] == 0:
							continue
							M['m00'] = 1

						cx = int(M['m10']/M['m00'])
						cy = int(M['m01']/M['m00'])

						cv2.circle(temp_b, (cx,cy), 30, (255, 0,0), 10)


						i += 1





		alpha = np.sum(temp, axis=-1) > 0
		alpha = np.uint8(alpha * 255)
		overlay_img = np.dstack((temp, alpha))

		if self.pcb_board.double_sided:
			alpha_b = np.sum(temp_b, axis=-1) > 0
			alpha_b = np.uint8(alpha_b * 255)
			overlay_img_b = np.dstack((temp_b, alpha_b))

			return overlay_img, overlay_img_b
		else:
			return overlay_img





