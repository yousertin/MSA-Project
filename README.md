# Abstract

This project presents a Direct Stiffness Method (DSM) calculator for three-dimensional structural analysis. The program is designed to read structural models from a JSON input file, allowing users to define units, nodal coordinates, element connectivity, boundary conditions, material properties, section properties, nodal loads, member loads, temperature loads, and fabrication errors in a clear and organized format. By combining a structured input file with a Jupyter Notebook workflow, the project provides a straightforward and flexible framework for building and analyzing structural systems.

The README is organized to guide users through the full workflow of the program. It first explains how to prepare the JSON input file and how each data block should be modified to define a structural model correctly. It then introduces how to run the notebook and interpret the analysis process. To demonstrate the validity and applicability of the program, the project includes validation examples for a 3D truss structure and a 3D frame structure, followed by a more comprehensive study of a complex structure. Overall, this project aims to provide a practical and extensible DSM-based tool for learning, verification, and structural analysis of 3D systems.

---

# I. How to use 

This project will prompt you to install the required dependencies the first time it is opened in VS Code. If you choose Yes, the corresponding environment will be installed automatically.

## (I) Modify the JSON Input File

The program reads the structural model from a JSON file.
Users can modify the model by editing the corresponding sections in the JSON file.  
The overall structure is:

```json
{
    "UNIT": {},
    "NODE": {},
    "ELEM": {},
    "CONS": {},
    "MATL": {},
    "SECT": {},
    "NDLD": {},
    "MBLD": {},
    "TPLD": {},
    "FABR": {}
}
```

### 1. General Rules

1. All IDs are stored as strings, such as `"1"`, `"2"`, `"3"`.
2. `NODE`, `ELEM`, `MATL`, and `SECT` IDs must be consistent across the file.
3. The unit system must match the values used in the file. In the current template:
   - force: `kN`
   - length: `m`
   - temperature: `°C`
4. Make sure the JSON syntax is valid:
   - use double quotes `"`
   - do not leave a trailing comma after the last item in an object or array

---

### 2. UNIT

The `UNIT` block defines the unit system for the entire model.

```json
"UNIT": {
    "FORCE": "KN",
    "DIST": "M",
    "TEMPER": "C"
}
```

Normally this block only needs to be set once.

---

### 3. NODE

The `NODE` block defines nodal coordinates.

```json
"NODE": {
    "1": {
        "X": 0.0,
        "Y": 0.0,
        "Z": 0.0
  },
    "2": {
        "X": 5.0,
        "Y": 0.0,
        "Z": 0.0
  }
}
```

- `"1"`, `"2"` are node IDs
- `X`, `Y`, `Z` are the global coordinates of each node

To add a new node, create a new ID and provide its coordinates.

---

### 4. ELEM

The `ELEM` block defines element connectivity and element properties.

```json
"ELEM": {
    "1": {
        "TYPE": "TRUSS",
        "MATL": 1,
        "SECT": 1,
        "NODE": [1, 2],
        "MT": 0
  }
}
```

#### Fields

- `TYPE`: element type
  - `"TRUSS"`
  - `"BEAM"`
  - `"FRAME"`
- `MATL`: material ID
- `SECT`: section ID
- `NODE`: two end nodes of the element
- `MT`: release-type indicators used by the program

#### Meaning of `MT`

Each of these fields uses the following integer code:

- `0` = fixed-fixed
- `1` = release at I end
- `2` = release at J end
- `3` = hinge-hinge

Here:

- **I end** means the first node in the `NODE` array
- **J end** means the second node in the `NODE` array

For example, if:

```json
"NODE": [3, 4]
```

then:
- node `3` is the **I end**
- node `4` is the **J end**

#### Example

```json
"2": {
    "TYPE": "FRAME",
    "MATL": 2,
    "SECT": 2,
    "NODE": [3, 4],
    "MT": 1
}
```

When modifying an element, make sure:
- both node IDs already exist in `NODE`
- the referenced material already exists in `MATL`
- the referenced section already exists in `SECT`

---

### 5. CONS

The `CONS` block defines constrained degrees of freedom at nodes.

```json
"CONS": {
    "1": {
        "Ux": 0,
        "Uy": 0,
        "Uz": 0,
        "Rx": 0,
        "Ry": 0,
        "Rz": 0
  }
}
```

Here the key corresponds to the node ID.

#### Meaning

- `Ux`, `Uy`, `Uz`: translational constraints
- `Rx`, `Ry`, `Rz`: rotational constraints

A value of `0` means the corresponding DOF is fixed at zero.

#### Example

Fully fixed support at node 1:

```json
"1": {
    "Ux": 0,
    "Uy": 0,
    "Uz": 0,
    "Rx": 0,
    "Ry": 0,
    "Rz": 0
}
```

Pinned support example:

```json
"2": {
    "Ux": 0,
    "Uy": 0,
    "Uz": 0
}
```

---

### 6. MATL

The `MATL` block defines material properties.

```json
"MATL": {
    "1": {
        "NAME": "CONCRETE",
        "E": 3.0e7,
        "TEMPCOEF": 1.0,
        "nu": 0.3
    },
    "2": {
        "NAME": "STEEL",
        "E": 2.0e8,
        "TEMPCOEF": 1.0,
        "nu": 0.3
    }
}
```

#### Fields

- `NAME`: material name
- `E`: elastic modulus
- `TEMPCOEF`: thermal coefficient used in temperature loading
- `nu`: poisson's ratio

#### Example

```json
"1": {
    "NAME": "STEEL",
    "E": 2.0e8,
    "TEMPCOEF": 1.2e-5,
    "nu": 0.3
}
```

Note: under the `kN-m` unit system, elastic modulus should be given in `kN/m^2`.

---

### 7. SECT

The `SECT` block defines section properties.

```json
    "SECT": {
    "1": {
        "A": 1.0,
        "Iy": 1.0,
        "Iz": 1.0,
        "J": 1.0
    }
}
```

#### Fields

- `A`: cross-sectional area
- `Iy`: second moment of area about local y-axis
- `Iz`: second moment of area about local z-axis
- `J`: torsional constant

#### Example

```json
"2": {
    "A": 0.02,
    "Iy": 8.0e-5,
    "Iz": 5.0e-5,
    "J": 1.0e-5
}
```

For truss elements, only `A` is essential, but the current format keeps all four properties for consistency.

---

### 8. NDLD

The `NDLD` block defines nodal loads.

```json
"NDLD": {
    "2": {
        "Fx": 0.0,
        "Fy": -100.0,
        "Fz": 0.0,
        "Mx": 0.0,
        "My": 0.0,
        "Mz": 0.0
  }
}
```

Here the key corresponds to the node ID.

#### Fields

- `Fx`, `Fy`, `Fz`: nodal forces
- `Mx`, `My`, `Mz`: nodal moments

#### Example

Apply a downward force of `100 kN` at node 2:

```json
"2": {
    "Fx": 0.0,
    "Fy": -100.0,
    "Fz": 0.0,
    "Mx": 0.0,
    "My": 0.0,
    "Mz": 0.0
}
```

---

### 9. MBLD

The `MBLD` block defines member loads in the **global coordinate system**.

```json
"MBLD": {
    "1": {
        "q_global": [0.0, 0.0, 0.0],
        "P_global": [0.0, 0.0, 0.0],
        "P_loc": 0.0,
        "M_global": [0.0, 0.0, 0.0],
        "M_loc": 0.0
    }
}
```

Here the key corresponds to the element ID.

#### Fields

- `q_global`: full-span uniformly distributed load vector in global coordinates, given as `[qx, qy, qz]`
- `P_global`: concentrated force vector in global coordinates, given as `[Px, Py, Pz]`
- `P_loc`: relative location of the concentrated force along the member, in the range `[0, 1]`
- `M_global`: concentrated moment vector in global coordinates, given as `[Mx, My, Mz]`
- `M_loc`: relative location of the concentrated moment along the member, in the range `[0, 1]`

#### Notes

- All load vectors are defined in the **global Cartesian coordinate system**.
- `q_global` is assumed to act over the **entire member length**.
- `P_global` represents **one concentrated force** on the member.
- `M_global` represents **one concentrated moment** on the member.
- In the current implementation of `fef_cal_global`, the concentrated moment is only supported when its transformed local equivalent acts about the **local x-axis** only.

#### Example

Uniform distributed load on element 1 in the negative global Z direction:

```json
"1": {
    "q_global": [0.0, 0.0, -20.0],
    "P_global": [0.0, 0.0, 0.0],
    "P_loc": 0.0,
    "M_global": [0.0, 0.0, 0.0],
    "M_loc": 0.0
}
```

Point load on element 2 at midspan in the negative global Y direction:

```json
"2": {
    "q_global": [0.0, 0.0, 0.0],
    "P_global": [0.0, -50.0, 0.0],
    "P_loc": 0.5,
    "M_global": [0.0, 0.0, 0.0],
    "M_loc": 0.0
}
```

Concentrated moment on element 3 at midspan:

```json
"3": {
    "q_global": [0.0, 0.0, 0.0],
    "P_global": [0.0, 0.0, 0.0],
    "P_loc": 0.0,
    "M_global": [10.0, 0.0, 0.0],
    "M_loc": 0.5
}
```

---

### 10. TPLD

The `TPLD` block defines uniform temperature loading for elements.

```json
"TPLD": {
    "1": {
        "TEMP": 20.0
    }
}
```

Here the key corresponds to the element ID.

#### Field

- `TEMP`: uniform temperature change applied to the element

#### Example

Apply a uniform temperature increase of `20 C` to element 1:

```json
"1": {
    "TEMP": 20.0
}
```

---

### 11. FABR

The `FABR` block defines fabrication error for elements.

```json
"FABR": {
    "1": {
        "ERROR": 0.002
    }
}
```

Here the key corresponds to the element ID.

#### Field

- `ERROR`: fabrication error assigned to the element

#### Example

Apply a fabrication error of `0.002 m` to element 1:

```json
"1": {
    "ERROR": 0.002
}
```

---

### 12. Example Workflow

To build a model, users typically follow these steps:

1. Define the unit system in `UNIT`
2. Add all nodal coordinates in `NODE`
3. Define material properties in `MATL`
4. Define section properties in `SECT`
5. Create elements in `ELEM`
6. Add supports in `CONS`
7. Add nodal loads in `NDLD`
8. Add member loads in `MBLD`
9. Add temperature loads in `TPLD` if needed
10. Add fabrication errors in `FABR` if needed

---

### 13. Important Notes

- Keep all IDs consistent across different blocks
- Check that each element references valid node, material, and section IDs
- Check that all values follow the selected unit system
- Validate the JSON file before running the program
- If the program reports missing data, first check whether all required IDs and fields are defined correctly

---

## (II) Run the Jupyter Notebook

The program can be run directly in a Jupyter Notebook by specifying the input JSON file path, then calling the corresponding solver and postprocessing function.

### 1. Pure Truss Structure

For a model containing only **TRUSS** elements:

- Use the solver with the prefix `truss`
- Use the postprocessor with the prefix `truss`

Example:

```python
filepath = 'inputs/validation_truss_xxxx.json'

result = solver.truss_solver(filepath)
pp = truss_output(
    filepath,
    solver_result,
    deformation_scale=None,
    load_scale=None,
    show_node_ids=True,
    show_member_ids=False,
    show=True,
    table_output="xlsx",
):
```

### 2. Pure Frame Structure

For a model containing only **FRAME** elements:

- Use the solver with the prefix `frame`
- Use the postprocessor with the prefix `frame`

Example:

```python
filepath = 'inputs/validation_frame_xxxx.json'

result = solver.frame_solver(filepath)
pp = postprocess.frame_output(
    filepath,
    solver_result,
    deformation_scale=None,
    load_scale=None,
    show_node_ids=True,
    show_member_ids=False,
    show=True,
    table_output="xlsx",
):
```

### 3. Hybrid Structure

For a model containing both **TRUSS** and **FRAME** elements:

- Use the solver with the prefix `hybrid`
- Use the postprocessor with the prefix `hybrid`

This is because the hybrid model is solved by the hybrid solver, while the result output is handled using the hybrid postprocessor.

Example:

```python
filepath = 'inputs/final_structure_xxxx.json'

result = solver.hybrid_solver(filepath)
pp = postprocess.hybrid_output(
    filepath,
    solver_result,
    deformation_scale=None,
    load_scale=None,
    show_node_ids=True,
    show_member_ids=False,
    show=True,
    table_output="xlsx",
):
```

### Notes:

The parameters of output function are defined as follows:

- `filepath`: path to the input JSON model file
- `solver_result`: result dictionary returned by the solver
- `deformation_scale`: scale factor used for plotting the deformed shape; `None` means the default or automatic scale is used
- `load_scale`: scale factor used for plotting the applied loads; `None` means the default or automatic scale is used
- `show_node_ids`: whether node IDs are displayed in the figure
- `show_member_ids`: whether member IDs are displayed in the figure
- `show`: whether the figure is displayed directly
- `table_output`: output format of the result tables; for example, `"xlsx"` exports the tables to an Excel file

---

# II. Example of 3D Truss Structure Validation

### Model Definition

The node numbering order and corresponding positions are as follows:

- **Odd-numbered nodes** are on the left truss plane: $x=0$
- **Even-numbered nodes** are on the right truss plane: $x=3$
- Along the roof truss length, the nodes are numbered in ascending order of **$y$**
- The roof height is represented by the **$z$ coordinate**: bottom chord nodes have $z=0$, while upper chord or ridge nodes have $z=2.598$ or $z=5.196$

| Node | Position $(X, Y, Z)$ m | Description |
|---|---|---|
| 1 | $(0,\ 0,\ 0)$ | Left end bottom node |
| 2 | $(3,\ 0,\ 0)$ | Right end bottom node |
| 3 | $(0,\ 4,\ 2.598)$ | Left front upper chord node |
| 4 | $(3,\ 4.5,\ 2.598)$ | Right front upper chord node |
| 5 | $(0,\ 6,\ 0)$ | Left bottom chord node |
| 6 | $(3,\ 6,\ 0)$ | Right bottom chord node |
| 7 | $(0,\ 9,\ 5.196)$ | Left node near the ridge |
| 8 | $(3,\ 9,\ 5.196)$ | Right node near the ridge |
| 9 | $(0,\ 12,\ 0)$ | Left bottom chord node |
| 10 | $(3,\ 12,\ 0)$ | Right bottom chord node |
| 11 | $(0,\ 13.5,\ 2.598)$ | Left rear upper chord node |
| 12 | $(3,\ 13.5,\ 2.598)$ | Right rear upper chord node |
| 13 | $(0,\ 18,\ 0)$ | Left end bottom node |
| 14 | $(3,\ 18,\ 0)$ | Right end bottom node |

It can also be understood in pairs of transverse nodes:

- Pair 1: 1–2, $y=0$
- Pair 2: 3–4, $y=4.5$
- Pair 3: 5–6, $y=6$
- Pair 4: 7–8, $y=9$
- Pair 5: 9–10, $y=12$
- Pair 6: 11–12, $y=13.5$
- Pair 7: 13–14, $y=18$

The element definitions are listed below.

All members are defined as **TRUSS** elements with **Material 1**, **Section 1**, and **MT = 0**.

| Element | Connectivity $(i, j)$ | Description |
|---|---:|---|
| 1 | (1, 5) | Left bottom chord member |
| 2 | (1, 3) | Left end diagonal member |
| 3 | (3, 5) | Left lower diagonal member |
| 4 | (3, 7) | Left upper chord member |
| 5 | (5, 7) | Left web diagonal member |
| 6 | (5, 9) | Left bottom chord member |
| 7 | (7, 9) | Left web diagonal member |
| 8 | (7, 11) | Left upper chord member |
| 9 | (9, 11) | Left lower diagonal member |
| 10 | (9, 13) | Left bottom chord member |
| 11 | (11, 13) | Left end diagonal member |
| 12 | (2, 6) | Right bottom chord member |
| 13 | (2, 4) | Right end diagonal member |
| 14 | (4, 6) | Right lower diagonal member |
| 15 | (4, 8) | Right upper chord member |
| 16 | (6, 8) | Right web diagonal member |
| 17 | (6, 10) | Right bottom chord member |
| 18 | (8, 10) | Right web diagonal member |
| 19 | (8, 12) | Right upper chord member |
| 20 | (10, 12) | Right lower diagonal member |
| 21 | (10, 14) | Right bottom chord member |
| 22 | (12, 14) | Right end diagonal member |
| 23 | (1, 2) | Transverse end bottom tie |
| 24 | (3, 4) | Transverse front upper tie |
| 25 | (5, 6) | Transverse bottom tie |
| 26 | (7, 8) | Transverse ridge tie |
| 27 | (9, 10) | Transverse bottom tie |
| 28 | (11, 12) | Transverse rear upper tie |
| 29 | (13, 14) | Transverse end bottom tie |
| 30 | (1, 4) | Front end transverse diagonal |
| 31 | (2, 3) | Front end transverse diagonal |
| 32 | (1, 6) | Lower transverse diagonal |
| 33 | (2, 5) | Lower transverse diagonal |
| 34 | (3, 8) | Front upper transverse diagonal |
| 35 | (4, 7) | Front upper transverse diagonal |
| 36 | (5, 10) | Middle lower transverse diagonal |
| 37 | (6, 9) | Middle lower transverse diagonal |
| 38 | (7, 12) | Upper transverse diagonal |
| 39 | (8, 11) | Upper transverse diagonal |
| 40 | (9, 14) | Rear lower transverse diagonal |
| 41 | (10, 13) | Rear lower transverse diagonal |
| 42 | (11, 14) | Rear end transverse diagonal |
| 43 | (12, 13) | Rear end transverse diagonal |

It can also be understood by member groups:

- **Left truss plane members:** 1--11  
- **Right truss plane members:** 12--22  
- **Transverse members:** 23--29  
- **Transverse bracing members:** 30--43

In addition, the cross-section info are listed below:

- Young's Modulus: $E=70 GPa$
- Area: $A=4000 mm^2$

In summary:

**The nodes are numbered from front to back in the $y$ direction, and for each transverse section, the left node is numbered first and the right node second. Thus, left-side nodes are odd and right-side nodes are even.**

### Validation File Description for Truss Model

In addition to the geometric modeling information above, four separate validation files were prepared to verify the implementation of different load cases. All four files use the same structural geometry, element connectivity, material, section, and boundary-condition definitions. The difference between them lies in the applied loading or imposed action.

#### 1. `validation_truss_nodal_loads.json`

This file is used to validate the nodal load function.

- A nodal load of $F_z = -100$ $kN$ is applied at node 11
- A nodal load of $F_x = 100$ $kN$ is applied at node 12
- All other nodal loads are zero
- No temperature load, fabrication error, or support displacement is applied in this case

This case is intended to verify whether the program can correctly assemble concentrated nodal forces into the global load vector and produce the corresponding structural response.

#### 2. `validation_truss_supp_disp.json`

This file is used to validate the support displacement function.

- An imposed support displacement of $u_z = 0.01$ $m$ is specified
- No external nodal load is applied
- No temperature load or fabrication error is applied in this case

This case is intended to verify whether the program can correctly convert prescribed support movement into the equivalent structural response and reaction output.

#### 3. `validation_truss_temperature.json`

This file is used to validate the temperature load function.

- A temperature change of $\Delta T = 30^\circ\mathrm{C}$ is assigned to all 43 truss elements
- No external nodal load is applied
- No support displacement or fabrication error is applied in this case

This case is intended to verify whether the program can correctly calculate thermal strain effects and assemble the corresponding equivalent load contribution.

#### 4. `validation_truss_fab_error.json`

This file is used to validate the fabrication error function.

- A fabrication error value of $\mathrm{ERROR} = 0.01$ $m$ on element 6 is assigned
- A fabrication error value of $\mathrm{ERROR} = -0.01$ $m$ on element 17 (Regarding the xz-plane symmetry of element 6) is assigned
- No external nodal load is applied
- No support displacement or temperature load is applied in this case

This case is intended to verify whether the program can correctly account for initial length error effects in truss members and include them in the analysis.

#### Summary

These four validation files were created so that each loading function can be checked independently before applying the program to more complicated structural cases. In other words:

- `validation_truss_nodal_loads.json` verifies nodal force input
- `validation_truss_supp_disp.json` verifies imposed support displacement
- `validation_truss_temperature.json` verifies temperature loading
- `validation_truss_fab_error.json` verifies fabrication error loading

By separating the validation cases in this way, it becomes easier to confirm that each loading module is implemented correctly and that the corresponding response is physically reasonable.

---

# III. Example of 3D Frame Structure Validation

### Model Definition

The frame validation model is a **three-dimensional four-column frame structure** with a square plan and multiple floor levels.

The node numbering order and corresponding positions are as follows:

- The structure has a square plan of **$8 \times 8$ m**
- The four corner columns are located at:
  - $(0,\ 0)$
  - $(0,\ 8)$
  - $(8,\ 8)$
  - $(8,\ 0)$
- The structure has five elevation levels in the **$z$ direction**:
  - $z=0$
  - $z=6$
  - $z=12$
  - $z=18$
  - $z=24$
- At each elevation, the nodes are numbered in a consistent order around the frame:
  - first $(0,\ 0)$
  - second $(0,\ 8)$
  - third $(8,\ 8)$
  - fourth $(8,\ 0)$
- Therefore, nodes are numbered **floor by floor from bottom to top**

| Node | Position $(X, Y, Z)$ m | Description |
|---|---|---|
| 1 | $(0,\ 0,\ 0)$ | Bottom node at corner 1 |
| 2 | $(0,\ 8,\ 0)$ | Bottom node at corner 2 |
| 3 | $(8,\ 8,\ 0)$ | Bottom node at corner 3 |
| 4 | $(8,\ 0,\ 0)$ | Bottom node at corner 4 |
| 5 | $(0,\ 0,\ 6)$ | First-floor node at corner 1 |
| 6 | $(0,\ 8,\ 6)$ | First-floor node at corner 2 |
| 7 | $(8,\ 8,\ 6)$ | First-floor node at corner 3 |
| 8 | $(8,\ 0,\ 6)$ | First-floor node at corner 4 |
| 9 | $(0,\ 0,\ 12)$ | Second-floor node at corner 1 |
| 10 | $(0,\ 8,\ 12)$ | Second-floor node at corner 2 |
| 11 | $(8,\ 8,\ 12)$ | Second-floor node at corner 3 |
| 12 | $(8,\ 0,\ 12)$ | Second-floor node at corner 4 |
| 13 | $(0,\ 0,\ 18)$ | Third-floor node at corner 1 |
| 14 | $(0,\ 8,\ 18)$ | Third-floor node at corner 2 |
| 15 | $(8,\ 8,\ 18)$ | Third-floor node at corner 3 |
| 16 | $(8,\ 0,\ 18)$ | Third-floor node at corner 4 |
| 17 | $(0,\ 0,\ 24)$ | Roof-level node at corner 1 |
| 18 | $(0,\ 8,\ 24)$ | Roof-level node at corner 2 |
| 19 | $(8,\ 8,\ 24)$ | Roof-level node at corner 3 |
| 20 | $(8,\ 0,\ 24)$ | Roof-level node at corner 4 |

It can also be understood by floor levels:

- Ground level: 1--4, $z=0$
- First floor: 5--8, $z=6$
- Second floor: 9--12, $z=12$
- Third floor: 13--16, $z=18$
- Roof level: 17--20, $z=24$

The element definitions are listed below.

All members are defined as **FRAME** elements with **Material 1**, **Section 1**, and **MT = 0**.

| Element | Connectivity $(i, j)$ | Description |
|---|---:|---|
| 1 | (1, 5) | Column member at corner 1, level 0--6 |
| 2 | (2, 6) | Column member at corner 2, level 0--6 |
| 3 | (3, 7) | Column member at corner 3, level 0--6 |
| 4 | (4, 8) | Column member at corner 4, level 0--6 |
| 5 | (5, 9) | Column member at corner 1, level 6--12 |
| 6 | (6, 10) | Column member at corner 2, level 6--12 |
| 7 | (7, 11) | Column member at corner 3, level 6--12 |
| 8 | (8, 12) | Column member at corner 4, level 6--12 |
| 9 | (9, 13) | Column member at corner 1, level 12--18 |
| 10 | (10, 14) | Column member at corner 2, level 12--18 |
| 11 | (11, 15) | Column member at corner 3, level 12--18 |
| 12 | (12, 16) | Column member at corner 4, level 12--18 |
| 13 | (13, 17) | Column member at corner 1, level 18--24 |
| 14 | (14, 18) | Column member at corner 2, level 18--24 |
| 15 | (15, 19) | Column member at corner 3, level 18--24 |
| 16 | (16, 20) | Column member at corner 4, level 18--24 |
| 17 | (5, 6) | First-floor beam |
| 18 | (6, 7) | First-floor beam |
| 19 | (7, 8) | First-floor beam |
| 20 | (8, 5) | First-floor beam |
| 21 | (9, 10) | Second-floor beam |
| 22 | (10, 11) | Second-floor beam |
| 23 | (11, 12) | Second-floor beam |
| 24 | (12, 9) | Second-floor beam |
| 25 | (13, 14) | Third-floor beam |
| 26 | (14, 15) | Third-floor beam |
| 27 | (15, 16) | Third-floor beam |
| 28 | (16, 13) | Third-floor beam |
| 29 | (17, 18) | Roof beam |
| 30 | (18, 19) | Roof beam |
| 31 | (19, 20) | Roof beam |
| 32 | (20, 17) | Roof beam |

It can also be understood by member groups:

- **Column members:** 1--16  
- **First-floor beam members:** 17--20  
- **Second-floor beam members:** 21--24  
- **Third-floor beam members:** 25--28  
- **Roof beam members:** 29--32  

The support conditions are defined as follows:

- Nodes **1, 2, 3, and 4** are the four ground-contact nodes
- These four nodes are all defined as **fixed supports**
- Therefore, all six degrees of freedom at these nodes are restrained:
  - $U_x=0$
  - $U_y=0$
  - $U_z=0$
  - $R_x=0$
  - $R_y=0$
  - $R_z=0$

In summary:

**The nodes are numbered floor by floor from bottom to top. At each elevation, the four corner nodes are numbered in a consistent order around the square frame. The model consists of four vertical columns and four horizontal beams at each upper level, forming a regular three-dimensional frame validation structure.**

### Validation File Description for Frame Model

In addition to the geometric modeling information above, six separate validation files were prepared to verify the implementation of different loading cases and release conditions for the 3D frame model. All six files use the same frame geometry, element connectivity, material, section, and boundary-condition definitions. In particular, the model consists of a 20-node, 32-element, four-level three-dimensional frame, and nodes 1 to 4 are fully restrained. The difference between the files lies in the applied loading, imposed support movement, fabrication error, temperature action, or release condition.

#### 1. `validation_frame_nodal_loads.json`

This file is used to validate the nodal load function for the frame model.

- A nodal moment of $M_x = 1000$ $kN \cdot m$ is applied at node 5
- A nodal moment of $M_x = 1000$ $kN \cdot m$ is applied at node 8
- A nodal moment of $M_y = -1000$ $kN \cdot m$ is applied at node 15
- A nodal moment of $M_y = -1000$ $kN \cdot m$ is applied at node 16
- No member load, temperature load, fabrication error, or support displacement is applied in this case

This case is intended to verify whether the program can correctly assemble concentrated nodal actions, especially nodal moments, into the global load vector and produce the corresponding frame response.

#### 2. `validation_frame_member_loads.json`

This file is used to validate the member load function for the frame model.

- A uniformly distributed member load of $q_x = 25$ $kN/m$ in the global $x$-direction is assigned to elements 3, 4, 7, 8, 11, 12, 15, 16, 19, 23, 27, and 31
- No concentrated member force is applied
- No concentrated member moment is applied
- No external nodal load, support displacement, temperature load, or fabrication error is applied in this case

This case is intended to verify whether the program can correctly convert distributed member loads into equivalent nodal actions and recover the corresponding frame response.

#### 3. `validation_frame_moment_release.json`

This file is used to validate the moment release function for the frame model.

- The same uniformly distributed member load of $q_x = 25$ $kN/m$ in the global $x$-direction is assigned to elements 3, 4, 7, 8, 11, 12, 15, 16, 19, 23, 27, and 31
- Element 7 is assigned with `MT = 2`
- Element 11 is assigned with `MT = 1`
- Element 22 is assigned with `MT = 2`
- Element 23 is assigned with `MT = 1`
- No external nodal load, support displacement, temperature load, or fabrication error is applied in this case

This case is intended to verify whether the program can correctly handle member end release conditions in the frame formulation while still accounting for member loading effects.

#### 4. `validation_frame_supp_disp.json`

This file is used to validate the support displacement function for the frame model.

- An imposed support displacement of $u_x = -0.01$ $m$, $u_y = -0.01$ $m$, and $u_z = -0.01$ $m$ is specified at node 1
- An imposed support displacement of $u_x = 0.01$ $m$, $u_y = 0.01$ $m$, and $u_z = 0.01$ $m$ is specified at node 3
- No external nodal load is applied
- No member load, temperature load, or fabrication error is applied in this case

This case is intended to verify whether the program can correctly transform prescribed support movement into the equivalent structural response and reaction output in a 3D frame system.

#### 5. `validation_frame_temperature.json`

This file is used to validate the temperature load function for the frame model.

- A temperature change of $\Delta T = -30^\circ\mathrm{C}$ is assigned to all 32 frame elements
- No external nodal load is applied
- No member load, support displacement, or fabrication error is applied in this case

This case is intended to verify whether the program can correctly calculate thermal strain effects in frame members and assemble the corresponding equivalent load contribution.

#### 6. `validation_frame_fab_error.json`

This file is used to validate the fabrication error function for the frame model.

- A fabrication error value of $\mathrm{ERROR} = -0.01$ $m$ is assigned to element 5
- A fabrication error value of $\mathrm{ERROR} = -0.01$ $m$ is assigned to element 6
- No external nodal load is applied
- No member load, support displacement, or temperature load is applied in this case

This case is intended to verify whether the program can correctly account for initial length error effects in frame members and include them in the analysis.

#### Summary

These six validation files were created so that each loading function and release condition can be checked independently before applying the program to more complicated frame structures. In other words:

- `validation_frame_nodal_loads.json` verifies nodal action input
- `validation_frame_supp_disp.json` verifies imposed support displacement
- `validation_frame_temperature.json` verifies temperature loading
- `validation_frame_fab_error.json` verifies fabrication error loading
- `validation_frame_member_loads.json` verifies distributed member loading
- `validation_frame_moment_release.json` verifies moment release implementation

By separating the validation cases in this way, it becomes easier to confirm that each module is implemented correctly and that the corresponding frame response is physically reasonable.

---

# IV. One Complex Structure Study

### Model Definition

The final bridge model is a **three-dimensional three-span continuous arch-truss bridge structure**.  
It is composed of two longitudinal main truss planes, transverse connecting members, vertical and diagonal web systems, and arch ribs arranged in all three spans.

The overall bridge layout can be summarized as follows:

- The **total bridge length** is **$576$ m**
- The **span arrangement** is:
  - **$180 + 216 + 180$ m**
- The structure has **four support lines**, corresponding to the two end supports and two internal supports
- The bridge is modeled as a **continuous system over three spans**
- The bridge adopts **two longitudinal main trusses**
- The **transverse spacing between the two main trusses** is **$12.5$ m**
- The model uses a **regular longitudinal panel length of $9$ m**

From the bridge-engineering point of view, the superstructure may be understood as a **continuous stiffening-truss system combined with arch ribs**.

The truss geometry is defined as follows:

- The **standard main-truss depth** is **$8$ m**
- In the arch-foot region, the structure includes a **lower extended truss segment of $8$ m**
- This extension is not a simple vertical drop, but a **large X-shaped transition panel** near the arch springing
- Within this transition region, one diagonal member extends downward directly toward the support, forming the characteristic local geometry at the arch foot

The arch system can be summarized as follows:

- The bridge contains **three arch zones**, one in each span
- Since the bridge has two longitudinal truss planes, the full model contains **six arch ribs in total**
- The **side-span arch ribs** are arranged in the two side spans
- The **main-span arch ribs** are arranged in the center span

For the **side spans**:

- The **arch-foot horizontal length** is **$45$ m** from the support line to the springing position
- The **arch rib span** is **$90$ m**
- The **arch height** is **$24$ m**
- The corresponding **rise-to-span ratio** is:

$$
\frac{f}{L}=\frac{24}{90}\approx \frac{1}{3.75}
$$

For the **main span**:

- The **arch-foot horizontal length** is also **$45$ m** from each internal support line to the springing position
- The **arch rib span** is **$126$ m**
- The **arch height** is **$32$ m**
- The corresponding **rise-to-span ratio** is:

$$
\frac{f}{L}=\frac{32}{126}\approx \frac{1}{3.94}
$$

Therefore, the middle span adopts a **higher arch rib** than the two side spans, while the side spans use relatively lower arch ribs. This produces a clear distinction between the central main load-carrying region and the side-span transition regions.

In terms of element modeling, the bridge is defined as a **mixed truss-frame system**:

- The **arch rib members** are modeled as **FRAME** elements so that their bending behavior can be considered
- All other members are modeled as **TRUSS** elements
- This includes the main truss chords, vertical members, diagonal members, transverse connecting members, and the arch-foot transition members
- In the current model, the arch ribs are the only members assigned as frame elements, while the remaining structural members are treated as axial-force members

### Final Structure Model Description

The final structure is a three-dimensional bridge model used for the final-stage verification of the program. It is a mixed truss-frame model: most members are modeled as truss elements, while the arch rib members are modeled as frame elements so that bending behavior can be included.

All five files use the same structural geometry, element connectivity, material, section, and support definitions. The difference between them lies only in the applied load case.

The model uses one steel material and one section set:

- Material: `STEEL`
- $E = 70000000.0$
- $\nu = 0.3$
- `TEMPCOEF = 1.0`

- $A = 0.0474$
- $I_y = 0.00222$
- $I_z = 0.00222$
- $J = 2.22 \times 10^{-5}$

The five model files are listed below:

#### 1. `final_structure_nodal_loads.json`

This file is used to verify the nodal load function for the final structure model.

- Downward nodal loads are applied on selected top-surface nodes
- The main nonzero nodal load is $F_z = -50$ kN
- No additional member load, temperature load, or special support displacement is introduced beyond the model definition

#### 2. `final_structure_member_loads.json`

This file is used to verify the member load function for the final structure model.

- Distributed member loads are applied to selected elements
- The applied member load is `q_global = [0.0, -1.0, 0.0]` kN/m
- This case is intended to represent lateral loading on one side of the bridge

#### 3. `final_structure_supp_disp.json`

This file is used to verify the support displacement function for the final structure model.

- Imposed support displacement is assigned at selected support nodes
- The main prescribed displacement is $u_z = 0.01$ m
- This case is intended to test the structural response caused by support movement

#### 4. `final_structure_temperature.json`

This file is used to verify the temperature load function for the final structure model.

- A uniform temperature change is assigned to the elements
- The applied temperature load is `TEMP = 50.0`
- This case is intended to verify the thermal load assembly and structural response

### 5. `final_structure_comprehensive_loads.json`

This file is used to define a combined load case for the final bridge model.

The structural geometry, element connectivity, material, section, and support definitions are the same as those used in the other final-structure files. The model is still a mixed truss-frame system, where most members are modeled as truss elements and the arch rib members are modeled as frame elements.

This file includes multiple load effects in one model:

- Downward nodal loads are applied at selected deck nodes
- The nodal load magnitudes are not uniform
- A uniformly distributed member load of `q_global = [0.0, 0.0, -120.0]` kN/m is applied to selected elements
- Nonuniform support displacements are assigned at selected support nodes
- The imposed support movement includes different values of $u_x$, $u_y$, and $u_z$
- A uniform temperature load `TEMP = 50.0` is applied in this case

This file is intended to represent a more realistic comprehensive loading condition of the final bridge model, in which distributed live load effects and support movement are considered simultaneously.

#### Summary

These five files were prepared so that the final bridge structure can be checked under different loading types separately before more complicated combined load cases are considered. In this way, each loading function can be verified clearly on the same final structural model.

---

# V. Output

When the program is executed in `main.ipynb`, the output is provided in both **graphical** and **tabular** forms.

### 1. Graphical output in `main.ipynb`

The notebook can directly display the structural model in three dimensions, including:

- the original 3D structural geometry
- the deformed shape of the structure
- the overall deformation pattern under the applied load case

This makes it possible to visually examine the structural configuration and the displacement response in the notebook environment.

### 2. Tabular output in Excel

When `table_output="xlsx"` is used, the numerical results are exported to an Excel file.

For the current comprehensive bridge example, the Excel file contains the following worksheets:

- `Node Displacements`
- `Maximum Displacement Summary`
- `Reaction Forces`
- `Frame Member Summary`
- `Frame Member Full Results`

### 3. Content of each output table

#### `Node Displacements`

This sheet stores the nodal displacement results of the structure, including:

- node ID
- nodal coordinates
- translational displacements: $u_x$, $u_y$, $u_z$
- rotational displacements: $r_x$, $r_y$, $r_z$
- displacement magnitude $|u|$

#### `Maximum Displacement Summary`

This sheet provides a compact summary of the most important displacement results, including:

- maximum total displacement
- maximum absolute $u_x$
- maximum absolute $u_y$
- maximum absolute $u_z$
- the corresponding node IDs

#### `Reaction Forces`

This sheet stores the support reaction results, including the reaction forces at restrained nodes.

#### `Frame Member Summary`

This sheet provides a concise member-level summary, including:

- element ID and element type
- end nodes
- member length
- local axial deformation
- axial strain
- axial force
- axial stress
- member end forces and end moments

#### `Frame Member Full Results`

This sheet provides the detailed member output, including:

- global nodal displacement components of each member
- local nodal displacement components of each member
- detailed local end force vector results


---

# Conclusion

This project provides basic three-dimensional structural modeling and analysis capability based on the Direct Stiffness Method.

The validation files show that the current implementation can handle the following functions:

- **Truss**
  1. nodal load input
  2. support displacement
  3. temperature loading
  4. fabrication error loading

- **Frame**
  1. nodal action input
  2. member loading
  3. moment release
  4. support displacement
  5. temperature loading
  6. fabrication error loading

In addition, the final complex bridge example shows that the current framework can also be extended to mixed truss-frame structural analysis for more complicated structures and load combinations.

For reproduction, users only need to open and run the main Jupyter Notebook of the project.


---