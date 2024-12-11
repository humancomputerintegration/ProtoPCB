"""
    Holds component matching module as well as component match representation
    also includes helper functions for image rotation
"""

import cv2 
import numpy as np
import re
import json

import math

from kicad_mod import *
from PCB_utils import *

import os.path

def rotation(image, angleInDegrees):
    """
        Helper function for 'get_match_images_info', 'map_pads', 'get_images_of_match'. Used to rotate images for specific orientations.
        Parameters:
        image (2D array): image to rotate
        angleInDegrees (int): degrees to rotate image by

        Returns:
        (img array) rotated image array
    """
    h, w = image.shape[:2]
    img_c = (w / 2, h / 2)

    rot = cv2.getRotationMatrix2D(img_c, angleInDegrees, 1)

    rad = math.radians(angleInDegrees)
    sin = math.sin(rad)
    cos = math.cos(rad)
    b_w = int((h * abs(sin)) + (w * abs(cos)))
    b_h = int((h * abs(cos)) + (w * abs(sin)))

    rot[0, 2] += ((b_w / 2) - img_c[0])
    rot[1, 2] += ((b_h / 2) - img_c[1])

    outImg = cv2.warpAffine(image, rot, (b_w, b_h), flags=cv2.INTER_LINEAR)
    return outImg

class ComponentMatch():
    """
        Represents a component match and includes relevant details of the match for future analysis.
        Properties include
        score (float) - how well the match performs
        pad_centers (array) - coordinates of the center of each pad hit in the match
        pad_list (array) - an array of all pads hit (identified by contour ID)
        coordinates (tuple) - the x,y coordinates of the match on the mask image
        orientation (int) - the rotation of the component. will be 0, 45, 90,...315
        pad_IDs (dict) - list of pads hit split up by the pin 

        set through component matching process:
        fp_contours (array) - the contours of the match footprint
        pad_coverage (dict) - total area of the coverage of each pad 

    """
    def __init__(self, score, pad_centers, pad_list, coordinates, orientation):
        """
        init for component match 

        Parameters:
        score (float) - how well the match performs
        pad_centers (array) - coordinates of the center of each pad hit in the match
        pad_list (array) - an array of all pads hit (identified by contour ID)
        coordinates (tuple) - the x,y coordinates of the match on the mask image
        orientation (int) - the rotation of the component. will be 0, 45, 90,...315
        """
        self.score = score
        self.pad_centers = pad_centers
        self.pad_list = pad_list
        self.coordinates = coordinates
        self.orientation = orientation
        self.pad_IDs = {}

    def visualize_match(self, title, wait_key, bg_img, offset):
        '''
        Method for visualizing match information

        Parameters:
        title (str) - what you want the title of the popup window to be
        wait_key (bool) - whether or not to have a wait key
        bg_img (2D array) - what to superimpose visualizations on
        offset (tuple) - coordinates to offset contours on
        '''

        img = bg_img.copy()

        for fp_cnt in self.fp_contours:
            cv2.drawContours(img, [fp_cnt], 0, (0, 255, 0), 5, offset=offset)

        if hasattr(self, 'interventions'):
            for intervention in self.interventions:
                if intervention['type'] == 'add solder point':
                    cv2.drawContours(img, [intervention['contour']], 0, (255, 255, 0), -1, offset=offset)
                elif intervention['type'] == 'cut trace':
                    cv2.line(img, intervention['start'], intervention['end'], (255,255,0), 2)


        cv2.imshow(title, img)
        if wait_key:
            key = cv2.waitKeyEx(0)

    def update_traces(self, pcb_board):

        self.touched_traces_dict = {}
        self.touched_traces_list = []

        for pin, pads in self.pad_IDs.items():
            for pad in pads:
                for trace_ID, trace_info in pcb_board.board_connections_dict.items():
                    if self.fb == 'front':
                        if pad in trace_info['front pads']:
                            if pin in self.touched_traces_dict.keys():
                                self.touched_traces_dict[pin].append(trace_ID)
                            else:
                                self.touched_traces_dict[pin] = [trace_ID]
                            self.touched_traces_list.append(trace_ID)
                            break
                    else:
                        if pad in trace_info['back pads']:
                            if pin in self.touched_traces_dict.keys():
                                self.touched_traces_dict[pin].append(trace_ID)
                            else:
                                self.touched_traces_dict[pin] = [trace_ID]
                            self.touched_traces_list.append(trace_ID)
                            break

        return self

    def to_json(self):
        print('cm to json')

        d_obj = vars(self).copy()

        for key, val in d_obj.items():
            

            if key == 'fp_contours':
                str_fp_cnt = '//'.join(str(elem) for elem in val)
                    
                d_obj['fp_contours'] = str_fp_cnt

        return d_obj

    def copy(self):
        cm = ComponentMatch(self.score, self.pad_centers, self.pad_list, self.coordinates, self.orientation)

        for key, val in vars(self).copy().items():
                
            setattr(cm, key, val) 

        return cm

class ComponentMatching():
    """
        Represents process of component matching and related information
        mask_rgb (2D array) - solder mask image
        mask_contours (array) - array of contours for solderable pads
        fp_file (str) - file path for component footprint image
        footprint_rgb (2D array) - image of component footprint
        fp_alpha (2D array) - image of component footprint reversed (alpha)
        fp_contours (array) - contours of fp
        num_fp_pads (int) - number of pads of component footprint
        pcb_rgb (2D array) - image of full PCB with traces
        trace_contours (array) - array of all contours in the PCB image (connected parts)
        pad_map (dict) - each pad with corresponding pad center
        trace_map (dict) - each trace with corresponding pads within trace
    """
    def __init__(self):
        """
        init for component matching

        use different pathways to initialize values

        """
        self.pad_map = {}
        self.trace_map = {}


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

    def initialize_fp_from_file(self, fp_file_png, fp_file):
        '''
        initialize footprint info from file 

        Parameters:
        fp_file_png (str) - file path for component footprint image
        fp_file (str) - file path for .kicad_mod where footprint info can be found

        Sets:
        self.footprint_rgb (2D array) - image of component footprint
        self.fp_alpha (2D array) - image of component footprint reversed (alpha)
        self.fp_contours (array) - contours of fp
        self.num_fp_pads (int) - number of pads of component footprint

        '''

        self.fp_file = fp_file
        if not os.path.exists(self.fp_file):
            name = fp_file.split('/')[-1]
            temp_dir = os.getcwd() + "/temp"
            self.fp_file = temp_dir + "/Footprint Libraries/KiCad.pretty/" + name
            print(self.fp_file)
        
        #read footprint image and create small border to improve masking
        footprint_rgb0 = cv2.imread(fp_file_png)
        self.footprint_rgb = cv2.copyMakeBorder(footprint_rgb0, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255,255,255))
        
        ##generate mask over pads
        self.fp_alpha = cv2.bitwise_not(self.footprint_rgb)
        
        ## use alpha image to find contours of footprint (identify pads)
        fp_alpha_img_grey = cv2.cvtColor(self.fp_alpha, cv2.COLOR_BGR2GRAY)
        self.fp_contours, fp_hierarchy = cv2.findContours(fp_alpha_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        self.num_fp_pads = len(self.fp_contours)

        

    def initialize_via_files(self,mask_file_png, fp_file_png, fp_file, pcb_file_png):
        """
        initialize cm info via the file pngs (useful for component matching pathway)

        Parameters:
        mask_file_png (str) - file path for PCB solder masks image
        fp_file_png (str) - file path for component footprint image
        fp_file (str) - file path for .kicad_mod where footprint info can be found
        pcb_file_png (str) - file path for full PCB image

        """

        #reatouched_refd solder mask image and identify all solder pad contours
        self.mask_rgb = cv2.imread(mask_file_png)
        mask_grey = cv2.cvtColor(self.mask_rgb, cv2.COLOR_BGR2GRAY)
        inv_mask_grey = cv2.bitwise_not(mask_grey)
        self.mask_contours, mask_contours_hierarchy = cv2.findContours(inv_mask_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        self.fp_file = fp_file
        
        #read footprint image and create small border to improve masking
        footprint_rgb0 = cv2.imread(fp_file_png)
        self.footprint_rgb = cv2.copyMakeBorder(footprint_rgb0, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255,255,255))
        
        ##generate mask over pads
        self.fp_alpha = cv2.bitwise_not(self.footprint_rgb)
        
        ## use alpha image to find contours of footprint (identify pads)
        fp_alpha_img_grey = cv2.cvtColor(self.fp_alpha, cv2.COLOR_BGR2GRAY)
        self.fp_contours, fp_hierarchy = cv2.findContours(fp_alpha_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        #cv2.imshow('fp alpha', self.fp_alpha)
        #key = cv2.waitKeyEx(0)
        self.num_fp_pads = len(self.fp_contours)
        
        #read pcb with traces image
        self.pcb_rgb = cv2.imread(pcb_file_png)
        
        #identify all contours in the main pcb image - traces
        t_img_grey = cv2.cvtColor(self.pcb_rgb, cv2.COLOR_BGR2GRAY)
        t_inv_img_grey = cv2.bitwise_not(t_img_grey)
        self.trace_contours, trace_hierarchy = cv2.findContours(t_img_grey, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        
        ## ANALYZE TRACE IMAGE AND CREATE REPRESENTATIONS
        self.pad_map = gen_pad_map(self.mask_contours)
        self.trace_map = connected_pads(self.pad_map, self.trace_contours, trace_hierarchy, t_inv_img_grey)


    def get_pad_info(self, match_loc, w, h, match_contours, fp_alpha, fb='front'):
        """
            Helper function for 'find_matches'. Gets the pad centers for affected pads. Also does some initial processing to ensure that pad coverage area is enough.

            Parameters:
            match_loc (tuple): location of match in question (top left coordinates)
            w (int): width of the component footprint
            h (int): height of the component footprint
            match_contours (array): array of the contours present in the region of interest
            fp_alpha (2D array): img of the footprint of component (inverted)

            Optional:
            fb (str) - designate if you're looking on the back or front of the pcb

            Returns:
            pad_centers (array): array of the coordinates of the pad centers touched
            match_pad_map (dict): dict that contains arrays of relevant pads across each pin
            match_area_map (dict): dict that contains area coverage of each pad
            true_match (bool): whether or not this is an appropriate match (for example, the same pad is not touched by two pins)
            fp_contours (array): the footprint contours from the alpha image
        """

        #**NOTE** fp_alpha is passed in because orientation may be different
        true_match = True
        pad_centers = []
        match_pad_map = {}
        match_area_map = {}
        
        fp_alpha_img = cv2.cvtColor(fp_alpha, cv2.COLOR_BGR2GRAY)
        fp_contours, fp_hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        #going through all contours found in match area (rect of match loc)
        for m_cnt in match_contours:
        
            # check area of match contour in template
            mask = np.zeros(fp_alpha_img.shape[:2], np.uint8)
            cv2.drawContours(mask, [m_cnt], 0, (255,255,255), -1)
            
            
            # where does the pcb intersect with this pad
            intersection = cv2.bitwise_and(fp_alpha_img, mask)
            
            
            int_contours, int_hierarchy = cv2.findContours(intersection, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
            if len(int_contours) == 1:
                #if more, you're using the same pad, if 0 there is no intersection

                #coordinates for intersection
                M_i = cv2.moments(int_contours[0])
                
                #coordinates of contour on crop
                M = cv2.moments(m_cnt)

                if (M['m00'] > 0) and (M_i['m00'] > 0):
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])
                    #get intersection middle too
                    i_cx = int(M_i['m10']/M_i['m00'])
                    i_cy = int(M_i['m01']/M_i['m00'])

                    #adjusted coordinates on main image
                    m_cx = int(match_loc[0] + cx)
                    m_cy = int(match_loc[1] + cy)

                    #loop through original mask image to identify the pads corresponding to intersection points
                    if fb == 'front':
                        mask_contours = self.pcb_board.mask_contours
                    else:
                        mask_contours = self.pcb_board.mask_back_contours


                    for mask_cnt in mask_contours:
                        result = cv2.pointPolygonTest(mask_cnt, (m_cx, m_cy), False)

                        #this point is inside a pad in the solder mask image
                        if result == 1:

                            #get center for the identified pad
                            P_M = cv2.moments(mask_cnt)
                            P_cx = int(P_M['m10']/P_M['m00'])
                            P_cy = int(P_M['m01']/P_M['m00'])

                            if (P_cx, P_cy) not in pad_centers: #need to add this pad
                                pad_centers.append((P_cx, P_cy))
                                
                                for i in range(len(fp_contours)):
                                    id_result = cv2.pointPolygonTest(fp_contours[i], (i_cx, i_cy), False)
                                    if id_result == 1 or id_result == 0:
                                        if i in match_pad_map.keys():
                                            match_pad_map[i].append((P_cx, P_cy))
                                            match_area_map[i] += M_i['m00']
                                        else:
                                            match_pad_map[i] = [(P_cx, P_cy)]
                                            match_area_map[i] = M_i['m00']
                                    

                            else: #pad was already in pad_centers
                                #identify which footprint pad intersection corresponds to
                                for i in range(len(fp_contours)):
                                    id_result = cv2.pointPolygonTest(fp_contours[i], (i_cx, i_cy), False)
                                    if id_result == 1 or id_result == 0:
                                        for id, centers in match_pad_map.items():
                                            if ((P_cx, P_cy) in centers) and (id != i):
                                                true_match = False #if that pad center is associated with a different pin on the template footprint, not a match
            elif len(int_contours) > 1:
                true_match = False
                
        if len(fp_contours) > len(match_pad_map.keys()):
            true_match = False

        for i in range(len(fp_contours)):
            f_M = cv2.moments(fp_contours[i])
            #min_area_coverage = f_M['m00'] * 2 / 10
            min_area_coverage = f_M['m00'] * 5 / 10
            if i in match_area_map.keys() and match_area_map[i] < min_area_coverage:
                true_match = False

        return pad_centers, match_pad_map, match_area_map, true_match, fp_contours
        
        
    def get_list_from_pad_centers(self, pad_centers_list, pad_map):
        """
            Helper function for 'find_matches'. Gets the list of pads that the match covers (identified based on match contours IDs). 

            Parameters:
            pad_centers_list (array): array of the pad centers of hit pads by component
            pad_map (dict): dict with each pad ID and corresponding center
            
            Returns:
            pad_list(array): array of pads hit by match using mask contours IDs
        
        """
        pad_list = []
        for center in pad_centers_list:
            for pad_id, pad_center in pad_map.items():
                if center == pad_center:
                    pad_list.append(pad_id)
        return pad_list
        
        
    def find_matches(self, orig_img, fp_img, alpha, pad_map, orientation, offset=(0,0), fb='front'):
        """
            Returns an array of Component Match objects.

            Parameters:
                    orig_img (int array): A decimal integer
                    fp_img (int arry): Another decimal integer
                    alpha (int array):
                    pad_map (dict): map of pad ID to center coordinates of each pad

            Optional Parameters:
                    offset (tuple) - default (0,0). to only search on a particular location (i.e. for trace matching)
                    fb (str) - designate if searching on the front or back
            Returns:
                    match_list (Component Match array): array of Component Match objects
        """

        #**NOTE** fp_img and alpha passed in for different orientations
        # Store width and height of template in w and h
        h, w = fp_img.shape[:2]
        
        def match_template(img, template):
            h,w = img.shape[:2]
            th,tw = template.shape[:2]

            img = cv2.bitwise_not(img)
            template = cv2.bitwise_not(template)

            fp_white_pix = np.sum(template == 255)

            res = np.zeros(img.shape[:2])

            min_d = min(th,tw)
            min_di = min(h,w)
            
            rad = max(int(min_d/20), int(min_di/140))

            for i in range(0, h, rad):
                for j in range(0, w, rad):

                    if i + th < h and j + tw < w:
                        img_crop = img[i:(i+th), j:(j+tw)]
                        intersection = cv2.bitwise_and(template, img_crop)
                        
                        number_of_white_pix = np.sum(intersection == 255) 
                        number_of_black_pix = np.sum(intersection == 0)


                        if number_of_white_pix == 0:
                            res[i,j] = 0
                        else:
                            res[i,j] = number_of_white_pix/(fp_white_pix * 1.00)
                            
                            
                            

                    else:
                        res[i,j] = 0
                    j += rad
                i += rad

            return res

        # Perform match operations.
        res = match_template(orig_img, fp_img)
        
        threshold = 0.15
        #threshold = 0.5

        matches = 0
        matches_pad_list = []
        match_list = []
        
        max_val = 1
        #rad = int(math.sqrt(h*h+w*w)/16) # 8 seemed to work well to account for close by pads
        i_h,i_w = orig_img.shape[:2]
        min_d = min(i_h,i_w)
        min_di = min(h,w)
        
        rad = max(int(min_di/20), int(min_d/140))


        while max_val > threshold:

            # find max value of correlation image
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
           
            if max_val > threshold:

                ##check num of pads in match

                #crop match img and invert for processing
                if fb == 'front':
                    pcb_img = self.pcb_board.mask_rgb
                else:
                    pcb_img = self.pcb_board.mask_rgb_back
                match_crop = pcb_img[(offset[1] + max_loc[1]):( offset[1] + max_loc[1] + h), (offset[0] + max_loc[0]):(offset[0] + max_loc[0]+w)]


                match_crop_bw = cv2.cvtColor(match_crop, cv2.COLOR_BGR2GRAY)
                match_inv = cv2.bitwise_not(match_crop_bw)

                match_contours, hierarchy = cv2.findContours(match_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                num_match_pads = len(match_contours)
                
                # filter if less than # fp pads (aka the required number of pads)
                #if num_match_pads >= self.num_fp_pads:
                if True:

                    # are these the same pads as a different match?

                    pad_centers_list, match_pad_map, match_area_map, true_match, fp_contours = self.get_pad_info((max_loc[0] + offset[0], max_loc[1] + offset[1]), w, h, match_contours, alpha, fb=fb)
                    


                    pad_list = self.get_list_from_pad_centers(pad_centers_list, pad_map)
                    
                    if true_match and (pad_list not in matches_pad_list) and (len(pad_list) >= self.num_fp_pads):
                        matches_pad_list.append(pad_list)

                        c_match = ComponentMatch(max_val, match_pad_map, pad_list, (max_loc[0] + offset[0], max_loc[1] + offset[1]), orientation)
                        c_match.fp_contours = fp_contours
                        c_match.pad_coverage = match_area_map
                        c_match.fb = fb
                        match_list.append(c_match)

                    # write black circle at max_loc in corr_img
                    cv2.circle(res, (max_loc), radius=rad, color=0, thickness=cv2.FILLED)

                else:
                    #make sure to blackout location so loop doesn't get stuck
                    cv2.circle(res, (max_loc), radius=rad, color=0, thickness=cv2.FILLED)

            else:
                break

        return match_list
        
 
    def find_matches_incomplete(self, orig_img, fp_img, alpha, pad_map, orientation, num_fp_pads, offset=(0,0), fb='front'):
        """
            Returns an array of Component Match objects and allows for an incomplete match.

            Parameters:
                    orig_img (int array): A decimal integer
                    fp_img (int arry): Another decimal integer
                    alpha (int array):
                    pad_map (dict): map of pad ID to center coordinates of each pad
                    num_fp_pads(int): number of fp pads of concern now (after modification)

            Optional Parameters:
                    offset (tuple) - default (0,0). to only search on a particular location (i.e. for trace matching)
                    fb (str) - designate if searching on the front or back
            Returns:
                    match_list (Component Match array): array of Component Match objects
        """

        #**NOTE** fp_img and alpha passed in for different orientations
        # Store width and height of template in w and h
        h, w = fp_img.shape[:2]

        def match_template(img, template):
            h,w = img.shape[:2]
            th,tw = template.shape[:2]

            img = cv2.bitwise_not(img)
            template = cv2.bitwise_not(template)



            fp_white_pix = np.sum(template == 255)

            res = np.zeros(img.shape[:2])

            min_d = min(th,tw)
            min_di = min(self.pcb_board.pcb_rgb.shape[:2])
            
            rad = max(int(min_d/16), int(min_di/100))

            for i in range(0, h, rad):
                for j in range(0, w, rad):

                    if i + th < h and j + tw < w:
                        img_crop = img[i:(i+th), j:(j+tw)]
                        intersection = cv2.bitwise_and(template, img_crop)


                        
                        number_of_white_pix = np.sum(intersection == 255) 
                        number_of_black_pix = np.sum(intersection == 0)

                        if number_of_white_pix == 0:
                            res[i,j] = 0
                        else:
                            res[i,j] = number_of_white_pix/(fp_white_pix * 1.00)


                    else:
                        res[i,j] = 0
                    j += rad
                i += rad

            return res

        # Perform match operations.
        res = match_template(orig_img, fp_img)

        # Specify a threshold (TO DO: OPTION TO CHANGE?)
        threshold = 0.3
        #threshold = 0.5

        matches = 0
        matches_pad_list = []
        match_list = []
        
        max_val = 1
        i_h,i_w = self.pcb_board.pcb_rgb.shape[:2]
        min_d = min(i_h,i_w)
        min_di = min(h,w)

        rad = max(int(min_di/16), int(min_d/100))

        while max_val > threshold:

            # find max value of correlation image
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if max_val > threshold:

                ##check num of pads in match

                #crop match img and invert for processing
                if fb == 'front':
                    pcb_img = self.pcb_board.mask_rgb
                else:
                    pcb_img = self.pcb_board.mask_rgb_back

                match_crop = pcb_img[(offset[1] + max_loc[1]):( offset[1] + max_loc[1] + h), (offset[0] + max_loc[0]):(offset[0] + max_loc[0]+w)]
                match_crop_bw = cv2.cvtColor(match_crop, cv2.COLOR_BGR2GRAY)
                match_inv = cv2.bitwise_not(match_crop_bw)

                match_contours, hierarchy = cv2.findContours(match_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                num_match_pads = len(match_contours)
                
                # filter if less than # fp pads (aka the required number of pads)
                if num_match_pads >= num_fp_pads:

                    # are these the same pads as a different match?

                    pad_centers_list, match_pad_map, match_area_map, true_match, fp_contours = self.get_pad_info((max_loc[0] + offset[0], max_loc[1] + offset[1]), w, h, match_contours, alpha, fb=fb)
                    
                    pad_list = self.get_list_from_pad_centers(pad_centers_list, pad_map)

                    if true_match and (pad_list not in matches_pad_list) and (len(pad_list) >= num_fp_pads):
                        matches_pad_list.append(pad_list)

                        c_match = ComponentMatch(max_val, match_pad_map, pad_list, (max_loc[0] + offset[0], max_loc[1] + offset[1]), orientation)
                        c_match.fp_contours = fp_contours
                        c_match.pad_coverage = match_area_map
                        c_match.incomplete = True
                        c_match.fb = fb

                        match_list.append(c_match)

                    # write black circle at max_loc in corr_img
                    cv2.circle(res, (max_loc), radius=rad, color=0, thickness=cv2.FILLED)

                else:
                    #make sure to blackout location so loop doesn't get stuck
                    cv2.circle(res, (max_loc), radius=rad, color=0, thickness=cv2.FILLED)

            else:
                break

        return match_list

    def get_matches(self):
        """
            Generate the relevant data to visually represent all component matches.

            Returns:
            f_map (array): array of filtered component matches
        
        """
        orientations = [0, 45, 90, 135, 180, 225, 270, 315]

        pin_map, pin_centers_map = self.get_pin_mapping(self.fp_contours, self.fp_file)
        
        cm_o_arr = []

        for orientation in orientations:
            if orientation == 0:
                alpha = self.fp_alpha
                template = self.footprint_rgb
            else:
                alpha = rotation(self.fp_alpha, orientation)
                template= cv2.bitwise_not(alpha)

    
            match_list = self.find_matches(self.pcb_board.mask_rgb, template, alpha, self.pcb_board.front_pad_map, orientation)
            
            if orientation == 0:
                self.relabel_contours(pin_map, match_list, self.pcb_board.front_pad_map)
            else:
                fp_alpha_img = cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY)
                o_fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                o_map = self.map_pads(self.fp_contours, self.fp_alpha, o_fp_contours, alpha, orientation)
                pin_o_map = self.map_rt_cnt_to_pins(pin_map, o_map)
                self.relabel_contours(pin_o_map, match_list, self.pcb_board.front_pad_map)

            cm_o_arr.append(match_list)

            if self.pcb_board.double_sided:
                matchb_list = self.find_matches(self.pcb_board.mask_rgb_back, template, alpha, self.pcb_board.back_pad_map, orientation, fb='back')

                if orientation == 0:
                    self.relabel_contours(pin_map, matchb_list, self.pcb_board.back_pad_map)
                else:
                    fp_alpha_img = cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY)
                    o_fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    o_map = self.map_pads(self.fp_contours, self.fp_alpha, o_fp_contours, alpha, orientation)
                    pin_o_map = self.map_rt_cnt_to_pins(pin_map, o_map)
                    self.relabel_contours(pin_o_map, matchb_list, self.pcb_board.back_pad_map)

                cm_o_arr.append(matchb_list)


        f_map = self.filter_matches(cm_o_arr)
        #print(len(f_map))

        #ff_map = self.valid_single_component_match(f_map, pad_map, trace_map)
        # turn on for single component match
        
        return f_map

    def get_incomplete_matches(self, ignore_pins):
        '''
        searches for matches that can ignore finding a connecting pad for specified pin

        Parameters:
        ignore_pins (array) - int array of pins on footprint that can be ignored

        Returns:
        matches (array) - array of ComponentMatch matches
        '''

        # prepare footprint to ignore pins (remove those pads)
        modified_template = self.footprint_rgb.copy()
        pin_map, pin_centers_map = self.get_pin_mapping(self.fp_contours, self.fp_file)

        removed_cnts = []
        for pin in ignore_pins:
            cnt_ID = -1
            for pin_tuple in pin_map:
                if pin_tuple[0] == pin:
                    cnt_ID = pin_tuple[1]
                    break
            if cnt_ID != -1:
                cv2.drawContours(modified_template, self.fp_contours, cnt_ID, (255,255,255), -1)
                removed_cnts.append(self.fp_contours[cnt_ID])

        #modified template now has erased the pins

        ##get alpha
        modified_alpha = cv2.bitwise_not(modified_template)

        ##get num pads
        mod_fp_alpha_img_grey = cv2.cvtColor(modified_alpha, cv2.COLOR_BGR2GRAY)
        mod_fp_contours, fp_hierarchy = cv2.findContours(mod_fp_alpha_img_grey, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        mod_num_fp_pads = len(mod_fp_contours)

        m_pin_map, m_pin_centers_map = self.get_pin_mapping(mod_fp_contours, self.fp_file)

        orientations = [0, 45, 90, 135, 180, 225, 270, 315]

        cm_o_arr = []

        for orientation in orientations:
            if orientation == 0:
                alpha = modified_alpha
                template = modified_template
            else:
                alpha = rotation(modified_alpha, orientation)
                template= cv2.bitwise_not(alpha)
    
            match_list = self.find_matches_incomplete(self.pcb_board.mask_rgb, template, alpha, self.pcb_board.front_pad_map, orientation, mod_num_fp_pads)

            for match in match_list:
                match.pins_missing = ignore_pins
                match.removed_cnts = removed_cnts

            if orientation == 0:
                self.relabel_contours(m_pin_map, match_list, self.pcb_board.front_pad_map)
            else:
                fp_alpha_img = cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY)
                o_fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                o_map = self.map_pads(self.fp_contours, self.fp_alpha, o_fp_contours, alpha, orientation)
                pin_o_map = self.map_rt_cnt_to_pins(m_pin_map, o_map)
                self.relabel_contours(pin_o_map, match_list, self.pcb_board.front_pad_map)

            cm_o_arr.append(match_list)

            if self.pcb_board.double_sided:
                matchb_list = self.find_matches_incomplete(self.pcb_board.mask_rgb_back, template, alpha, self.pcb_board.back_pad_map, orientation, mod_num_fp_pads, fb='back')

                if orientation == 0:
                    self.relabel_contours(pin_map, matchb_list, self.pcb_board.back_pad_map)
                else:
                    fp_alpha_img = cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY)
                    o_fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    o_map = self.map_pads(self.fp_contours, self.fp_alpha, o_fp_contours, alpha, orientation)
                    pin_o_map = self.map_rt_cnt_to_pins(pin_map, o_map)
                    self.relabel_contours(pin_o_map, matchb_list, self.pcb_board.back_pad_map)

                cm_o_arr.append(matchb_list)

        f_map = self.filter_matches(cm_o_arr)
        f_map = self.add_traces_data_to_matches(f_map)

        ff_map = []

        # do filtering on these matches and attach warnings 
        for match in f_map:
            if self.check_isolated_pins(match):
                self.add_warnings_missing_pins(match)
                ff_map.append(match)


        return ff_map
        
    def get_matches_with_interventions(self):
        '''
            Used to find component matches that only need an added pad or an scratched trace to be complete matches

            Returns
            matches (array) - array of Component Match objects
        '''
        ignore_pins = []
        matches_dict = {}
        for i in range(self.num_fp_pads):
            ignore_pins = [i]
            i_matches = self.get_incomplete_matches(ignore_pins)
            if len(i_matches) > 0:
                matches_dict[i] = i_matches
        #dict not useful now but maybe later for considering which pin to remove to find most matches

        all_matches = []
        for match_i, matches in matches_dict.items():
            
            for match in matches:
                if hasattr(match, 'warnings'):
                    #handle for trace cutting
                    warnings = match.warnings['pins_missing']
                    if 'touched pads' in warnings.keys():
                        
                        self.find_trace_cuts(match, warnings['touched pads'], warnings['touched traces'])
                        
                    elif 'add solder points' in warnings.keys():
                        
                        if warnings['add solder points']:
                            match.interventions = []

                            for cnt in match.removed_cnts:
                                mask = np.zeros(self.footprint_rgb.shape[:2], np.uint8)
                                
                                cv2.drawContours(mask, [cnt], 0, (255,255,255), -1)
                                rotated_mask = rotation(mask, match.orientation)
                                solder_contours, _hierarchy = cv2.findContours(rotated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                                intervention_data = {'type': 'add solder point', 'contour': solder_contours[0]}
                                match.interventions.append(intervention_data)
                                
            all_matches.append(matches)

        filtered_matches = self.filter_matches(all_matches)

        return filtered_matches

    def filter_for_matches_on_trace(self, matches, trace_ID, pins):
        '''
            Function used to turn full matches into an array of matches that are specific to a trace
            
            Parameters:
            trace_ID (int) - ID of trace in trace map
            pins (array) - array of pins that are important for matches

            Returns
            matches (array) - array of ComponentMatch objects
        '''


        f_matches = []

        for match in matches:
            for pin in pins:
                if trace_ID in match.touched_traces_dict[pin]:
                    f_matches.append(match)
                    break
            if len(pins) == 0:
                if trace_ID in match.touched_traces_list:
                    f_matches.append(match)

        return f_matches

    def filter_out_traces(self, matches, traces, pins):
        '''

        Function to remove matches that touch traces on specified pins

        Parameters:
            matches(array) - array of matches to filter on
            traces (array) - array of traces to filter out
            pins (array) - array of pins that are important for matches

            Returns
            matches (array) - array of ComponentMatch objects

        '''

        f_matches = []

        for match in matches:
            remove_match = False
            '''
            for pin in pins:
                for trace_ID in match.touched_traces_dict[pin]:
                    if trace_ID in traces:
                        remove_match = True
                        break
                if remove_match:
                    break
            '''
            for trace_ID in match.touched_traces_list:
                if trace_ID in traces:
                    remove_match = True
                    break
            if not remove_match:
                f_matches.append(match)

        return f_matches


    def get_matches_on_trace(self, trace_ID, pins, ignore_pads = {'front pads': [], 'back pads': []}):
        '''
            Function used by net or circuit matching to only search around pads of relevant traces

            Parameters:
            trace_ID (int) - ID of trace to search on for board
            pins (array) - array of pins that are important for matches

            Optional:
            ignore_pads (dict) - dict of pads to ignore in matching process, has 'front pads' and 'back pads' arrays

            Returns
            matches (array) - array of ComponentMatch objects for pin
            trace_matches (array) - full array of traces matches (not specific to pin)
        '''
        
        pins_full_trace_matches = []
        full_trace_matches = []
        full_matches = []

        if self.pcb_board.get_num_pads_on_traces([trace_ID]) > 10:
            matches = self.get_matches()
            matches = self.add_traces_data_to_matches(matches)
            full_matches += matches
            for match in matches:
                if trace_ID in match.touched_traces_list:
                    full_trace_matches.append(match)
                    pins_covered = True
                    for pin in pins:
                        if trace_ID not in match.touched_traces_dict[pin]:
                            pins_covered = False
                            break

                    if pins_covered:
                        pins_full_trace_matches.append(match)

        else:
            f_trace_pads = self.pcb_board.board_connections_dict[trace_ID]['front pads']
            for pad in f_trace_pads:
                if pad not in ignore_pads['front pads']:
                    matches = self.get_matches_around_pad(pad)
                    matches = self.add_traces_data_to_matches(matches)
                    f_matches = self.match_on_pins(matches, pad, pins)
                    pins_full_trace_matches += f_matches
                    full_trace_matches += matches

            b_trace_pads = self.pcb_board.board_connections_dict[trace_ID]['back pads']
            for pad in b_trace_pads:
                if pad not in ignore_pads['back pads']:
                    matches = self.get_matches_around_pad(pad, fb="back")
                    matches = self.add_traces_data_to_matches(matches)
                    
                    f_matches = self.match_on_pins(matches, pad, pins)

                    pins_full_trace_matches += f_matches
                    full_trace_matches += matches

        pins_full_trace_matches = self.filter_matches([pins_full_trace_matches])
        full_trace_matches = self.filter_matches([full_trace_matches])

        return pins_full_trace_matches, full_trace_matches, full_matches

    def save_matches(self, file, matches):
        print('save_matches')

        data = {'id': 'save_matches', 'matches': []}

        for match in matches:
            data['matches'].append(match.to_json())
            

        with open(file, 'w') as f:
            json.dump(data, f)

    def load_matches(self, file, id):
        with open(file, 'r') as f:
            data = json.load(f)

        matches = []

        for match in data['matches']:
            cm = ComponentMatch(0.00, [], [], (0,0), 0)

            for key,val in match.items():

                if key == 'fp_contours':
                    val = val.replace('\n\n ', '*')
                    val = val.replace('   ', ' ')
                    val = val.replace('  ', ' ')
                    val = val.replace('[ ', '[')
                    val = val.replace(' ', ',')
                    res = val.split('//')

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

                    cm.fp_contours = tuple(np.array(n_arr, dtype=np.int32))
                else:
                    setattr(cm, key, val) 

            matches.append(cm)

        return matches
        




    def filter_out_pads(self, matches, ignore_pads):
        f_matches = []
        for match in matches:
            add_match = True
            if match.fb == 'front':
                m_pads = match.pad_list
                for m_pad in m_pads:
                    if m_pad in ignore_pads['front pads']:
                        add_match = False
                        break

            else:
                m_pads = match.pad_list
                for m_pad in m_pads:
                    if m_pad in ignore_pads['back pads']:
                        add_match = False
                        break

            if add_match:
                f_matches.append(match)

        return f_matches



    def find_trace_cuts(self, match, touched_pads, touched_traces):
        '''
            Helper function for 'get_matches_with_interventions'. NOTE: trace cuts are only to create independence between pin pads here.

            Parameters:
            match (ComponentMatch object) - the incomplete match to check on
            touched_pads (array) - array of touched pad IDs for missing pins contours
            touched_traces (array) - array of touched traces IDs for missing pins contours

            Modifies:
            match - adds interventions 

            Returns:
            bool - true if interventions found
        '''

        if match.fb == 'front':
            mask_contours = self.pcb_board.mask_contours
            trace_contours = self.pcb_board.trace_contours
            pcb_img = self.pcb_board.pcb_rgb
            pad_map = self.pcb_board.front_pad_map
        else:
            mask_contours = self.pcb_board.mask_back_contours
            trace_contours = self.pcb_board.trace_back_contours
            pcb_img = self.pcb_board.pcb_rgb_back
            pad_map = self.pcb_board.back_pad_map

        cut_trace_added = False
        for touched_trace in touched_traces:
            if touched_trace in match.touched_traces_list:
                #cut needs to be made on this trace
                
                # get location of the pads within trace that the cut needs to be between

                # pads of missing pin
                mp_pads_in_trace = []
                for touched_pad in touched_pads:
                    if match.fb == 'front':
                        if touched_pad in self.pcb_board.board_connections_dict[touched_trace]['front pads']:
                            mp_pads_in_trace.append(touched_pad)
                    else:
                        if touched_pad in self.pcb_board.board_connections_dict[touched_trace]['back pads']:
                            mp_pads_in_trace.append(touched_pad)

                # pads of connected pin
                cp_pads_in_trace = []
                for pad_ID in match.pad_list:
                    if match.fb == 'front':
                        if pad_ID in self.pcb_board.board_connections_dict[touched_trace]['front pads']:
                            cp_pads_in_trace.append(pad_ID)
                    else:
                        if pad_ID in self.pcb_board.board_connections_dict[touched_trace]['back pads']:
                            cp_pads_in_trace.append(pad_ID)


                # find mid point between each set of pads

                ## get bounding coordinates for pads of missing pins (rough just based on pad centers)
                mp_lt_X = 100000000000000000
                mp_lt_Y = 100000000000000000
                mp_rb_X = -1 
                mp_rb_Y = -1

                for pad in mp_pads_in_trace:
                    x,y,w,h = cv2.boundingRect(mask_contours[pad])
                    if x < mp_lt_X:
                        mp_lt_X = x
                    if x+w > mp_rb_X:
                        mp_rb_X = x+w
                    if y < mp_lt_Y:
                        mp_lt_Y = y
                    if y+h > mp_rb_Y:
                        mp_rb_Y = y+h

                ## get bounding coordinates for pads of component pins (rough just based on pad centers)

                cp_lt_X = 100000000000000000
                cp_lt_Y = 100000000000000000
                cp_rb_X = -1
                cp_rb_Y = -1

                for pad in cp_pads_in_trace:
                    x,y,w,h = cv2.boundingRect(mask_contours[pad])
                    if x < cp_lt_X:
                        cp_lt_X = x
                    if x+w > cp_rb_X:
                        cp_rb_X = x+w
                    if y < cp_lt_Y:
                        cp_lt_Y = y
                    if y+h > cp_rb_Y:
                        cp_rb_Y = y+h

                ## get mid point between

                c_Y = int(min(cp_rb_Y, mp_rb_Y) + (max(cp_lt_Y, mp_lt_Y) - min(cp_rb_Y, mp_rb_Y))/2)
                c_X = int(min(cp_rb_X, mp_rb_X) + (max(cp_lt_X, mp_lt_X) - min(cp_rb_X, mp_rb_X))/2)


                # horizontal cuts
                if (mp_rb_Y < cp_lt_Y) or (cp_rb_Y < mp_lt_Y):
                    #try horizontal cut
                    

                    trace_img = np.zeros(pcb_img.shape[:2], np.uint8)
                    cv2.drawContours(trace_img, trace_contours, touched_trace, (255,255,255), -1)
                    cv2.line(trace_img, (min(cp_lt_X, mp_lt_X), c_Y), (max(cp_rb_X, mp_rb_X), c_Y), (0,0,0), 2)

                    cut_trace_contours, _hierarchy = cv2.findContours(trace_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                    mp_touched_cut_traces = []

                    for pad in mp_pads_in_trace:
                        ct_cnt_ID = 0
                        for cut_trace_contour in cut_trace_contours:
                            pad_center = pad_map[pad]
                            result = cv2.pointPolygonTest(cut_trace_contour, pad_center, False)
                            if result == 1:
                                mp_touched_cut_traces.append(ct_cnt_ID)
                            ct_cnt_ID += 1

                    cut_worked = True
                    for pad in cp_pads_in_trace:
                        ct_cnt_ID = 0
                        for cut_trace_contour in cut_trace_contours:
                            pad_center = pad_map[pad]
                            result = cv2.pointPolygonTest(cut_trace_contour, pad_center, False)
                            if result == 1:
                                if ct_cnt_ID in mp_touched_cut_traces:
                                    #this cut didn't work
                                    cut_worked = False
                                    break
                            ct_cnt_ID += 1
                        if not cut_worked:
                            break

                    if cut_worked:
                        cut_trace_added = True
                        if hasattr(match, 'interventions'):
                            match.interventions.append({'type': 'cut trace','start': (min(cp_lt_X, mp_lt_X), c_Y),  'end': (max(cp_rb_X, mp_rb_X), c_Y), 'mp_pads': mp_pads_in_trace, 'cp_pads': cp_pads_in_trace})
                        else:
                            match.interventions = [{'type': 'cut trace', 'start': (min(cp_lt_X, mp_lt_X), c_Y),  'end': (max(cp_rb_X, mp_rb_X), c_Y), 'mp_pads': mp_pads_in_trace, 'cp_pads': cp_pads_in_trace}]

                # vertical cuts
                if (mp_rb_X < cp_lt_X) or (cp_rb_X < mp_lt_X):
                    #try vertical cut
                    
                    trace_img = np.zeros(self.pcb_rgb.shape[:2], np.uint8)
                    cv2.drawContours(trace_img, self.trace_contours, touched_trace, (255,255,255), -1)
                    cv2.line(trace_img, (c_X, min(cp_lt_Y, mp_lt_Y)), (c_X, max(cp_rb_Y, mp_rb_Y)), (0,0,0), 2)

                    cut_trace_contours, _hierarchy = cv2.findContours(trace_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                    mp_touched_cut_traces = []

                    for pad in mp_pads_in_trace:
                        ct_cnt_ID = 0
                        for cut_trace_contour in cut_trace_contours:
                            pad_center = pad_map[pad]
                            result = cv2.pointPolygonTest(cut_trace_contour, pad_center, False)
                            if result == 1:
                                mp_touched_cut_traces.append(ct_cnt_ID)
                            ct_cnt_ID += 1

                    cut_worked = True
                    for pad in cp_pads_in_trace:
                        ct_cnt_ID = 0
                        for cut_trace_contour in cut_trace_contours:
                            pad_center = pad_map[pad]
                            result = cv2.pointPolygonTest(cut_trace_contour, pad_center, False)
                            if result == 1:
                                if ct_cnt_ID in mp_touched_cut_traces:
                                    #this cut didn't work
                                    cut_worked = False
                                    break
                        if not cut_worked:
                            break

                    if cut_worked:
                        cut_trace_added = True
                        if hasattr(match, 'interventions'):
                            match.interventions.append({'type': 'cut trace', 'start': (c_X, min(cp_lt_Y, mp_lt_Y)),  'end': (c_X, max(cp_rb_Y, mp_rb_Y)), 'mp_pads': mp_pads_in_trace, 'cp_pads': cp_pads_in_trace})
                        else:
                            match.interventions = [{'type': 'cut trace', 'start': (c_X, min(cp_lt_Y, mp_lt_Y)),  'end': (c_X, max(cp_rb_Y, mp_rb_Y)), 'mp_pads': mp_pads_in_trace, 'cp_pads': cp_pads_in_trace}]


                ## note: could also consider 45 degree cuts
                ## note: if bounding boxes intersect - more creative cuts are needed (probably very rare for component case)

        if cut_trace_added:
            return True
        else:
            return False



    def bounded_coord(self, coord, max_w, max_h):
        '''
            Helper function for 'get_matches_around_pad'

            Parameters:
            coord (tuple) - tuple to redefine according to bounds
            max_w - max width dimension to return
            max_h - max height dimension to return

            Returns:
            coord (tuple) - properly adjusted/bounded tuple
        '''

        if coord[0] < 0:
            #coord[0] = 0
            coord = (0, coord[1])

        if coord[0] > max_w:
            #coord[0] = max_w
            coord = (max_w, coord[1])

        if coord[1] < 0:
            #coord[1] = 0
            coord = (coord[0], 0)

        if coord[1] > max_h:
            #coord[1] = max_h
            coord = (coord[0], max_h)

        return coord

    def get_matches_around_pad(self, pad_ID, fb="front"):
        '''
            Helper function for 'get_matches_on_trace'. Used to get matches around a specific pad.

            Parameters:
            pad_ID (int) - ID of pad in mask_contours

            Optional:
            fb (str) - designate to search on front or back of PCB

        '''
        
        if fb == 'front':
            p_center = self.pcb_board.front_pad_map[pad_ID]
            pad_map = self.pcb_board.front_pad_map
            mask_img = self.pcb_board.mask_rgb
        else:
            p_center = self.pcb_board.back_pad_map[pad_ID]
            pad_map = self.pcb_board.back_pad_map
            mask_img = self.pcb_board.mask_rgb_back

        h, w = self.footprint_rgb.shape[:2]

        max_h, max_w = mask_img.shape[:2]

        m_dim = max(h, w)

        #bounds
        #left-top
        lt_coord = (p_center[0]-(2*m_dim), p_center[1]-(2*m_dim))
        
        lt_coord = self.bounded_coord(lt_coord, max_w, max_h)
        

        #right-bottom
        rb_coord = (p_center[0]+ (2*m_dim), p_center[1] + (2*m_dim))
        rb_coord = self.bounded_coord(rb_coord, max_w, max_h)



        cropped_search_img = mask_img[lt_coord[1]: rb_coord[1], lt_coord[0]: rb_coord[0]]
        
        orientations = [0, 45, 90, 135, 180, 225, 270, 315]

        pin_map, pin_centers_map = self.get_pin_mapping(self.fp_contours, self.fp_file)

        cm_o_arr = []

        for orientation in orientations:
            if orientation == 0:
                alpha = self.fp_alpha
                template = self.footprint_rgb
            else:
                alpha = rotation(self.fp_alpha, orientation)
                template= cv2.bitwise_not(alpha)
    
            match_list = self.find_matches(cropped_search_img, template, alpha, pad_map, orientation, offset=lt_coord, fb=fb)
            
            if orientation == 0:
                self.relabel_contours(pin_map, match_list, pad_map)
            else:
                fp_alpha_img = cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY)
                o_fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                o_map = self.map_pads(self.fp_contours, self.fp_alpha, o_fp_contours, alpha, orientation)
                pin_o_map = self.map_rt_cnt_to_pins(pin_map, o_map)
                self.relabel_contours(pin_o_map, match_list, pad_map)

            cm_o_arr.append(match_list)


        f_matches = self.filter_matches(cm_o_arr)

        return f_matches

    def match_on_pins(self, matches, pad_ID, pin_arr):
        '''
            Helper function for 'get_matches_on_trace'. Verifies that component match ensures connections for all pins needed for net AND is connected to proper pad

            Parameters:
            matches (array) - array of matches to filter on
            pad_ID (int) - contour ID that 
            pin_arr (array) - array of pin IDs that need to be connected

            Returns:
            f_matches (array) - filtered array of matches that properly connects pads/pins
        '''

        f_matches = []

        for match in matches:
            add_to_matches = True
            # pins are connected if multiple
            if len(pin_arr) > 1:
                touched_traces = match.touched_traces_dict[pin_arr[0]]
                
                for pin in pin_arr[1:]:
                    s_touched_traces = match.touched_traces_dict[pin]
                    pin_within_traces = False
                    for s_touched_trace in s_touched_traces:
                        if s_touched_trace in touched_traces:
                            pin_within_traces = True

                    if not pin_within_traces:
                        add_to_matches = False
                        break

            if not add_to_matches:
                break

            # connected to proper pad?

            touches_pad = False

            for pin in pin_arr:
                pads_touched = match.pad_IDs[pin]
                for pad in pads_touched:
                    if pad == pad_ID:
                        touches_pad = True
                        break

            if not touches_pad:
                add_to_matches = False

            if add_to_matches:
                f_matches.append(match)

        return f_matches


    def add_traces_data_to_matches(self, matches):
        '''
            Function to add touched traces to component matches

            Parameters:
            matches (array) - array of matches that don't have trace info attached

            Returns:
            match array that has data updated
        '''
        n_matches = []
        for match in matches:
            match.touched_traces_dict = {}
            match.touched_traces_list = []
            for pin, pads in match.pad_IDs.items():
                for pad in pads:
                    for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
                        if match.fb == 'front':
                            if pad in trace_info['front pads']:
                                if pin in match.touched_traces_dict.keys():
                                    match.touched_traces_dict[pin].append(trace_ID)
                                else:
                                    match.touched_traces_dict[pin] = [trace_ID]
                                match.touched_traces_list.append(trace_ID)
                                break
                        else:
                            if pad in trace_info['back pads']:
                                if pin in match.touched_traces_dict.keys():
                                    match.touched_traces_dict[pin].append(trace_ID)
                                else:
                                    match.touched_traces_dict[pin] = [trace_ID]
                                match.touched_traces_list.append(trace_ID)
                                break

            if len(match.touched_traces_dict.keys()) == len(match.pad_IDs.keys()):
                n_matches.append(match)

        return n_matches

    def add_warnings_missing_pins(self, match):
        '''
            Helper function for 'get_incomplete_matches'. Adds relevant warnings for incomplete matches regarding the pins that weren't accounted for.

            Parameters: 
            match (ComponentMatch object) - match object to check and attach warnings to

        '''

        h, w = rotation(self.footprint_rgb, match.orientation).shape[:2]

        if match.fb == 'front':
            mask_img = self.pcb_board.mask_rgb
        else:
            mask_img = self.pcb_board.mask_rgb_back

        match_crop = mask_img[match.coordinates[1]: match.coordinates[1] + h, match.coordinates[0]: match.coordinates[0] + w]
        match_crop_bw = cv2.cvtColor(match_crop, cv2.COLOR_BGR2GRAY)
        inv_match_crop = cv2.bitwise_not(match_crop_bw)

        touched_pads = []
        touched_traces = []

        touched_pad_centers = []

        for removed_cnt in match.removed_cnts:
            # check is this on top of any solderable pad areas

            mask = np.zeros(self.footprint_rgb.shape[:2], np.uint8)
            cv2.drawContours(mask, [removed_cnt], 0, (255,255,255), -1)
            rotated_mask = rotation(mask, match.orientation)

            # where does the solder mask image intersect with this pad
            intersection = cv2.bitwise_and(inv_match_crop, rotated_mask)
            int_contours, int_hierarchy = cv2.findContours(intersection, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            

            for int_cnt in int_contours:
                M = cv2.moments(int_cnt)

                if (M['m00'] > 0):
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])

                    #adjusted coordinates on main image
                    m_cx = int(match.coordinates[0] + cx)
                    m_cy = int(match.coordinates[1] + cy)

                    if match.fb == 'front':
                        mask_contours = self.pcb_board.mask_contours
                    else:
                        mask_contours = self.pcb_board.mask_back_contours
                    for mask_cnt in mask_contours:
                        result = cv2.pointPolygonTest(mask_cnt, (m_cx, m_cy), False)

                        if result == 1:
                            #this point is inside a pad in the solder mask image

                            #get center for the identified pad
                            P_M = cv2.moments(mask_cnt)
                            P_cx = int(P_M['m10']/P_M['m00'])
                            P_cy = int(P_M['m01']/P_M['m00'])
                            touched_pad_centers.append((P_cx, P_cy))

            for touched_pad_center in touched_pad_centers:
                if match.fb == 'front':
                    for pad_id, pad_center in self.pcb_board.front_pad_map.items():
                        if touched_pad_center == pad_center:
                            touched_pads.append(pad_id)

                            for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
                                if pad_id in trace_info['front pads']:
                                    touched_traces.append(trace_ID)
                                    break
                            break
                else:
                    for pad_id, pad_center in self.pcb_board.back_pad_map.items():
                        if touched_pad_center == pad_center:
                            touched_pads.append(pad_id)

                            for trace_ID, trace_info in self.pcb_board.board_connections_dict.items():
                                if pad_id in trace_info['back pads']:
                                    touched_traces.append(trace_ID)
                                    break
                            break


        if len(touched_pads) > 0:
            if hasattr(match, 'warnings'):
                match.warnings['pins_missing'] = {'touched traces': touched_traces, 'touched pads': touched_pads}
            else:
                match.warnings = {'pins_missing': {'touched traces': touched_traces, 'touched pads': touched_pads}}
        else:
            # nothing to solder pin to, consider adding solder pad
            if hasattr(match, 'warnings'):
                match.warnings['pins_missing'] = {'add solder points': True}
            else:
                match.warnings = {'pins_missing': {'add solder points': True}}
    
    def relabel_contours(self, cnt_map, matches, pad_map):
        """
            Helper function for 'get_matches'. Relabels matches depending on the appropriate pin to contour mapping.
            Parameters:
            cnt_map (dict): mapping between rotated component contours and original component contours with pins
            matches (array): array of all the matches found with this rotation
            pad_map(dict): dict of pads and corresponding center coordinates.

            Effects each match element in matches array
        
        """

        for match in matches:
            
            pad_centers = {}
            pad_coverage = {}
            for cnt_mapping in cnt_map:
                pad_centers[cnt_mapping[0]] = match.pad_centers[cnt_mapping[1]].copy()
                pad_coverage[cnt_mapping[0]] = match.pad_coverage[cnt_mapping[1]]
            
            match.pad_centers = pad_centers
            match.pad_coverage = pad_coverage

            for pin, arr_pad_centers in match.pad_centers.items():
                match.pad_IDs[pin] = self.get_list_from_pad_centers(arr_pad_centers, pad_map)

    
    def map_rt_cnt_to_pins(self, pin_cnt_map, orig_cnt_map):
        """
            Helper function for 'get_matches'. Reorganizes pin labeling to "true" pin labels based on footprint representation.
            Parameters:
            pin_cnt_map (dict): "true" match between pin labels and component footprint contours
            orig_cnt_map (dict): dict of match of contours between rotation and original contours

            Returns:
            n_cnt_map (dict): adjusted mapping between pin label and contours
        
        """
        n_cnt_map = []
        for mapping in pin_cnt_map:
            o_val = mapping[1]
            for o_mapping in orig_cnt_map:
                if o_mapping[0] == o_val:
                    n_cnt_map.append((mapping[0], o_mapping[1]))

        return n_cnt_map
        
    def get_pin_mapping(self, orig_fp_contours, fp_filename):
        """
            Helper function for 'get_matches'. Uses original footprint file to create a mapping of which pin is attached to which contour in footprint.
            Parameters:
            orig_fp_contours (array): array of contours in the footprint image
            fp_filename (str): string of the footprint file 

            Returns:
            map (array): mapping between pin label and contours
            p_no_loc(dict): pad to pad center map
        
        """
        
        if not os.path.exists(fp_filename):
            name = fp_filename.split('/tests')
            fp_filename = name[0] + name[1]
        footprint_kicad = KicadMod(filename=fp_filename)

        pads = footprint_kicad._getPads()
        (h, w) = self.fp_alpha.shape[:2]

        map = []
        p_no_loc = {}
        max_pin = 0

        temp = self.fp_alpha.copy()


        for pad in pads:
            x = pad['pos']['x']
            y = pad['pos']['y']

            x = int(x*48)
            y = int(y*48)

            p_x = x+(w//2)
            p_y = y + (h//2)

            cv2.circle(temp, (p_x, p_y), 5, (255, 0, 0), -1)

            p_no_loc[pad['number']] = (p_x, p_y)

            for i in range(len(orig_fp_contours)):
                result = cv2.pointPolygonTest(orig_fp_contours[i], (p_x, p_y), False)
                if result == 1:
                    map.append((pad['number'], i))
                    


        if len(map) < len(pads):
            map = []
            for pad in pads:
                x = pad['pos']['x']
                y = pad['pos']['y']

                x = int(x*48)
                y = int(y*48)

                p_x = x+(w//2)
                p_y = y + (h//2)

                p_no_loc[pad['number']] = (p_x, p_y)

                for i in range(len(orig_fp_contours)):
                    result = cv2.pointPolygonTest(orig_fp_contours[i], (p_x, p_y), False)
                    if result == 1:
                        map.append((pad['number'], i))
                            
        return map, p_no_loc
        
    def map_pads(self, orig_contours, orig_alpha, rt_contours, rt_alpha, rt_degrees):
        """
            Helper function for 'get_matches'. Uses original footprint file to create a mapping of which pin is attached to which contour in footprint.
            Parameters:
            orig_fp_contours (array): array of contours in the footprint image
            fp_filename (str): string of the footprint file 

            Returns:
            map (array): mapping between pin label and contours
        
        """
        map = []
        for i in range(len(orig_contours)):

            # isolate this pad shape and perform rotation
            mask = np.zeros(orig_alpha.shape[:2], np.uint8)
            cv2.drawContours(mask, orig_contours, i, (255,255,255), -1)
            rt_mask = rotation(mask, rt_degrees)


            pad_contour, hierarchy = cv2.findContours(rt_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            M = cv2.moments(pad_contour[0])
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])


            for j in range(len(rt_contours)):
                result = cv2.pointPolygonTest(rt_contours[j], (cx, cy), False)
                if result == 1:
                    map.append((i,j))

        return map
        
    def filter_matches(self, arr_matches):
        '''
        Returns array of matches that removes any duplicates (i.e. crosses over the same pad).

                Parameters:
                        arr_matches (match array): Collective array of all matches array

                Returns:
                        r_f_matches (array): filtered matches (if it touches the same pads but one has a higher score, remove the other)
        '''

        f_map = []
        r_f_matches = []

        b_map = []
        r_b_matches = []

        for match_arr in arr_matches:
            for match in match_arr:

                if match.fb == 'front' and match.pad_centers not in f_map:
                    f_map.append(match.pad_centers)
                    r_f_matches.append(match)
                elif match.fb == 'back' and match.pad_centers not in b_map:
                    b_map.append(match.pad_centers)
                    r_b_matches.append(match)
                else:
                    # compare matches based on score, if higher score change r_f

                    if match.fb == 'front':
                        for r_f_match in r_f_matches:
                            if r_f_match.pad_centers == match.pad_centers:

                                #if r_f_match.score > match.score:
                                if self.min_pin_coverage(match.pad_coverage) > self.min_pin_coverage(r_f_match.pad_coverage):
                                    r_f_matches.remove(r_f_match)
                                    r_f_matches.append(match)
                    else:
                        for r_b_match in r_b_matches:
                            if r_b_match.pad_centers == match.pad_centers:

                                #if r_f_match.score > match.score:
                                if self.min_pin_coverage(match.pad_coverage) > self.min_pin_coverage(r_b_match.pad_coverage):
                                    r_b_matches.remove(r_b_match)
                                    r_b_matches.append(match)
                                              
        return r_f_matches + r_b_matches

    def sort_matches(self, matches):
        '''
        Sorts matches based on pad coverage

        Parameters:
        matches (arr) - array of matches

        Returns:
        sorted_matches (arr) - array of sorted matches
        '''

        matches.sort(key=lambda x: self.min_pin_coverage(x.pad_coverage), reverse=True)

        return matches

    def min_pin_coverage(self, coverage_dict):
        '''
        Helper function for 'filter_matches'. Returns the minimum pin coverage across pins.

                Parameters:
                        coverage_dict (dict): each pin, coverage area

                Returns:
                        (int): coverage minimum
        '''
        min_coverage = 1000000000
        for pin, coverage in coverage_dict.items():
            if coverage < min_coverage:
                min_coverage = coverage

        return min_coverage
        
    def valid_single_component_match(self, f_map, pad_map, trace_map):
        """
            Helper function for 'get_matches'. Only used if want to verify that all pads have a place to solder connections to.
            Parameters:
            f_map (array): array of matches
            pad_map (dict): dict of pads and corresponding center coordinates.
            trace_map (dict): dict of traces and corresponding pads within them.

            Returns:
            ff_map (array): array of matches that are further filtered
        
        """
        ff_map = []
        for match in f_map:
            valid_match = True
            # each component pad and the centers of pads on searched upon PCB
            for pad, centers in match.pad_centers.items():
                pad_connected = False
                # for each pad on searched upon PCB
                for center in centers:
                    # is it connected to another solderable pad area?

                    # which pad ID does this belong to?
                    pad_ID = list(pad_map.keys())[list(pad_map.values()).index(center)]

                    for trace_ID, connected_pads in trace_map.items():
                        if pad_ID in connected_pads:
                            if len(connected_pads) > 1:
                                pad_connected = True

                if not pad_connected:
                    valid_match = False

            if valid_match:
                ff_map.append(match)

        return ff_map
        
    def check_isolated_pins(self, match, ignore_pairs=[]):
        '''
            Check if pins are properly isolated from each other (no shorts between them)

            Parameters: 
            match (ComponentMatch) - Component Match object, represents a component match.

            Optional Parameters:
            ignore_pairs

            Returns:
            bool - True if proper isolation, False if not
        '''

        touched_traces = []
        touched_traces_by_pin = {}
        

        for pin, traces in match.touched_traces_dict.items():
            for trace in traces:
                if trace not in touched_traces:
                    touched_traces.append(trace)
                    if trace in touched_traces_by_pin.keys():
                        touched_traces_by_pin[trace].append(pin)
                    else:
                        touched_traces_by_pin[trace] = [pin]
                else:
                    #identify the pin(s) that already is part of that trace
                    touched_pins = touched_traces_by_pin[trace]
                    for touched_pin in touched_pins:
                        if (pin, touched_pin) not in ignore_pairs:
                            return False

        return True





    def get_images_of_match(self, match, pad_map, trace_map):
        """
            Only used to get images for visualization purposes.
            Parameters:
            match (ComponentMatch): match to visualize
            pad_map (dict): dict of pads and corresponding center coordinates.
            trace_map (dict): dict of traces and corresponding pads within them.

            Returns:
            match_crop (2D array): image of the match footprint overlayed on pcb
            pcb_view_img (2D array): image of the match with relevant traces colored in
        
        """
        pcb_view_img = self.pcb_rgb.copy()
        for pad, centers in match.pad_centers.items():
            for center in centers:
                pad_ID = list(pad_map.keys())[list(pad_map.values()).index(center)]

                for trace_ID, connected_pads in trace_map.items():
                    if pad_ID in connected_pads:
                        for c_pad in connected_pads:
                            cv2.drawContours(pcb_view_img, self.mask_contours, c_pad, (255,0,0), 2)
                
                cv2.drawContours(pcb_view_img, self.mask_contours, pad_ID, (255,255,0), -1)
        
        #draw overlap in another window
        alpha_rt = rotation(self.fp_alpha, match.orientation)
        fp_alpha_img = cv2.cvtColor(alpha_rt, cv2.COLOR_BGR2GRAY)
        fp_contours, hierarchy = cv2.findContours(fp_alpha_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        h, w = alpha_rt.shape[:2]
    
        loc = [match.coordinates[0], match.coordinates[1]]
        ct_img_rgb = self.pcb_rgb.copy()
        match_crop = ct_img_rgb[loc[1]:(loc[1] + h), loc[0]:(loc[0]+w)]
        for fp_cnt in fp_contours:
            cv2.drawContours(match_crop, [fp_cnt], 0, (0, 0, 255), 2)
        
        
        return match_crop, pcb_view_img

    def get_transparent_overlay(self, match):
        '''
            Used for gui displays, returns an image that is transparent with connected pads highlighted

            Returns:
            pcb_view_img (2D array): image of match with pads colored in (transparent)

        '''
        if match.fb == 'front':
            pcb_rgb = self.pcb_board.pcb_rgb
            pad_map = self.pcb_board.front_pad_map
            mask_contours = self.pcb_board.mask_contours
        else:
            pcb_rgb = self.pcb_board.pcb_rgb_back
            pad_map = self.pcb_board.back_pad_map
            mask_contours = self.pcb_board.mask_back_contours

        alpha_temp = np.zeros(pcb_rgb.shape[:3], np.uint8)
        colored_pads_temp = alpha_temp.copy()


        for pad, centers in match.pad_centers.items():
            for center in centers:
                pad_ID = list(pad_map.keys())[list(pad_map.values()).index(center)]
                #cv2.drawContours(alpha_temp, mask_contours, pad_ID, (255,255,255), -1)
                cv2.drawContours(colored_pads_temp, mask_contours, pad_ID, (255,255,0), -1)

        for fp_cnt in match.fp_contours:
            cv2.drawContours(colored_pads_temp, [fp_cnt], 0, (0,0, 255), 6, offset=match.coordinates)


        pin_1_pad = match.pad_IDs['1'][0]
        
        pin_1_center = pad_map[pin_1_pad]
        cv2.circle(colored_pads_temp,pin_1_center, 15, (0, 0, 255), -1)

        alpha = np.sum(colored_pads_temp, axis=-1) > 0
        alpha = np.uint8(alpha * 255)
        overlay_img = np.dstack((colored_pads_temp, alpha))

        return overlay_img


 
