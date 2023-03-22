# DOI: 10.1039/C9TA13506E (Paper) J. Mater. Chem. A, 2020, 8, 4473-4482

from __future__ import print_function
import numpy as np
from itertools import chain
import math

from numpy import pi, sin, cos, arccos, sqrt, dot
from numpy.linalg import norm

from macrodensity.cart2frac import get_fractional_to_cartesian_matrix

def cell_to_cellpar(cell, radians=False):
    """Returns the cell parameters [a, b, c, alpha, beta, gamma].

    Angles are in degrees unless radian=True is used.
    """
    lengths = [np.linalg.norm(v) for v in cell]
    angles = []
    for i in range(3):
        j = i - 1
        k = i - 2
        ll = lengths[j] * lengths[k]
        if ll > 1e-16:
            x = np.dot(cell[j], cell[k]) / ll
            angle = 180.0 / pi * arccos(x)
        else:
            angle = 90.0
        angles.append(angle)
    if radians:
        angles = [angle * pi / 180 for angle in angles]
    return np.array(lengths + angles)

def read_cell(FILE, quiet = False):
    with open(FILE, "r") as f:
        cell = np.zeros(shape=(3, 3))
        tmp = f.readline().split()
        cell[0:1] = float(tmp[0]), float(tmp[1]), float(tmp[2])
        tmp = f.readline().split()
        cell[1:2] = float(tmp[0]), float(tmp[1]), float(tmp[2])
        tmp = f.readline().split()
        cell[2:3] = float(tmp[0]), float(tmp[1]), float(tmp[2])
    return cell

def read_geo(FILE, quiet=False):
    with open(FILE, "r") as f:
        num_atoms = int(f.readline().split()[0])
        atom_type=[''] 
        coord = np.zeros(shape=(num_atoms, 3))
        _ = f.readline()
        for i in range(num_atoms):
            tmp = f.readline().split()
            atom_type.append(tmp[0])
            coord[i,0] = float(tmp[1])
            coord[i,1] = float(tmp[2])
            coord[i,2] = float(tmp[3])
    return atom_type, coord,num_atoms

def dist_point(cube_origin_t,coord,params,num_atoms):
    a=params[0]
    b=params[1]
    c=params[2]
    alpha=params[3]
    beta=params[4]
    gamma=params[5]
    trans = get_fractional_to_cartesian_matrix(a,b,c,alpha,beta,gamma)
    cart= np.matmul(trans,cube_origin_t)
    dist=1000
    for i in range(num_atoms):
        dist_l=sqrt(((coord[i,0]-cart[0])**2)+((coord[i,1]-cart[1])**2)+((coord[i,2]-cart[2])**2))
        if dist_l < dist:
            dist = dist_l
    return dist

def test_point(cube_origin,coord,params,num_atoms,thr):
    a=params[0]
    b=params[1]
    c=params[2]
    alpha=params[3]
    beta=params[4]
    gamma=params[5]
    trans = get_fractional_to_cartesian_matrix(a,b,c,alpha,beta,gamma)
    cart= np.matmul(trans,cube_origin)
    #print(cart)
    logical=1
    for i in range(num_atoms): 
        dist=sqrt(((coord[i,0]-cart[0])**2)+((coord[i,1]-cart[1])**2)+((coord[i,2]-cart[2])**2))
        #print(dist)
        if dist < float(thr):
            logical=0
            break
    return logical

def read_cube_density(FILE, quiet = False):

##    print("Reading cube file...")
    with open(FILE, "r") as f:
        _ = f.readline()
        _ = f.readline()
        num_atoms = int(f.readline().split()[0])

        lattice = np.zeros(shape=(3,3))
        tmp = f.readline().split()
        NGX = int(tmp[0])
        lattice[0:1] = float(tmp[1]), float(tmp[2]), float(tmp[3])
        tmp = f.readline().split()
        NGY = int(tmp[0])
        lattice[1:2] = float(tmp[1]), float(tmp[2]), float(tmp[3])
        tmp = f.readline().split()
        NGZ = int(tmp[0])
        lattice[2:3] = float(tmp[1]), float(tmp[2]), float(tmp[3])

        bohr = 0.52917721067
        lattice[0:1]=NGX*lattice[0:1]*bohr
        lattice[1:2]=NGY*lattice[1:2]*bohr
        lattice[2:3]=NGZ*lattice[2:3]*bohr


        atom_type = np.zeros(num_atoms)
        coord = np.zeros(shape=(num_atoms, 3))
        for i in range(num_atoms):
            tmp = f.readline().split()
            atom_type[i] = int(tmp[0])
            coord[i,0] = float(tmp[2])
            coord[i,1] = float(tmp[3])
            coord[i,2] = float(tmp[4])


##        print("Reading 3D data...")
        Potential = (f.readline().split()
            for i in range((int(NGZ/6) + (NGZ%6 > 0)) * NGY *NGX))
        Potential = np.fromiter(chain.from_iterable(Potential), float)

##    print("Average of the potential = ", np.average(Potential))
    return Potential, NGX, NGY, NGZ, lattice



def density_grid_cube(Density, nx, ny, nz, Volume=1):
    '''Convert the potential
    Args:
       Density: Array of the grid potential of a cube file
       nx,y,z : Number of mesh points in x/y/z
    Returns:
       Potential_grid: the (normalized) quantity on a mesh
    '''
    l = 0
    hartree2eV = 27.211399
    Potential_grid = np.zeros(shape=(nx,ny,nz))
    for k in range(nx):
        for j in range(ny):
            for i in range(nz):
                Potential_grid[k,j,i] = (Density[l] / Volume) * hartree2eV 
                l = l + 1
    return Potential_grid

