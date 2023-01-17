# -*- coding: utf-8 -*-
from __future__ import absolute_import

from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain
from aiida.orm import Str, load_node
from aiida.plugins import CalculationFactory, DataFactory, WorkflowFactory
from aiida_lsmo.utils import aiida_dict_merge

# import aiida data
Dict = DataFactory('dict')  # pylint: disable=invalid-name
CifData = DataFactory('cif')  # pylint: disable=invalid-name

Cp2kBaseWorkChain = WorkflowFactory('cp2k.base')  # pylint: disable=invalid-name


class GetElectronInjection(WorkChain):
    """Workchain to get cubes after electron injection"""
    @classmethod
    def define(cls, spec):
        """Define workflow specification."""
        super().define(spec)

        spec.input('ms_pk', valid_type=Str)
        spec.expose_inputs(Cp2kBaseWorkChain, namespace='cp2k_base')

        # specify the chain of calculations to be performed
        spec.outline(cls.load_node, cls.run_cp2k, cls.return_results)

        spec.expose_outputs(Cp2kBaseWorkChain, include=['remote_folder'])

    def load_node(self):
        self.ctx.ms_wc = load_node(self.inputs.ms_pk.value)

    def run_cp2k(self):
        """Pass the Cp2kMultistageWorkChain outputs as inputs for
            Cp2kDdecWorkChain: cp2k_base (metadata), cp2k_params, structure and WFN.
        """

        cp2k_inputs = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base'))
        cp2k_params_modify = Dict(
            dict={
                'GLOBAL': {
                    'RUN_TYPE': 'ENERGY'
                },
                'FORCE_EVAL': {
                    'DFT': {
                        'PRINT': {
                            'V_HARTREE_CUBE': {
                                '_': 'ON',
                                'STRIDE': '1 1 1',
                            },
                            'PDOS': {
                                '_': 'OFF'
                            },
                            'MO_CUBES': {
                                'NHOMO': '1',
                                'NLUMO': '1',
                                'WRITE_CUBE': 'T',
                            }    
                        },
                        #added
                        'SCF': {
                            'SCF_GUESS': 'ATOMIC'
                        },
                        #until here
                        'CHARGE': -1,
                        'MULTIPLICITY': 2,
                        'UKS': True
                    },
                },
            })

        cp2k_params = aiida_dict_merge(
            self.ctx.ms_wc.outputs.last_input_parameters, cp2k_params_modify)
        cp2k_inputs['cp2k']['parameters'] = cp2k_params
        cp2k_inputs['cp2k'][
            'parent_calc_folder'] = self.ctx.ms_wc.outputs.remote_folder

        cp2k_inputs['cp2k'][
            'structure'] = self.ctx.ms_wc.outputs.output_structure

        cp2k_inputs['metadata']['label'] = 'cp2k_energy'
        cp2k_inputs['metadata']['call_link_label'] = 'call_cp2k_energy'

        cp2k_inputs['cp2k']['settings'] = Dict(
            dict={'additional_retrieve_list': ['aiida-WFN*.cube']})

        running = self.submit(Cp2kBaseWorkChain, **cp2k_inputs)
        return ToContext(cp2k_wc=running)

    def return_results(self):
        """Return exposed outputs"""
        self.out_many(self.exposed_outputs(self.ctx.cp2k_wc,
                                           Cp2kBaseWorkChain))


#can modify to display exit errors