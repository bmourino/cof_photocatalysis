# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Work chain to compute a band structure using CP2K."""
from __future__ import absolute_import

import os
from copy import deepcopy

import ruamel.yaml as yaml
import six

from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import BandsData, Dict, Str, StructureData, Float, CifData
from aiida.plugins import WorkflowFactory
from aiida_lsmo.utils.cp2k_utils import get_multiplicity_section
from photocat_workchains.utility.cp2k_utils_master import get_kinds_section
from aiida_lsmo.utils.multiply_unitcell import check_resize_unit_cell_legacy
from aiida_lsmo.utils import get_structure_from_cif

Cp2kBaseWorkChain = WorkflowFactory('cp2k.base')  # pylint: disable=invalid-name

HARTREE2EV = 27.211399
HARTREE2KJMOL = 2625.500

VAL_ELEC = {
    'Ag': 19,
    'Au': 1,
    'Al': 3,
    'Ar': 8,
    'As': 5,
    'B': 3,
    'Be': 4,
    'Br': 7,
    'C': 4,
    'Ca': 10,
    'Cd': 20,
    'Cl': 7,
    'Co': 17,
    'Cr': 14,
    'Cu': 19,
    'F': 7,
    'Fe': 16,
    'Ga': 3,
    'H': 1,
    'He': 2,
    'I': 7,
    'In': 3,
    'K': 9,
    'Li': 3,
    'Mg': 2,
    'Mn': 15,
    'N': 5,
    'Na': 9,
    'Ne': 8,
    'Ni': 18,
    'O': 6,
    'P': 5,
    'S': 6,
    'Sc': 11,
    'Si': 4,
    'Ti': 12,
    'V': 13,
    'Zn': 12,
    'Zr': 12,
}


def merge_dict(dct, merge_dct):
    """ Taken from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, merge_dict recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct (overwrites dct data if in both)
    :return: None
    """
    import collections  # pylint:disable=import-outside-toplevel
    for k, _ in merge_dct.items():  # it was .iteritems() in python2
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            merge_dict(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


@calcfunction
def merge_Dict(dict1, dict2):  # pylint: disable=invalid-name
    """Make all the data in the second Dict overwrite the corrisponding data in the first Dict."""
    result = dict1.get_dict()
    merge_dict(result, dict2.get_dict())
    return Dict(dict=result)


def add_condband(structure):
    """Add 20% of conduction bands to the CP2K input. If 20 % is 0, then add only one."""
    total = 0
    for symbol in structure.get_ase().get_chemical_symbols():
        total += VAL_ELEC[symbol]
    added_mos = total // 10  # 20% of conduction band
    if added_mos == 0:
        added_mos = 1
    return added_mos


def update_input_dict_for_bands(input_dict, seekpath, structure):
    """Insert kpoint path into the input dictonary of CP2K."""

    i_dict = input_dict.get_dict()

    path = seekpath.dict['path']
    coords = seekpath.dict['point_coords']

    kpath = []
    for pnt in path:
        pnt1 = pnt[0] + ' ' + ' '.join(str(x) for x in coords[pnt[0]])
        pnt2 = pnt[1] + ' ' + ' '.join(str(x) for x in coords[pnt[1]])
        kpath.append({
            '_': '',
            'UNITS': 'B_VECTOR',
            'NPOINTS': 20,  #changed here for second round of BS calculations - originally it was 10
            'SPECIAL_POINT': [pnt1, pnt2]
        })

    kpath_dict = {
        'FORCE_EVAL': {
            'DFT': {
                'PRINT': {
                    'BAND_STRUCTURE': {
                        #'FILE_NAME': 'cof.bs', #changed here - change back later, removing this line
                        'KPOINT_SET': kpath
                    }
                }
            }
        }
    }
    merge_dict(i_dict, kpath_dict)

    added_mos = {
        'FORCE_EVAL': {
            'DFT': {
                'SCF': {
                    'ADDED_MOS': add_condband(structure)
                }
            }
        }
    }
    merge_dict(i_dict, added_mos)

    min_cell_size = Float(10.0)
    resize = check_resize_unit_cell_legacy(structure, min_cell_size)  # Dict
    if resize['nx'] > 1 or resize['ny'] > 1 or resize['nz'] > 1:
        scheme = 'MONKHORST-PACK'
        scheme_grid = scheme + ' ' + str(resize['nx']) + ' ' + str(resize['ny']) + ' ' + str(resize['nz'])
        kpoints_dict = {
            'FORCE_EVAL': {
                'DFT': {
                    'KPOINTS': {
                        'SCHEME': scheme_grid,
                        'WAVEFUNCTIONS': 'COMPLEX',
                        'SYMMETRY': 'F',
                        'FULL_GRID': 'T',
                        'PARALLEL_GROUP_SIZE': 0
                    }
                }
            }
        }
        print('Using SCHEME MONKHORST-PACK with GRID {}x{}x{}'.format(resize['nx'], resize['ny'], resize['nz']))
    else:
        kpoints_dict = {
                'FORCE_EVAL': {
                    'DFT': {
                        'KPOINTS': {
                            'SCHEME': 'GAMMA',
                            'WAVEFUNCTIONS': 'COMPLEX',
                            'SYMMETRY': 'F',
                            'FULL_GRID': 'T',
                            'PARALLEL_GROUP_SIZE': 0
                        }
                    }
                }
            }
        print('At gamma point')
    
    merge_dict(i_dict, kpoints_dict)

    return Dict(dict=i_dict)


@calcfunction
def seekpath_structure_analysis(structure, parameters):
    """This calcfunction will take a structure and pass it through SeeKpath to get the
    primitive cell and the path of high symmetry k-points through its Brillouin zone.
    Note that the returned primitive cell may differ from the original structure in
    which case the k-points are only congruent with the primitive cell.
    """

    from aiida.tools import get_kpoints_path  # pylint:disable=import-outside-toplevel

    return get_kpoints_path(structure, **parameters.get_dict())

@calcfunction
def structure_with_pbc(s):
    atoms = s.get_ase()
    atoms.pbc = True
    new_s = CifData(ase=atoms)
    return new_s


class Cp2kBandsWorkChain(WorkChain):
    """Compute Band Structure of a material."""
    @classmethod
    def define(cls, spec):
        super(Cp2kBandsWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kBaseWorkChain,
                           namespace='cp2k_base',
                           exclude=('cp2k.structure', 'cp2k.parameters',
                                    'cp2k.metadata.options.parser_name'))
        spec.input('structure', valid_type=StructureData)
        spec.input('protocol_tag', valid_type=Str, default=lambda: Str('bs'))
        spec.input(
            'cp2k_base.cp2k.metadata.options.parser_name',
            valid_type=six.string_types,
            default='cp2k_advanced_parser',
            non_db=True,
            help=
            'Parser of the calculation: the default is cp2k_advanced_parser to get the bands.'
        )
        spec.outline(
            cls.setup,
            cls.run_seekpath,
            cls.prepare_bands_calculation,
            cls.run_bands_calculation,
            cls.return_results,
        )
        spec.output('output_bands', valid_type=BandsData)

    def setup(self):
        """Perform initial setup."""
        self.ctx.structure = self.inputs.structure
        thisdir = os.path.dirname(os.path.abspath(__file__))
        yamlfullpath = os.path.join(thisdir, 'settings',
                                    self.inputs.protocol_tag.value + '.yaml')

        with open(yamlfullpath, 'r') as stream:
            #yaml1 = yaml.YAML() #added this 
            #yaml1.allow_duplicate_keys = True #and this, to supress duplicate check (wasn't allowing me to specify kpoints: found duplicate key "KPOINT" with value "0 0 0.5 0.125" (original value: "0 0 0 0.125"))
            self.ctx.protocol = yaml.load(stream) #changed here from yaml to yaml1

        self.ctx.cp2k_param = deepcopy(self.ctx.protocol['settings'])

        kinds = get_kinds_section(self.ctx.structure, self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, kinds)
        multiplicity = get_multiplicity_section(self.ctx.structure,
                                              self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, multiplicity)

    def run_seekpath(self):
        """Run Seekpath to get the primitive structure
        N.B. If, after cell optimization the symmetry change,
        the primitive cell will be different!"""

        seekpath_parameters = Dict(dict={
            'symprec': 0.1, #this was 1e-06, changing to 0.1 to allow for primitive searching through symmetry on aug26
            'angle_tolerance': -1.0
        })
        self.ctx.structure = structure_with_pbc(self.ctx.structure)
        self.ctx.structure = get_structure_from_cif(self.ctx.structure)
        seekpath_result = seekpath_structure_analysis(self.ctx.structure,
                                                      seekpath_parameters)
        self.ctx.seekpath_analysis = seekpath_result['parameters']
        self.ctx.structure = seekpath_result['primitive_structure']

    def prepare_bands_calculation(self):
        """Prepare all the neccessary input links to run the calculation."""

        # ToDo: check if structure too small for gamma-only and add sampling

        # Add molecular orbitals and kpoints path that was generated by seekpath
        self.ctx.parameters = update_input_dict_for_bands(
            Dict(dict=self.ctx.cp2k_param), self.ctx.seekpath_analysis,
            self.ctx.structure)
        min_cell_size = Float(10.0)
        resize = check_resize_unit_cell_legacy(self.ctx.structure, min_cell_size)  # Dict
        if resize['nx'] > 1 or resize['ny'] > 1 or resize['nz'] > 1:
            self.report(
                'Using SCHEME MONKHORST-PACK with GRID {}x{}x{}'.format(resize['nx'], resize['ny'], resize['nz']))
        else:
            self.report(
                'At gamma point.')            

    def run_bands_calculation(self):
        """Run cp2k calculation."""

        inputs = AttributeDict(
            self.exposed_inputs(Cp2kBaseWorkChain, namespace='cp2k_base'))
        inputs.cp2k.structure = self.ctx.structure
        inputs.cp2k.parameters = self.ctx.parameters

        # inputs['cp2k']['settings'] = Dict(
        #     dict={'additional_retrieve_list': ['*.bs']})

        # Create the calculation process and launch it
        running = self.submit(Cp2kBaseWorkChain, **inputs)
        self.report(
            'Submitted Cp2kBaseWorkChain for band structure calculation.')
        return ToContext(calculation=running)

    def return_results(self):
        """Extract output_parameters."""
        self.out('output_bands', self.ctx.calculation.outputs.output_bands)