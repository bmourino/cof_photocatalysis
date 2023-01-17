#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""Pre-screening script to separate database in the following groups: COFs with open-shell metals, COFs with halogens (that don't have open-shell metals) and COFs with none."""


from pymatgen.core import Lattice, Structure, Molecule, Site
from pymatgen.io.cif import CifParser
import shutil, os, glob

cif_dir_in = "/home/beatriz/Documents/Projects/COFs/aiida-workflow/structures-test"
all_structures = glob.glob(os.path.join(cif_dir_in, "*.cif"))
open_shell_dir = os.path.join(cif_dir_in, "open_shell")
halogens_dir = os.path.join(cif_dir_in, "halogens")
charged_dir = os.path.join(cif_dir_in, "charged")

open_shell = ['Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn']
halogens = ['F', 'Cl', 'Br', 'I', 'At']

def is_metal(site: Site) -> bool:
    """3-d transition metal"""
    if str(site.specie) in open_shell:
        return True
    return False

def is_halogen(site: Site) -> bool:
    """checks if specie is halogen"""
    if str(site.specie) in halogens:
        return True
    return False

for s in all_structures:
    parser = CifParser(s)
    structure = parser.get_structures()[0]
    s_name = os.path.basename(s)
    for i, site in enumerate(structure):
        if is_metal(site):
            shutil.move(str(s), str(open_shell_dir))
            print(s_name, i, site, 'structure has 3d metal')
            break
        if is_halogen(site) and not is_metal(site):
            shutil.move(str(s), str(halogens_dir))
            print(s_name, i, site, 'structure has halogen')
            break