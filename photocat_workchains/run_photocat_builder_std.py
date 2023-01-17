#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""Script to submit PhotoCatWorkChain."""

import os, time
from re import A
import glob
import ntpath

from pathlib import Path
from ase.io import read

from aiida import orm

from aiida.plugins import DataFactory, WorkflowFactory
from aiida.engine import submit
from aiida.orm import Dict, SinglefileData, CifData, Int, load_code, load_group, Code, Str, StructureData, Float
from aiida.orm.nodes.data.data import Data

from aiida.plugins import DataFactory
from aiida_lsmo.utils.multiply_unitcell import check_resize_unit_cell_legacy, resize_unit_cell

# Workchain object
Cp2kPhotoCatWorkChain = WorkflowFactory('photocat_workchains.cp2k_photocat')  # pylint: disable=invalid-name

# Data objects
CifData = DataFactory('cif')  # pylint: disable=invalid-name

### INPUTS
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
cif_dir_in = "/home/beatriz/Documents/Projects/chem-mofs/structures/all_ff_eqeq_cifs/MOF901/round1/DFT2"
all_structures = glob.glob(os.path.join(cif_dir_in, "*.cif"))
cp2k_code = Code.get_from_string('cp2k-9.1@daint-pr128')
group_label = 'chemmofs-mof901_1_dft2'
# group_label_halogen = 'test_group_halogen'
# group_label_metal = 'test_group_metal'
##########

#if using base: define parameters

# Submit the calculations
wc_group = load_group(group_label)
#wc_group_halogen = load_group(group_label_halogen)
#wc_group_metal = load_group(group_label_metal)

def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


for s in all_structures:
    s_ase = read(s)
    structure = CifData(ase=s_ase)
    structure.label = path_leaf(Path(s)) #removed the .stem to see if it prints right this time

    builder = Cp2kPhotoCatWorkChain.get_builder()
    builder.metadata.label = cif_dir_in
    builder.structure = structure
    
    builder.cp2k_energy.cp2k_base.cp2k.code = cp2k_code
    builder.cp2k_multistage.cp2k_base.cp2k.settings = Dict(dict={'additional_retrieve_list': ['*.pdos', '*.cube']})
    builder.cp2k_multistage.cp2k_base.cp2k.code = cp2k_code
    builder.cp2k_bands.cp2k_base.cp2k.code = cp2k_code

    builder.cp2k_energy.min_cell_size = Float(10.0)
    builder.cp2k_multistage.min_cell_size = Float(10.0)

    min_cell_size = Float(10.0)
    structuredata = StructureData(ase=s_ase)
    resize = check_resize_unit_cell_legacy(structuredata, min_cell_size)  # Dict
    if resize['nx'] > 1 or resize['ny'] > 1 or resize['nz'] > 1:
        resized_struct = resize_unit_cell(structuredata, resize)
        structuredata = resized_struct
        print('Unit cell resized by {}x{}x{} (StructureData<{}>)'.format(resize['nx'], resize['ny'], resize['nz'], resized_struct.pk))
    else:
        print('Unit cell was NOT resized')

    #struc_size_test = get_structure_from_cif(structure) #don't know if I need this, probably not
    numatoms = structuredata.get_ase().get_global_number_of_atoms()
    print('total number of atoms', numatoms)

    if numatoms >= 700:
        builder.cp2k_energy.cp2k_base.cp2k.parameters = Dict(dict={'GLOBAL': {'EXTENDED_FFT_LENGTHS': True}})
        builder.cp2k_multistage.cp2k_base.cp2k.parameters = Dict(dict={'GLOBAL': {'EXTENDED_FFT_LENGTHS': True}})
        builder.cp2k_multistage.cp2k_base.cp2k.parameters = Dict(dict={'MOTION': {'GEO_OPT': {'OPTIMIZER': 'LBFGS'}}})
        builder.cp2k_multistage.cp2k_base.cp2k.parameters = Dict(dict={'MOTION': {'CELL_OPT': {'OPTIMIZER': 'LBFGS'}}})

    if numatoms <= 100:
        builder.cp2k_energy.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 4
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_multistage.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 4
           },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_bands.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 4
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
    elif 100 < numatoms <= 400:
        builder.cp2k_energy.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 16
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_multistage.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 16
           },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_bands.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 16
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
    elif numatoms > 400:
        builder.cp2k_energy.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 32
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_multistage.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 32
           },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }
        builder.cp2k_bands.cp2k_base.cp2k.metadata.options = {
            'resources': {
                'num_machines': 32
            },
            'max_wallclock_seconds': 6 * 60 * 60,
            'withmpi': True,
        }

    if numatoms <= 1200: #changed to 1200 for chemmofs
        wc = submit(builder)
        print("structure.label", "structure.pk", "wc.pk")
        print(structure.label, structure.pk, wc.pk)
        wc_group.add_nodes(wc)
        time.sleep(5)
    else:
        print(structure.label, 'has more than 1000 atoms and will not be considered for screening')

#to do:
    #DONE - splt_db.py with mof checker before submitting, tag in groups:
        #DONE - splt_db.py check if it has halogens and tag;
        #DONE - splt_db.py check if it has metals and tag;

    #presettings for submission:
        #DONE check if it needs to be resized;
            #DONE if so, set structure as the resized one;
        #DONE check if number of atoms is smaller than limit (1000 atoms maybe?); 
        #DONE change resources according to number of atoms; 
        #DONE change BFGS and LBFGS according to number of atoms;

    #grouping:
        #DONE add group label and append each calc

    #after completed, can I tag/group bandgaps smaller than threshold? - maybe this would be best in the workchain; 

##if I can do all of this for the run file, use cp2k_photocat and not the new version (don't need to modify anything in the workchain)

##DONE script to separate cofs with halogens and open shell


##ask about .bs
