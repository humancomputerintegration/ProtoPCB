import cairosvg
import os
import re
import subprocess
from svg_edit import *
import cv2
from Objectifier import Objectifier

'''

INPUT VALIDATION METHODS

'''

def checkFileExists(file_address):
    if not os.path.exists(file_address):
        print(f"Error: File '{file_address}' does not exist.")
        return False
    
    # Try to load the image using cv2.imread to further validate
    try:
        img = cv2.imread(file_address)
        if img is None:
            print(f"Error: '{file_address}' is not a valid image file.")
            return False
    except Exception as e:
        print(f"Error: Exception occurred while trying to load '{file_address}': {str(e)}")
        return False
    
    return True


# check color format is (#, #, #) where # are integers 0-255
def validateRGB(color):
    if isinstance(color, str):
        regex = "^\(\s*(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\s*,\s*(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\s*,\s*(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\s*\)$"
        return bool(re.match(regex, color))
    elif isinstance(color, tuple):
        if not isinstance(color, tuple) or len(color) != 3:
            return False
        for component in color:
            if not isinstance(component, int) or not (0 <= component <= 255):
                return False
        return True
    else:
        return False



# INPUTS: String full address to a file, String type of file ('png', 'jpeg', etc)
# OUTPUT: boolean, is the file of correct type
def validateFileType(file, type):
    # Extract file extension
    file_extension = getFileExtension(file)
    
    # Compare file extension with the specified type
    if file_extension.lower() == type.lower():
        return True
    else:
        print(f"Error: File '{file}' does not have the correct type (.'{type}')")
        raise ValueError(f"File '{file}' does not have the correct type (.'{type}')'.")
        return False

# INPUTS: String full address to a file
# OUTPUT: the . extension of the file
def getFileExtension(file):
    return os.path.splitext(file)[1][1:].strip()

# INPUTS: String full address to a file , String new desired type of file ('png', 'jpeg', etc)
# OUTPUT: String, is the new file address
def changeFileType(file, newType):
    # Split the file path into directory path and file name
    directory, filename = os.path.split(file)
    
    # Split the filename into base name and extension
    basename, old_extension = os.path.splitext(filename)
    
    # Clean up the extension (remove the dot)
    old_extension = old_extension[1:] if old_extension.startswith('.') else old_extension
    
    # Normalize newType to lowercase
    newType, old_extension = newType.lower(), old_extension.lower()
    
    # If the current extension is the same as newType, return the original file address
    if old_extension == newType:
        return file
    
    # If there's no extension in the original filename, simply add the newType
    if not old_extension:
        new_filename = f"{basename}.{newType}"
    else:
        # Replace the old extension with the new one
        new_filename = f"{basename}.{newType}"
    
    # Combine the directory and the new filename to get the new file address
    new_file_address = os.path.join(directory, new_filename)
    
    return new_file_address



'''

IMAGE RELATED METHODS

'''


def svg_to_png(svg_file):
	cairosvg.svg2png(url=svg_file, write_to=svg_file[:-3] + "png", scale=4, background_color="white")


# displays an image using opencv, good for testing
def displayImage(title, image):
    # Display the image (optional)
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()




'''

CLI RELATED METHODS

'''


# kicad_cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
def create_pcb_png(pcb_filename, outputDir, kicad_cli):
	complete = subprocess.run([kicad_cli, "pcb", "export", "svg", pcb_filename, "-o", outputDir + "/traces.svg", "--layers", "F.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
	print(complete)

	#complete = subprocess.run(["svgexport", output + "/traces.svg", output + "/traces.png", "4x", "svg{background:white;}"])
	svg_to_png(outputDir + "/traces.svg")


def create_pcb_png_back(pcb_filename, outputDir, kicad_cli):
    complete = subprocess.run([kicad_cli, "pcb", "export", "svg", pcb_filename, "-o", outputDir + "/traces.svg", "--layers", "B.Cu", "--black-and-white", "--page-size-mode", "2", "--exclude-drawing-sheet"])
    print(complete)

	#complete = subprocess.run(["svgexport", output + "/traces.svg", output + "/traces.png", "4x", "svg{background:white;}"])
    svg_to_png(outputDir + "/traces.svg")


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

    width = maxX - minX
    height = maxY-minY

    return (minX, minY), width, height
