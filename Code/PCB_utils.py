"""
    Holds relevant functions for processing PCB info into relevant information
"""
import cv2
import numpy as np

import os
import subprocess

from svg_edit import svg_to_png_gen
from Objectifier import Objectifier

from identifyHoles import *

def gen_pad_map(contours, ignore_contours =[]):
    """
        Helper function for 'process_PCB_png_files'. Generates a dict mapping out all pads (by contour ID) and their corresponding centers. 

        Parameters:
        contours (array): array of the pad contours of solder mask image
        
        Returns:
        pad_map(dict): dict of pads and corresponding center coordinates.
    
    """
    pad_map = {}
    num = 0

    for cnt in contours:
        M = cv2.moments(cnt)
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])

        pad_map[num] = (cx,cy)
        num = num + 1

    return pad_map


def connected_pads(pad_map, trace_contours, trace_hierarchy, trace_img, hole_arr = []):
    """
        Helper function for 'initialize_via_files'. Creates a mapping of all traces and the pads that are connected within the trace.
        Parameters:
        pad_map (dict): dict of pads and corresponding center coordinates.
        trace_contours (array): all contours of traces in full PCB image
        trace_hierarchy (array): hierarchical information about trace contours
        trace_img (2D array): image of full PCB with traces

        Optional:
        hole_arr (array): array of holes (to deal with vias)
        
        Returns:
        traces_map (dict): dict of traces and corresponding pads within the trace.

    """
    traces_map = {}
    rows = trace_hierarchy[0].shape[0]


    for i in range(rows):
        #if outermost contour - pass
        if trace_hierarchy[0][i][3] == -1:
            continue

        for pad, pad_center in pad_map.items():

            within_trace = cv2.pointPolygonTest(trace_contours[i], pad_center, False)

            if within_trace == 1:
                #Currently does not account for through-hole

                # CHECK - does the pad exist within non trace space? (i.e. inner contour)
                #does an inner contour exist?
                if (trace_hierarchy[0][i][2]!=-1):
                    inner_cnt = trace_hierarchy[0][i][2]
                    #initially add the point unless a contour hole where the point lies in exists
                    add_point = True

                    # are there other holes to account for?
                    # go through all inner contours
                    #[0] is the next contour at this level
                    while (trace_hierarchy[0][inner_cnt][0] != -1):
                        within_hole = cv2.pointPolygonTest(trace_contours[inner_cnt], pad_center, False)
                        if within_hole == 1:
                            cnt_th = False
                            if trace_hierarchy[0][inner_cnt][2] == -1:
                                if len(hole_arr) > 0:
                                    cnt_th = contour_contains_throughhole(trace_contours[inner_cnt], hole_arr)
                            if not cnt_th:
                                
                                add_point = False
                                break
                        inner_cnt = trace_hierarchy[0][inner_cnt][0]

                    #check last contour on this "level"
                    if trace_hierarchy[0][inner_cnt][0] == -1:
                        within_hole = cv2.pointPolygonTest(trace_contours[inner_cnt], pad_center, False)
                        if within_hole == 1:
                            cnt_th = False
                            if trace_hierarchy[0][inner_cnt][2] == -1:

                                if len(hole_arr) > 0:
                                    cnt_th = contour_contains_throughhole(trace_contours[inner_cnt], hole_arr)
                            if not cnt_th:
                                
                                add_point = False
                            

                    if add_point:
                        if i in traces_map:
                            traces_map[i].append(pad)
                        else:
                            traces_map[i] = [pad]


                # CHECK - is this an outer contour (an empty hole)
                elif (contour_is_empty(trace_contours[i], trace_img) == 1):
                    continue
                else:

                    # add pad to dict for this trace
                    if i in traces_map:
                        traces_map[i].append(pad)
                    else:
                        traces_map[i] = [pad]



    return traces_map


def contour_is_empty(contour, trace_img):
    """
        Helper function for 'connected_pads'. Checks to make sure contour is empty (there are no additional features to account for).
        Parameters:
        contour (array): contour of section in question
        trace_img (2D array): the image to process contour on
        
        Returns:
        (int): 1 if contour is truly empty, -1 if contour is not
    
    """
    # note: only use if there's no inner child
    # only checks if mean val is black/white
    M = cv2.moments(contour)
    cx = int(M['m10']/M['m00'])
    cy = int(M['m01']/M['m00'])

    mask = np.zeros(trace_img.shape,np.uint8)
    cv2.drawContours(mask,[contour],0,255,-1)
    mean_val = cv2.mean(trace_img,mask = mask)

    is_empty = (mean_val[0] <= 100)

    if is_empty == 1:
        return 1
    else:
        return -1


def contour_contains_throughhole(contour, hole_arr):
    """
        Helper function for 'connected_pads'. Checks to see if contour in question contains throughhole (i.e. the other side is also connected)
        Parameters:
        contour (array): contour of section in question
        hole_arr (array): all holes found on board
        
        Returns:
        (boolean): True if contains throughhole, False if not
    
    """
    contains_th = False
    for hole in hole_arr:
        
        if hasattr(hole, 'isThroughHole') and hole.isThroughHole:
            within_hole = cv2.pointPolygonTest(contour, hole.coordinates, False)
            if within_hole == 1:
                contains_th = True
                break
        
        elif hasattr(hole, 'isVia') and hole.isVia:

            within_hole = cv2.pointPolygonTest(contour, hole.coordinates, False)
            if within_hole == 1:
                contains_th = True
                break

    return contains_th


def generate_pngs_from_dir(dir_path, output_dir):
    '''
        script to generate png images across a whole directory of .kicad_pcb

        Parameters:
        dir_path (str) - directory with all .kicad_pcb files
        output_dir (str) - directory with to output png files
    '''

    contents = os.listdir(dir_path)
    kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

    for content in contents:
        if content[-9:]=='kicad_pcb':
            name = content[:-10]
            #run pcb png generation command line

            png_output_dir = output_dir + "/" + name
            os.mkdir(png_output_dir)
        
            ## first masks only
            
            complete = subprocess.run([kicad_cli, "pcb", "export", "svg", dir_path + "/" + content, "-o", png_output_dir + "/" + name + "-f-mask.svg", "--layers", "F.Mask", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
            print(complete)
            
            svg_to_png(png_output_dir + "/" + name + "-f-mask.svg")
            
            ## then traces too
            
            complete = subprocess.run([kicad_cli, "pcb", "export", "svg", dir_path + "/" + content, "-o", png_output_dir + "/" + name + "-f-traces.svg", "--layers", "F.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
            print(complete)
            
            svg_to_png(png_output_dir + "/" + name + "-f-traces.svg")


def get_board_bounds(pcb_file):
    '''
        Retrieve top left and bottom coordinates for bounds of edge cuts on a PCB 

        Parameters:
        pcb_file (str) - .kicad_pcb file path
        
        Returns
        top_left (tuple) - coordinate of top left corner
        width (float) - width of board
        height (float) - height of board

    '''

    pcb = Objectifier(pcb_file)

    root = pcb.root

    minX = 10000000.00
    minY = 10000000.00

    maxX = -10000000.00
    maxY = -10000000.00

    # CHECK GR_RECT, GR_LINE, GR_ARC, GR_CIRCLE

    ## GR_RECT
    for node in root.xpath('/kicad_pcb/gr_rect'):
        layer = node.xpath('layer')[0].first_child
        if layer == 'Edge.Cuts':
            start = node.xpath('start')[0].childs
            if start[0] < minX:
                minX = start[0]
            if start[1] < minY:
                minY = start[1]
            if start[0] > maxX:
                maxX = start[0]
            if start[1] > maxY:
                maxY = start[1]

            end = node.xpath('end')[0].childs
            if end[0] < minX:
                minX = end[0]
            if end[1] < minY:
                minY = end[1]
            if end[0] > maxX:
                maxX = end[0]
            if end[1] > maxY:
                maxY = end[1]

    #'''
    ## GR_LINE
    for node in root.xpath('/kicad_pcb/gr_line'):
        layer = node.xpath('layer')[0].first_child
        if layer == 'Edge.Cuts':
            start = node.xpath('start')[0].childs
            if start[0] < minX:
                minX = start[0]
            if start[1] < minY:
                minY = start[1]
            if start[0] > maxX:
                maxX = start[0]
            if start[1] > maxY:
                maxY = start[1]

            end = node.xpath('end')[0].childs
            if end[0] < minX:
                minX = end[0]
            if end[1] < minY:
                minY = end[1]
            if end[0] > maxX:
                maxX = end[0]
            if end[1] > maxY:
                maxY = end[1]
    #'''

    '''
    ## GR_ARC
    for node in root.xpath('/kicad_pcb/gr_arc'):
        layer = node.xpath('layer')[0].first_child
        if layer == 'Edge.Cuts':
            start = node.xpath('start')[0].childs
            if start[0] < minX:
                minX = start[0]
            if start[1] < minY:
                minY = start[1]
            if start[0] > maxX:
                maxX = start[0]
            if start[1] > maxY:
                maxY = start[1]

            mid = node.xpath('mid')[0].childs
            if mid[0] < minX:
                minX = mid[0]
            if mid[1] < minY:
                minY = mid[1]
            if mid[0] > maxX:
                maxX = mid[0]
            if mid[1] > maxY:
                maxY = mid[1]

            end = node.xpath('end')[0].childs
            if end[0] < minX:
                minX = end[0]
            if end[1] < minY:
                minY = end[1]
            if end[0] > maxX:
                maxX = end[0]
            if end[1] > maxY:
                maxY = end[1]

    ## GR_CIRCLE
    for node in root.xpath('/kicad_pcb/gr_circle'):
        layer = node.xpath('layer')[0].first_child
        if layer == 'Edge.Cuts':
            center = node.xpath('center')[0].childs
            end = node.xpath('end')[0].childs

            lX = center[0] - end[0]

            tY = center[1] - end[1]

            rX = center[0] + end[0]

            bY = center[1] + center[1]

            if lX < minX:
                minX = lX
            if tY < minY:
                minY = tY
            if rX > maxX:
                maxX = rX
            if bY > maxY:
                maxY = bY

            if end[0] < minX:
                minX = end[0]
            if end[1] < minY:
                minY = end[1]
            if end[0] > maxX:
                maxX = end[0]
            if end[1] > maxY:
                maxY = end[1]
    '''
    '''
    # CHECK ZONES

    for node in root.xpath('/kicad_pcb/zone'):
        polygon_pts = node.xpath('polygon/pts/xy')
        for polygon_pt in polygon_pts:
            [x,y] = polygon_pt.childs
            
            if x < minX:
                minX = x
            if y < minY:
                minY = y
            if x > maxX:
                maxX = x
            if y > maxY:
                maxY = y
    '''

    '''
    # CHECK FOOTPRINTS (SILKSCREEN AND MARGIN)
    for node in root.xpath('/kicad_pcb/footprint'):
        at = node.xpath('at')[0].childs
        
        if len(at) > 2 and (at[2] == 90):
            for fp_line in node.xpath('fp_line'):
                start = fp_line.xpath('start')[0].childs
                end = fp_line.xpath('end')[0].childs
                
                sx = at[0] + start[1]
                sy = at[1] + start[0]


                ex = at[0] + end[1]
                ey = at[1] + end[0]

                if sx < minX:
                    minX = sx
                if sy < minY:
                    minY = sy
                if sx > maxX:
                    maxX = sx
                if sy > maxY:
                    maxY = sy

                if ex < minX:
                    minX = ex
                if ey < minY:
                    minY = ey
                if ex > maxX:
                    maxX = ex
                if ey > maxY:
                    maxY = ey

        elif len(at)> 2 and ((at[2] == 270) or at[2] == -90):
            for fp_line in node.xpath('fp_line'):
                start = fp_line.xpath('start')[0].childs
                end = fp_line.xpath('end')[0].childs

                
                sx = at[0] + (start[1] * -1)
                sy = at[1] + start[0]


                ex = at[0] + (end[1] * -1)
                ey = at[1] + end[0]

                if sx < minX:
                    minX = sx
                if sy < minY:
                    minY = sy
                if sx > maxX:
                    maxX = sx
                if sy > maxY:
                    maxY = sy

                if ex < minX:
                    minX = ex
                if ey < minY:
                    minY = ey
                if ex > maxX:
                    maxX = ex
                if ey > maxY:
                    maxY = ey


        elif len(at) > 2 and at[2] == 180:
            for fp_line in node.xpath('fp_line'):
                start = fp_line.xpath('start')[0].childs
                end = fp_line.xpath('end')[0].childs
                

                
                sx = at[0] + start[0]
                sy = at[1] + (start[1]*-1)


                ex = at[0] + end[0] 
                ey = at[1] + (end[1] *-1)

                if sx < minX:
                    minX = sx
                if sy < minY:
                    minY = sy
                if sx > maxX:
                    maxX = sx
                if sy > maxY:
                    maxY = sy

                if ex < minX:
                    minX = ex
                if ey < minY:
                    minY = ey
                if ex > maxX:
                    maxX = ex
                if ey > maxY:
                    maxY = ey

        else:
            for fp_line in node.xpath('fp_line'):
                start = fp_line.xpath('start')[0].childs
                end = fp_line.xpath('end')[0].childs

                
                sx = at[0] + start[0]
                sy = at[1] + start[1]


                ex = at[0] + end[0] 
                ey = at[1] + end[1] 

                if sx < minX:
                    minX = sx
                if sy < minY:
                    minY = sy
                if sx > maxX:
                    maxX = sx
                if sy > maxY:
                    maxY = sy

                if ex < minX:
                    minX = ex
                if ey < minY:
                    minY = ey
                if ex > maxX:
                    maxX = ex
                if ey > maxY:
                    maxY = ey
        
    '''



    width = maxX - minX
    height = maxY-minY


    return (minX, minY), width, height


def is_board_fb(pcb_file):
    '''
        Checks if pcb board contains relevant features on both front and back

        Parameters:
        pcb_file (str): design file of PCB

        Returns:
        (bool) True if board is double sided

    '''
    pcb = Objectifier(pcb_file)

    root = pcb.root

    double = False

    for node in root.xpath('/kicad_pcb/footprint'):
        layer = node.xpath('layer')[0].first_child
        if layer == 'B.Cu':
            double = True
            break

    return double




class PCB_Board:
    '''
        class representation of the PCB Board being searched on. Organizes information derived from copper layer images & drill file information.

    '''

    def __init__(self, kicad_pcb_file):
        '''
            initialization for PCB Board object

            Parameters:
            kicad_pcb_file (str) - file of pcb design file (.kicad_pcb)
        '''
        self.pcb_file = kicad_pcb_file
        self.double_sided = is_board_fb(kicad_pcb_file)

        
    def create_vias_profile(self, hole_arr):
        '''
            initialization for PCB Board object

            Parameters:
            kicad_pcb_file (str) - file of pcb design file (.kicad_pcb)
        '''
        
        tl_coords, width, height = get_board_bounds(self.pcb_file)

        rows = self.trace_hierarchy[0].shape[0]

        vias_dict = {}

        for hole in hole_arr:
            (x,y) = hole.coordinates

            y = ((abs(y) - tl_coords[1])/ height) * self.pcb_rgb.shape[0] 
            x = ((x - tl_coords[0])/ width) * self.pcb_rgb.shape[1]  
            x, y = (abs(round(x)), abs(round(y)))

            mask_val = self.mask_rgb[y][x]

            hole.coordinates = (x,y)

            
            
            if list(mask_val) == [255, 255, 255]:
                hole.isVia = True


                for i in range(rows):
                    if self.trace_hierarchy[0][i][3] == -1:
                        continue

                    if self.trace_hierarchy[0][i][2] != -1:
                        inner_cnt_ID = self.trace_hierarchy[0][i][2]
                        
                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                            within_trace = cv2.pointPolygonTest(self.trace_contours[i], (x,y), False)
                            if within_trace == 1:
                                found_via = False

                                within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)

                                if within_trace == 1:
                                    
                                    found_via = True
                                    if i in vias_dict.keys():
                                        vias_dict[i]['holes'].append(hole)
                                    else:
                                        vias_dict[i] = {'holes': [hole]}

                                if not found_via:
                                    while not found_via and self.trace_hierarchy[0][inner_cnt_ID][0] != -1:
                                        inner_cnt_ID = self.trace_hierarchy[0][inner_cnt_ID][0]

                                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                                            within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)

                                            if within_trace == 1:
                                                
                                                if i in vias_dict.keys():
                                                    vias_dict[i]['holes'].append(hole)
                                                else:
                                                    vias_dict[i] = {'holes': [hole]}
                                                found_via = True


            else:
                hole.isVia = False

                for i in range(rows):
                    if self.trace_hierarchy[0][i][3] == -1:
                        inner_cnt_ID = self.trace_hierarchy[0][i][2]
                        within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)
                        
                        if within_trace == 1:
                            hole.isThroughHole = True

                        while self.trace_hierarchy[0][inner_cnt_ID][0] != -1:
                            inner_cnt_ID = self.trace_hierarchy[0][inner_cnt_ID][0]
                            
                            within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)
                            if within_trace == 1:
                                hole.isThroughHole = True
                                if inner_cnt_ID in vias_dict.keys():
                                    vias_dict[inner_cnt_ID]['holes'].append(hole)
                                else:
                                    vias_dict[inner_cnt_ID] = {'holes': [hole]}
                                break

                        if not hasattr(hole, 'isThroughHole') or not hole.isThroughHole:
                            hole.isDrillHole = True
                        continue

                    if self.trace_hierarchy[0][i][2] != -1:
                        if self.trace_hierarchy[0][i][3] != 0:
                            inner_cnt_ID = self.trace_hierarchy[0][i][2]
                            within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)
                            if within_trace == 1:
                                hole.isThroughHole = True
                                if i in vias_dict.keys():
                                    vias_dict[i]['holes'].append(hole)
                                else:
                                    vias_dict[i] = {'holes': [hole]}

                            while self.trace_hierarchy[0][inner_cnt_ID][0] != -1:
                                inner_cnt_ID = self.trace_hierarchy[0][inner_cnt_ID][0]
                                within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], (x,y), False)
                                if within_trace == 1:
                                    hole.isThroughHole = True
                                    if i in vias_dict.keys():
                                        vias_dict[i]['holes'].append(hole)
                                    else:
                                        vias_dict[i] = {'holes': [hole]}
                                    break

                            

                            if not hasattr(hole, 'isThroughHole') or not hole.isThroughHole:
                                hole.isDrillHole = True
                        
                if not hasattr(hole, 'isThroughHole') or not hole.isThroughHole:
                    hole.isDrillHole = True
                else:
                    #add this through hole to the via dict
                    for i in range(rows):
                        if self.trace_hierarchy[0][i][3] == -1:
                            continue

                        if self.trace_hierarchy[0][i][2] != -1:
                            inner_cnt_ID = self.trace_hierarchy[0][i][2]
                            
                            if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                                within_trace = cv2.pointPolygonTest(self.trace_contours[i], (x,y), False)
                                if within_trace == 1:

                                    if i in vias_dict.keys():

                                        if hole not in vias_dict[i]['holes']:
                                            vias_dict[i]['holes'].append(hole)

                                        
                                    else:
                                        vias_dict[i] = {'holes': [hole]}

        self.hole_arr = hole_arr


        ## now create mapping to backside using vias info

        connected_traces_back_dict = {}
        vias_dict_back = {}

        for trace_fID in vias_dict.keys():
            holes = vias_dict[trace_fID]['holes']

            rows = self.trace_back_hierarchy[0].shape[0]
            temp = self.pcb_rgb_back.copy()
            for hole in holes:
                
                for i in range(rows):
                    if self.trace_back_hierarchy[0][i][3] == -1:
                        continue

                    if self.trace_back_hierarchy[0][i][2] != -1:
                        inner_cnt_ID = self.trace_back_hierarchy[0][i][2]

                        found_via = False
                        
                        while self.trace_back_hierarchy[0][inner_cnt_ID][0] != -1:
                            if self.trace_back_hierarchy[0][inner_cnt_ID][2] == -1:
                                within_trace = cv2.pointPolygonTest(self.trace_back_contours[inner_cnt_ID], hole.coordinates, False)
                                if within_trace == 1:
                                    found_via = True
                                    
                                    if i in connected_traces_back_dict.keys():

                                        connected_traces_back_dict[i].append(trace_fID)
                                    else:
                                        connected_traces_back_dict[i] = [trace_fID]

                                    break
                            inner_cnt_ID = self.trace_back_hierarchy[0][inner_cnt_ID][0]


                        if not found_via:
                            #check last one
                            if self.trace_back_hierarchy[0][inner_cnt_ID][2] == -1:
                                within_trace = cv2.pointPolygonTest(self.trace_back_contours[inner_cnt_ID], hole.coordinates, False)
                                if within_trace == 1:
                                    found_via = True
                                    
                                    if i in connected_traces_back_dict.keys():

                                        connected_traces_back_dict[i].append(trace_fID)
                                    else:
                                        connected_traces_back_dict[i] = [trace_fID]




        trace_index = 0
        board_connections_dict = {}
        touched_front_traces = []
        touched_back_traces = []

        for b_trace_ID in connected_traces_back_dict.keys():
            
            connection_dict = {'front traces': [], 'back traces': [b_trace_ID], 'holes': []}

            f_traces = connected_traces_back_dict[b_trace_ID]
            
            
            is_connected_to_existing = False
            for f_trace in f_traces:
                if f_trace not in touched_front_traces:
                    touched_front_traces.append(f_trace)

                    if f_trace not in connection_dict['front traces']:
                        connection_dict['front traces'].append(f_trace)
                        connection_dict['holes'] += vias_dict[f_trace]['holes']
                        
                elif f_trace in connection_dict['front traces']:
                    continue
                else:
                    is_connected_to_existing = True
                    for t_index in board_connections_dict.keys():
                        if f_trace in board_connections_dict[t_index]['front traces']:
                            for ff_trace in f_traces:
                                if ff_trace not in board_connections_dict[t_index]['front traces']:
                                    board_connections_dict[t_index]['front traces'].append(ff_trace)
                                    board_connections_dict[t_index]['holes'] += vias_dict[ff_trace]['holes']

                                if ff_trace not in touched_front_traces:
                                    touched_front_traces.append(ff_trace)

                            if b_trace_ID not in board_connections_dict[t_index]['back traces']:
                                board_connections_dict[t_index]['back traces'].append(b_trace_ID)
                                touched_back_traces.append(b_trace_ID)
                            break
                    break

            if not is_connected_to_existing:
                board_connections_dict[trace_index] = connection_dict
                touched_back_traces.append(b_trace_ID)
                trace_index += 1

        # add other traces that contain pads

        ## determine any pads that contain Drill Holes (ignore)

        f_pads_ignore = []
        b_pads_ignore = []

        
        for hole in self.hole_arr:
            if hasattr(hole, 'isDrillHole') and hole.isDrillHole:
                f_m_cnt_i = 0
                for f_m_cnt in self.mask_contours:
                    within_pad = cv2.pointPolygonTest(f_m_cnt, hole.coordinates, False)
                    if within_pad == 1:
                        f_pads_ignore.append(f_m_cnt_i)
                        break
                    f_m_cnt_i += 1

                b_m_cnt_i = 0
                for b_m_cnt in self.mask_back_contours:
                    within_pad = cv2.pointPolygonTest(b_m_cnt, hole.coordinates, False)
                    if within_pad == 1:
                        b_pads_ignore.append(b_m_cnt_i)
                        break
                    b_m_cnt_i += 1

        f_mask_contours = []
        b_mask_contours = []

        f_m_cnt_i = 0
        for f_m_cnt in self.mask_contours:
            if f_m_cnt_i not in f_pads_ignore:
                f_mask_contours.append(f_m_cnt)
            f_m_cnt_i += 1

        b_m_cnt_i = 0
        for b_m_cnt in self.mask_back_contours:
            if b_m_cnt_i not in b_pads_ignore:
                b_mask_contours.append(b_m_cnt)
            b_m_cnt_i += 1

        self.mask_contours = f_mask_contours
        self.mask_back_contours = b_mask_contours

        ## start with front traces
        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        t_inv_img_grey = cv2.bitwise_not(t_img_grey)

        front_pad_map = gen_pad_map(self.mask_contours, f_pads_ignore)
        front_trace_map = connected_pads(front_pad_map, self.trace_contours, self.trace_hierarchy, t_inv_img_grey, hole_arr = self.hole_arr)

        tb_img_grey = cv2.cvtColor(self.pcb_rgb_back, cv2.COLOR_BGR2GRAY)
        tb_inv_img_grey = cv2.bitwise_not(tb_img_grey)

        back_pad_map = gen_pad_map(self.mask_back_contours, b_pads_ignore)
        back_trace_map = connected_pads(back_pad_map, self.trace_back_contours, self.trace_back_hierarchy, tb_inv_img_grey, hole_arr = self.hole_arr)

        
        for trace_index in board_connections_dict.keys():
            f_pads = []
            for f_trace in board_connections_dict[trace_index]['front traces']:
                if f_trace in front_trace_map.keys():
                    f_pads += front_trace_map[f_trace]

            board_connections_dict[trace_index]['front pads'] = f_pads

            b_pads = []
            for b_trace in board_connections_dict[trace_index]['back traces']:
                if b_trace in back_trace_map.keys():
                    b_pads += back_trace_map[b_trace]

            board_connections_dict[trace_index]['back pads'] = b_pads

        ## just check for stragglers in trace map

        for f_trace in front_trace_map.keys():
            if f_trace not in touched_front_traces:
                trace_index += 1
                board_connections_dict[trace_index] = {'front traces': [f_trace], 'back traces': [], 'back pads': [], 'front pads': front_trace_map[f_trace]}

        
        for b_trace in back_trace_map.keys():
            if b_trace not in touched_back_traces:
                trace_index += 1
                board_connections_dict[trace_index] = {'front traces': [], 'back traces': [b_trace], 'back pads': back_trace_map[b_trace], 'front pads': []}

        self.board_connections_dict = board_connections_dict
        self.front_pad_map = front_pad_map
        self.back_pad_map = back_pad_map


        
    
    def create_updated_vias_profile(self):

        rows = self.trace_hierarchy[0].shape[0]

        vias_dict = {}

        for hole in self.hole_arr:
            if hole.isVia:
                for i in range(rows):
                    if self.trace_hierarchy[0][i][3] == -1:
                        continue

                    if self.trace_hierarchy[0][i][2] != -1:
                        inner_cnt_ID = self.trace_hierarchy[0][i][2]
                        
                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                            within_trace = cv2.pointPolygonTest(self.trace_contours[i], hole.coordinates, False)
                            if within_trace == 1:
                                found_via = False

                                within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], hole.coordinates, False)

                                if within_trace == 1:
                                    
                                    found_via = True
                                    if i in vias_dict.keys():
                                        vias_dict[i]['holes'].append(hole)
                                    else:
                                        vias_dict[i] = {'holes': [hole]}

                                if not found_via:
                                    while not found_via and self.trace_hierarchy[0][inner_cnt_ID][0] != -1:
                                        inner_cnt_ID = self.trace_hierarchy[0][inner_cnt_ID][0]

                                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                                            within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], hole.coordinates, False)

                                            if within_trace == 1:
                                                
                                                if i in vias_dict.keys():
                                                    vias_dict[i]['holes'].append(hole)
                                                else:
                                                    vias_dict[i] = {'holes': [hole]}
                                                    found_via = True
            elif hasattr(hole, 'isThroughHole') and hole.isThroughHole:
                for i in range(rows):
                    if self.trace_hierarchy[0][i][3] == -1:
                        continue

                    if self.trace_hierarchy[0][i][2] != -1:
                        inner_cnt_ID = self.trace_hierarchy[0][i][2]

                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                            within_trace = cv2.pointPolygonTest(self.trace_contours[i], hole.coordinates, False)
                            if within_trace == 1:
                                found_th = False

                                within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], hole.coordinates, False)

                                if within_trace == 1:

                                    found_th = True

                                    if i in vias_dict.keys():
                                        vias_dict[i]['holes'].append(hole)
                                    else:
                                        vias_dict[i] = {'holes': [hole]}
                                
                                if not found_th:
                                    while not found_th and self.trace_hierarchy[0][inner_cnt_ID][0] != -1:
                                        inner_cnt_ID = self.trace_hierarchy[0][inner_cnt_ID][0]

                                        if self.trace_hierarchy[0][inner_cnt_ID][2] == -1:
                                            within_trace = cv2.pointPolygonTest(self.trace_contours[inner_cnt_ID], hole.coordinates, False)

                                            if within_trace == 1:
                                                
                                                if i in vias_dict.keys():
                                                    vias_dict[i]['holes'].append(hole)
                                                else:
                                                    vias_dict[i] = {'holes': [hole]}
                                                    found_th = True



        ## now create mapping to backside using vias info

        connected_traces_back_dict = {}
        vias_dict_back = {}

        for trace_fID in vias_dict.keys():
            holes = vias_dict[trace_fID]['holes']

            rows = self.trace_back_hierarchy[0].shape[0]
            temp = self.pcb_rgb_back.copy()
            for hole in holes:
                
                for i in range(rows):
                    if self.trace_back_hierarchy[0][i][3] == -1:
                        continue

                    if self.trace_back_hierarchy[0][i][2] != -1:
                        inner_cnt_ID = self.trace_back_hierarchy[0][i][2]

                        found_via = False
                        
                        while self.trace_back_hierarchy[0][inner_cnt_ID][0] != -1:
                            if self.trace_back_hierarchy[0][inner_cnt_ID][2] == -1:
                                within_trace = cv2.pointPolygonTest(self.trace_back_contours[inner_cnt_ID], hole.coordinates, False)
                                if within_trace == 1:
                                    found_via = True
                                    
                                    if i in connected_traces_back_dict.keys():

                                        connected_traces_back_dict[i].append(trace_fID)
                                    else:
                                        connected_traces_back_dict[i] = [trace_fID]

                                    break
                            inner_cnt_ID = self.trace_back_hierarchy[0][inner_cnt_ID][0]


                        if not found_via:
                            #check last one
                            if self.trace_back_hierarchy[0][inner_cnt_ID][2] == -1:
                                within_trace = cv2.pointPolygonTest(self.trace_back_contours[inner_cnt_ID], hole.coordinates, False)
                                if within_trace == 1:
                                    found_via = True
                                    
                                    if i in connected_traces_back_dict.keys():

                                        connected_traces_back_dict[i].append(trace_fID)
                                    else:
                                        connected_traces_back_dict[i] = [trace_fID]




        trace_index = 0
        board_connections_dict = {}
        touched_front_traces = []
        touched_back_traces = []

        for b_trace_ID in connected_traces_back_dict.keys():
            
            connection_dict = {'front traces': [], 'back traces': [b_trace_ID], 'holes': []}

            f_traces = connected_traces_back_dict[b_trace_ID]
            
            
            is_connected_to_existing = False
            for f_trace in f_traces:
                if f_trace not in touched_front_traces:
                    touched_front_traces.append(f_trace)

                    if f_trace not in connection_dict['front traces']:
                        connection_dict['front traces'].append(f_trace)
                        connection_dict['holes'] += vias_dict[f_trace]['holes']
                elif f_trace in connection_dict['front traces']:
                    continue
                else:
                    is_connected_to_existing = True
                    for t_index in board_connections_dict.keys():
                        if f_trace in board_connections_dict[t_index]['front traces']:
                            for ff_trace in f_traces:
                                if ff_trace not in board_connections_dict[t_index]['front traces']:
                                    board_connections_dict[t_index]['front traces'].append(ff_trace)
                                    board_connections_dict[t_index]['holes'] += vias_dict[ff_trace]['holes']
                                if ff_trace not in touched_front_traces:
                                    touched_front_traces.append(ff_trace)

                            if b_trace_ID not in board_connections_dict[t_index]['back traces']:
                                board_connections_dict[t_index]['back traces'].append(b_trace_ID)
                                touched_back_traces.append(b_trace_ID)
                            break
                    break

            if not is_connected_to_existing:
                board_connections_dict[trace_index] = connection_dict
                touched_back_traces.append(b_trace_ID)
                trace_index += 1

        # add other traces that contain pads
        f_pads_ignore = []
        b_pads_ignore = []

        
        for hole in self.hole_arr:
            if hasattr(hole, 'isDrillHole') and hole.isDrillHole:
                f_m_cnt_i = 0
                for f_m_cnt in self.mask_contours:
                    within_pad = cv2.pointPolygonTest(f_m_cnt, hole.coordinates, False)
                    if within_pad == 1:
                        f_pads_ignore.append(f_m_cnt_i)
                        break
                    f_m_cnt_i += 1

                b_m_cnt_i = 0
                for b_m_cnt in self.mask_back_contours:
                    within_pad = cv2.pointPolygonTest(b_m_cnt, hole.coordinates, False)
                    if within_pad == 1:
                        b_pads_ignore.append(b_m_cnt_i)
                        break
                    b_m_cnt_i += 1


        ## start with front traces
        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        t_inv_img_grey = cv2.bitwise_not(t_img_grey)

        front_pad_map = gen_pad_map(self.mask_contours, f_pads_ignore)
        front_trace_map = connected_pads(front_pad_map, self.trace_contours, self.trace_hierarchy, t_inv_img_grey, hole_arr = self.hole_arr)

        tb_img_grey = cv2.cvtColor(self.pcb_rgb_back, cv2.COLOR_BGR2GRAY)
        tb_inv_img_grey = cv2.bitwise_not(tb_img_grey)

        back_pad_map = gen_pad_map(self.mask_back_contours, b_pads_ignore)
        back_trace_map = connected_pads(back_pad_map, self.trace_back_contours, self.trace_back_hierarchy, tb_inv_img_grey, hole_arr = self.hole_arr)


        for trace_index in board_connections_dict.keys():
            f_pads = []
            for f_trace in board_connections_dict[trace_index]['front traces']:
                if f_trace in front_trace_map.keys():
                    f_pads += front_trace_map[f_trace]

            board_connections_dict[trace_index]['front pads'] = f_pads

            b_pads = []
            for b_trace in board_connections_dict[trace_index]['back traces']:
                if b_trace in back_trace_map.keys():
                    b_pads += back_trace_map[b_trace]

            board_connections_dict[trace_index]['back pads'] = b_pads

        ## just check for stragglers in trace map

        for f_trace in front_trace_map.keys():
            if f_trace not in touched_front_traces:
                trace_index += 1
                board_connections_dict[trace_index] = {'front traces': [f_trace], 'back traces': [], 'back pads': [], 'front pads': front_trace_map[f_trace]}

        
        for b_trace in back_trace_map.keys():
            if b_trace not in touched_back_traces:
                trace_index += 1
                board_connections_dict[trace_index] = {'front traces': [], 'back traces': [b_trace], 'back pads': back_trace_map[b_trace], 'front pads': []}

        self.board_connections_dict = board_connections_dict
        self.front_pad_map = front_pad_map
        self.back_pad_map = back_pad_map

        
        
    def create_profile(self):

        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        t_inv_img_grey = cv2.bitwise_not(t_img_grey)

        front_pad_map = gen_pad_map(self.mask_contours)
        front_trace_map = connected_pads(front_pad_map, self.trace_contours, self.trace_hierarchy, t_inv_img_grey)
        self.front_pad_map = front_pad_map

        board_connections_dict = {}
        trace_index = 0
        for f_trace in front_trace_map.keys():
            board_connections_dict[trace_index] = {'front traces': [f_trace], 'back traces': [], 'front pads': front_trace_map[f_trace], 'back pads': []}
            trace_index += 1

        if self.double_sided:
            tb_img_grey = cv2.cvtColor(self.pcb_rgb_back, cv2.COLOR_BGR2GRAY)
            tb_inv_img_grey = cv2.bitwise_not(tb_img_grey)

            back_pad_map = gen_pad_map(self.mask_back_contours)
            back_trace_map = connected_pads(back_pad_map, self.trace_back_contours, self.trace_back_hierarchy, tb_inv_img_grey)
            self.back_pad_map = back_pad_map

            trace_index = len(board_connections_dict.keys())
            for b_trace in back_trace_map.keys():
                board_connections_dict[trace_index] = {'front traces': [], 'back traces': [b_trace], 'front pads': [], 'back pads': back_trace_map[b_trace]}
                trace_index += 1

        self.board_connections_dict = board_connections_dict

                    

    def initialize_via_files(self, mask_front, trace_front, mask_back = '', trace_back = '', drill=''):
        self.pcb_rgb = cv2.imread(trace_front)
        self.mask_rgb = cv2.imread(mask_front)

        if self.double_sided:
            self.pcb_rgb_back = cv2.imread(trace_back)
            self.mask_rgb_back = cv2.imread(mask_back)


        m_img_grey = cv2.cvtColor(self.mask_rgb, cv2.COLOR_BGR2GRAY)
        inv_m_img_grey = cv2.bitwise_not(m_img_grey)
        self.mask_contours, hierarchy = cv2.findContours(inv_m_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)


        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        t_inv_img_grey = cv2.bitwise_not(t_img_grey)
        self.trace_contours, self.trace_hierarchy = cv2.findContours(t_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)


        if self.double_sided:
            mb_img_grey = cv2.cvtColor(self.mask_rgb_back, cv2.COLOR_BGR2GRAY)
            inv_mb_img_grey = cv2.bitwise_not(mb_img_grey)
            self.mask_back_contours, hierarchy = cv2.findContours(inv_mb_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            tb_img_grey = cv2.cvtColor(self.pcb_rgb_back, cv2.COLOR_BGR2GRAY)
            tb_inv_img_grey = cv2.bitwise_not(tb_img_grey)
            self.trace_back_contours, self.trace_back_hierarchy = cv2.findContours(tb_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

            holes_arr = getHolesFromDRL(drill)
            
            if len(holes_arr) > 0:
                self.create_vias_profile(holes_arr)
            else:
                self.create_profile()
        else:
            self.create_profile()
    
    def integrate_trace_cuts(self, trace_cuts_dict):


        if not hasattr(self, 'pcb_rgb_original'):
            self.trace_cuts = True
            self.pcb_rgb_original = self.pcb_rgb.copy()
            self.trace_contours_original = self.trace_contours
            self.trace_hierarchy_original = self.trace_hierarchy
            self.front_pad_map_original = self.front_pad_map
            self.board_connections_dict_original = self.board_connections_dict

            if not hasattr(self, 'pcb_rgb_back_original') and self.double_sided:
                self.pcb_rgb_back_original = self.pcb_rgb_back.copy()
                self.trace_back_contours_original = self.trace_back_contours
                self.trace_back_hierarchy_original = self.trace_back_hierarchy
                self.back_pad_map_original = self.back_pad_map


        self.trace_cuts = True
        self.pcb_rgb_previous = self.pcb_rgb.copy()
        self.trace_contours_previous = self.trace_contours
        self.trace_hierarchy_previous = self.trace_hierarchy
        self.front_pad_map_previous = self.front_pad_map
        self.board_connections_dict_previous = self.board_connections_dict

        if self.double_sided:
            self.pcb_rgb_back_previous = self.pcb_rgb_back.copy()
            self.trace_back_contours_previous = self.trace_back_contours
            self.trace_back_hierarchy_previous = self.trace_back_hierarchy
            self.back_pad_map_previous = self.back_pad_map


        new_pcb_rgb = self.pcb_rgb.copy()


        for trace_cut_cnt in trace_cuts_dict['front cuts']:
            cv2.drawContours(new_pcb_rgb, [trace_cut_cnt], 0, (255, 255, 255), -1)

        if self.double_sided:
            new_pcb_rgb_back = self.pcb_rgb_back.copy()
            for trace_cut_cnt in trace_cuts_dict['back cuts']:
                cv2.drawContours(new_pcb_rgb_back, [trace_cut_cnt], 0, (255, 255, 255), -1)

            self.update_profile(new_pcb_rgb, new_pcb_rgb_back)
        else:
            self.update_profile(new_pcb_rgb)

    def revert(self):

        self.trace_cuts = True

        if not hasattr(self, 'pcb_rgb_previous'):
            return 

        self.pcb_rgb = self.pcb_rgb_previous.copy()
        self.trace_contours = self.trace_contours_previous
        self.trace_hierarchy = self.trace_hierarchy_previous
        self.front_pad_map = self.front_pad_map_previous
        self.board_connections_dict = self.board_connections_dict_previous

        if self.double_sided:
            self.pcb_rgb_back = self.pcb_rgb_back_previous.copy()
            self.trace_back_contours = self.trace_back_contours_previous
            self.trace_back_hierarchy = self.trace_back_hierarchy_previous
            self.back_pad_map = self.back_pad_map_previous

    def revert_original(self):
        self.trace_cuts = False
        self.pcb_rgb = self.pcb_rgb_original.copy()

        self.trace_contours = self.trace_contours_original
        self.trace_hierarchy = self.trace_hierarchy_original
        self.front_pad_map = self.front_pad_map_original
        self.board_connections_dict = self.board_connections_dict_original

        if self.double_sided:
            self.pcb_rgb_back = self.pcb_rgb_back_original.copy()
            self.trace_back_contours = self.trace_back_contours_original
            self.trace_back_hierarchy = self.trace_back_hierarchy_original
            self.back_pad_map = self.back_pad_map_original


    def update_profile(self, pcb_rgb, pcb_rgb_back = []):
        self.pcb_rgb = pcb_rgb
        
        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        self.trace_contours, self.trace_hierarchy = cv2.findContours(t_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)


        if len(pcb_rgb_back) != 0:
            self.pcb_rgb_back = pcb_rgb_back

            tb_img_grey = cv2.cvtColor(self.pcb_rgb_back, cv2.COLOR_BGR2GRAY)
            self.trace_back_contours, self.trace_back_hierarchy = cv2.findContours(tb_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

            self.create_updated_vias_profile()

        else:
            self.create_profile()

    def copy_self(self):

        new_pcb = PCB_Board(self.pcb_file)
        
        new_pcb.board_connections_dict = self.board_connections_dict

        new_pcb.pcb_rgb = self.pcb_rgb.copy()
        new_pcb.mask_rgb = self.mask_rgb.copy()
        new_pcb.mask_contours = self.mask_contours
        new_pcb.trace_contours = self.trace_contours
        new_pcb.trace_hierarchy = self.trace_hierarchy
        new_pcb.front_pad_map = self.front_pad_map.copy()

        #self.double_sided = False
        #CHANGE BACK

        if self.double_sided:
            new_pcb.hole_arr = self.hole_arr
            new_pcb.pcb_rgb_back = self.pcb_rgb_back.copy()
            new_pcb.mask_rgb_back = self.mask_rgb_back.copy()
            new_pcb.trace_back_contours = self.trace_back_contours
            new_pcb.trace_back_hierarchy = self.trace_back_hierarchy
            new_pcb.mask_back_contours = self.mask_back_contours
            new_pcb.back_pad_map = self.back_pad_map.copy()

        if hasattr(self, 'trace_cuts'):
            new_pcb.trace_cuts = self.trace_cuts


        if hasattr(self, 'pcb_rgb_original'):
            new_pcb.pcb_rgb_original = self.pcb_rgb_original.copy()
            new_pcb.trace_contours_original = self.trace_contours_original
            new_pcb.trace_hierarchy_original = self.trace_hierarchy_original
            new_pcb.front_pad_map_original = self.front_pad_map_original
            new_pcb.board_connections_dict_original = self.board_connections_dict_original

            if hasattr(self, 'pcb_rgb_back_original') and self.double_sided:
                new_pcb.pcb_rgb_back_original = self.pcb_rgb_back_original.copy()
                new_pcb.trace_back_contours_original = self.trace_back_contours_original
                new_pcb.trace_back_hierarchy_original = self.trace_back_hierarchy_original
                new_pcb.back_pad_map_original = self.back_pad_map_original

        if hasattr(self, 'pcb_rgb_previous'):
            new_pcb.pcb_rgb_previous = self.pcb_rgb_previous.copy()
            new_pcb.trace_contours_previous = self.trace_contours_previous
            new_pcb.trace_hierarchy_previous = self.trace_hierarchy_previous
            new_pcb.front_pad_map_previous = self.front_pad_map_previous
            new_pcb.board_connections_dict_previous = self.board_connections_dict_previous

            if self.double_sided:
                new_pcb.pcb_rgb_back_previous = self.pcb_rgb_back_previous.copy()
                new_pcb.trace_back_contours_previous = self.trace_back_contours_previous
                new_pcb.trace_back_hierarchy_previous = self.trace_back_hierarchy_previous
                new_pcb.back_pad_map_previous = self.back_pad_map_previous



        return new_pcb

    def view_board(self, trace):

        cpy = self.pcb_rgb.copy()


        for f_trace in self.board_connections_dict[trace]['front traces']:
            cv2.drawContours(cpy, self.trace_contours, f_trace, (255, 0, 0), -1)

        cv2.imshow('pcb rgb', cpy)
        key = cv2.waitKeyEx(0)









    


    def get_num_pads_on_traces(self, traces):
        '''
            Helper function for net matching to return the number of total pads on connected trace

        '''
        print('get_num_pads_on_traces')
        num_pads = 0

        for trace in traces:
            num_pads += len(self.board_connections_dict[trace]['front pads'])
            num_pads += len(self.board_connections_dict[trace]['back pads'])
            

        return num_pads



