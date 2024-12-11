from cairosvg import *
from lxml import etree

import os.path

def gen_footprint_PNG(svg_file):

	tree = etree.parse(svg_file)
	root = tree.getroot()

	prefix = root.tag[:-3]

	leftmost_x = 1000000.00
	rightmost_x = -1.10
	topmost_y = 1000000.00
	btmmost_y = -1.00


	for child in root:
		for path in child.iter(prefix + 'path'):
			path_pts = path.attrib['d'].split(' ')
			for pt in path_pts:
				if pt == 'M' or pt == 'Z':
					continue
				else:
					[x_s,y_s] = pt.split(',')
					x = float(x_s)
					y = float(y_s)
					
					if x < leftmost_x:
						leftmost_x = x
					if x > rightmost_x:
						rightmost_x = x
					if y < topmost_y:
						topmost_y = y
					if y > btmmost_y:
						btmmost_y = y
		for circle in child.iter(prefix + 'circle'):
		
			cx = float(circle.attrib['cx'])
			cy = float(circle.attrib['cy'])
			r = float(circle.attrib['r'])

			if cx-r < leftmost_x:
				leftmost_x = cx-r
			if cx+r > rightmost_x:
				rightmost_x = cx+r
			if cy -r< topmost_y:
				topmost_y = cy - r
			if cy +r> btmmost_y:
				btmmost_y = cy + r

	sub_x = leftmost_x - 0.10
	sub_y = topmost_y - 0.10

	for child in root:
		for path in child.iter(prefix + 'path'):
			path_pts = path.attrib['d'].split(' ')
			new_path_pts_str = ''
			for pt in path_pts:
				if pt == 'M':
					new_path_pts_str = 'M '
				elif pt == 'Z':
					new_path_pts_str = new_path_pts_str + 'Z'
				else:
					[x_s,y_s] = pt.split(',')
					x = float(x_s) - sub_x
					y = float(y_s) - sub_y
					new_path_pts_str = new_path_pts_str + str(x) + "," + str(y) + " "

			path.attrib['d'] = new_path_pts_str

		for circle in child.iter(prefix + 'circle'):
			cx = float(circle.attrib['cx'])
			cy = float(circle.attrib['cy'])

			n_cx = cx - sub_x
			n_cy = cy - sub_y

			circle.attrib['cx'] = str(n_cx)
			circle.attrib['cy'] = str(n_cy)
					
	diff_x = rightmost_x - leftmost_x + 0.2
	diff_y = btmmost_y - topmost_y + 0.2

	root.attrib['width'] = str(diff_x) + "mm"
	root.attrib['height'] = str(diff_y) + "mm"
	viewbox_arr = root.attrib['viewBox'].split(' ')
	viewbox_arr[2] = diff_x
	viewbox_arr[3] = diff_y
	new_viewbox_str = ''
	for elem in viewbox_arr:
		new_viewbox_str = new_viewbox_str + str(elem) + ' '

	root.attrib['viewBox'] = new_viewbox_str[:-1]

	tree.write(svg_file)
	svg2png(url=svg_file, write_to=svg_file[:-3] + "png", scale=4, dpi=300, background_color="white")

def gen_sch_PNG(svg_file):

	tree = etree.parse(svg_file)
	root = tree.getroot()

	prefix = root.tag[:-3]

	leftmost_x = 1000000.00
	rightmost_x = -1.10
	topmost_y = 1000000.00
	btmmost_y = -1.00


	for child in root:
		for path in child.iter(prefix + 'path'):
			path_pts = path.attrib['d'].split(' ')
			for pt in path_pts:
				if pt == 'M' or pt == 'Z' or pt == 'L':
					continue
				elif ',' in pt:
					[x_s,y_s] = pt.split(',')
					x = float(x_s)
					y = float(y_s)
					
					if x < leftmost_x:
						leftmost_x = x
					if x > rightmost_x:
						rightmost_x = x
					if y < topmost_y:
						topmost_y = y
					if y > btmmost_y:
						btmmost_y = y
				elif len(pt) == 0:
					continue
				elif pt[0] == 'M':
					x = float(pt[1:])
					if x < leftmost_x:
						leftmost_x = x
					if x > rightmost_x:
						rightmost_x = x
				elif pt[0] == 'L':
					x = float(pt[1:])
					if x < leftmost_x:
						leftmost_x = x
					if x > rightmost_x:
						rightmost_x = x
				elif pt[0] == 'A':
					x = float(pt[1:])
					if x < leftmost_x:
						leftmost_x = x
					if x > rightmost_x:
						rightmost_x = x
				else:
					y = float(pt)
					if y < topmost_y:
						topmost_y = y
					if y > btmmost_y:
						btmmost_y = y

		for path in child.iter(prefix + 'g'):
			if 'class' in path.attrib:
				g_class = path.attrib['class']
				if g_class == 'stroked-text':
					for path2 in path.iter(prefix + 'path'):
						path_pts = path2.attrib['d'].split(' ')
						for pt in path_pts:
							if pt == 'M' or pt == 'Z':
								continue
							elif ',' in pt:
								[x_s,y_s] = pt.split(',')
								x = float(x_s)
								y = float(y_s)
								
								if x < leftmost_x:
									leftmost_x = x
								if x > rightmost_x:
									rightmost_x = x
								if y < topmost_y:
									topmost_y = y
								if y > btmmost_y:
									btmmost_y = y
							elif len(pt) == 0:
								continue
							elif pt[0] == 'M':
								x = float(pt[1:])
								if x < leftmost_x:
									leftmost_x = x
								if x > rightmost_x:
									rightmost_x = x
							elif pt[0] == 'L':
								x = float(pt[1:])
								if x < leftmost_x:
									leftmost_x = x
								if x > rightmost_x:
									rightmost_x = x
							elif pt[0] == 'A':
								x = float(pt[1:])
								if x < leftmost_x:
									leftmost_x = x
								if x > rightmost_x:
									rightmost_x = x
							else:
								y = float(pt)
								if y < topmost_y:
									topmost_y = y
								if y > btmmost_y:
									btmmost_y = y

			for path2 in path.iter(prefix + 'path'):
				path_pts = path2.attrib['d'].split(' ')
				for pt in path_pts:
					if pt == 'M' or pt == 'Z' or pt == 'L':
						continue
					elif ',' in pt:
						[x_s,y_s] = pt.split(',')
						x = float(x_s)
						y = float(y_s)
						
						if x < leftmost_x:
							leftmost_x = x
						if x > rightmost_x:
							rightmost_x = x
						if y < topmost_y:
							topmost_y = y
						if y > btmmost_y:
							btmmost_y = y
					elif len(pt) == 0:
						continue
					elif pt[0] == 'M':
						x = float(pt[1:])
						if x < leftmost_x:
							leftmost_x = x
						if x > rightmost_x:
							rightmost_x = x
					elif pt[0] == 'L':
						x = float(pt[1:])
						if x < leftmost_x:
							leftmost_x = x
						if x > rightmost_x:
							rightmost_x = x
					elif pt[0] == 'A':
						x = float(pt[1:])
						if x < leftmost_x:
							leftmost_x = x
						if x > rightmost_x:
							rightmost_x = x
					else:
						y = float(pt)
						if y < topmost_y:
							topmost_y = y
						if y > btmmost_y:
							btmmost_y = y

		for path in child.iter(prefix + 'rect'):
			path_x = path.attrib['x']
			path_y = path.attrib['y']
			path_w = path.attrib['width']
			path_h = path.attrib['height']
			x = float(path_x)
			y = float(path_y)
			w = float(path_w)
			h = float(path_h)
			
			if x < leftmost_x:
				leftmost_x = x
			if x + w > rightmost_x:
				rightmost_x = x + w
			if y < topmost_y:
				topmost_y = y
			if y + h > btmmost_y:
				btmmost_y = y + h

		for path in child.iter(prefix + 'circle'):
			path_x = path.attrib['cx']
			path_y = path.attrib['cy']

			x = float(path_x)
			y = float(path_y)
			
			if x < leftmost_x:
				leftmost_x = x
			if x > rightmost_x:
				rightmost_x = x
			if y < topmost_y:
				topmost_y = y
			if y > btmmost_y:
				btmmost_y = y


	sub_x = leftmost_x - 0.10
	sub_y = topmost_y - 0.10

	for child in root:
		for path in child.iter(prefix + 'path'):
			path_pts = path.attrib['d'].split(' ')
			new_path_pts_str = ''
			for pt in path_pts:
				if pt == 'M':
					new_path_pts_str = 'M '
				elif pt == 'Z':
					new_path_pts_str = new_path_pts_str + 'Z'
				elif pt == 'L':
					new_path_pts_str = new_path_pts_str + 'L'
				elif ',' in pt:
					[x_s,y_s] = pt.split(',')
					x = float(x_s) - sub_x
					y = float(y_s) - sub_y
					new_path_pts_str = new_path_pts_str + str(x) + "," + str(y) + " "
				elif len(pt) == 0:
					continue
				elif len(pt) == 1:
					new_path_pts_str = new_path_pts_str + pt
				elif pt[0] == 'M':
					x_s = float(pt[1:])
					x = x_s - sub_x
					new_path_pts_str = new_path_pts_str + 'M' + str(x) + " "
				elif pt[0] == 'L':
					x_s = float(pt[1:])
					x = x_s - sub_x
					new_path_pts_str = new_path_pts_str + 'L' + str(x) + " "
				elif pt[0] == 'A':
					x_s = float(pt[1:])
					x = x_s - sub_x
					new_path_pts_str = new_path_pts_str + 'A' + str(x) + " "
				else:
					y_s = float(pt)
					y = y_s - sub_y
					new_path_pts_str = new_path_pts_str + str(y) + " "

			path.attrib['d'] = new_path_pts_str

		
		for path in child.iter(prefix + 'rect'):
			path_x = path.attrib['x']
			path_y = path.attrib['y']

			x = float(path_x) - sub_x
			y = float(path_y) - sub_y

			path.attrib['x'] = str(x)
			path.attrib['y'] = str(y)

		for path in child.iter(prefix + 'circle'):
			path_x = path.attrib['cx']
			path_y = path.attrib['cy']

			x = float(path_x) - sub_x
			y = float(path_y) - sub_y

			path.attrib['cx'] = str(x)
			path.attrib['cy'] = str(y)
					
	diff_x = rightmost_x - leftmost_x + 0.2
	diff_y = btmmost_y - topmost_y + 0.2

	root.attrib['width'] = str(diff_x) + "mm"
	root.attrib['height'] = str(diff_y) + "mm"
	viewbox_arr = root.attrib['viewBox'].split(' ')
	viewbox_arr[2] = diff_x
	viewbox_arr[3] = diff_y
	new_viewbox_str = ''
	for elem in viewbox_arr:
		new_viewbox_str = new_viewbox_str + str(elem) + ' '

	root.attrib['viewBox'] = new_viewbox_str[:-1]

	tree.write(svg_file)
	svg2png(url=svg_file, write_to=svg_file[:-3] + "png", scale=4, dpi=300, background_color="white")


def svg_to_png_gen(svg_file, background_color="white"):
	
	svg2png(url=svg_file, write_to=svg_file[:-3] + "png", scale=4, dpi=300, background_color=background_color)
	

