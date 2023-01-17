# -*- coding: utf-8 -*-
# To be developed.
# General outline:
# sp, relax, bandstructure, use the last geoopt settings
# retrieve homo-lumo cubes and dos

from __future__ import absolute_import, print_function

import os, time
import sys

import numpy as np
from ase.atoms import Atoms
import ruamel.yaml as yaml
from copy import deepcopy

import click
from aiida.common import AttributeDict, NotExistent
from aiida.engine import ToContext, WorkChain, if_, calcfunction
from aiida.orm import Code, Dict, SinglefileData, StructureData, Str
from aiida.plugins import CalculationFactory, DataFactory, WorkflowFactory
from aiida_lsmo.utils import get_structure_from_cif, HARTREE2EV


CifData = DataFactory('cif')  # pylint: disable=invalid-name
Cp2kBandsWorkChain = WorkflowFactory('photocat_workchains.bandstructure')
Cp2kMultistageWorkChain = WorkflowFactory('lsmo.cp2k_multistage')
THIS_DIR = os.path.dirname(os.path.realpath(__file__))

@calcfunction
def structure_with_pbc(s):
    atoms = s.get_ase()
    atoms.pbc = True
    new_s = StructureData(ase=atoms)
    return new_s


class Cp2kPhotoCatWorkChain(WorkChain):
    """A workchain that combines: Cp2kBaseWorkChain + Cp2kMultistageWorkChain + Bandstructure"""
    @classmethod
    def define(cls, spec):
        """Define workflow specification."""
        super().define(spec)

        spec.input('structure', valid_type=CifData, help='input structure')
        spec.input('protocol_tag', valid_type=Str, default=lambda: Str('ms-cofs')) ##HERE
        spec.expose_inputs(Cp2kMultistageWorkChain, namespace='cp2k_energy', exclude=['cp2k.structure']) #should I change it?
        spec.expose_inputs(Cp2kMultistageWorkChain, namespace='cp2k_multistage', exclude=['structure'])
        spec.expose_inputs(Cp2kBandsWorkChain, namespace='cp2k_bands', exclude=['structure'])

        spec.input('cp2k_energy.cp2k.parameters',
            valid_type=Dict,
            required=False,
            help='Specify custom CP2K settings to overwrite the input dictionary just before submitting the CalcJob')
        spec.input('cp2k_energy.cp2k.metadata.options.parser_name',
                   valid_type=str,
                   default='lsmo.cp2k_advanced_parser',
                   non_db=True,
                   help='Parser of the calculation: the default is cp2k_advanced_parser to get the necessary info')

        spec.outline(
            cls.setup,
            cls.run_energy,
            cls.inspect_energy,
            if_(cls.should_run_multistage)(
                cls.run_multistage,
                cls.run_bandstructure,
                cls.return_results,    
            )

        )

        spec.expose_outputs(Cp2kBandsWorkChain)
        spec.expose_outputs(Cp2kMultistageWorkChain)

    def setup(self):
        """Perform initial setup."""
        self.ctx.structure = self.inputs.structure
        thisdir = os.path.dirname(os.path.abspath(__file__))
        yamlfullpath = os.path.join(thisdir, 'settings',
                                    self.inputs.protocol_tag.value + '.yaml')

        with open(yamlfullpath, 'r') as stream:
            self.ctx.protocol = yaml.safe_load(stream)

    def run_energy(self):
        """Run Cp2kMultistage work chain with only single point in the protocol"""
        sp_inputs = AttributeDict(self.exposed_inputs(Cp2kMultistageWorkChain, namespace='cp2k_energy'))
        sp_inputs.structure = get_structure_from_cif(self.inputs.structure)
        sp_inputs.protocol_yaml = SinglefileData(file=os.path.abspath(os.path.join(THIS_DIR, 'settings/sp-mofs.yaml'))) #sp-mofs.yaml protocol is doing a "shake" with geometry optimization before testing for band gap, useful for hypothetical MOFs: for COFs, use sp.yaml; can be improved to allow changing in the run file
        running = self.submit(Cp2kMultistageWorkChain, **sp_inputs)
        return ToContext(sp_wc=running)

    def inspect_energy(self):  # pylint: disable=inconsistent-return-statements
        """Inspect the energy calculation and check if the band gap is appropriate."""
        self.ctx.settings_ok = True
        cp2k_out = self.ctx.sp_wc.outputs.output_parameters
        #self.report("Bandgap: {:.3f} ev".format(cp2k_out["HOMO_-_LUMO_gap_[eV]"])) - work on it later
        min_bandgap_ev = min(cp2k_out['final_bandgap_spin1_au'], cp2k_out['final_bandgap_spin2_au']) * HARTREE2EV #maybe change here to ['energy'] and multiply to get ev - check if it makes sense on the output
        bandgap_thr_ev = 0.1 #test, use 0.5 later
        #is_bandgap_small = (bandgap < bandgap_thr_ev)
        if min_bandgap_ev < bandgap_thr_ev:
            self.report("BAD SETTINGS: band gap is < {:.3f} eV".format(bandgap_thr_ev))
            self.ctx.settings_ok = False

    def should_run_multistage(self):
        """Returns True if band gap from single point calculation is higher than 0.5 eV."""
        #ToDo: look for how it was done on Cp2kMultistage and adapt
        return self.ctx.settings_ok

    def run_multistage(self):
        """Run Cp2kMultistage work chain"""
        # ToDo: retrieve HOMO/LUMO CUBES, also retrieve the wfn *pdos *wfn ADDITIONAL_RETRIEVE_LIST
        ms_inputs = AttributeDict(self.exposed_inputs(Cp2kMultistageWorkChain, namespace='cp2k_multistage'))
        ms_inputs['structure'] = get_structure_from_cif(self.inputs.structure)
        ms_inputs['protocol_yaml'] = SinglefileData(file=os.path.abspath(os.path.join(THIS_DIR, 'settings/ms-cofs-2.yaml')))
        running = self.submit(Cp2kMultistageWorkChain, **ms_inputs)
        return ToContext(ms_wc=running)

    def run_bandstructure(self):
        bands_input = AttributeDict(self.exposed_inputs(Cp2kBandsWorkChain, namespace='cp2k_bands'))
        bands_input['structure'] = structure_with_pbc(self.ctx.ms_wc.outputs.output_structure)
        running = self.submit(Cp2kBandsWorkChain, **bands_input)
        return ToContext(bands_wc=running)

    def return_results(self):
        """Return exposed outputs"""
        self.out_many(
            self.exposed_outputs(self.ctx.ms_wc, Cp2kMultistageWorkChain))
        self.out_many(
            self.exposed_outputs(self.ctx.bands_wc, Cp2kBandsWorkChain))
        self.report('WorkChain terminated correctly.')

#print band gap after cell