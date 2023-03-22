# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import time

from aiida.engine import calcfunction, submit
from aiida.orm import Code, StructureData, load_node, Str, CifData, CalcFunctionNode, load_group
from aiida.orm.querybuilder import QueryBuilder
from aiida.plugins import DataFactory, WorkflowFactory

cp2k_code = Code.get_from_string('cp2k-9.1@daint-pr128')

# create a new group for only hole injection calculations
group_label_h = 'chemmofs-mof901_1_dft2h'

# use the group_label var to indicate where you placed your main Cp2kPhotoCatWorkChain calculations
group_label = 'chemmofs-mof901_1_dft2'



Dict = DataFactory('dict')

KEEP_LIST = [
   
]

NO_RUN = [

]

wc_group = load_group(group_label_h)

@calcfunction
def structure_with_pbc(s):
    atoms = s.get_ase()
    atoms.pbc = True
    new_s = StructureData(ase=atoms)
    return new_s


def main():
    GetHoleInjection = WorkflowFactory('photocat_workchains.get_hole_injection')
    Cp2kPhotoCatWorkChain = WorkflowFactory('photocat_workchains.cp2k_photocat')
    MultistageWorkChain = WorkflowFactory('lsmo.cp2k_multistage')

    qb = QueryBuilder()
    qb.append(Group, filters={'label': group_label}, tag='group')
    qb.append(Cp2kPhotoCatWorkChain, with_group='group', tag='photocat')
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
        old_structure = load_node(result[-1])

        structure = structure_with_pbc(old_structure)

        cifstr = load_node(result[0])        
        if cifstr.label in NO_RUN:
            continue
        else:
            cp2k_options = {
                'resources': {
                    'num_machines': 2
                },
                'max_wallclock_seconds': 3 * 60 * 60,
                'withmpi': True,
            }

            inputs = {
                'ms_pk': Str(result[1]),
                'cp2k_base': {
                    'cp2k': {
                        'code': cp2k_code,
                        'metadata': {
                            'options': cp2k_options,
                        },
                        'parameters': Dict(dict={
                            #also tried adding here
                            'FORCE_EVAL': {
                                'DFT':{
                                    'SCF': {
                                        'SCF_GUESS': 'ATOMIC'
                                        },
                        },
                    },}),
                    }
                },
            }
            
            print("structure.label", "structure.pk", "wc.pk")
            wc = submit(GetHoleInjection, **inputs)
            print((cifstr.label, structure.pk, wc.pk))
            wc_group.add_nodes(wc)
            time.sleep(5)

if __name__ == '__main__':
    main()







    # for result in qb_results:
    #     old_structure = load_node(result[-1])

    #     structure = structure_with_pbc(old_structure)
    #     cifstr = load_node(result[0])        
    #     builder = GetHoleInjection.get_builder()

    #     cp2k_options = {
    #         'resources': {
    #             'num_machines': 2
    #         },
    #         'max_wallclock_seconds': 3 * 60 * 60,
    #         'withmpi': True,
    #     }

    #     param = {
    #         Dict(dict={
    #                     #also tried adding here
    #                     'FORCE_EVAL': {
    #                         'DFT':{
    #                             'SCF': {
    #                                 'SCF_GUESS': 'ATOMIC'
    #                                 },
    #                 },
    #             },}),
    #                 }

    #     builder.structure = structure
    #     builder.ms_pk = Str(result[1])
    #     builder.cp2k_base.cp2k.code = cp2k_code
    #     builder.cp2k_base.cp2k.metadata.options = cp2k_options
    #     builder.cp2k_base.cp2k.parameters = param

    #     print("structure.label", "structure.pk", "wc.pk")
    #     wc = submit(builder)
    #     print((cifstr.label, structure.pk, wc.pk))
    #     wc_group.add_nodes(wc)
    #     time.sleep(5)