"""
    Holds relevant functions for reading in file information.
    Examples for reading in .kicad_sch files and .net files
"""
from Objectifier import Objectifier,Node

import re


def get_starting_symbol(filename_sch): 
    """
        Gets the component with the most number of pins from the .kicad_sch file

        Parameters:
        filename_sch (str): string of the .kicad_sch file path

        Returns:
        name (str): Name of the component (based on library ID)
        footprint (str): Name of the footprint for the component
    """
    sch = Objectifier(filename_sch)
    root = sch.root

    cmpnt_dict = {}

    for node in root.xpath('/kicad_sch/symbol'):
        sym_name = node.xpath('lib_id')[0].first_child
        footprint = ""

        for prop in node.xpath('property'):
            if (prop.first_child == 'Footprint'):
                footprint = prop.childs[1]

        cmpnt_dict[sym_name] = {'Footprint': footprint, 'Pins': len(node.xpath('pin'))}


    sorted_components = dict(sorted(cmpnt_dict.items(), key=lambda item: item[1]['Pins'], reverse=True))


    name = list(sorted_components)[0]
    footprint = cmpnt_dict[name]['Footprint']

    ##NOTE: could also use netlist to determine

    return name, footprint

def get_symbol(filename_sch, ref): 
    """
        Gets the symbol name of a ref from the .kicad_sch file

        Parameters:
        filename_sch (str): string of the .kicad_sch file path
        ref (str): ref in question

        Returns:
        name (str): Name of the component (based on library ID)
    """
    
    sch = Objectifier(filename_sch)
    root = sch.root

    cmpnt_dict = {}

    for node in root.xpath('/kicad_sch/symbol'):
        sym_name = node.xpath('lib_id')[0].first_child
        
        for prop in node.xpath('property'):
            if (prop.first_child == 'Reference'):
                
                sch_ref = prop.childs[1]
                if sch_ref == ref:
                    return sym_name


    return ''

def get_connections(filename_net):
    """
    Gets all the net connections from the .net file

    Parameters:
    filename_net (str): string of the .net file path

    Returns:
    nets_arr (array of dicts): array of each net represented by a {'name': '', 'node arr': []} format.
    'node arr' represented as an array of node dicts as {'ref': '', 'pin': '', 'footprint': ''}
    """
    net = Objectifier(filename_net)
    root = net.root

    nets_arr = []

    for net in root.xpath('/export/nets/net'):

        net_name = net.xpath('name')[0].first_child
        node_arr = []
        if (net_name[:3] == 'Net'):
            for node in net.xpath('node'):
                ref = node.xpath('ref')[0].first_child
                pin = node.xpath('pin')[0].first_child
                footprint = get_footprint_of_ref(root, ref)
                lib, part = get_lib_part(root, ref)
                pins = get_pins_of_ref(root, lib, part)

                if pins > 0:
                    node_dict = {'ref': ref, 'pin': pin, 'footprint': footprint, 'total pins': pins}

                    node_arr.append(node_dict)
            net_dict = {'name': net_name, 'node arr': node_arr}
            nets_arr.append(net_dict)

        else:
            if (net_name == 'GND') or (net_name == 'VCC'):
                for node in net.xpath('node'):
                    ref = node.xpath('ref')[0].first_child
                    pin = node.xpath('pin')[0].first_child
                    footprint = get_footprint_of_ref(root, ref)
                    lib, part = get_lib_part(root, ref)
                    pins = get_pins_of_ref(root, lib, part)
                    node_dict = {'ref': ref, 'pin': pin, 'footprint': footprint, 'total pins': pins}
                    node_arr.append(node_dict)
                net_dict = {'name': net_name, 'node arr': node_arr}
                nets_arr.append(net_dict)
            elif 'unconnected' in net_name:
                continue
            else:
                for node in net.xpath('node'):
                    ref = node.xpath('ref')[0].first_child
                    pin = node.xpath('pin')[0].first_child
                    footprint = get_footprint_of_ref(root, ref)
                    lib, part = get_lib_part(root, ref)
                    pins = get_pins_of_ref(root, lib, part)
                    node_dict = {'ref': ref, 'pin': pin, 'footprint': footprint, 'total pins': pins}
                    node_arr.append(node_dict)
                net_dict = {'name': net_name, 'node arr': node_arr}
                nets_arr.append(net_dict)
                

    return nets_arr

def get_lib_part(root, ref):
    """
        Helper function for 'get_connections'. Identifies the library and part for the specified component ref.
        Parameters:
        root (Objectifier root): root of the Objectifier tree from .net file
        ref (str): reference identifier

        Returns:
        lib (str) lib for component
        part (str) part for component
    """

    for component in root.xpath('/export/components/comp'):
        n_ref = component.xpath('ref')[0].first_child
        if n_ref  == ref:
            lib = component.xpath('libsource/lib')[0].first_child
            part = component.xpath('libsource/part')[0].first_child
            return lib, part

def get_ordered_components_list(filename_net):
    """
    Uses the net file to retrieve an ordered list of components (decreasing by pin number) also returns component footprints and corresponding refs

    Parameters:
    filename_net (str): string of the .net file path

    Returns:
    ref_arr_sorted (array of str): Array of the refs (as str) in order
    footprint_dict (dict): 'footprint': [array of refs]

    """
    net = Objectifier(filename_net)
    root = net.root

    cmpnt_arr = []
    footprint_dict = {}

    for component in root.xpath('/export/components/comp'):
        ref = component.xpath('ref')[0].first_child
        lib = component.xpath('libsource/lib')[0].first_child
        part = component.xpath('libsource/part')[0].first_child
        footprint = component.xpath('footprint')[0].first_child
        pins = get_pins_of_ref(root, lib, part)
        cmpnt_arr.append({'ref': ref, 'pins': pins})

        if footprint in footprint_dict.keys():
            footprint_dict[footprint].append(ref)
        else:
            footprint_dict[footprint] = [ref]

    sorted_components = sorted(cmpnt_arr, key=lambda item: item['pins'], reverse=True)
    
    ref_arr_sorted = []
    for cmpnt in sorted_components:
        if cmpnt['pins'] != 0:
            ref_arr_sorted.append(cmpnt['ref'])

    return ref_arr_sorted, footprint_dict


def get_pins_of_ref(root, lib, part):
    """
        Helper function for 'get_ordered_components_list'. Identifies the number of pins for that component.
        Parameters:
        root (Objectifier root): root of the Objectifier tree from .net file
        lib (str): library ID for component 
        part (str): part ID in library for component

        Returns:
        (int) number of pins for that component
    """

    for libpart in root.xpath('/export/libparts/libpart'):
        libpart_lib = libpart.xpath('lib')[0].first_child
        libpart_part = libpart.xpath('part')[0].first_child
        if libpart_lib == lib and libpart_part == part:
            
            if len(libpart.xpath('pins')) > 0:
                return len(libpart.xpath('pins')[0])
            else:
                return 0

def get_footprint_of_ref(root, ref):
    """
        Helper function for 'get_connections'. Identifies the corresponding footprint for that component.
        Parameters:
        root (Objectifier root): root of the Objectifier tree from .net file
        ref (str): reference of component

        Returns:
        (str) footprint for that component
    """
    for cmpnt in root.xpath('/export/components/comp'):
        cmpnt_ref = cmpnt.xpath('ref')[0].first_child
        if cmpnt_ref == ref:
            footprint = cmpnt.xpath('footprint')[0].first_child

    return footprint

