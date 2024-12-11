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

from PCB_utils import PCB_Board

class TestComponentMatchMethods(unittest.TestCase):

    def test_direct_match(self):
        mask_file_png = current_directory + '/testfiles/0_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/0_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/0_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)
 
        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()

        self.assertEqual(2, len(matches))

    def test_indirect_match(self): 
        mask_file_png = current_directory + '/testfiles/1_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/1_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/1_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()
        
        print(len(matches))

        self.assertEqual(2, len(matches)) 

    def test_filtered_matches(self):
        mask_file_png = current_directory + '/testfiles/1_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/R_0805_2012Metric.png'
        fp_file = current_directory + '/testfiles/R_0805_2012Metric.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/1_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/1_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()

        print(len(matches))

        self.assertEqual(178, len(matches))

    def test_pad_coverage(self):
        #'''
        mask_file_png = current_directory + '/testfiles/2_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/R_0805_2012Metric.png'
        fp_file = current_directory + '/testfiles/R_0805_2012Metric.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/2_test_pcb_mask.png'
        pcb_file = current_directory + '/testfiles/2_test_pcb.kicad_pcb'
        #'''
        
       
        '''
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        #filename_net = current_directory + '/testfiles/8_test_net.net'
        mask_file_png = current_directory + '/testfiles/22_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/22_test_pcb_traces.png'
        maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        drill_file = current_directory + '/testfiles/22_test.drl'
        pcb_file = current_directory + '/testfiles/22_test.kicad_pcb'
        '''

        pcb = PCB_Board(pcb_file)
        pcb.double_sided = False
        pcb.initialize_via_files(mask_file_png, pcb_file_png)
        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()

        img = pcb.pcb_rgb.copy()

        print(len(matches))
        for match in matches:
            img = pcb.pcb_rgb.copy()
            for fp_cnt in match.fp_contours:
                cv2.drawContours(img, [fp_cnt], 0, (0, 0, 255), 8, offset=match.coordinates)

            cv2.imshow("matches", img)
        
            key = cv2.waitKeyEx(0)
       
        cv2.imshow("matches", img)
        
        key = cv2.waitKeyEx(0)

        #previous 42
        #self.assertEqual(25, len(matches))

    

class TestNetMatchMethods(unittest.TestCase):

    def test_direct_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/0_test_net.net'
        mask_file_png = current_directory + '/testfiles/0_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/0_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/0_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net = get_connections(filename_net)[0]
        nm = NetMatching(net['node arr'], net['name'])
        nm.pcb_board = pcb

        trace_cm_arr = nm.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        processed_net_matches = nm.process_trace_matches(trace_cm_arr) 
        filtered_net_matches = nm.filter_matches(processed_net_matches)

        #nm.visualize_net_matches(filtered_net_matches)
        self.assertEqual(3, len(filtered_net_matches)) #used to be 4


    def test_indirect_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/0_test_net.net'
        mask_file_png = current_directory + '/testfiles/1_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/1_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/1_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net = get_connections(filename_net)[0]
        nm = NetMatching(net['node arr'], net['name'])
        nm.pcb_board = pcb

        trace_cm_arr = nm.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        processed_net_matches = nm.process_trace_matches(trace_cm_arr) 
        filtered_net_matches = nm.filter_matches(processed_net_matches)
        full_matches = nm.get_complete_matches(filtered_net_matches, len(net['node arr']))
        #print(len(full_matches))
        #nm.visualize_net_matches(full_matches)

        self.assertEqual(22, len(full_matches)) #used to be 9

    def test_multi_pin_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net = get_connections(filename_net)[6]
        nm = NetMatching(net['node arr'], net['name'])
        nm.pcb_board = pcb

        trace_cm_arr = nm.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        processed_net_matches = nm.process_trace_matches(trace_cm_arr) 
        filtered_net_matches = nm.filter_matches(processed_net_matches)
        full_matches = nm.get_complete_matches(filtered_net_matches, len(net['node arr']))

        #print(len(full_matches))
        #nm.visualize_net_matches(full_matches)

        self.assertEqual(2, len(full_matches))

class TestCircuitMatchMethods(unittest.TestCase):

    def test_direct_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        #cir_m.visualize_matches(valid_matches)

        self.assertEqual(1, len(full_matches))

    def test_indirect_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/4_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/4_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/4_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)


        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        #cir_m.visualize_matches(full_matches)
        self.assertEqual(1, len(full_matches))

    def test_fifo(self):

        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        #print(valid_match)
        full_matches = cir_m.get_full_matches([valid_match], len(net_arr))

        #cir_m.visualize_matches([valid_match.circuit_arr])
        self.assertEqual(1, len(full_matches))


class TestIncompleteComponentMatchMethods(unittest.TestCase):

    def test_connected_pin_match(self):
        mask_file_png = current_directory + '/testfiles/5_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/5_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/5_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        ignore_pins = [2]
        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_incomplete_matches(ignore_pins)
        cm.add_traces_data_to_matches(matches)

        #print(len(matches))

        #for match in matches:
        #    match.visualize_match("match", True, cm.pcb_board.pcb_rgb, match.coordinates)
        self.assertEqual(1, len(matches))

    def test_indirect_match(self):
        mask_file_png = current_directory + '/testfiles/6_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/6_test_pcb_mask.png'
        pcb_file = current_directory + '/testfiles/5_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        ignore_pins = [2]
        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_incomplete_matches(ignore_pins)
        cm.add_traces_data_to_matches(matches)

        #for match in matches:
        #    match.visualize_match("match", True, cm.pcb_board.pcb_rgb, match.coordinates)
        self.assertEqual(4, len(matches))

    def test_find_interventions_add_pad(self):
        mask_file_png = current_directory + '/testfiles/6_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/6_test_pcb_mask.png'
        pcb_file = current_directory + '/testfiles/5_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()

        if len(matches) == 0:
            #normal matching failed! see if it's possible to find with interventions
            matches = cm.get_matches_with_interventions()
        
        #print(len(matches))
        #for match in matches:
        #    match.visualize_match("match", True, cm.pcb_board.pcb_rgb, match.coordinates)

        self.assertEqual(16, len(matches)) #orig 7

    def test_find_interventions_cut_trace(self):
        #not done
        mask_file_png = current_directory + '/testfiles/5_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/5_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/5_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()
        cm.add_traces_data_to_matches(matches)

        #do additional filtering for this example
        f_matches = []
        for match in matches:
            if cm.check_isolated_pins(match):
                f_matches.append(match)

        if len(f_matches) == 0:
            matches = cm.get_matches_with_interventions()

        #print(len(matches))

        #for match in matches:
        #    match.visualize_match("match", True, cm.pcb_board.pcb_rgb, match.coordinates)
        
        self.assertEqual(4, len(matches))

class TestIncompleteNetMatchMethods(unittest.TestCase):

    def test_multi_node(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net = get_connections(filename_net)[6]
        
        net['node arr'] = net['node arr'][:-1] #removed U1-8
        

        nm = NetMatching(net['node arr'], net['name'])
        nm.pcb_board = pcb


        trace_cm_arr = nm.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        processed_net_matches = nm.process_trace_matches(trace_cm_arr) 
        filtered_net_matches = nm.filter_matches(processed_net_matches)
        full_matches = nm.get_complete_matches(filtered_net_matches, len(net['node arr']))
        
        #print(full_matches)
        #nm.visualize_net_matches(full_matches)
        self.assertEqual(2, len(full_matches))

    def test_find_interventions(self):

        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/8_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/6_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net = get_connections(filename_net)[6]
        #net['node arr'] = net['node arr'][:-1] #removed U1-8
        nm = NetMatching(net['node arr'], net['name'])
        nm.pcb_board = pcb


        trace_cm_arr = nm.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        processed_net_matches = nm.process_trace_matches(trace_cm_arr) 
        filtered_net_matches = nm.filter_matches(processed_net_matches)
        full_matches = nm.get_complete_matches(filtered_net_matches, len(net['node arr']))
        
        if len(full_matches) == 0:
            #need to find matches with interventions

            net_node_IDs = []
            for node in nm.nodes:
                node_ID = node['ref'] + '-' + node['pin']
                net_node_IDs.append(node_ID)

            matches_with_interventions = []
            for filtered_net_match in filtered_net_matches:

                node_matches_present = []
                for node in filtered_net_match['nodes']:
                    node_matches_present.append(node['node'])

                missing_node_IDs = []
                for net_node_ID in net_node_IDs:
                    if net_node_ID not in node_matches_present:
                        missing_node_IDs.append(net_node_ID)

                updated_matches = nm.find_wire_interventions(filtered_net_match, missing_node_IDs, temp_dir, kicad_cli, footprints_dir)

                matches_with_interventions += updated_matches

            #nm.visualize_net_matches(matches_with_interventions)
            #print(len(matches_with_interventions))
        self.assertEqual(2, len(matches_with_interventions))


class TestIncompleteCircuitMatchMethods(unittest.TestCase):

    def test_indirect_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/4_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/4_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/4_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)

        #skip index 4 - Net-(UI-CV)
        net_arr = net_arr[:4] + net_arr[5:]

        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb
        
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        cir_m.visualize_matches(full_matches)
        print(len(full_matches))
        self.assertEqual(1, len(full_matches))

    def test_find_interventions(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/8_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/6_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                #cir_m.visualize_matches(full_matches)

        #print(len(full_matches))
        self.assertEqual(1, len(full_matches))

    def test_find_interventions2(self):
        '''
            test for non-initial component intervention finding
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/9_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/7_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)


        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb
        
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                #cir_m.visualize_matches(full_matches)
            elif len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    matches_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)
                    matches_wi += matches_wi_arr
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                #cir_m.visualize_matches(full_matches)

        self.assertEqual(1, len(full_matches))

    def test_find_interventions3(self):
        '''
            combo of above two interventions
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/10_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/10_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))

                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        valid_matches = matches_wi
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)
                    matches_wi += match_wi_arr

                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                #cir_m.visualize_matches(full_matches)

        self.assertEqual(2, len(full_matches))

    def test_find_interventions4(self):
        '''
            variation of above interventions
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/11_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/11_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb
        
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))

                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        #valid_matches = matches_wi
                        valid_matches = cir_m.get_full_matches(matches_wi, 5)
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)
                    matches_wi += match_wi_arr

                
                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))
                #cir_m.visualize_matches(full_matches)

        self.assertEqual(8, len(full_matches))

    def test_find_interventions5(self):
        '''
            4 wires removed (including one between initial component pins)
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/12_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/12_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)


        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                
                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        #valid_matches = matches_wi
                        valid_matches = cir_m.get_full_matches(matches_wi, 5)
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)
                    matches_wi += match_wi_arr

                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))

        #for full_match in full_matches:
        #    cir_m.visualize_matches([full_match])
        
        self.assertEqual(8, len(full_matches))

    def test_find_interventions6(self):
        '''
            5 wires removed (including one between initial component pins)
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/13_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/13_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                
                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        #valid_matches = matches_wi
                        valid_matches = cir_m.get_full_matches(matches_wi, 5)
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)
                    matches_wi += match_wi_arr

                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))

        #for full_match in full_matches:
        #    cir_m.visualize_matches([full_match])
        
        #print(len(full_matches))
        self.assertEqual(16, len(full_matches))

    def test_find_interventions7(self):
        '''
            all but 3 wires removed 
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/14_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/14_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        #valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        #full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        valid_matches = []
        full_matches = []
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                
                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        valid_matches = cir_m.get_full_matches(cir_m.filter_duplicates(matches_wi), 5)
                        
                        
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)

                    #for match_wi_ar in match_wi_arr:
                    #    cir_m.visualize_matches([match_wi_ar.circuit_arr])

                    matches_wi += match_wi_arr

                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))

        #for full_match in full_matches:
        #    cir_m.visualize_matches([full_match])
        
        #print(len(full_matches))
        self.assertEqual(16, len(full_matches))

    def test_find_interventions8(self):
        '''
            all but 2 wires removed 
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        #valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        #full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        valid_matches = []
        full_matches = []
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        
                        valid_matches = cir_m.get_full_matches(cir_m.filter_duplicates(matches_wi), 5)
                        
                        
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)

                    #for match_wi_ar in match_wi_arr:
                    #    cir_m.visualize_matches([match_wi_ar.circuit_arr])

                    matches_wi += match_wi_arr

                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))

        #for full_match in full_matches:
        #    cir_m.visualize_matches([full_match])
        
        #print(len(full_matches))
        self.assertEqual(3840, len(full_matches))

    def test_interventions_fifo(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/17_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/17_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        #valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        #full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        valid_matches = []
        full_matches = []
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_mwi_fifo(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))

                if len(full_matches) == 0:
                    if len(matches_wi) > 0:
                        valid_matches = cir_m.get_full_matches(cir_m.filter_duplicates(matches_wi), 5)
                        
                        
            if len(valid_matches) > 0:
                # find what nets are missing & try to create better matches
                matches_wi = []
                for valid_match in valid_matches:
                    missing_nets = cir_m.get_missing_nets(valid_match)
                    match_wi_arr = cir_m.find_wire_interventions(valid_match, missing_nets, temp_dir, kicad_cli, footprints_dir)

                    for match_wi_ar in match_wi_arr:
                        cir_m.visualize_matches([match_wi_ar.circuit_arr])

                    matches_wi += match_wi_arr

                filtered_matches = cir_m.filter_duplicates(matches_wi)
                full_matches = cir_m.get_full_matches(filtered_matches, len(net_arr))

        #print(len(full_matches))
        #cir_m.visualize_matches(full_matches)
        self.assertEqual(1, len(full_matches))

    def test_interventions_fifo2(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/8_test_net.net'
        mask_file_png = current_directory + '/testfiles/22_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/22_test_pcb_traces.png'
        maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        drill_file = current_directory + '/testfiles/22_test.drl'
        pcb_file = current_directory + '/testfiles/22_test.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        '''
        temp = cir_m.pcb_rgb.copy()
        for trace_ID, trace_pads in cir_m.trace_map.items():
            cv2.drawContours(temp, cir_m.trace_contours, trace_ID, (255,0,0), 2)
            for trace_pad in trace_pads:
                cv2.drawContours(temp, cir_m.mask_contours, trace_pad, (0, 255, 0), -1)

        cv2.imshow("trace map", temp)

        '''

        '''
        valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        
        if valid_match != None:
            print(valid_match.circuit_arr)
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
        else:
            print('no ideal matches - start seeing if a match with intervention is possible')

            missing_nets = []
            missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
            for missing_net_arr in missing_nets_arr:
                missing_nets.append(missing_net_arr['name'])

            #print(cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr))
            valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo(cir_m.current_best_match['match'], missing_nets, temp_dir, kicad_cli, footprints_dir)

            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                matches = cir_m.get_mwi_fifo(temp_dir, kicad_cli, footprints_dir)
                print(len(matches))
                print('done')

                if len(matches) > 0:
                    print('match with interventions found')
                    matches_arr = []
                    pcb_overlay = cir_m.get_transparent_overlay(matches[0].circuit_arr)
                    #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
                    #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
        '''

        match, n_index, n_last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
        
        print('done')

        if match != None:
            print('match with interventions found')
            print(match.nets)
            matches_arr = []
            pcb_overlay = cir_m.get_transparent_overlay(match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
            #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})

class TestPCB_Board(unittest.TestCase):
    def test_direct_cm_match(self):
        pcb_file = current_directory + '/testfiles/22_test.kicad_pcb'
        mask_file_png = current_directory + '/testfiles/22_test_pcb_mask.png'
        maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/22_test_pcb_traces.png'
        pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        drill_file = current_directory + '/testfiles/22_test.drl'
        
        
        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        
        cm = ComponentMatching()
        cm.pcb_board = pcb

        
        cm.initialize_fp_from_file(fp_file_png, fp_file)
        matches = cm.get_matches()
        matches = cm.sort_matches(matches)

        
        print(len(matches))
        for match in matches:
            img = cm.get_transparent_overlay(match)

            cv2.imshow("overlay", img)
            key = cv2.waitKeyEx(0)

        self.assertEqual(4, len(matches))

    def test_interventions_fifo(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/8_test_net.net'

        pcb_file = current_directory + '/testfiles/22_test.kicad_pcb'
        mask_file_png = current_directory + '/testfiles/22_test_pcb_mask.png'
        maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcb_file_png = current_directory + '/testfiles/22_test_pcb_traces.png'
        pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        drill_file = current_directory + '/testfiles/22_test.drl'

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)

        
        if valid_match != None:
            print(valid_match.circuit_arr)
            '''
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
            '''
        else:
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            missing_nets = []
            missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
            for missing_net_arr in missing_nets_arr:
                missing_nets.append(missing_net_arr['name'])

            #print(cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr))
            valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo(cir_m.current_best_match['match'], missing_nets, temp_dir, kicad_cli, footprints_dir)

            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                matches = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
                print(len(matches))
                print('done')

                if len(matches) > 0:
                    print('match with interventions found')
                    matches_arr = []
                    pcb_overlay = cir_m.get_transparent_overlay(matches[0].circuit_arr)
                    #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
                    #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
                
        '''
        match, n_index, n_last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
        
        print('done')

        if match != None:
            print('match with interventions found')
            print(match.nets)
            matches_arr = []
            pcb_overlay = cir_m.get_transparent_overlay(match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
            #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
        '''

    def test_interventions_fifo2(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/8_test_net.net'

        pcb_file = current_directory + '/testfiles/22_test.kicad_pcb'
        mask_file_png = current_directory + '/testfiles/22_test_pcb_mask.png'
        maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcb_file_png = current_directory + '/testfiles/22_test_pcb_traces.png'
        pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        drill_file = current_directory + '/testfiles/22_test.drl'

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        #h, w = pcb.pcb_rgb.shape[:2]
        #line_width = int(math.sqrt(h*w)/240)
        #print(line_width)

        #temp = pcb.pcb_rgb.copy()
        #cv2.circle(temp, (50,50), 25, (255, 0, 0), line_width)

        #cv2.imshow('circle', temp)
        #key = cv2.waitKeyEx(0)

        #valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        valid_match = None
        
        if valid_match != None:
            print(valid_match.circuit_arr)
            pcb_overlay, _ = cir_m.get_transparent_overlay(valid_match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            '''
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
            '''
        else:
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            #missing_nets = []
            #missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
            #for missing_net_arr in missing_nets_arr:
            #    missing_nets.append(missing_net_arr['name'])

            #print(cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr))
            #valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo(cir_m.current_best_match['match'], missing_nets, temp_dir, kicad_cli, footprints_dir)
            valid_match = None
            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                match, search_index, last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
                #print(len(matches))
                print('done')

                if match != None:
                    print('match with interventions found')
                    cir_m.visualize_matches([match.circuit_arr])
                    nm = NetMatching('', '')
                    nm.pcb_board = cir_m.pcb_board
                    #nm.visualize_net_matches(match.circuit_arr)

                    cir_m.get_cuts_overlay(match.interventions_net_arr)

                    n_search_index = search_index

                    while 1:
                        n_match, n_index, n_last_loc = cir_m.recursive_search_from_match(last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir)

                        if n_match != None:
                            print('match with interventions found recursively')
                            cir_m.visualize_matches([n_match.circuit_arr])
                            n_search_index = n_index - 1
                            last_loc = n_last_loc

                        else:
                            break

                        n_search_index += 1


                    #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
                    #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
                
        '''
        match, n_index, n_last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
        
        print('done')

        if match != None:
            print('match with interventions found')
            print(match.nets)
            matches_arr = []
            pcb_overlay = cir_m.get_transparent_overlay(match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
            #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
        '''

    def test_interventions_fifo3(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        #filename_net = current_directory + '/testfiles/8_test_net.net'


       
        #'''
        pcb_file = current_directory + '/testfiles/10_test_pcb.kicad_pcb'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        #maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcb_file_png = current_directory + '/testfiles/8_test_pcb_traces.png'
        #pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        #drill_file = current_directory + '/testfiles/22_test.drl'
        #'''

        


        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        #pcb.double_sided = False
        #pcb.initialize_via_files(mask_file_png, mask_file_png)
        #pcb.initialize_via_files(mask_file_png, pcb_file_png)
        
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        #pcb.initialize_via_files(mask_file_png, mask_file_png, maskb_file_png, maskb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        #h, w = pcb.pcb_rgb.shape[:2]
        #line_width = int(math.sqrt(h*w)/240)
        #print(line_width)

        #temp = pcb.pcb_rgb.copy()
        #cv2.circle(temp, (50,50), 25, (255, 0, 0), line_width)

        #cv2.imshow('circle', temp)
        #key = cv2.waitKeyEx(0)

        #valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        valid_match = None
        
        if valid_match != None:
           
            print(valid_match.circuit_arr)
            pcb_overlay, _ = cir_m.get_transparent_overlay(valid_match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            '''
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
            '''
        else:
            print('no valid matches found without interventions')
            cv2.imshow("NO INITIAL MATCHES", pcb.pcb_rgb)
            key = cv2.waitKeyEx(0)
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            valid_match = None
            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                match, search_index, last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
                #print(len(matches))
                print('done')

                if match != None:
                    print('match with interventions found')
                    print(last_loc[0])

                    for loc in last_loc:
                        print(loc['fxn'])

                    cir_m.visualize_matches([match.circuit_arr])
                    nm = NetMatching('', '')
                    nm.pcb_board = cir_m.pcb_board
                    nm.visualize_net_matches(match.circuit_arr)

                    cuts = cir_m.get_cuts_overlay(match.interventions_net_arr)

                    cv2.imshow('cuts', cuts)
                    #key = cv2.waitKeyEx(0)

                    n_search_index = search_index
                    print(search_index)

                    filtered_matches = [match]
                    #print(match.interventions_net_arr)


                    while False:
                        print('start while')
                        print(n_search_index)
                        n_match, n_index, n_last_loc = cir_m.recursive_search_from_match(last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir)

                        if n_match != None:
                            print('match with interventions found recursively')
                            print(len(n_last_loc))
                            print(n_last_loc[-1])
                            print(n_match)
                            print(n_index)

                            cir_m.visualize_matches([n_match.circuit_arr], wait=False)

                            print(n_match.nets)

                            print('filtered')
                            print(len(filtered_matches))
                            filtered = cir_m.filter_duplicates(filtered_matches + [n_match.copy()])
                            if len(filtered) == len(filtered_matches):
                                print('was a duplicate')
                                print(len(filtered_matches))

                            elif len(filtered) < len(filtered_matches):
                                print('decrease')
                            else:
                                print('different match found')


                                filtered_matches = filtered.copy()

                            print(len(filtered_matches))

                            cir_m.get_cuts_overlay(n_match.interventions_net_arr)
                            #key = cv2.waitKeyEx(0)
                            n_search_index = n_index -1 
                            last_loc = n_last_loc

                        else:
                            break

                        n_search_index += 1


                    min_interventions = 5000
                    min_match = None

                    for filtered_match in filtered_matches:
                        if len(filtered_match.interventions_net_arr) < min_interventions:
                            min_interventions = len(filtered_match.interventions_net_arr)
                            min_match = filtered_match
                    print('min match')
                    nm.visualize_net_matches(min_match.circuit_arr)

                
      

    def test_interventions_fifo4(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        #pcb.double_sided = False
        #pcb.initialize_via_files(mask_file_png, pcb_file_png)
        
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb


        valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        #valid_match = None
        
        if valid_match != None:
            print(valid_match.circuit_arr)
            pcb_overlay, _ = cir_m.get_transparent_overlay(valid_match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            key = cv2.waitKeyEx(0)
            '''
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
            '''
        else:
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            missing_nets = []
            
            valid_match = None
            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                match, search_index, last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
                #print(len(matches))
                print('done')

                if match != None:
                    print('match with interventions found')
                    print(last_loc[0])

                    for loc in last_loc:
                        print(loc['fxn'])

                    cir_m.visualize_matches([match.circuit_arr])
                    nm = NetMatching('', '')
                    nm.pcb_board = cir_m.pcb_board
                    #nm.visualize_net_matches(match.circuit_arr)

                    cir_m.get_cuts_overlay(match.interventions_net_arr)

                    n_search_index = search_index

                    filtered_matches = [match]
                    #print(match.interventions_net_arr)


                    while 1:
                        print('start while')
                        print(n_search_index)
                        n_match, n_index, n_last_loc = cir_m.recursive_search_from_match(last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir)

                        if n_match != None:
                            print('match with interventions found recursively')
                            #cir_m.visualize_matches([n_match.circuit_arr])

                            print(n_match.nets)

                            print('filtered')
                            print(len(filtered_matches))
                            filtered = cir_m.filter_duplicates(filtered_matches + [n_match.copy()])
                            if len(filtered) == len(filtered_matches):
                                print('was a duplicate')
                                #for filtered_match in filtered_matches:
                                #    print(filtered_match.interventions_net_arr)
                                #    print('ppp')
                                print(len(filtered_matches))

                            elif len(filtered) < len(filtered_matches):
                                print('decrease?')
                                #print(n_match.interventions_net_arr)
                                print('--')
                            else:
                                print('different match found')

                                filtered_matches = filtered.copy()

                            print(len(filtered_matches))

                            cir_m.get_cuts_overlay(n_match.interventions_net_arr)
                            #key = cv2.waitKeyEx(0)
                            n_search_index = n_index -1 
                            last_loc = n_last_loc

                        else:
                            break

                        n_search_index += 1

                
        
        '''

    def test_interventions_fifo5(self):
        '''
            Use a FIFO strategy to find matches quickly
        '''
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        #filename_net = current_directory + '/testfiles/8_test_net.net'
        

        
        '''
        pcb_file = current_directory + '/testfiles/10_test_pcb.kicad_pcb'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        #maskb_file_png = current_directory + '/testfiles/22_test_pcb_mask_back.png'
        pcb_file_png = current_directory + '/testfiles/8_test_pcb_traces.png'
        #pcbb_file_png = current_directory + '/testfiles/22_test_pcb_traces_back.png'
        #drill_file = current_directory + '/testfiles/22_test.drl'
        
        
        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        #pcb.double_sided = False
        #pcb.initialize_via_files(mask_file_png, pcb_file_png)
        
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        #pcb.initialize_via_files(mask_file_png, mask_file_png, maskb_file_png, maskb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

       

        #valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)
        valid_match = None
        
        if valid_match != None:
           
            print(valid_match.circuit_arr)
            pcb_overlay, _ = cir_m.get_transparent_overlay(valid_match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            #key = cv2.waitKeyEx(0)
            '''
            full_matches = cir_m.get_full_matches([valid_match], 2)

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    pcb_overlay = cir_m.get_transparent_overlay(match)
                    matches_arr.append({'match': match, 'pcb view': pcb_overlay})
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
            '''
        else:
            print('no valid matches found without interventions')
            cv2.imshow("NO INITIAL MATCHES2", pcb.pcb_rgb)
            key = cv2.waitKeyEx(0)
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            valid_match = None
            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                match, search_index, last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)
                #print(len(matches))
                print('done')

                if match != None:
                    print('match with interventions found')
                    print(last_loc[0])

                    for loc in last_loc:
                        print(loc['fxn'])

                    print(last_loc)

                    print(len(match.interventions_net_arr))
                    print(match.get_interventions_count())

                    #cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb2best_match.json', [match.circuit_arr])

                    #for intervention in match.interventions_net_arr:
                    #    if 'add wire' in intervention.keys():


                    #cir_m.visualize_matches([match.circuit_arr])
                    nm = NetMatching('', '')
                    nm.pcb_board = cir_m.pcb_board
                    #nm.visualize_net_matches(match.circuit_arr)

                    print(match.interventions_net_arr)
                    cir_m.get_cuts_overlay(match.interventions_net_arr)


                    n_search_index = search_index
                    

                    filtered_matches = [match]
                    


                    while 1:
                        print('start while')
                        print(n_search_index)
                        n_match, n_index, n_last_loc = cir_m.recursive_search_from_match(last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir)

                        if n_match != None:
                            print('match with interventions found recursively')
                            print(len(n_last_loc))
                            print(n_last_loc[-1])

                            for loc in n_last_loc:
                                print(loc['fxn'])

                            
                            print(n_match.nets)

                            
                            filtered = cir_m.filter_duplicates(filtered_matches + [n_match.copy()])
                            if len(filtered) == len(filtered_matches):
                                print('was a duplicate')
                               
                                print(len(filtered_matches))

                            elif len(filtered) < len(filtered_matches):
                                print('decrease?')
                                #print(n_match.interventions_net_arr)
                                print('--')
                                
                            else:
                                print('different match found')
                                


                                filtered_matches = filtered.copy()

                            print(len(filtered_matches))

                            cir_m.get_cuts_overlay(n_match.interventions_net_arr)
                            #key = cv2.waitKeyEx(0)

                            n_search_index = n_index -1 
                            last_loc = n_last_loc

                        else:
                            break

                        n_search_index += 1


                    best_match = match
                    best_interventions = match.get_interventions_count()

                    for f_match in filtered_matches:
                        

                        int_count = f_match.get_interventions_count()

                        if int_count < best_interventions:
                            best_match = f_match
                            best_interventions = int_count


                    best_match.get_interventions_count()

                    cir_m.visualize_matches([best_match.circuit_arr])

                    cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb2best_match.json', [best_match.circuit_arr])


                    #matches_arr.append({'match': matches[0].circuit_arr, 'pcb view': pcb_overlay})
                    #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
                


    def test_interventions_loaded(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = ''




        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        pcb = PCB_Board(pcb_file)
        
        pcb.initialize_via_files(mask_file_png, pcb_file_png, maskb_file_png, pcbb_file_png, drill_file)
        
        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb


        '''
        #to generate components
        cir_m.fill_cm_data(temp_dir, kicad_cli, footprints_dir)
        cir_m.generate_components_file(current_directory + '/testfiles/test_eval_1components.json')
        quit()
        '''

        cir_m.cm_dict, cir_m.cm_data = cir_m.load_component_matches_from_file(current_directory + '/testfiles/test_eval_1components.json')

        #'''
        #valid_match, n_index, last_loc = cir_m.get_matches_fifo(temp_dir, kicad_cli, footprints_dir)

        
        valid_match = None
        
        if valid_match != None:
           
            print(valid_match.circuit_arr)
            pcb_overlay, _ = cir_m.get_transparent_overlay(valid_match.circuit_arr)
            cv2.imshow('overlay', pcb_overlay)
            
        else:
            print('no valid matches found without interventions')
            cv2.imshow("NO INITIAL MATCHES2", pcb.pcb_rgb)
            #key = cv2.waitKeyEx(0)
            print('no ideal matches - start seeing if a match with intervention is possible')
            ##missing_nets = []
            #missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
            #for missing_net_arr in missing_nets_arr:
            #    missing_nets.append(missing_net_arr['name'])

            
            #valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo(cir_m.current_best_match['match'], missing_nets, temp_dir, kicad_cli, footprints_dir)
            valid_match = None
            if valid_match != None:

                cir_m.visualize_matches([valid_match.circuit_arr])
            else:
                print('searching for fifo')
                
                match, search_index, last_loc = cir_m.get_mwi_fifo2(temp_dir, kicad_cli, footprints_dir)

                if match != None:
                    print('match with interventions found')
                    print(last_loc[0])


                    for loc in last_loc:
                        print(loc['fxn'])


                    print(match.interventions_net_arr)
                    print(match.get_interventions_count())


                    cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb3match1.json', [match.copy().circuit_arr])

                    cir_m.get_cuts_overlay(match.interventions_net_arr)


                    n_search_index = search_index


                    filtered_matches = [match]
                    


                    while 1:
                        print('start while')
                        print(n_search_index)
                        n_match, n_index, n_last_loc = cir_m.recursive_search_from_match(last_loc, n_search_index, temp_dir, kicad_cli, footprints_dir)

                        if n_match != None:
                            print('match with interventions found recursively')
                            
                            for loc in n_last_loc:
                                print(loc['fxn'])

                            

                            #cir_m.visualize_matches([n_match.circuit_arr])

                            print(n_match.nets)

                            print('filtered')
                            print(len(filtered_matches))
                            filtered = cir_m.filter_duplicates(filtered_matches + [n_match.copy()])
                            if len(filtered) == len(filtered_matches):
                                print('was a duplicate')
                                cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb3match2.json', [n_match.copy().circuit_arr])
                                
                                print(len(filtered_matches))

                            elif len(filtered) < len(filtered_matches):
                                print('decrease?')
                            else:
                                print('different match found')
                                
                                for i,j in n_match.ref_dict.items():
                                    print(i)
                                    print(j.pad_IDs)
                                if len(filtered_matches) == 399:
                                    key = cv2.waitKeyEx(0)
                                cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb3match_last.json', [n_match.copy().circuit_arr])
                               

                                filtered_matches = filtered.copy()

                            print(len(filtered_matches))

                            cir_m.get_cuts_overlay(n_match.interventions_net_arr)

                            n_search_index = n_index -1 
                            last_loc = n_last_loc

                        else:
                            break

                        n_search_index += 1


                    best_match = match
                    best_interventions = match.get_interventions_count()

                    for f_match in filtered_matches:
                        #print('------')
                        #print(f_match.get_interventions_count())
                        #print('--------')

                        int_count = f_match.get_interventions_count()

                        if int_count < best_interventions:
                            best_match = f_match
                            best_interventions = int_count


                    best_match.get_interventions_count()

                    print(len(filtered_matches))

                    key = cv2.waitKeyEx(0)

                    cir_m.visualize_matches([best_match.circuit_arr])

                    cir_m.save_matches(current_directory + '/testfiles/test_save_pcb1pcb2best_match.json', [best_match.circuit_arr])

                    print(best_match.ref_dict.keys())

                    for net in best_match.circuit_arr:
                        print(net['net'])

                    
        



class TestSaveLoad(unittest.TestCase):

    def test_save(self):
        mask_file_png = current_directory + '/testfiles/0_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/0_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/0_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)
 
        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.get_matches()

        self.assertEqual(2, len(matches))

        #for match in matches:
        #    match.visualize_match('component test', True, pcb.pcb_rgb, match.coordinates)

        # TO DO: save matches

        cm.save_matches(current_directory + '/testfiles/test_save.json', matches)

    def test_load(self):
        mask_file_png = current_directory + '/testfiles/0_test_pcb_mask.png'
        fp_file_png = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.png'
        fp_file = current_directory + '/testfiles/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'
        pcb_file_png = current_directory + '/testfiles/0_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/0_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        cm = ComponentMatching()
        cm.pcb_board = pcb
        cm.initialize_fp_from_file(fp_file_png, fp_file)

        matches = cm.load_matches(current_directory + '/testfiles/test_save.json', 'test2')

        for match in matches:
            match.visualize_match('component test', True, pcb.pcb_rgb, match.coordinates)

    def test_save_circuit_match(self):
        print('test save load')

        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        cir_m.visualize_matches(valid_matches)

        #self.assertEqual(1, len(full_matches))

        cv2.imshow("test", pcb.pcb_rgb)

        cir_m.save_matches(current_directory + '/testfiles/test_save_circuit.json', full_matches)


    def test_load_circuit_match(self):
        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/3_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/3_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        cv2.imshow("test", pcb.pcb_rgb)

        matches = cir_m.load_matches(current_directory + '/testfiles/test_save_circuit.json', 'test2')

        cir_m.visualize_matches(matches)

    def test_save_interventions(self):

        temp_dir = parent_directory + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        filename_net = current_directory + '/testfiles/1_test_net.net'
        mask_file_png = current_directory + '/testfiles/3_test_pcb_mask.png'
        pcb_file_png = current_directory + '/testfiles/8_test_pcb_traces.png'
        pcb_file = current_directory + '/testfiles/6_test_pcb.kicad_pcb'

        pcb = PCB_Board(pcb_file)
        pcb.initialize_via_files(mask_file_png, pcb_file_png)

        net_arr = get_connections(filename_net)
        sorted_refs, footprint_dict = get_ordered_components_list(filename_net)

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = pcb

        cv2.imshow("test", pcb.pcb_rgb)

        '''
        
        valid_matches = cir_m.run_cm_via_traces(temp_dir, kicad_cli, footprints_dir)
        full_matches = cir_m.get_full_matches(valid_matches, len(net_arr))
        
        if len(full_matches) == 0:
            if len(valid_matches) == 0:
                matches_wi = cir_m.get_matches_with_interventions(temp_dir, kicad_cli, footprints_dir)
                full_matches = cir_m.get_full_matches(matches_wi, len(net_arr))
                #cir_m.visualize_matches(full_matches)

        cir_m.save_matches(current_directory + '/testfiles/test_save_interventions.json', full_matches)
        
        #self.assertEqual(1, len(full_matches))
        '''

        matches = cir_m.load_matches(current_directory + '/testfiles/test_save_interventions.json', 'test2')

        cir_m.visualize_matches(matches)






if __name__ == '__main__':
    unittest.main()
