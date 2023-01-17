import glob, os
from cube import Cube
ecubes = glob.glob(os.path.join(efolder, "aiida-WFN*.cube"))
hcubes = glob.glob(os.path.join(hfolder, "aiida-WFN*.cube"))
a=[]
c=[]
for cube in ecubes:
    b = cube.split("_")[-3]
    if b in a:
        c = b
    else:
        a.append(b)
efile = "aiida-WFN_" + c + "_1-1_0.cube" #was 1
einj = glob.glob(os.path.join(efolder, efile))
e=[]
d=[]
for cube in hcubes:
    b = cube.split("_")[-3]
    if b in e:
        d = b
    else:
        e.append(b)
hfile = "aiida-WFN_" + d + "_2-1_0.cube"
hinj = glob.glob(os.path.join(hfolder, hfile))
cubee = Cube(einj[0])
cubeh = Cube(hinj[0])
so = cubee.__mul__(cubeh)
print(so)
