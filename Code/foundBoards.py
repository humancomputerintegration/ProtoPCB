import cv2
import numpy as np
# INPUT BOARD FILE
file = ''
board_img = cv2.imread(file)

original = board_img.copy()

img = cv2.imread(file)
img2 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
inv_img = cv2.bitwise_not(img2)

imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

ret, thresh = cv2.threshold(imgray, 200, 200, 200)

contours2, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


img = cv2.imread(file, cv2.IMREAD_GRAYSCALE)
edges = cv2.Canny(img,60,100)
cv2.imshow('edges', edges)
key = cv2.waitKeyEx(0)

contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

#'''

image = board_img.copy()

# trace 12, 15, 25, 26, 38, 68, 84, 232, 237, 241, 242, 251, 252, 255, 264, 266, 286, 287, 295
# 314, 383, 386, 400, 416, 417, 432, 462, 465
#pad 46, 9, 10, 11,51, 57, 71, 87, 105, 106, 153, 159, 171, 173, 185, 187, 192, 196, 203, 206, 212, 216, 234, 236
#238,245, 268, 288, 290, 293, 309 315, 327, 403, 420, 421, 433, 463, 466, 473, 477

#via 69, 121, 243, 381, 384, 418

trace_cnts = [11, 12, 15, 25, 26, 38, 50, 56, 68, 76, 84, 104, 123, 125, 152, 176, 191, 201, 229, 231, 232, 237, 241, 242, 251, 252, 255, 264, 266, 286, 287, 295, 314, 374, 383, 386, 400, 416, 417, 432, 462, 465, 476]

pad_cnts = [3, 4, 6, 46, 9, 10,51, 57, 71, 87, 105, 106, 153, 159, 171, 173, 185, 187, 192, 196, 203, 206, 212, 216, 234, 236, 238,245, 268, 288, 290, 292, 293, 309, 315, 327, 403, 420, 421, 433, 463, 466, 473, 477]

via_cnts = [1, 69, 121, 243, 381, 384, 418]

for pad_cnt_ID in pad_cnts:
	#print(pad_cnt_ID)
	cv2.drawContours(image, contours, pad_cnt_ID, (255, 255, 0), -1)
	cv2.imshow('pads', image)
	#key = cv2.waitKeyEx(0)

pad_cnts2 = [5, 33, 60, 84, 87]

for pad_cnt_ID in pad_cnts2:
	cv2.drawContours(image, contours2, pad_cnt_ID, (255, 255, 0), -1)
	cv2.imshow('pads', image)

key = cv2.waitKeyEx(0)


