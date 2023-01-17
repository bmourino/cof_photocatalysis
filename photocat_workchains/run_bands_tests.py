# -*- coding: utf-8 -*-
"""Band structure tests with general scheme (mp + gamma centered) submitted in batches for the groups cofs-batch7 and cofs-batch1 and maybe cofs-batch27 (excluding 3D and ones; 2D COFs, two that are not hexagonal, two hexagonal, and including COF-5 or 05001N2) changing the number of points in each section of the path (10,20,50) and the grid size (111,112,113,222,223)."""
from __future__ import absolute_import, print_function

import time, os, glob
from pathlib import Path
from ase.io import read

from aiida.engine import calcfunction, submit
from aiida.orm import Code, StructureData, load_node, CifData, Str, CalcFunctionNode
from aiida.orm.querybuilder import QueryBuilder
from aiida.plugins import DataFactory, WorkflowFactory
from bandstructure import Cp2kBandsWorkChain
from aiida_lsmo.utils import get_structure_from_cif

Dict = DataFactory('dict')

print("structure.label", "structure.pk", "wc.pk")
cp2k_code = Code.get_from_string('cp2k-9.1@daint-pr128')
group_label = 'bs-t6'
wc_group = load_group(group_label)

RUN_LIST = [
     '05001N2.cif',
     '07001N2.cif',
     '15090N2.cif',
     '15081N2.cif',
     '20420N2.cif'
]

@calcfunction
def structure_with_pbc(s):
    atoms = s.get_ase()
    atoms.pbc = True
    new_s = CifData(ase=atoms)
    return new_s


def main():
    Cp2kPhotoCatWorkChain = WorkflowFactory('photocat_workchains.cp2k_photocat')
    MultistageWorkChain = WorkflowFactory('lsmo.cp2k_multistage')

    qb = QueryBuilder()
    #qb.append(Group, filters={'label': 'cofs-batch7'}, tag='group')
    qb.append(Cp2kPhotoCatWorkChain, tag='photocat') #with_group='group',
    qb.append(CalcFunctionNode, filters={'label': {'==': 'get_structure_from_cif'}}, tag='get_st', with_incoming='photocat')
    qb.append(CifData, project=['label'], with_outgoing='get_st')
    qb.append(
        MultistageWorkChain, with_incoming='photocat',  # I am appending a CalcJobNode
        filters={  # Specifying the filters:
            'attributes.process_state': {
                '==': 'finished'
            },  # the calculation has to have finished AND
        },
        project=['uuid'],
        tag='ms')

    qb.append(StructureData, project=['label'], with_outgoing='ms')

    qb.append(Dict,
              with_incoming='ms',
              project=['uuid'],
              filters={'attributes': {
                  'has_key': 'natoms'
              }})

    qb.append(
        StructureData,  # this is the relaxed structure
        with_incoming='ms',
        project=['uuid'],
    )

    results = qb.all()

    qb_results_dict = {}
    qb_results = []
    names = []
    for result in results:
        qb_results_dict[result[0]] = results
        if result[0] in names:
            continue
        else:
            names.append(result[0])
            qb_results.append(result)
    len(qb_results)

    for result in qb_results:
        if result[0] in RUN_LIST:
            old_structure = load_node(result[-1])

            structure_cif = structure_with_pbc(old_structure)
            
            structure = get_structure_from_cif(structure_cif)

            cifstr = load_node(result[0])

            cp2k_options = {
                'resources': {
                    'num_machines': 2
                },
                'max_wallclock_seconds': 3 * 60 * 60,
                'withmpi': True,
            }

            inputs = {
                'structure': structure,
                'protocol_tag': Str('bs-t1'),
                'cp2k_base': {
                    'cp2k': {
                        'code': cp2k_code,
                        'metadata': {
                            'options': cp2k_options,
                        },
                    }
                },
            }

            wc = submit(Cp2kBandsWorkChain, **inputs)
            print((cifstr.label, structure.pk, wc.pk))
            wc_group.add_nodes(wc)
            time.sleep(5)


if __name__ == '__main__':
    main()


#to do:
#different conditions
#(OK) exclude the big ones - 15050N2.cif and 15030N2.cif - how? maybe by name? using no_keep list like kevin? 
#if conditions to know which parameters need to be changed
#(OK, just not sure about full_grid) add mp+gamma (general) to settings
#(OK, need to change back for later) ask to print cof.bs as output so I can plot and calculate my way - on settings
#later: tag differently so I can append with querybuilder
