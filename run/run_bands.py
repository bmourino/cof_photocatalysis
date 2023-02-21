# -*- coding: utf-8 -*-
"""Band structure calculations with 20 points at gamma point (if all a,b,c=>10) or with mp general scheme gamma centered (if one param x<10, grid is duplicated in x)"""
from __future__ import absolute_import, print_function
from multiprocessing.pool import RUN

import time, os, glob
from pathlib import Path
from ase.io import read

from aiida.engine import calcfunction, submit
from aiida.orm import Code, StructureData, load_node, CifData, Str, CalcFunctionNode, load_group
from aiida.orm.querybuilder import QueryBuilder
from aiida.plugins import DataFactory, WorkflowFactory


Dict = DataFactory('dict')

print("structure.label", "structure.pk", "wc.pk")
cp2k_code = Code.get_from_string('cp2k-9.1@daint-pr128')
group_label = 'ocofs-exc12'
wc_group = load_group(group_label)

NO_RUN_LIST = [
 '20544N2_ddec.cif',
 '20115N3_ddec.cif',
 '16440N2_ddec.cif',
 '21082N2_ddec.cif',
 '15031N2_ddec.cif',
 '19140N2_ddec.cif',
 '20443N3_ddec.cif',
 '20570N3_ddec.cif',
 '13020N2_ddec.cif',
 '18030N2_ddec.cif',
 '20370N3_ddec.cif',
 '20410N2_ddec.cif',
 '20441N3_ddec.cif',
 '19450N2_ddec.cif',
 '20211N2_ddec.cif',
 '16250N3_ddec.cif',
 '19482N2_ddec.cif',
 '14030N2_ddec.cif',
 '19190N2_ddec.cif',
 '15161N2_ddec.cif',
 '20500N3_ddec.cif',
 '20310N2_ddec.cif',
 '07013N3_ddec.cif',
 '18120N3_ddec.cif',
 '19180N2_ddec.cif',
 '16111N3_ddec.cif',
 '19103N2_ddec.cif',
 '19142N2_ddec.cif',
 '20010N2_ddec.cif',
 '15211N2_ddec.cif',
 '20541N2_ddec.cif',
 '19000N3_ddec.cif',
 '19072N2_ddec.cif',
 '20403N2_ddec.cif',
 '21053N2_ddec.cif',
 '20563N3_ddec.cif',
 '16113N3_ddec.cif',
 '20350N2_ddec.cif',
 '07010N3_ddec.cif',
 '19441N2_ddec.cif',
 '16320N2_ddec.cif',
 '20501N3_ddec.cif',
 '21021N2_ddec.cif',
 '20561N3_ddec.cif',
 '20401N2_ddec.cif',
 '17151N2_ddec.cif',
 '20564N3_ddec.cif',
 '13120N2_ddec.cif',
 '18011N3_ddec.cif',
 '19252N3_ddec.cif',
 '20112N3_ddec.cif',
 '17170N2_ddec.cif',
 '15201N3_ddec.cif',
 '15202N3_ddec.cif',
 '17162N3_ddec.cif',
 '20168N2_ddec.cif',
 '19003N3_ddec.cif',
 '20160N2_ddec.cif',
 '14100N2_ddec.cif',
 '19420N3_ddec.cif',
 '20430N3_ddec.cif',
 '20571N3_ddec.cif',
 '19421N3_ddec.cif',
 '21052N2_ddec.cif',
 '18031N2_ddec.cif',
 '14073N2_ddec.cif',
 '16360N2_ddec.cif',
 '20111N3_ddec.cif',
 '20118N3_ddec.cif',
 '13000N2_ddec.cif',
 '18033N2_ddec.cif',
 '18133N3_ddec.cif',
 '20281N2_ddec.cif',
 '20161N2_ddec.cif',
 '19465N2_ddec.cif',
 '15160N2_ddec.cif',
 '19365N2_ddec.cif',
 '19020N3_ddec.cif',
 '16150N2_ddec.cif',
 '19483N2_ddec.cif',
 '13142N2_ddec.cif',
 '19001N3_ddec.cif',
 '18020N3_ddec.cif',
 '16251N3_ddec.cif',
 '16112N3_ddec.cif',
 '16061N2_ddec.cif',
 '18040N3_ddec.cif',
 '16332N3_ddec.cif',
 '15081N2_ddec.cif',
 '16400N2_ddec.cif',
 '19400N3_ddec.cif',
 '20440N3_ddec.cif',
 '21013N2_ddec.cif',
 '07011N3_ddec.cif',
 '16110N3_ddec.cif',
 '17110N2_ddec.cif',
 '14072N2_ddec.cif',
 '15070N2_ddec.cif',
 '19481N2_ddec.cif',
 '14051N3_ddec.cif',
 '20471N2_ddec.cif',
 '20300N2_ddec.cif',
 '16490N2_ddec.cif',
 '19271N2_ddec.cif',
 '19401N3_ddec.cif',
 '18021N3_ddec.cif',
 '21012N2_ddec.cif',
 '19402N3_ddec.cif',
 '21020N2_ddec.cif',
 '20510N2_ddec.cif',
 '11031N2_ddec.cif',
 '20562N3_ddec.cif',
 '19022N3_ddec.cif',
 '20560N3_ddec.cif',
 '19455N2_ddec.cif',
 '16057N2_ddec.cif',
 '20491N2_ddec.cif',
 '21014N2_ddec.cif',
 '11002N2_ddec.cif',
 '15200N3_ddec.cif',
 '19251N3_ddec.cif',
 '13101N2_ddec.cif',
 '20117N3_ddec.cif',
 '09000N3_ddec.cif',
 '19250N3_ddec.cif',
 '19480N2_ddec.cif',
 '19454N2_ddec.cif',
 '19291N2_ddec.cif',
 '18142N3_ddec.cif',
 '20651N3_ddec.cif',
 '20114N3_ddec.cif',
 '18140N2_ddec.cif'
]


@calcfunction
def structure_with_pbc(s):
    atoms = s.get_ase()
    atoms.pbc = True
    new_s = CifData(ase=atoms)
    return new_s

def main():
    # Cp2kPhotoCatWorkChain = WorkflowFactory('photocat_workchains.cp2k_photocat')
    Cp2kPhotoCatWorkChain = WorkflowFactory('photocat_workchains.cp2k_photocat')
    Cp2kMultistageWorkChain = WorkflowFactory('lsmo.cp2k_multistage')
    Cp2kBandsWorkChain = WorkflowFactory('photocat_workchains.bandstructure')

    qb = QueryBuilder()
    qb.append(Group, filters={'label': group_label}, tag='group')
    qb.append(Cp2kPhotoCatWorkChain, with_group='group', tag='photocat') #with_group='group',
    qb.append(CalcFunctionNode, filters={'label': {'==': 'get_structure_from_cif'}}, tag='get_st', with_incoming='photocat')
    qb.append(CifData, project=['label'], with_outgoing='get_st')
    qb.append(
        Cp2kMultistageWorkChain, with_incoming='photocat',  # I am appending a CalcJobNode
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
        # if result[0] in RUN_LIST:
        builder = Cp2kBandsWorkChain.get_builder()
        builder.metadata.label = 'bs_prim_test'
        builder.metadata.description = 'bs test with true primitive, symprec 0.1 seekpath'

        #old_structure = load_node(result[-1])

        #structure_cif = structure_with_pbc(old_structure)

        cifstr = load_node(result[0])
                
        #structure = get_structure_from_cif(structure_cif)
        structure = load_node(result[-1])
        #structure.label = cifstr.label

        cp2k_options = {
            'resources': {
                'num_machines': 5
            },
            'max_wallclock_seconds': 3 * 60 * 60,
            'withmpi': True,
        }

        builder.structure = structure
        builder.protocol_tag = Str('bs')
        builder.cp2k_base.cp2k.code = cp2k_code
        builder.cp2k_base.cp2k.metadata.options = cp2k_options

        if cifstr.label in NO_RUN_LIST:
            print((cifstr.label, 'no issues with primitive structure, will not run again'))
        else:
            wc = submit(builder)
            print((cifstr.label, structure.pk, wc.pk))
            wc_group.add_nodes(wc)
        time.sleep(5)


if __name__ == '__main__':
    main()

