# Abstract

This project is all about a DSM calculator.

---
---

# Modifying the JSON Input File

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

## 1. General Rules

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

## 2. UNIT

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

## 3. NODE

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

## 4. ELEM

The `ELEM` block defines element connectivity and element properties.

```json
"ELEM": {
    "1": {
        "TYPE": "TRUSS",
        "MATL": 1,
        "SECT": 1,
        "NODE": [1, 2],
        "MTY": 0,
        "MTZ": 0
  }
}
```

### Fields

- `TYPE`: element type
  - `"TRUSS"`
  - `"BEAM"`
  - `"FRAME"`
- `MATL`: material ID
- `SECT`: section ID
- `NODE`: two end nodes of the element
- `MTY`, `MTZ`: release-type indicators used by the program

### Meaning of `MTY`, `MTZ`

Here, `Y` / `Z` indicates the `MT` value in the plane associated with the local y-axis or z-axis, respectively.

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

### Example

```json
"2": {
    "TYPE": "FRAME",
    "MATL": 2,
    "SECT": 2,
    "NODE": [3, 4],
    "MTY": 1,
    "MTZ": 0
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

### Meaning

- `Ux`, `Uy`, `Uz`: translational constraints
- `Rx`, `Ry`, `Rz`: rotational constraints

A value of `0` means the corresponding DOF is fixed at zero.

### Example

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

## 6. MATL

The `MATL` block defines material properties.

```json
"MATL": {
    "1": {
        "NAME": "CONCRETE",
        "E": 3.0e7,
        "TEMPCOEF": 1.0
    },
    "2": {
        "NAME": "STEEL",
        "E": 2.0e8,
        "TEMPCOEF": 1.0
    }
}
```

### Fields

- `NAME`: material name
- `E`: elastic modulus
- `TEMPCOEF`: thermal coefficient used in temperature loading

### Example

```json
"1": {
    "NAME": "STEEL",
    "E": 2.0e8,
    "TEMPCOEF": 1.2e-5
}
```

Note: under the `kN-m` unit system, elastic modulus should be given in `kN/m^2`.

---

## 7. SECT

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

### Fields

- `A`: cross-sectional area
- `Iy`: second moment of area about local y-axis
- `Iz`: second moment of area about local z-axis
- `J`: torsional constant

### Example

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

## 8. NDLD

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

### Fields

- `Fx`, `Fy`, `Fz`: nodal forces
- `Mx`, `My`, `Mz`: nodal moments

### Example

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

## 9. MBLD

The `MBLD` block defines member loads.

```json
"MBLD": {
    "1": {
        "q": 0.0,
        "qANGLE": 0.0,
        "P": 0.0,
        "PLOCATION": 0.0,
        "PANGLE": 0.0
  }
}
```

Here the key corresponds to the element ID.

### Fields

- `q`: distributed load magnitude
- `qANGLE`: distributed load direction angle
- `P`: concentrated load magnitude
- `PLOCATION`: location of the concentrated load along the member
- `PANGLE`: concentrated load direction angle

### Example

Uniform distributed load on element 1:

```json
"1": {
    "q": -20.0,
    "qANGLE": 90.0,
    "P": 0.0,
    "PLOCATION": 0.0,
    "PANGLE": 0.0
}
```

Point load on element 2 at midspan:

```json
"2": {
    "q": 0.0,
    "qANGLE": 0.0,
    "P": -50.0,
    "PLOCATION": 0.5,
    "PANGLE": 90.0
}
```

---

## 10. TPLD

The `TPLD` block defines uniform temperature loading for elements.

```json
"TPLD": {
    "1": {
        "TEMP": 20.0
    }
}
```

Here the key corresponds to the element ID.

### Field

- `TEMP`: uniform temperature change applied to the element

### Example

Apply a uniform temperature increase of `20 C` to element 1:

```json
"1": {
    "TEMP": 20.0
}
```

---

## 11. FABR

The `FABR` block defines fabrication error for elements.

```json
"FABR": {
    "1": {
        "ERROR": 0.002
    }
}
```

Here the key corresponds to the element ID.

### Field

- `ERROR`: fabrication error assigned to the element

### Example

Apply a fabrication error of `0.002 m` to element 1:

```json
"1": {
    "ERROR": 0.002
}
```

---

## 12. Example Workflow

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

## 13. Important Notes

- Keep all IDs consistent across different blocks
- Check that each element references valid node, material, and section IDs
- Check that all values follow the selected unit system
- Validate the JSON file before running the program
- If the program reports missing data, first check whether all required IDs and fields are defined correctly