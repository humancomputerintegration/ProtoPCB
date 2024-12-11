import math
import gerber
import cv2
from gerber.excellon import *
from globalHelperFunctions import *
import re
import numpy as np


# INPUT : full path to a file .drl 
# OUTPUT : LIST of TUPLES in format [(x1, y1), (x2, y2), ...] to represent vias' coordinates
# this method finds vias assuming that the smallest hole size on a given DRL file is the via (not a reliable alg)
# https://github.com/curtacircuitos/pcb-tools/tree/master LINK FOR GITHUB REPO USED
def findViasFromDrlFile(file):

    checkFileExists(file)


    excellonFileObject = gerber.read(file)
    drillhits = excellonFileObject.hits #.hits returns a list of DrillHit objects (class outlined in the github)
    smallestHole = math.inf
    viaCoordinates = []

    for dh in drillhits:
        tool = dh.tool
        diameter = tool.diameter

        coordinates = dh.position
        xCoordinate = coordinates[0]
        yCoordinate = coordinates[1]
        
        if(smallestHole > diameter):
            smallestHole = diameter
            viaCoordinates = []
            viaCoordinates.append((xCoordinate, yCoordinate))

        elif(diameter == smallestHole):
            viaCoordinates.append((xCoordinate, yCoordinate))

      
    return viaCoordinates



# INPUT: full path to a DRL file (PTH or NPTH)
# OUTPUT: list of Hole objects that correspond to each hole on the drill file
def getHolesFromDRL(file):

    holes = []
    excellonFileObject = gerber.read(file)
    drillhits = excellonFileObject.hits #.hits returns a list of DrillHit objects (class outlined in the github)

    
    for dh in drillhits:
        if isinstance(dh, DrillSlot):
            holeDiameter = dh.tool.diameter
            holePlated = dh.tool.plated

            (sx,sy) = dh.start
            (ex,ey) = dh.end

            x = (sx + ex)/2.0
            y = (sy + ey)/2.0

            coordinates = (x,y)
            holes.append(Hole(diameter=holeDiameter, isPlated=holePlated, isVia=False, coordinates=coordinates))


        else:
            tool = dh.tool
            holeDiameter = tool.diameter
            holePlated = tool.plated

            coordinates = dh.position
            xCoordinate = coordinates[0]
            yCoordinate = coordinates[1]  

            holes.append(Hole(diameter=holeDiameter, isPlated=holePlated, isVia=False, coordinates=(xCoordinate, yCoordinate)))


    return holes



#INPUT list of coordinates relative to TOP LEFT CORNER OF PCB BOARD in form [(x1, y1), (x2, y2), etc], the width and height of a pcb board
#RETURNS list of the mirrored coordinates relative to TOP LEFT CORNER OF PCB BOARD when the board is flipped around (top right corner from front facing)
def mirrorCoordinates(coordinates, pcbWidth, pcbHeight):
    mirrored_coords = []
    for x, y in coordinates:
        mirrored_y = pcbHeight - y  # Mirror only across the y-axis
        mirrored_coords.append((x, mirrored_y))
    return mirrored_coords



# INPUTS : coordinates (list of tuples), 
#           png_img_path (image you want to write on top of), 
#           viaColor (color of dots we are writing),
#           pcb_file_path (full path to the original pcb that the image is generated from)
# RETURN : new image with via coordinates on it
def printCoordinatesOntoPNG(coordinates, input_png_img_path, viaColor, pcb_file_path):

    #INPUT VALIDATION : color, input path, coordinates
    
    if not validateRGB(viaColor):
        viaColor = (0, 0, 255)
    
    checkFileExists(input_png_img_path)
    if not validateFileType(input_png_img_path, "png"):
        return
    
    checkFileExists(pcb_file_path)
    if not validateFileType(pcb_file_path, "kicad_pcb"):
        return

    if not isinstance(coordinates, list):
        print(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
        raise ValueError(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
        return
    
    for coord in coordinates:
        if not isinstance(coord, tuple) or len(coord) != 2:
            print(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
            raise ValueError(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
            return
        if not all(isinstance(val, (int, float)) for val in coord):
            print(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
            raise ValueError(f"Error: Coordinates are not in proper format [(x1, y1), (x2, y2), ...]")
            return
        


    # Convert coordinates to numpy array for easier manipulation
    coordinates = np.array(coordinates)


    image = cv2.imread(input_png_img_path)
    imgHeight, imgWidth, channels = image.shape # height and width of the image in PIXELS, (not relevant) number of channels in the image (e.g., 3 for RGB color images)
    #print(imgHeight, imgWidth)

    boardCoordinates, pcbWidth, pcbHeight = get_board_bounds(pcb_file_path)


    # Draw dots on the image for each coordinate
    for (x, y) in coordinates:

        print(x,y)   
        y = (abs(y) / pcbHeight) * imgHeight 
        x = (abs(x) / pcbWidth) * imgWidth    
        x, y = (abs(round(x)), abs(round(y)))
        print(x,y)

        cv2.circle(image, (x,y), 5, viaColor, -1)
        displayImage('Vias Marked', image)

    return image



# CLASS HOLE - for each hole listed on the drill file, we will store if it's plated, if it's a via, coordinates, and the diameter
class Hole:
    def __init__(self, diameter: float, isPlated: bool, isVia: bool, coordinates: tuple):
        self.diameter = diameter
        self._isPlated = isPlated
        self._isVia = isVia
        self.coordinates = coordinates  # Coordinates should be a tuple (x, y)

    def __repr__(self):
        return (f"Hole(diameter={self.diameter}, isPlated={self._isPlated}, "
                f"isVia={self._isVia}, coordinates={self.coordinates})")

    def __str__(self):
        return (f"Hole with diameter {self.diameter}mm, "
                f"{'plated' if self._isPlated else 'not plated'}, "
                f"{'via' if self._isVia else 'not via'}, "
                f"at coordinates {self.coordinates}")

    @property
    def isPlated(self) -> bool:
        """Return True if the hole is plated, False otherwise."""
        return self._isPlated

    @isPlated.setter
    def isPlated(self, value: bool):
        """Set whether the hole is plated or not."""
        self._isPlated = value

    @property
    def isVia(self) -> bool:
        """Return True if the hole is a via, False otherwise."""
        return self._isVia

    @isVia.setter
    def isVia(self, value: bool):
        """Set whether the hole is a via or not."""
        self._isVia = value

    def set_diameter(self, diameter: float):
        """Set the diameter of the hole."""
        self.diameter = diameter

    @property
    def x(self) -> float:
        """Return the x-coordinate of the hole."""
        return self.coordinates[0]

    @x.setter
    def x(self, value: float):
        """Set the x-coordinate of the hole."""
        self.coordinates = (value, self.coordinates[1])

    @property
    def y(self) -> float:
        """Return the y-coordinate of the hole."""
        return self.coordinates[1]

    @y.setter
    def y(self, value: float):
        """Set the y-coordinate of the hole."""
        self.coordinates = (self.coordinates[0], value)

    def set_coordinates(self, x: float, y: float):
        """Set the coordinates of the hole."""
        self.coordinates = (x, y)

