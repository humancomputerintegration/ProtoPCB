
import tkinter as tk
from tkinter import *
from tkinter import PhotoImage, Button, Entry, Canvas, filedialog
from tkinter.ttk import Style
from pathlib import Path

from PIL import Image
from PIL import ImageTk

from sch_reader import get_starting_symbol, get_connections, get_ordered_components_list, get_symbol
from svg_edit import svg_to_png_gen, gen_footprint_PNG, gen_sch_PNG

from ComponentMatch import *
from CircuitMatch import CircuitMatching
from PCB_utils import PCB_Board

import subprocess
import threading
import queue

import os

import cv2


class ProtoPCBApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        #self = tk()
        self.title("ProtoPCB")
        self._frame = None
        self.switch_frame(StartPage2)
        #self.switch_frame(VisualizationPage)
        self.session_data = {}
        self.progress_status = StringVar()
        self.queue = queue.Queue()
        self.all_files_generated = threading.Condition()

    
    def switch_frame(self, frame_class):
        """Destroys current frame and replaces it with a new one."""
        new_frame = frame_class(self)
        if self._frame is not None:

            for widgets in self._frame.winfo_children():
                
                if isinstance(widgets, Canvas):
                    widgets.delete("all")
                widgets.destroy()
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()
    
    def session_values(self, dict):
        for k,v in dict.items():
            self.session_data[k] = v

    def generateFootprintimg(self, footprint, ref, queue):
        '''
            runs thread to create image of footprint
        '''

        output = os.getcwd() + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

        footprint_arr = footprint.split(":")
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        
        fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
        self.fp_parent_file = fp_parent_file
        self.footprint = footprint_arr[1]
        
        sp_args = [kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", output, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"]
        #self.queue = queue.Queue()
        KiCad_CLI_Thread(queue, sp_args).start()
        self.fp_img_file = output + "/" + footprint_arr[1] + ".png"
        self.component_name = get_symbol(self.sch_file, ref)
        
        
        symbols_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/"
        symbol_arr = self.component_name.split(':')

        
        sp_args = [kicad_cli, "sym", "export", "svg", symbols_dir + symbol_arr[0] + ".kicad_sym", "-o", output, "--symbol", symbol_arr[1]]
        KiCad_CLI_Thread(queue, sp_args).start()
        self.sym_img_file = output + "/" + symbol_arr[1] + ".png"
        

    def generatePCBimg(self, file, queue, fb=False):
        output = os.getcwd() + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        
        sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/mask.svg", "--layers", "F.Mask", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"]
        
        KiCad_CLI_Thread(queue, sp_args).start()
        

        if fb:
            sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/mask_back.svg", "--layers", "B.Mask", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"]
            #self.queue = queue.Queue()
            KiCad_CLI_Thread(queue, sp_args).start()

        ## then traces too
        
        sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/traces.svg", "--layers", "F.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"]
        
        KiCad_CLI_Thread(queue, sp_args).start()
        
        self.fb = fb

        if fb:
            sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/traces_back.svg", "--layers", "B.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"]
            KiCad_CLI_Thread(queue, sp_args).start()

            #also generate drill file
            sp_args = [kicad_cli, "pcb", "export", "drill", file, "-o", output + "/"]
            KiCad_CLI_Thread(queue, sp_args).start()



        ## board image for visualizing 
        condition = threading.Condition()
        sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/board.svg", "--layers", "F.Cu,F.Mask,F.Silkscreen,F.Courtyard",  "--page-size-mode", "2", "--exclude-drawing-sheet"]
        
        KiCad_CLI_Thread(queue, sp_args).start()

        if fb:
            sp_args = [kicad_cli, "pcb", "export", "svg", file, "-o", output + "/board_back.svg", "--layers", "B.Cu,B.Mask,B.Silkscreen,B.Courtyard",  "--page-size-mode", "2", "--exclude-drawing-sheet"]
        
            KiCad_CLI_Thread(queue, sp_args).start()

    def process_queue(self):
        try:
            msg = self.queue.get_nowait()
            # Show result of the task if needed
            if isinstance(msg, str):
                if msg == 'board images':
                    self.progress_status.set('Generating board images...')
                    self.after(100, self.process_queue)
                elif msg == 'board images complete - component':
                    self.progress_status.set('Retrieving component data...')
                    self.after(100, self.process_queue)
                elif msg == 'board images complete - circuit':
                    self.progress_status.set('Retrieving net list data...')
                    self.after(100, self.process_queue)
                elif msg == 'running component matching':
                    self.progress_status.set(f'Running Component Matching on {self.footprint}...')
                    self.after(100, self.process_queue)
                elif msg == 'running circuit matching':
                    self.progress_status.set(f'Running Circuit Matching ...')
                    self.after(100, self.process_queue)
                elif msg == 'file generated':
                    self.files_needed -= 1
                    if self.files_needed == 0:
                        self.all_files_generated.notify()
                        self.all_files_generated.release()
                    self.after(100, self.process_queue)
            elif isinstance(msg, dict):
                if msg['type'] == 'Component Matches':
                    self.temp_img = msg['matches'][0]['pcb view']
                    self.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
                    self.matches = msg['matches']
                    self.switch_frame(ComponentVisPage)
                    self._frame.update(self)
                if msg['type'] == 'Circuit Matches':
                    if isinstance(msg['matches'][0]['pcb view'], dict):
                        self.temp_img = msg['matches'][0]['pcb view']['front']
                        self.temp_img_back = msg['matches'][0]['pcb view']['back']
                        self.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
                        self.board_img_back = cv2.imread(os.getcwd() + "/temp/board_back.png")
                    else:
                        self.temp_img = msg['matches'][0]['pcb view']
                        self.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
                    self.current_match = msg['matches'][0]['match']
                    self.matches = msg['matches']
                    self.switch_frame(VidCircuitDraft)
                    self._frame.update(self)
                if msg['type'] == 'Best Current Match':
                    match = msg['match']
                    self.progress_status.set(f'Current best match has {len(match.nets)} nets and is missing {len(msg["net_arr"]) - len(match.nets)}')
                    self.best_match_btn.place(
                        x=10,
                        y=240,
                        width=200.0,
                        height=40.0
                    )
                    self.current_best_match = msg
                    
                    ## TO IMPLEMENT: if viewing a current best match and new one appears, update view?
                    self.after(100, self.process_queue)
                if msg['type'] == 'get_ordered_components_list':
                    self.refs_sorted = msg['refs_sorted']
                    self.footprint_dict = msg['footprint_dict']
                    self.switch_frame(ComponentSelectorPage)
        except queue.Empty:
            self.after(100, self.process_queue)

    def wait_for_files(self, files_needed):
        self.files_needed = files_needed
        print(self.files_needed)

        self.all_files_generated.acquire()
        print('wait for files lock')
        self.after(100, self.process_queue)



    def runComponentMatching(self, footprint, ref):
        
        output = os.getcwd() + "/temp"

        pcb = PCB_Board(self.pcb_file)

        
        self.all_files_generated.acquire()
        
        self.queue.put_nowait('board images')
        self.generatePCBimg(self.pcb_file, self.queue, fb=pcb.double_sided)
        self.generateFootprintimg(footprint, ref, self.queue)
        self.after(100, self.process_queue)

        temp_str = self.pcb_file.split('/')[-1]
        temp_str_arr = temp_str.split('.')

        board_name_str = ''
        for t_str in temp_str_arr[:-1]:
            if board_name_str != '':
                board_name_str = board_name_str + '.' + t_str
            else:
                board_name_str = t_str
        
        self.ref = ref

        cm = ComponentMatching()
        if pcb.double_sided:
            #0- mask
            #1- fp png
            #2 - fp file
            #3 - traces
            #4 - mask back
            #5 - mask front
            #6 - drill
            self.files_needed = 6
            cm_init_files = [output + "/mask.png", output + "/" + self.footprint + ".png", self.fp_parent_file + "/" + self.footprint + ".kicad_mod", output + "/traces.png", output + "/mask_back.png", output + "/traces_back.png", output + "/" + board_name_str + ".drl"]
        else:
            self.files_needed = 4
            cm_init_files = [output + "/mask.png", output + "/" + self.footprint + ".png", self.fp_parent_file + "/" + self.footprint + ".kicad_mod", output + "/traces.png"]
        
        #self.queue = queue.Queue()
        ComponentMatching_Thread(self.queue, cm, pcb, cm_init_files, self.all_files_generated).start()
        self.after(100, self.process_queue)
    
    def runCircuitMatching(self, sch_file, pcb_file):
        output = os.getcwd() + "/temp"
        
        self.pcb_file = pcb_file.split('/')[-1]
        self.sch_file = sch_file.split('/')[-1]

        #pcb_mask_generated = threading.Condition()
        #pcb_traces_generated = threading.Condition()
        #net_file_generated = threading.Condition()
        self.all_files_generated.acquire()

        self.pcb_file = pcb_file

        pcb = PCB_Board(self.pcb_file)
        #pcb.double_sided = True
        self.queue.put_nowait('board images')
        self.generatePCBimg(self.pcb_file, self.queue, fb=pcb.double_sided)
        self.generateNetList(sch_file[15:], self.queue)
        self.after(100, self.process_queue)

        if pcb.double_sided:
            self.files_needed = 7
        else:
            self.files_needed = 4

        CircuitMatching_Thread(pcb, self.queue, self.all_files_generated).start()


        self.after(100, self.process_queue)

    def generateNetList(self, sch_file, queue):
        
        output = os.getcwd() + "/temp"
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        
        sp_args = [kicad_cli, "sch", "export", "netlist", sch_file, "-o", output + "/sch.net"]

        KiCad_CLI_Thread(queue, sp_args).start()

        ## also gen png of schematic
        sp_args = [kicad_cli, "sch", "export", "svg", sch_file, "-o", output, "--exclude-drawing-sheet", "--no-background-color"]

        KiCad_CLI_Thread(queue, sp_args).start()

        temp_str = sch_file.split('/')[-1]
        temp_str_arr = temp_str.split('.')

        sch_file_name = ''
        for t_str in temp_str_arr[:-1]:
            if sch_file_name != '':
                sch_file_name = sch_file_name + '.' + t_str
            else:
                sch_file_name = t_str

        self.sch_img_file = output + "/" + sch_file_name + ".png"

    def get_components(self):


        output = os.getcwd() + "/temp"

        net_file = output + "/sch.net"

        Read_Files_Thread(self.queue, self.all_files_generated, 'get_ordered_components_list', net_file).start()

        




class KiCad_CLI_Thread(threading.Thread):
    def __init__(self, queue, sp_args):
        super().__init__()
        self.queue = queue
        self.sp_args = sp_args
    def run(self):
        subprocess.run(self.sp_args)

        if self.sp_args[1] == 'fp' and self.sp_args[2] == 'export' and self.sp_args[3] == 'svg':
            try:
                gen_footprint_PNG(self.sp_args[6] + "/" + self.sp_args[8] + ".svg")
                self.queue.put_nowait('file generated')
            except:
                self.sp_args[4] = ''
                subprocess.run(self.sp_args)
                gen_footprint_PNG(self.sp_args[6] + "/" + self.sp_args[8] + ".svg")
                self.queue.put_nowait('file generated')

        if self.sp_args[1] == 'pcb' and self.sp_args[2] == 'export' and self.sp_args[3] == 'svg':
            if len(self.sp_args[8]) > 8: 
                svg_to_png_gen(self.sp_args[6], background_color="black")
            else:
                svg_to_png_gen(self.sp_args[6])
                self.queue.put_nowait('file generated')
        elif self.sp_args[1] == 'pcb' and self.sp_args[2] == 'export' and self.sp_args[3] == 'drill':
            self.queue.put_nowait('file generated')

        if self.sp_args[1] == 'sym':
            #print('gen footprint images skipped')
            try:
                gen_sch_PNG(self.sp_args[6] + "/" + self.sp_args[-1] + ".svg")
            except:
                #sp_args[6]
                self.sp_args[4] = ''
                subprocess.run(self.sp_args)
                gen_sch_PNG(self.sp_args[6] + "/" + self.sp_args[-1] + ".svg")
                self.queue.put_nowait('file generated')

        if self.sp_args[1] == 'sch':
            if self.sp_args[3] == "svg":
                #name = self.sp_args[4].split('/')[-1].split('.')[0]

                temp_str = self.sp_args[4].split('/')[-1]
                temp_str_arr = temp_str.split('.')

                name = ''
                for t_str in temp_str_arr[:-1]:
                    if name != '':
                        name = name + '.' + t_str
                    else:
                        name = t_str

                gen_sch_PNG(self.sp_args[6] + "/" + name + ".svg")
                self.queue.put_nowait('file generated')
            if self.sp_args[3] == 'netlist':
                self.queue.put_nowait('file generated')

class ComponentMatching_Thread(threading.Thread):
    def __init__(self, queue, cm, pcb, cm_init_files, all_files_generated):
        super().__init__()
        self.queue = queue
        self.cm = cm
        self.pcb = pcb
        self.cm_init_files = cm_init_files
        self.all_files_generated = all_files_generated
        
    def run(self):
        self.all_files_generated.acquire()

        self.queue.put_nowait('running component matching')

        self.cm.initialize_fp_from_file(self.cm_init_files[1], self.cm_init_files[2])
        
        self.cm.pcb_board = self.pcb

        if len(self.cm_init_files) == 4:
            self.pcb.initialize_via_files(self.cm_init_files[0], self.cm_init_files[3])
        else:
            self.pcb.initialize_via_files(self.cm_init_files[0], self.cm_init_files[3], self.cm_init_files[4], self.cm_init_files[5], self.cm_init_files[6])
        
        matches = self.cm.get_matches()
        
        matches = self.cm.sort_matches(matches)
        

        self.queue.put_nowait('generating images of matches')
        print(f'generating images of {len(matches)} matches')

        if len(matches) > 0:
            matches_arr = []
            for match in matches:
                pcb_overlay = self.cm.get_transparent_overlay(match)
                matches_arr.append({'match': match, 'pcb view': pcb_overlay})
        self.queue.put_nowait({'type': 'Component Matches', 'matches': matches_arr})
        self.all_files_generated.release()

class CircuitMatching_Thread(threading.Thread):
    def __init__(self, pcb, queue, all_files_generated):
        super().__init__()
        self.queue = queue
        self.pcb = pcb
        self.all_files_generated = all_files_generated
        
    def run(self):
        output = os.getcwd() + "/temp"
        self.all_files_generated.acquire()
        #self.pcb_mask_generated.wait()
        #self.pcb_traces_generated.acquire()
        self.queue.put_nowait('board images complete - circuit')
        #self.pcb_traces_generated.wait()
        #self.net_file_generated.acquire()

        self.queue.put_nowait('processing net list')

        net_arr = get_connections(output + '/' + 'sch.net')
        sorted_refs, footprint_dict = get_ordered_components_list(output + '/' + 'sch.net')

        self.queue.put_nowait('running circuit matching')

        temp_str = self.pcb.pcb_file.split('/')[-1]
        temp_str_arr = temp_str.split('.')

        drill_file_name = ''
        for t_str in temp_str_arr[:-1]:
            if drill_file_name != '':
                drill_file_name = drill_file_name + '.' + t_str
            else:
                drill_file_name = t_str

        #drill_file_name = self.pcb.pcb_file.split('/')[-1].split('.')[0]
        self.pcb.initialize_via_files(output + '/' + 'mask.png', output + '/' + 'traces.png', output + '/' + 'mask_back.png', output + '/' + 'traces_back.png', output + '/' + drill_file_name + '.drl')

        cir_m = CircuitMatching(sorted_refs, footprint_dict, net_arr)
        cir_m.pcb_board = self.pcb

        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"

        BestCurrentMatch_Thread(self.queue, cir_m).start()

        valid_match, n_index, last_loc = cir_m.get_matches_fifo(output, kicad_cli, footprints_dir)
        
        if valid_match != None:
            full_matches = cir_m.get_full_matches([valid_match], len(net_arr))

            if len(full_matches) > 0:
                matches_arr = []
                for match in full_matches:
                    if self.pcb.double_sided:
                        pcb_overlay, pcb_overlay_b = cir_m.get_transparent_overlay(match)
                        nets_view_dict = cir_m.get_nets_transparent_overlay(match)
                        matches_arr.append({'match': match, 'pcb view': {'front': pcb_overlay, 'back': pcb_overlay_b}, 'nets view dict': nets_view_dict})
                    
                    else:
                        pcb_overlay = cir_m.get_transparent_overlay(match)
                        nets_view_dict = cir_m.get_nets_transparent_overlay(match)
                        matches_arr.append({'match': match, 'pcb view': pcb_overlay, 'nets view dict': nets_view_dict})
                    
                self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                 self.queue.put_nowait('no non-intervention matches found')
                 print('zero ideal matches')
        else:
            print('no ideal matches - start seeing if a match with intervention is possible')
            
            if cir_m.current_best_match != None:
                missing_nets = []
                missing_nets_arr = cir_m.get_missing_nets(cir_m.current_best_match['match'].circuit_arr)
                for missing_net_arr in missing_nets_arr:
                    missing_nets.append(missing_net_arr['name'])
                valid_match, n_index, last_loc = cir_m.get_next_mwi_fifo_from_match(cir_m.current_best_match['match'], output, kicad_cli, footprints_dir)
            else:
                valid_match = None
            if valid_match != None:
                print('valid match was not none')
                #full_matches = cir_m.get_full_matches([valid_match], len(cir_m.net_arr))
                matches_arr = []
                pcb_overlay = cir_m.get_transparent_overlay(valid_match.circuit_arr)
                nets_view_dict = cir_m.get_nets_transparent_overlay(valid_match.circuit_arr)
                cuts_overlay, cuts_overlay_b = cir_m.get_cuts_overlay(valid_match)
                nets_view_dict['Board Cuts'] = [cuts_overlay, cuts_overlay_b]
                matches_arr.append({'match': valid_match.circuit_arr, 'pcb view': pcb_overlay, 'nets view dict': nets_view_dict})
                #self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
            else:
                print('searching for fifo')
                
                match, n_index, n_last_loc = cir_m.get_mwi_fifo2(output, kicad_cli, footprints_dir)
                cir_m.finished = True

                if match != None:
                    print('match with interventions found')
                    matches_arr = []

                    if cir_m.pcb_board.double_sided:
                        pcb_overlay, pcb_overlay_b = cir_m.get_transparent_overlay(match.circuit_arr)
                        nets_view_dict = cir_m.get_nets_transparent_overlay(match.circuit_arr)
                        cuts_overlay, cuts_overlay_b = cir_m.get_cuts_overlay(match.interventions_net_arr)
                        nets_view_dict['Board Cuts'] = [cuts_overlay, cuts_overlay_b]
                        matches_arr.append({'match': match.circuit_arr, 'pcb view': {'front': pcb_overlay, 'back': pcb_overlay_b}, 'nets view dict': nets_view_dict})
                        self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
                    else:
                        pcb_overlay = cir_m.get_transparent_overlay(match.circuit_arr)
                        nets_view_dict = cir_m.get_nets_transparent_overlay(match.circuit_arr)
                        matches_arr.append({'match': match.circuit_arr, 'pcb view': pcb_overlay, 'nets view dict': nets_view_dict})
                        self.queue.put_nowait({'type': 'Circuit Matches', 'matches': matches_arr})
                    

                    
        
        self.all_files_generated.release()
        #self.pcb_traces_generated.release()
        #self.net_file_generated.release()



class BestCurrentMatch_Thread(threading.Thread):
    def __init__(self, queue, circuit_matching):
        super().__init__()
        self.queue = queue
        self.circuit_matching = circuit_matching
        
    def run(self):

        while 1:
            time.sleep(20)

            if hasattr(self.circuit_matching, 'current_best_match'):
                if self.circuit_matching.current_best_match != None:
                    self.queue.put_nowait({'type': 'Best Current Match', 'match': self.circuit_matching.current_best_match['match'], 'net_arr': self.circuit_matching.net_arr, 'missing nets': self.circuit_matching.current_best_match['missing nets'], 'circuit_matching': self.circuit_matching})
            if hasattr(self.circuit_matching, 'finished'):
                if self.circuit_matching.finished:
                    break

class Read_Files_Thread(threading.Thread):
    def __init__(self, queue, all_files_generated, action_type, file):
        super().__init__()
        self.queue = queue
        self.all_files_generated = all_files_generated
        self.action_type = action_type
        self.file = file
        
    def run(self):
        self.all_files_generated.acquire()
        if self.action_type == 'get_ordered_components_list':
            refs_sorted, footprint_dict = get_ordered_components_list(self.file)
            self.queue.put_nowait({'type': 'get_ordered_components_list', 'refs_sorted': refs_sorted, 'footprint_dict': footprint_dict})
        self.all_files_generated.release()

class StartPage(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 600,
            width = 500,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        canvas.pack()
        canvas.create_text(
            20,
            20,
            anchor="nw",
            text="ProtoPCB",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 40 * -1)
        )
        

        canvas.pack()
        canvas.create_text(
            20,
            100,
            anchor="nw",
            text="Select PCB File from File Dialog",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 13 * -1)
        )
        
        select_pcb_btn = Button(
            text = "Select File",
            borderwidth=0,
            highlightthickness=0,
            command=self.selectPCBFile,
            relief="flat"
        )
        
        select_pcb_btn.place(
            x=20,
            y=160,
            width=100.0,
            height=40.0
        )
        self.filename = StringVar()
        self.filename.set("No file selected")
        
        label_file_selected = tk.Label(anchor = "nw",
                            textvariable = self.filename,
                            width = 100, height = 2,
                            fg = "blue", bg = "white")
        
        label_file_selected.place(x = 10, y = 120, width = 400)
        
        canvas.create_text(
            20,
            240,
            anchor="nw",
            text="Select Schematic File from File Dialog",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 13 * -1)
        )
        
        select_sch_btn = Button(
            text = "Select File",
            borderwidth=0,
            highlightthickness=0,
            command=self.selectSchFile,
            relief="flat"
        )
        
        select_sch_btn.place(
            x=20,
            y=300,
            width=100.0,
            height=40.0
        )
        
        self.filename_sch = StringVar()
        self.filename_sch.set("No file selected")
        
        label_file_sch_selected = tk.Label(anchor = "nw",
                            textvariable = self.filename_sch,
                            width = 100, height = 2,
                            fg = "blue", bg = "white")
        
        label_file_sch_selected.place(x = 10, y = 260, width = 400)
        
        analysis_btn = Button(
            text = "Run Analysis",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.runAnalysis(parent),
            relief="flat"
        )
        
        analysis_btn.place(
            x=20,
            y=440,
            width=100.0,
            height=40.0
        )
        
                                                        
    def selectPCBFile(self):
        filename = filedialog.askopenfilename(initialdir = "/",
                                              title = "Select a File",
                                              filetypes = [("kicad pcb",
                                                            "*.kicad_pcb")])
          
        # Change label contents
        #self.label_file_selected.config(text="File Opened: "+filename)
        self.filename.set("File Selected: "+filename)
        
    
    def selectSchFile(self):
        filename_sch = filedialog.askopenfilename(initialdir = "/",
                                              title = "Select a File",
                                              filetypes = [("kicad sch",
                                                            "*.kicad_sch")])

        self.filename_sch.set("File Selected: "+filename_sch)
    
    def runAnalysis(self, parent):
        name, footprint = get_starting_symbol(self.filename_sch.get()[15:])
        
        session_data = {'component name': name, 'component footprint': footprint}
        session_data['sch filename'] = self.filename_sch.get()[15:]
        session_data['pcb filename'] = self.filename.get()[15:]
        
        
        #run footprint png generation command line
        
        kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        
        footprint_arr = footprint.split(":")
        footprints_dir= "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
        
        fp_parent_file = footprints_dir + footprint_arr[0] + ".pretty"
        
        output = os.getcwd() + "/temp"
        
        complete = subprocess.run([kicad_cli, "fp", "export", "svg", fp_parent_file, "-o", output, "--fp", footprint_arr[1], "--black-and-white", "-l", "F.Cu"])
        
        print(complete)
        
        gen_footprint_PNG(output + "/" + footprint_arr[1] + ".svg")
        
        #run pcb png generation command line
        
        ## first masks only
        
        complete = subprocess.run([kicad_cli, "pcb", "export", "svg", session_data['pcb filename'], "-o", output + "/mask.svg", "--layers", "F.Paste", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
        print(complete)
        
        #complete = subprocess.run(["svgexport", output + "/mask.svg", output + "/mask.png", "4x", "svg{background:white;}"])
        svg_to_png_gen(output + "/mask.svg")
        
        ## then traces too
        
        complete = subprocess.run([kicad_cli, "pcb", "export", "svg", session_data['pcb filename'], "-o", output + "/traces.svg", "--layers", "F.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
        print(complete)
        
        #complete = subprocess.run(["svgexport", output + "/traces.svg", output + "/traces.png", "4x", "svg{background:white;}"])
        svg_to_png_gen(output + "/traces.svg")
        
        #use images to run scripts
        cm = ComponentMatching()
        cm.initialize_via_files(output + "/mask.png", output + "/" + footprint_arr[1] + ".png", fp_parent_file + "/" + footprint_arr[1] + ".kicad_mod", output + "/traces.png")
        
        matches = cm.get_matches()
        #match_map = cm.valid_single_component_match(match_map, pad_map, trace_map)
        #only use above if you want to filter to make sure there is an additional solderable pad
        #print(match_map)
        closeup_view, pcb_view = cm.get_images_of_match(matches[0], cm.pad_map, cm.trace_map)
        
        
        #save info
        session_data['footprint png'] = output + "/" + footprint_arr[1] + ".png"
        session_data['mask png'] = output + "/mask.png"
        session_data['traces png'] = output + "/traces.png"
        session_data['pcb view'] = pcb_view
        session_data['closeup view'] = closeup_view
        session_data['match map'] = matches
        parent.session_values(session_data)
        
        
        #switch UI to display both images
        parent.switch_frame(VisualizationPage)

class VisualizationPage(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 800,
            width = 1000,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        # HEADER
        
        self.match_index = -1
        self.total_matches = -1
        
        match_map = parent.session_data['match map']
        self.total_matches = len(match_map)
        
        if self.total_matches > 0:
            self.match_index = 1
        
        self.label_match_index_str = StringVar()
        self.label_match_index_str.set("Single Component Match " + str(self.match_index) + " of " + str(self.total_matches))
        
        
        label_match_index = Label(canvas, anchor = "nw",
                            textvariable = self.label_match_index_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_match_index.grid(row=1,column=1, padx = 20, pady = 5, sticky="nw")
        tk.ttk.Separator(canvas,orient=HORIZONTAL).place(x=0,y=40, relwidth=1)
        
        # FIRST COLUMN
        
        label_pcb_view = Label(canvas, anchor = "nw",
                            text="PCB view (connected pads highlighted)",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_pcb_view.grid(row=2,column=1, padx = 20, pady = 5, sticky="nw")
        
        pcb_view_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 400,
            width = 400,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        b,g,r = cv2.split(parent.session_data['pcb view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        pcb_im = Image.fromarray(img)
        new_width  = 400
        new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        pcb_view_canvas.create_image(0, 0, image=pcb_img, anchor=NW)
        pcb_view_canvas.image = pcb_img
        pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10))

        
        # SECOND COLUMN
        label_cmpnt_match_view = Label(canvas, anchor = "nw",
            text="Close-up with match footprint overlaid",
            fg = "black",
            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_cmpnt_match_view.grid(row=2,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_match_view_canvas = Canvas(
            canvas,
            bg = "#FFF4FF",
            height = 200,
            width = 200,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        b,g,r = cv2.split(parent.session_data['closeup view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        closeup_im = Image.fromarray(img)
        new_width  = 200
        new_height = int(float(new_width) * float(h) / float(w))
        
        closeup_im = closeup_im.resize((new_width, new_height))
        closeup_img = ImageTk.PhotoImage(image=closeup_im)
        
        cmpnt_match_view_canvas.create_image(0, 0, image=closeup_img, anchor=NW)
        cmpnt_match_view_canvas.image = closeup_img
        
        cmpnt_match_view_canvas.configure(height=new_height)
        
        cmpnt_match_view_canvas.grid(row=3,column=2, padx=20, pady=5, sticky="nw")
        
        cmpnt_name = StringVar()
        cmpnt_name.set("Component Name: " + parent.session_data['component name'])
        
        l_cmpnt_match_name = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_name,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_cmpnt_match_name.grid(row=4,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_fp = StringVar()
        cmpnt_fp.set("Footprint: " + parent.session_data['component footprint'])
        
        l_fp = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_fp,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_fp.grid(row=5,column=2, padx = 20, pady = 5, sticky="nw")
        
        l_num_matches = Label(canvas, anchor = "nw",
                            text="# of total matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_num_matches.grid(row=6,column=2, padx = 20, pady = 5, sticky="nw")
        
        l_ideal_matches = Label(canvas, anchor = "nw",
                            text="ideal matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_ideal_matches.grid(row=7,column=2, padx = 20, pady = 5, sticky="nw")
        
        l_mod_matches = Label(canvas, anchor = "nw",
                            text="mod required matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_mod_matches.grid(row=8,column=2, padx = 20, pady = 5, sticky="nw")
        
        canvas.pack()
        
        
        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        next_btn = Button(toolbar,
            text = "See Next Best Match",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.nextMatch(parent),
            relief="flat"
        )
        
        next_btn.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')
    
    def goBack(self, parent):
        parent.switch_frame(StartPage)
    
    def nextMatch(self):
        print('next match pressed')
        
class StudyFullCircuit(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 1500,
            width = 2000,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        # HEADER
        
        self.match_index = -1
        self.total_matches = -1
        
        match_map = []
        self.total_matches = len(match_map)
        
        if self.total_matches > 0:
            self.match_index = 1
        
        self.label_match_index_str = StringVar()
        #self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + str(self.match_index) + " of " + str(self.total_matches))
        self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + '1' + " of " + self.total_matches + "// Searching on # PCB Boards from Library")
        
        
        label_match_index = Label(canvas, anchor = "nw",
                            textvariable = self.label_match_index_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_match_index.grid(row=1,column=1, padx = 20, pady = 5, sticky="nw")
        tk.ttk.Separator(canvas,orient=HORIZONTAL).place(x=0,y=40, relwidth=1)
        
        # FIRST COLUMN
        self.label_pcb_view_str = StringVar()
        self.label_pcb_view_str.set(f"Front PCB view from {parent.pcb_file.split('/')[-1]}")
        
        label_pcb_view = Label(canvas, anchor = "nw",
                            textvariable=self.label_pcb_view_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_pcb_view.grid(row=2,column=1, padx = 20, pady = 5, sticky="nw")
        
        if parent.fb:
            dim = 900
        else:
            dim = 600
        self.pcb_view_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 600,
            width = dim,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        if parent.fb:
            temp_img = cv2.hconcat([parent.temp_img, parent.temp_img_back])
        else:
            temp_img = parent.temp_img
        b,g,r,a = cv2.split(temp_img)
        #b,g,r = cv2.split(parent.session_data['pcb view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]

        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        
        
        pcb_im = Image.fromarray(image_new)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.image_on_pcb_canvas = self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10), sticky="news")
        
        
        # SECOND COLUMN
        self.label_cmpnt_match_view_str = StringVar()
        self.label_cmpnt_match_view_str.set(f"Circuit schematic from {parent.sch_file.split('/')[-1]}")
        
        label_cmpnt_match_view = Label(canvas, anchor = "nw",
            textvariable=self.label_cmpnt_match_view_str,
            fg = "black",
            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_cmpnt_match_view.grid(row=2,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_match_view_canvas = Canvas(
            canvas,
            bg = "#FFF4FF",
            height = 200,
            width = 400,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        #temp_img2 = cv2.imread(parent.temp_img)
        temp_img2 = cv2.imread(parent.sch_img_file)
        b,g,r = cv2.split(temp_img2)
        #b,g,r = cv2.split(parent.session_data['closeup view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        closeup_im = Image.fromarray(img)
        new_width  = 400
        new_height = int(float(new_width) * float(h) / float(w))
        
        closeup_im = closeup_im.resize((new_width, new_height))
        closeup_img = ImageTk.PhotoImage(image=closeup_im)
        
        cmpnt_match_view_canvas.create_image(0, 0, image=closeup_img, anchor=NW)
        cmpnt_match_view_canvas.image = closeup_img
        
        cmpnt_match_view_canvas.configure(height=new_height)
        
        cmpnt_match_view_canvas.grid(row=3,column=2, padx=20, pady=5, sticky="nw")
        '''
        cmpnt_name = StringVar()
        #cmpnt_name.set("Component Name: " + parent.session_data['component name'])
        cmpnt_name.set("Component Name: " + 'TEMP')
        
        l_cmpnt_match_name = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_name,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_cmpnt_match_name.grid(row=4,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_fp = StringVar()
        #cmpnt_fp.set("Footprint: " + parent.session_data['component footprint'])
        cmpnt_fp.set("Footprint: " + 'footprint')
        
        l_fp = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_fp,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_fp.grid(row=5,column=2, padx = 20, pady = 5, sticky="nw")
        '''
        l_interventions = Label(canvas, anchor = "nw",
                            text="Interventions: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_interventions.grid(row=6,column=2, padx = 20, pady = 5, sticky="nw")
        
        selector_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 20,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        if self.match_index > 0:
            self.options = list(parent.matches[self.match_index - 1]['nets view dict'].keys()) + ["All Nets"]
        else:
            self.options = list(parent.matches[0]['nets view dict'].keys()) + ["All Nets"]


        selected_view = StringVar() 
        selected_view.set( "All Nets" )

        dropdown = OptionMenu( selector_canvas , selected_view, *self.options )
        dropdown.grid(row=0, column=1) 

        l_select_view = Label(selector_canvas, anchor = "nw",
                            text="Select View: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        l_select_view.grid(row=0, column = 0)

        change_view_btn = Button(selector_canvas,
            text = "Change View",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.change_view(parent, selected_view.get()),
            relief="flat"
        )
        
        change_view_btn.grid(row=0, column=3, padx=5, pady=5, sticky="nw")
        
        selector_canvas.grid(row=7,column=2, padx = 20, pady = 5, sticky="nw")
        
        '''
        l_mod_matches = Label(canvas, anchor = "nw",
                            text="mod required matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_mod_matches.grid(row=8,column=2, padx = 20, pady = 5, sticky="nw")
        '''
        
        canvas.pack()
        
        
        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        self.next_btn = Button(toolbar,
            text = "See Next Best Match",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.nextMatch(parent),
            relief="flat"
        )
        
        self.next_btn.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')
    
    def goBack(self, parent):
        parent.switch_frame(StartPage)
    
    def nextMatch(self, parent):
        if self.match_index + 1 <= len(parent.matches):
            self.match_index += 1
            parent.temp_img = parent.matches[self.match_index - 1]['pcb view']
            parent.current_match = parent.matches[self.match_index - 1]['match']

            if parent.current_match.fb == 'front':
                parent.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
            else:
                parent.board_img = cv2.imread(os.getcwd() + "/temp/board_back.png")

            self.update(parent)

        if self.match_index + 1 > len(parent.matches):
            self.next_btn.config(state=DISABLED)

    def update(self, parent):
        if self.match_index == -1:
            if len(parent.matches) > 0:
                self.match_index = 1
        self.total_matches = len(parent.matches)

        if self.match_index + 1 > len(parent.matches):
            self.next_btn.config(state=DISABLED)

        self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + str(self.match_index) + " of " + str(self.total_matches))
        
        if parent.fb:
            temp_img = cv2.hconcat([parent.temp_img, parent.temp_img_back])
            board_img = cv2.hconcat([parent.board_img, parent.board_img_back])
            dim = 900
        else:
            temp_img = parent.temp_img
            board_img = parent.board_img
            dim = 600
        b,g,r,a = cv2.split(temp_img)
        overlay_img = cv2.merge((r,g,b,a))


        b,g,r = cv2.split(board_img)
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        rgba_img = cv2.cvtColor(image_new, cv2.COLOR_RGB2RGBA)
        disp_img = cv2.addWeighted(overlay_img, 1, rgba_img, 1, 0.0)
        
        
        pcb_im = Image.fromarray(disp_img)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        #self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10))

        self.pcb_view_canvas.itemconfig(self.image_on_pcb_canvas, image=self.pcb_img)

        if self.match_index > 0:
            self.options = list(parent.matches[self.match_index - 1]['nets view dict'].keys()) + ["All Nets"]
        else:
            self.options = list(parent.matches[0]['nets view dict'].keys()) + ["All Nets"]

    def change_view(self, parent, view_str):
        if view_str == 'All Nets':

            parent.temp_img = parent.matches[self.match_index - 1]['pcb view']['front']
            if parent.fb:
                parent.temp_img_back = parent.matches[self.match_index - 1]['pcb view']['back']
        else:
            if parent.fb:
                parent.temp_img = parent.matches[self.match_index - 1]['nets view dict'][view_str][0]
                parent.temp_img_back = parent.matches[self.match_index - 1]['nets view dict'][view_str][1]
            else:
                parent.temp_img = parent.matches[self.match_index - 1]['nets view dict'][view_str]
                
        
        self.update(parent)

class ComponentVisPage(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 800,
            width = 1000,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        # HEADER
        
        self.match_index = -1
        self.total_matches = -1
        
        #match_map = parent.session_data['match map']
        match_map = []
        self.total_matches = len(match_map)
        
        if self.total_matches > 0:
            self.match_index = 1
        
        self.label_match_index_str = StringVar()
        self.label_match_index_str.set("Single Component Match " + str(self.match_index) + " of " + str(self.total_matches))
        
        
        label_match_index = Label(canvas, anchor = "nw",
                            textvariable = self.label_match_index_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_match_index.grid(row=1,column=1, padx = 20, pady = 5, sticky="nw")
        tk.ttk.Separator(canvas,orient=HORIZONTAL).place(x=0,y=40, relwidth=1)
        
        # FIRST COLUMN
        
        label_pcb_view = Label(canvas, anchor = "nw",
                            text="PCB view",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_pcb_view.grid(row=2,column=1, padx = 20, pady = 5, sticky="nw")
        
        self.pcb_view_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 600,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        b,g,r,a = cv2.split(parent.temp_img)
        overlay_img = cv2.merge((r,g,b,a))
        b,g,r = cv2.split(parent.board_img)
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        rgba_img = cv2.cvtColor(image_new, cv2.COLOR_RGB2RGBA)
        disp_img = cv2.addWeighted(rgba_img, 1, overlay_img, 1, 0.0)
        
        
        pcb_im = Image.fromarray(disp_img)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = 600
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.image_on_pcb_canvas = self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        self.pcb_view_canvas.grid(row=3,column=1, rowspan=10, padx=20, pady=(5,10))

        
        # SECOND COLUMN
        label_cmpnt_match_view = Label(canvas, anchor = "nw",
            text="Close-up with match footprint overlaid",
            fg = "black",
            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_cmpnt_match_view.grid(row=2,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_match_view_canvas = Canvas(
            canvas,
            bg = "#FFF4FF",
            height = 200,
            width = 400,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        #b,g,r = cv2.split(parent.session_data['closeup view'])
        #b,g,r,a = cv2.split(cv2.imreaparent.fp_img_file)
        #img = cv2.merge((r,g,b))
        sym_img = cv2.imread(parent.sym_img_file)
        b,g,r = cv2.split(sym_img)
        sym_img = cv2.merge((r,g,b))
        fp_img = cv2.imread(parent.fp_img_file)

        img_list = [sym_img, fp_img]

        h_min = max(img.shape[0]  
                for img in img_list) 
        
        # image resizing  
        im_list_resize = [cv2.resize(img, (int(img.shape[1] * h_min / img.shape[0]), h_min), cv2.INTER_CUBIC) for img in img_list]

        img = cv2.hconcat(im_list_resize)
        h,w = img.shape[:2]
        
        closeup_im = Image.fromarray(img)
        new_width  = 400
        new_height = int(float(new_width) * float(h) / float(w))
        
        closeup_im = closeup_im.resize((new_width, new_height))
        closeup_img = ImageTk.PhotoImage(image=closeup_im)
        
        cmpnt_match_view_canvas.create_image(0, 0, image=closeup_img, anchor=NW)
        cmpnt_match_view_canvas.image = closeup_img
        
        cmpnt_match_view_canvas.configure(height=new_height)
        
        cmpnt_match_view_canvas.grid(row=3,column=2, padx=20, pady=5, sticky="nw")
        
        cmpnt_name = StringVar()
        #cmpnt_name.set("Component Name: " + parent.session_data['component name'])
        cmpnt_name.set("Component Name: " + parent.component_name)
        
        l_cmpnt_match_name = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_name,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_cmpnt_match_name.grid(row=4,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_fp = StringVar()
        #cmpnt_fp.set("Footprint: " + parent.session_data['component footprint'])
        cmpnt_fp.set("Footprint: " + parent.footprint)
        
        l_fp = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_fp,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_fp.grid(row=5,column=2, padx = 20, pady = 0, sticky="nw")
        
        '''
        l_num_matches = Label(canvas, anchor = "nw",
                            text="# of total matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_num_matches.grid(row=6,column=2, padx = 20, pady = 5, sticky="nw")
        
        l_ideal_matches = Label(canvas, anchor = "nw",
                            text="ideal matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_ideal_matches.grid(row=7,column=2, padx = 20, pady = 5, sticky="nw")
        
        l_mod_matches = Label(canvas, anchor = "nw",
                            text="mod required matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_mod_matches.grid(row=8,column=2, padx = 20, pady = 5, sticky="nw")
        '''
        
        canvas.pack()
        
        
        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        self.next_btn = Button(toolbar,
            text = "See Next Best Match",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.nextMatch(parent),
            relief="flat"
        )
        
        self.next_btn.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')
    
    def goBack(self, parent):
        parent.switch_frame(StartPage2)
    
    def nextMatch(self, parent):
        if self.match_index + 1 <= len(parent.matches):
            self.match_index += 1
            self.label_match_index_str.set("Single Component Match " + str(self.match_index) + " of " + str(self.total_matches))
            parent.temp_img = parent.matches[self.match_index - 1]['pcb view']
            parent.current_match = parent.matches[self.match_index -1]['match']
            if parent.current_match.fb == 'front':
                parent.board_img = cv2.imread(os.getcwd() + '/temp/board.png')
            else:
                parent.board_img = cv2.imread(os.getcwd() + '/temp/board_back.png')
            self.update(parent)

        if self.match_index + 1 > len(parent.matches):
            self.next_btn.config(state=DISABLED)

    def update(self,parent):

        #self.match_index = -1
        if self.match_index == -1:
            if len(parent.matches) > 0:
                self.match_index = 1
        self.total_matches = len(parent.matches)

        self.label_match_index_str.set("Single Component Match " + str(self.match_index) + " of " + str(self.total_matches))
        #parent.update()

        b,g,r,a = cv2.split(parent.temp_img)
        overlay_img = cv2.merge((r,g,b,a))
        b,g,r = cv2.split(parent.board_img)
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        rgba_img = cv2.cvtColor(image_new, cv2.COLOR_RGB2RGBA)
        disp_img = cv2.addWeighted(rgba_img, 1, overlay_img, 1, 0.0)
        
        
        pcb_im = Image.fromarray(disp_img)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = 600
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        #self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10))

        self.pcb_view_canvas.itemconfig(self.image_on_pcb_canvas, image=self.pcb_img)
        

class StartPage2(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 540,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        canvas.pack()
        canvas.create_text(
            40,
            20,
            anchor="nw",
            text="ProtoPCB",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 40 * -1)
        )
        

        canvas.pack()
        canvas.create_text(
            40,
            100,
            anchor="nw",
            text="Select PCB File or Image from File Dialog",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 13 * -1)
        )
        
        select_pcb_btn = Button(
            text = "Select File",
            borderwidth=0,
            highlightthickness=0,
            command=self.selectPCBFile,
            relief="flat"
        )
        
        select_pcb_btn.place(
            x=40,
            y=160,
            width=100.0,
            height=40.0
        )
        self.filename = StringVar()
        self.filename.set("No file selected")

        self.filename_vid = StringVar()
        self.filename_vid.set("No file selected")
        
        label_file_selected = tk.Label(anchor = "nw",
                            textvariable = self.filename_vid,
                            width = 100, height = 2,
                            fg = "blue", bg = "white")
        
        label_file_selected.place(x = 40, y = 120, width = 400)
        
        canvas.create_text(
            40,
            240,
            anchor="nw",
            text="Select Schematic File from File Dialog",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 13 * -1)
        )
        
        select_sch_btn = Button(
            text = "Select File",
            borderwidth=0,
            highlightthickness=0,
            command=self.selectSchFile,
            relief="flat"
        )
        
        select_sch_btn.place(
            x=40,
            y=300,
            width=100.0,
            height=40.0
        )
        
        self.filename_sch = StringVar()
        self.filename_sch.set("No file selected")

        self.filename_sch_vid = StringVar()
        self.filename_sch_vid.set("No file selected")
        
        label_file_sch_selected = tk.Label(anchor = "nw",
                            textvariable = self.filename_sch_vid,
                            width = 100, height = 2,
                            fg = "blue", bg = "white")
        
        label_file_sch_selected.place(x = 40, y = 260, width = 400)


        canvas.create_text(
            40,
            410,
            anchor="nw",
            text="If no PCB is provided, ProtoPCB will run search on PCB library",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 13 * -1)
        )
        
        sel_cmpnt_btn = Button(
            text = "Select Component from Schematic",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.select_component(parent),
            relief="flat"
        )
        
        sel_cmpnt_btn.place(
            x=40,
            y=440,
            width=250.0,
            height=40.0
        )

        cir_analysis_btn = Button(
            text = "Run Circuit Match Analysis",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.runCircuitAnalysis(parent),
            relief="flat"
        )
        
        cir_analysis_btn.place(
            x=340,
            y=440,
            width=200.0,
            height=40.0
        )
              
                                                            
    def selectPCBFile(self):
        '''
        filename = filedialog.askopenfilename(initialdir = "/",
                                              title = "Select a File",
                                              filetypes = [("kicad pcb",
                                                            "*.kicad_pcb"), ("jpg", "*.jpg"), ("png", "*.png")])
        '''
        #'''
        filename = filedialog.askopenfilename(initialdir = "/",
                                              title = "Select a File or Image")
        #'''
          
        # Change label contents
        #self.label_file_selected.config(text="File Opened: "+filename)

        self.filename.set("File Selected: "+filename)

        self.filename_vid.set("File Selected: " + filename.split('/')[-1])
        
    
    def selectSchFile(self):
        filename_sch = filedialog.askopenfilename(initialdir = "/",
                                              title = "Select a File",
                                              filetypes = [("kicad sch",
                                                            "*.kicad_sch")])

        self.filename_sch.set("File Selected: "+filename_sch)
        self.filename_sch_vid.set("File Selected: " + filename_sch.split('/')[-1])
    

    def select_component(self, parent):
        parent.component_matching = True
        parent.pcb_file = self.filename.get()[15:]
        parent.sch_file = self.filename_sch.get()[15:]
        parent.switch_frame(LoadingScreen)
        
        parent.wait_for_files(2)
        
        parent.generateNetList(self.filename_sch.get()[15:], parent.queue)
        
        parent.get_components()

    def runCircuitAnalysis(self, parent):
        parent.component_matching = False
        parent.switch_frame(LoadingScreen)
        parent.runCircuitMatching(self.filename_sch.get(), self.filename.get()[15:])
        

class LoadingScreen(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 300,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        canvas.pack()
        canvas.create_text(
            10,
            10,
            anchor="nw",
            text="ProtoPCB",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 20 * -1)
        )
        

        canvas.pack()
        canvas.create_text(
            100,
            100,
            text="Loading...",
            fill="#019A07",
            font=("RobotoRoman CondensedRegular", 30 * -1)
        )

        label_status = tk.Label(anchor = "nw",
                            textvariable = parent.progress_status,
                            width = 100, height = 2,
                            fg = "green", bg = "white")
        
        label_status.place(x = 50, y = 150, width = 400)

        label_notes = tk.Label(anchor = "nw",
                            text = "",
                            width = 200, height = 2,
                            fg = "green", bg = "white")
        
        label_notes.place(x = 50, y = 200, width = 400)

        if parent.component_matching:
            label_notes.place_forget()

        parent.best_match_btn = Button(
            text = "Checkout Current Best Match",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.checkout_current_best_match(parent),
            relief="flat"
        )
        
        parent.best_match_btn.place(
            x=10,
            y=240,
            width=200.0,
            height=40.0
        )

        parent.best_match_btn.place_forget()

    def checkout_current_best_match(self, parent):
        if parent.fb:
            parent.temp_img, parent.temp_img_back = parent.current_best_match['circuit_matching'].get_transparent_overlay(parent.current_best_match['match'].circuit_arr)
            parent.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
            parent.board_img_back = cv2.imread(os.getcwd() + "/temp/board_back.png")
        else:
            parent.temp_img = parent.current_best_match['circuit_matching'].get_transparent_overlay(parent.current_best_match['match'].circuit_arr)
            parent.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
        
        parent.switch_frame(BestCurrentMatch)
        parent._frame.update(parent)

class ComponentSelectorPage(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 500,
            width = 800,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )


        label_app_title = Label(canvas, anchor = "nw",
                            text = "ProtoPCB",
                            fg = "#019A07",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_app_title.grid(row=0,column=0, padx = 20, pady = 5, sticky="nw")


        sch_canvas = Canvas(
            canvas,
            bg = "white",
            height = 300,
            width = 400,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        label_sch = Label(canvas, anchor = "nw",
                            text = "Schematic uploaded",
                            fg = "#019A07",
                            bg = "white", font=("RobotoRoman CondensedRegular", 14))
        
        label_sch.grid(row=1,column=0, padx = 20, pady = 5, sticky="nw")



        # Following line overlays transparent rectangle 
        # over the image 
        disp_img = cv2.imread(parent.sch_img_file)
        b,g,r = cv2.split(disp_img)
        #b,g,r = cv2.split(parent.session_data['closeup view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        sch_im = Image.fromarray(img)
        if h > w:
            new_height = 400
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = 400
            new_height = int(float(new_width) * float(h) / float(w))
        
        sch_im = sch_im.resize((new_width, new_height))
        sch_img = ImageTk.PhotoImage(image=sch_im)
        
        image_on_pcb_canvas = sch_canvas.create_image(0, 0, image=sch_img, anchor=NW)
        sch_canvas.image = sch_img

        sch_canvas.grid(row=2, column=0, padx=20, pady=5, sticky="news")

        label_select = Label(canvas, anchor = "nw",
                            text = "Select component to find matches for:",
                            fg = "#019A07",
                            bg = "white", font=("RobotoRoman CondensedRegular", 14))
        
        label_select.grid(row=3,column=0, padx = 20, pady = 5, sticky="nw")
        


        self.footprint_strvar = StringVar()

        ref = parent.refs_sorted[0]
        fp_of_ref = ''
        for footprint in parent.footprint_dict.keys():
            if ref in parent.footprint_dict[footprint]:
                fp_of_ref = footprint
                break

        self.footprint_strvar.set(f'Footprint: {fp_of_ref}')
        
        selector_canvas = Canvas(
            canvas,
            bg = "white",
            height = 20,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        options = parent.refs_sorted

        selected_ref = StringVar() 
        selected_ref.set(parent.refs_sorted[0])

        dropdown = OptionMenu( selector_canvas , selected_ref, *options, command=lambda x: self.new_ref_selected(parent, x))
        dropdown.grid(row=0, column=0) 

        label_fp = Label(selector_canvas, anchor = "nw",
                            textvariable = self.footprint_strvar,
                            fg = "black",
                            bg = "white")
        
        label_fp.grid(row=0,column=1, padx = 20, pady = 5, sticky="nw")
        
        
        selector_canvas.grid(row=4,column=0, padx = 20, pady = 5, sticky="nw")
        
        canvas.pack()

        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        self.next_btn = Button(toolbar,
            text = "Run Component Matching",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.runCM(parent),
            relief="flat"
        )
        
        self.next_btn.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')

    def new_ref_selected(self, parent, ref):
        
        fp_of_ref = ''
        for footprint in parent.footprint_dict.keys():
            if ref in parent.footprint_dict[footprint]:
                fp_of_ref = footprint
                break

        self.footprint_strvar.set(f'Footprint: {fp_of_ref}')
        self.selected_ref = ref
    
    def goBack(self, parent):
        parent.switch_frame(StartPage2)
    
    def runCM(self, parent):
        
        ref = ''
        if hasattr(self, 'selected_ref'):
            ref = self.selected_ref
        else:
            ref = parent.refs_sorted[0]

        parent.runComponentMatching(self.footprint_strvar.get()[11:], ref)
        parent.switch_frame(LoadingScreen)

class BestCurrentMatch(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 1500,
            width = 2000,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        # HEADER
        
        self.match_index = -1
        self.total_matches = -1
        
        match_map = []
        self.total_matches = len(match_map)
        
        if self.total_matches > 0:
            self.match_index = 1
        
        self.label_match_index_str = StringVar()
        self.label_match_index_str.set("ProtoPCB // Best Current Match on Full Circuit Match")
        
        
        label_match_index = Label(canvas, anchor = "nw",
                            textvariable = self.label_match_index_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_match_index.grid(row=1,column=1, padx = 20, pady = 5, sticky="nw")
        tk.ttk.Separator(canvas,orient=HORIZONTAL).place(x=0,y=40, relwidth=1)
        
        # FIRST COLUMN
        self.label_pcb_view_str = StringVar()
        self.label_pcb_view_str.set(f"Front PCB view from {parent.pcb_file}")
        
        label_pcb_view = Label(canvas, anchor = "nw",
                            textvariable=self.label_pcb_view_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_pcb_view.grid(row=2,column=1, padx = 20, pady = 5, sticky="nw")
        
        if parent.fb:
            dim = 900
        else:
            dim = 600

        self.pcb_view_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 600,
            width = dim,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        if parent.fb:
            temp_img = cv2.hconcat([parent.temp_img, parent.temp_img_back])
        else:
            temp_img = parent.temp_img
        b,g,r,a = cv2.split(temp_img)
        #b,g,r = cv2.split(parent.session_data['pcb view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]

        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        
        
        pcb_im = Image.fromarray(image_new)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.image_on_pcb_canvas = self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10), sticky="news")
        
        
        # SECOND COLUMN
        self.label_cmpnt_match_view_str = StringVar()
        self.label_cmpnt_match_view_str.set(f"Circuit schematic from {parent.sch_file}")
        
        label_cmpnt_match_view = Label(canvas, anchor = "nw",
            textvariable=self.label_cmpnt_match_view_str,
            fg = "black",
            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_cmpnt_match_view.grid(row=2,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_match_view_canvas = Canvas(
            canvas,
            bg = "#FFF4FF",
            height = 200,
            width = 400,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        #temp_img2 = cv2.imread(parent.temp_img)
        temp_img2 = cv2.imread(parent.sch_img_file)
        b,g,r = cv2.split(temp_img2)
        #b,g,r = cv2.split(parent.session_data['closeup view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        closeup_im = Image.fromarray(img)
        new_width  = 400
        new_height = int(float(new_width) * float(h) / float(w))
        
        closeup_im = closeup_im.resize((new_width, new_height))
        closeup_img = ImageTk.PhotoImage(image=closeup_im)
        
        cmpnt_match_view_canvas.create_image(0, 0, image=closeup_img, anchor=NW)
        cmpnt_match_view_canvas.image = closeup_img
        
        cmpnt_match_view_canvas.configure(height=new_height)
        
        cmpnt_match_view_canvas.grid(row=3,column=2, padx=20, pady=5, sticky="nw")
        
        l_interventions = Label(canvas, anchor = "nw",
                            text="Interventions: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_interventions.grid(row=6,column=2, padx = 20, pady = 5, sticky="nw")

        self.l_missing_nets_str = StringVar()
        self.l_missing_nets_str.set(f"Missing nets: {parent.current_best_match['missing nets']}")
        l_missing_nets = Label(canvas, anchor = "nw", textvariable = self.l_missing_nets_str, fg="black", bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        
        canvas.pack()
        
        
        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        self.return_search = Button(toolbar,
            text = "Return to Main Search",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.return_to_search(parent),
            relief="flat"
        )
        
        self.return_search.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')
    
    def goBack(self, parent):
        parent.switch_frame(StartPage)

    def return_to_search(self, parent):
        parent.switch_frame(LoadingScreen)

    def update(self, parent):

        self.label_match_index_str.set("ProtoPCB // // Best Current Match on Full Circuit Match")
        

        if parent.fb:
            b,g,r,a = cv2.split(cv2.hconcat([parent.temp_img, parent.temp_img_back]))
            overlay_img = cv2.merge((r,g,b,a))
            b,g,r = cv2.split(cv2.hconcat([parent.board_img, parent.board_img_back]))
            dim = 900
        else:
            b,g,r,a = cv2.split(parent.temp_img)
            overlay_img = cv2.merge((r,g,b,a))
            b,g,r = cv2.split(parent.board_img)
            dim = 600
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        overlay = img.copy() 

          
        self.l_missing_nets_str.set(f"Missing nets: {parent.current_best_match['missing nets']}")
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        rgba_img = cv2.cvtColor(image_new, cv2.COLOR_RGB2RGBA)
        disp_img = cv2.addWeighted(overlay_img, 1, rgba_img, 1, 0.0)
        
        
        pcb_im = Image.fromarray(disp_img)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        #self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10))

        self.pcb_view_canvas.itemconfig(self.image_on_pcb_canvas, image=self.pcb_img)

class VidCircuitDraft(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        canvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = 1500,
            width = 2000,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        # HEADER
        
        self.match_index = -1
        self.total_matches = -1
        
        match_map = []
        self.total_matches = len(match_map)
        
        if self.total_matches > 0:
            self.match_index = 1
        
        self.label_match_index_str = StringVar()
        #self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + str(self.match_index) + " of " + str(self.total_matches))
        self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + '1' + " of " + '12' + "                                                                                                                          Searching on 42 PCB Boards from Library")
              
        
        label_match_index = Label(canvas, anchor = "nw",
                            textvariable = self.label_match_index_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 20))
        
        label_match_index.grid(row=1,column=1, columnspan=2, padx = 20, pady = 5, sticky="nw")
        tk.ttk.Separator(canvas,orient=HORIZONTAL).place(x=0,y=40, relwidth=1)
        
        # FIRST COLUMN
        self.label_pcb_view_str = StringVar()
        self.label_pcb_view_str.set(f"Front PCB view from ATtiny85-MP3.kicad_pcb")
        
        label_pcb_view = Label(canvas, anchor = "nw",
                            textvariable=self.label_pcb_view_str,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_pcb_view.grid(row=2,column=1, padx = 20, pady = 5, sticky="nw")
        
        parent.fb = True
        if parent.fb:
            dim = 900
        else:
            dim = 600
        self.pcb_view_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 600,
            width = dim,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        
        if parent.fb:
            temp_img = cv2.hconcat([parent.temp_img, parent.temp_img_back])
        else:
            temp_img = parent.temp_img
        b,g,r,a = cv2.split(temp_img)
        #b,g,r = cv2.split(parent.session_data['pcb view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]

        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        
        
        pcb_im = Image.fromarray(image_new)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.image_on_pcb_canvas = self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        self.pcb_view_canvas.grid(row=3,column=1, rowspan=12, padx=20, pady=(5,10), sticky="news")
        
        
        # SECOND COLUMN
        self.label_cmpnt_match_view_str = StringVar()
        self.label_cmpnt_match_view_str.set(f"Circuit schematic from Connectivity Probe.kicad_sch")
        
        label_cmpnt_match_view = Label(canvas, anchor = "nw",
            textvariable=self.label_cmpnt_match_view_str,
            fg = "black",
            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        label_cmpnt_match_view.grid(row=2,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_match_view_canvas = Canvas(
            canvas,
            bg = "#FFF4FF",
            height = 200,
            width = 300,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        temp_img2 = cv2.imread(parent.sch_img_file)
        b,g,r = cv2.split(temp_img2)
        #b,g,r = cv2.split(parent.session_data['closeup view'])
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        
        closeup_im = Image.fromarray(img)
        new_width  = 300
        new_height = int(float(new_width) * float(h) / float(w))
        
        closeup_im = closeup_im.resize((new_width, new_height))
        closeup_img = ImageTk.PhotoImage(image=closeup_im)
        
        cmpnt_match_view_canvas.create_image(0, 0, image=closeup_img, anchor=NW)
        cmpnt_match_view_canvas.image = closeup_img
        
        cmpnt_match_view_canvas.configure(height=new_height)
        
        cmpnt_match_view_canvas.grid(row=3,column=2, padx=20, pady=5, sticky="nw")
        '''
        cmpnt_name = StringVar()
        #cmpnt_name.set("Component Name: " + parent.session_data['component name'])
        cmpnt_name.set("Component Name: " + 'TEMP')
        
        l_cmpnt_match_name = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_name,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_cmpnt_match_name.grid(row=4,column=2, padx = 20, pady = 5, sticky="nw")
        
        cmpnt_fp = StringVar()
        #cmpnt_fp.set("Footprint: " + parent.session_data['component footprint'])
        cmpnt_fp.set("Footprint: " + 'footprint')
        
        l_fp = Label(canvas, anchor = "nw",
                            textvariable=cmpnt_fp,
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_fp.grid(row=5,column=2, padx = 20, pady = 5, sticky="nw")
        '''
        l_interventions = Label(canvas, anchor = "nw",
                            text="Multiple Interventions Needed",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_interventions.grid(row=4,column=2, padx = 20, pady = 5, sticky="nw")
        
        selector_canvas = Canvas(
            canvas,
            bg = "#FFFFFF",
            height = 20,
            width = 600,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        if self.match_index > 0:
            #self.options = list(["All Nets"])
            self.options = list(parent.matches[self.match_index - 1]['nets view dict'].keys()) + ["All Nets"]
        else:
            #self.options = list(["All Nets"])
            self.options = list(parent.matches[0]['nets view dict'].keys()) + ["All Nets"]


        selected_view = StringVar() 
        selected_view.set( "All Nets" )

        dropdown = OptionMenu( selector_canvas , selected_view, *self.options )
        dropdown.grid(row=0, column=1) 

        l_select_view = Label(selector_canvas, anchor = "nw",
                            text="Select View: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        l_select_view.grid(row=0, column = 0)

        change_view_btn = Button(selector_canvas,
            text = "Change View",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.change_view(parent, selected_view.get()),
            relief="flat"
        )
        
        change_view_btn.grid(row=0, column=3, padx=5, pady=5, sticky="nw")
        
        selector_canvas.grid(row=5,column=2, padx = 20, pady = 5, sticky="nw")
        
        '''
        l_mod_matches = Label(canvas, anchor = "nw",
                            text="mod required matches: ",
                            fg = "black",
                            bg = "white", font=("RobotoRoman CondensedRegular", 13))
        
        l_mod_matches.grid(row=8,column=2, padx = 20, pady = 5, sticky="nw")
        '''
        
        canvas.pack()
        
        
        # BOTTOM TOOLBAR
        
        toolbar = Frame(self)
        
        back_btn = Button(toolbar,
            text = "Back",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.goBack(parent),
            relief="flat"
        )
        
        back_btn.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        self.next_btn = Button(toolbar,
            text = "See Next Best Match",
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.nextMatch(parent),
            relief="flat"
        )
        
        self.next_btn.grid(row=0, column=1, padx=20, pady=20, sticky="ne")
        
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.pack(fill='x')
    
    def goBack(self, parent):
        parent.switch_frame(StartPage)
    
    def nextMatch(self, parent):
        if self.match_index + 1 <= len(parent.matches):
            self.match_index += 1
            parent.temp_img = parent.matches[self.match_index - 1]['pcb view']
            parent.current_match = parent.matches[self.match_index - 1]['match']

            if parent.current_match.fb == 'front':
                parent.board_img = cv2.imread(os.getcwd() + "/temp/board.png")
            else:
                parent.board_img = cv2.imread(os.getcwd() + "/temp/board_back.png")

            self.update(parent)

        if self.match_index + 1 > len(parent.matches):
            self.next_btn.config(state=DISABLED)

    def update(self, parent):
        if self.match_index == -1:
            if len(parent.matches) > 0:
                self.match_index = 1
        self.total_matches = len(parent.matches)

        #if self.match_index + 1 > len(parent.matches):
        #    self.next_btn.config(state=DISABLED)

        #self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + str(self.match_index) + " of " + str(self.total_matches))
        self.label_match_index_str.set("ProtoPCB // Full Circuit Match // " + '1' + " of " + '12' + "                                                                                                                          Searching on 42 PCB Boards from Library")
        
        if parent.fb:
            temp_img = cv2.hconcat([parent.temp_img, parent.temp_img_back])
            board_img = cv2.hconcat([parent.board_img, parent.board_img_back])
            dim = 900
        else:
            temp_img = parent.temp_img
            board_img = parent.board_img
            dim = 600
        b,g,r,a = cv2.split(temp_img)
        overlay_img = cv2.merge((r,g,b,a))


        b,g,r = cv2.split(board_img)
        img = cv2.merge((r,g,b))
        h,w = img.shape[:2]
        overlay = img.copy() 
          
        
        # A filled rectangle 
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)   
          
        alpha = 0.4  # Transparency factor. 
          
        # Following line overlays transparent rectangle 
        # over the image 
        image_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0) 
        rgba_img = cv2.cvtColor(image_new, cv2.COLOR_RGB2RGBA)
        disp_img = cv2.addWeighted(overlay_img, 1, rgba_img, 1, 0.0)
        
        
        pcb_im = Image.fromarray(disp_img)
        if h > w:
            new_height = 600
            new_width = int(float(new_height) * float(w)/float(h))
        else:
            new_width  = dim
            new_height = int(float(new_width) * float(h) / float(w))
        
        pcb_im = pcb_im.resize((new_width, new_height))
        self.pcb_img = ImageTk.PhotoImage(image=pcb_im)
        
        self.pcb_view_canvas.create_image(0, 0, image=self.pcb_img, anchor=NW)
        self.pcb_view_canvas.image = self.pcb_img
        #self.pcb_view_canvas.grid(row=3,column=1, rowspan=6, padx=20, pady=(5,10))

        self.pcb_view_canvas.itemconfig(self.image_on_pcb_canvas, image=self.pcb_img)


        if self.match_index > 0:
            self.options = list(parent.matches[self.match_index - 1]['nets view dict'].keys()) + ["All Nets"]
        else:
            self.options = list(parent.matches[0]['nets view dict'].keys()) + ["All Nets"]

    def change_view(self, parent, view_str):
        if view_str == 'All Nets':

            parent.temp_img = parent.matches[self.match_index - 1]['pcb view']['front']
            if parent.fb:
                parent.temp_img_back = parent.matches[self.match_index - 1]['pcb view']['back']
        else:
            if parent.fb:
                parent.temp_img = parent.matches[self.match_index - 1]['nets view dict'][view_str][0]
                parent.temp_img_back = parent.matches[self.match_index - 1]['nets view dict'][view_str][1]
            else:
                parent.temp_img = parent.matches[self.match_index - 1]['nets view dict'][view_str]
                
        
        self.update(parent)

        

app = ProtoPCBApp()

s = Style()

s.theme_use('classic')

app.mainloop()


