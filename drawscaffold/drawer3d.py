import math
import ezdxf
from ezdxf import units
from ezdxf.math import Vec3, Matrix44
from ezdxf.render import forms
from ezdxf.acis import api as acis

VERTICAL_PART = 200
HORIZONTAL_PART = 250
DIAGONAL_PART = 325
FOOT_PART = 50
FOOT_INSIDE_PART = 0.15
FLOOR_SPACE = 15
SUPPORT_SPACE = 47
DEPTH = 65

POST_R = 2.5            # dikey boru ~Ø50mm
RAIL_R = 2.0            # yatay/çapraz ~Ø40mm
FOOT_R = 3.0            # ayak pimi ~Ø60mm

PLATFORM_THICK = 3.0

C_POST = 5
C_RAIL = 4
C_DIAG = 6
C_PLATFORM = 1
C_FOOT = 3

constructor_height_in_cm = float(input("Bina Uzunluğunu cm cinsinden girin: "))
constructor_width_in_cm  = float(input("Bina Genişliğini cm cinsinden girin: "))
surface_slope  = float(input("Zemin Eğimini Girin: "))

floor_count  = int(constructor_height_in_cm // VERTICAL_PART)
module_count = int(constructor_width_in_cm  // HORIZONTAL_PART)

doc = ezdxf.new("R2018")
doc.units = units.CM

vport = doc.viewports.get("*ACTIVE")[0]
vport.reset_wcs()
vport.dxf.target = (constructor_width_in_cm/2, 10, constructor_height_in_cm/2)
vport.dxf.direction = (0, -1, 0)
vport.dxf.view_twist = 0

msp = doc.modelspace()
layer = doc.layers.add("scaff")

print(f"kat sayısı: {floor_count}")
print(f"modül sayısı: {module_count}")

def solid_from_mesh(mesh, color=None, layer_name="scaff"):
    m = Matrix44.x_rotate(math.radians(90))
    mesh = mesh.copy()
    mesh.transform(m)

    body = acis.body_from_mesh(mesh)
    solid = msp.add_3dsolid(dxfattribs={"layer": layer_name})
    acis.export_dxf(solid, [body])
    if color is not None:
        solid.dxf.color = color

    return solid

def cyl_solid(p0: Vec3, p1: Vec3, r: float, color=None):
    mesh = forms.cylinder_2p(count=16, radius=r, base_center=p0, top_center=p1, caps=True)
    return solid_from_mesh(mesh, color=color)

def box_solid(center: Vec3, size: Vec3, color=None):
    mesh = forms.cube(center=True)

    mesh = mesh.scale(size.x, size.y, size.z)
    mesh = mesh.translate(center.x, center.y, center.z)
    return solid_from_mesh(mesh, color=color)

diagonal_indexes = []
if module_count >= 5:
    for i in range(0, module_count, 6):
        diagonal_indexes.append(i)
        if i + 6 <= module_count:
            diagonal_indexes.append((i + i + 6) // 2)
            diagonal_indexes.append(i + 5)
diagonal_indexes = sorted(set(diagonal_indexes))
print(diagonal_indexes)

first_floor_diagonal = ''
add_r_diagonal = True
y0 = FOOT_PART - FOOT_INSIDE_PART

for floor in range(floor_count):
    x0 = 0.0
    for module in range(module_count):
        x1 = x0 + HORIZONTAL_PART
        y1 = y0 + VERTICAL_PART
        z0 = 0.0
        z1 = DEPTH

        # 4 köşe dikme (ön/arka)
        cyl_solid(Vec3(x0, y0, z0), Vec3(x0, y1, z0), POST_R, color=C_POST)
        cyl_solid(Vec3(x1, y0, z0), Vec3(x1, y1, z0), POST_R, color=C_POST)
        cyl_solid(Vec3(x0, y0, z1), Vec3(x0, y1, z1), POST_R, color=C_POST)
        cyl_solid(Vec3(x1, y0, z1), Vec3(x1, y1, z1), POST_R, color=C_POST)

        # Kiriş seviyeleri
        floor_y = y0 + FLOOR_SPACE
        s1_y = floor_y + SUPPORT_SPACE
        s2_y = s1_y + SUPPORT_SPACE

        # Ön yataylar
        if floor!=0:
            cyl_solid(Vec3(x0, floor_y, z1), Vec3(x1, floor_y, z1), RAIL_R, color=C_RAIL)
            cyl_solid(Vec3(x0, s1_y,   z1), Vec3(x1, s1_y,   z1), RAIL_R, color=C_RAIL)
            cyl_solid(Vec3(x0, s2_y,   z1), Vec3(x1, s2_y,   z1), RAIL_R, color=C_RAIL)

        # Arka yataylar
        # cyl_solid(Vec3(x0, floor_y, z0), Vec3(x1, floor_y, z0), RAIL_R, color=C_RAIL)
        # cyl_solid(Vec3(x0, s1_y, z0), Vec3(x1, s1_y, z0), RAIL_R, color=C_RAIL)
        # cyl_solid(Vec3(x0, s2_y, z0), Vec3(x1, s2_y, z0), RAIL_R, color=C_RAIL)

        # Yan kirişler (z yönü)
        if floor!=0 and (module == 0 or module == module_count-1):
            for yy in (floor_y, s1_y, s2_y):
                if module == 0:
                    cyl_solid(Vec3(x0, yy, z0), Vec3(x0, yy, z1), RAIL_R, color=C_RAIL)
                else:
                    cyl_solid(Vec3(x1, yy, z0), Vec3(x1, yy, z1), RAIL_R, color=C_RAIL)

        # Diyagonaller (ön yüz z=0)
        if module in diagonal_indexes:
            if add_r_diagonal:
                cyl_solid(Vec3(x0, y0, z1), Vec3(x1, y1, z1), RAIL_R, color=C_DIAG)
                if not first_floor_diagonal:
                    first_floor_diagonal = 'r'
            else:
                cyl_solid(Vec3(x1, y0, z1), Vec3(x0, y1, z1), RAIL_R, color=C_DIAG)
                if not first_floor_diagonal:
                    first_floor_diagonal = 'l'
            add_r_diagonal = not add_r_diagonal

        platform_center = Vec3((x0 + x1)/2.0, floor_y, DEPTH/2.0)
        platform_size   = Vec3(HORIZONTAL_PART, PLATFORM_THICK, DEPTH)
        box_solid(platform_center, platform_size, color=C_PLATFORM)

        x0 = x1

    # Katlar arası diyagonal yön flip
    add_r_diagonal = (first_floor_diagonal != 'r')
    first_floor_diagonal = ''
    y0 += VERTICAL_PART

# Ayaklar (ön/arka)
for i in range(module_count + 1):
    x = i * HORIZONTAL_PART
    for z in (0.0, DEPTH):
        cyl_solid(Vec3(x, 0.0, z), Vec3(x, FOOT_PART, z), FOOT_R, color=C_FOOT)

        plate_center = Vec3(x, -0.5, z)
        plate_size   = Vec3(10.0, 1.0, 10.0)  # X,Y,Z
        box_solid(plate_center, plate_size, color=C_FOOT)

doc.saveas("scaffold_3dsolid.dxf")
