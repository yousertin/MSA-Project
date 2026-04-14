import json


def read_nodes(json_file, node_key="NODE"):
    """
    Read node coordinates from a JSON file.

    Output format:
    {
        1: [x, y, z],
        2: [x, y, z],
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    node_key : str
        Top-level key storing the node data.

    Returns
    -------
    dict
        Dictionary whose keys are node IDs (int),
        and whose values are 3D coordinate lists:
        [x, y, z]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if node_key not in data:
        raise KeyError(f"Key '{node_key}' not found in the JSON file.")

    raw_nodes = data[node_key]
    nodes = {}

    for node_id_str, node_data in raw_nodes.items():
        node_id = int(node_id_str)

        x = node_data.get("X", 0.0)
        y = node_data.get("Y", 0.0)
        z = node_data.get("Z", 0.0)

        nodes[node_id] = [x, y, z]

    return nodes


def read_elements(json_file, elem_key="ELEM"):
    """
    Read element data from a JSON file.

    Output format:
    {
        1: ["B", 1, 1, [1, 2], 0],
        2: ["T", 2, 1, [2, 3], 1],
        ...
    }

    The list order is:
    [TYPE_initial, MATL, SECT, NODE, MT]

    Rules
    -----
    - TYPE is converted to its first capital letter:
      "TRUSS" -> "T"
      "BEAM"  -> "B"
      "FRAME" -> "F"

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    elem_key : str
        Top-level key storing the element data.

    Returns
    -------
    dict
        Dictionary whose keys are element IDs (int),
        and whose values are lists:
        [TYPE_initial, MATL, SECT, NODE, MT]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if elem_key not in data:
        raise KeyError(f"Key '{elem_key}' not found in the JSON file.")

    raw_elements = data[elem_key]
    elements = {}

    for elem_id_str, elem_data in raw_elements.items():
        elem_id = int(elem_id_str)

        elem_type = elem_data.get("TYPE", "")
        elem_type_initial = elem_type[0].upper() if elem_type else ""

        matl = elem_data.get("MATL", 0)
        sect = elem_data.get("SECT", 0)
        node = elem_data.get("NODE", [])
        mt = elem_data.get("MT", 0)

        elements[elem_id] = [elem_type_initial, matl, sect, node, mt]

    return elements


def read_constraints(json_file, cons_key="CONS", zero_tol=1e-12):
    """
    Read nodal boundary conditions from a JSON file.

    JSON format for each node
    -------------------------
    {
        "Ux": 1, "Uy": 1, "Uz": 1, "Rx": 0, "Ry": 0, "Rz": 0,
        "ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0
    }

    Return
    ------
    constraints : dict
        Example:
        {
            1: ["Ux", "Uy", "Uz"],
            2: ["Uy", "Uz"]
        }

    ur_local : dict
        Support displacement values corresponding to constrained DOFs only.
        Example:
        {
            1: [0.0, 0.0, 0.0],
            2: [0.0, 0.0]
        }

    Rule
    ----
    - If a restraint flag is 0 (or False), the corresponding support
      displacement must be 0.0, otherwise raise ValueError.
    - If a restraint flag is 1 (or True), the corresponding support
      displacement is allowed to be any float.
    """

    dof_pairs = [
        ("Ux", "ux"),
        ("Uy", "uy"),
        ("Uz", "uz"),
        ("Rx", "rx"),
        ("Ry", "ry"),
        ("Rz", "rz"),
    ]

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if cons_key not in data:
        raise KeyError(f"Key '{cons_key}' not found in the JSON file.")

    raw_constraints = data[cons_key]
    constraints = {}
    ur_local = {}

    for node_id_str, cons_data in raw_constraints.items():
        node_id = int(node_id_str)
        restrained_dofs = []
        restrained_vals = []

        for dof_flag_key, dof_val_key in dof_pairs:
            if dof_flag_key not in cons_data:
                raise KeyError(
                    f"Node {node_id}: missing key '{dof_flag_key}' in constraint data."
                )
            if dof_val_key not in cons_data:
                raise KeyError(
                    f"Node {node_id}: missing key '{dof_val_key}' in constraint data."
                )

            flag = cons_data[dof_flag_key]
            val = cons_data[dof_val_key]

            if flag not in (0, 1, False, True):
                raise ValueError(
                    f"Node {node_id}, DOF '{dof_flag_key}': "
                    f"restraint flag must be 0/1 or False/True, got {flag}."
                )

            try:
                val = float(val)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Node {node_id}, DOF '{dof_val_key}': "
                    f"support displacement must be a float, got {val}."
                )

            is_restrained = bool(flag)

            if not is_restrained:
                if abs(val) > zero_tol:
                    raise ValueError(
                        f"Node {node_id}, DOF '{dof_flag_key}': "
                        f"restraint flag = 0, so '{dof_val_key}' must be 0.0, got {val}."
                    )
            else:
                restrained_dofs.append(dof_flag_key)
                restrained_vals.append(val)

        constraints[node_id] = restrained_dofs
        ur_local[node_id] = restrained_vals

    return constraints, ur_local


def read_materials(json_file, matl_key="MATL"):
    """
    Read material properties from a JSON file.

    Output format:
    {
        1: [E, TEMPCOEF, nu],
        2: [E, TEMPCOEF, nu],
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    matl_key : str
        Top-level key storing the material data.

    Returns
    -------
    dict
        Dictionary whose keys are material IDs (int),
        and whose values are lists of 3 numbers:
        [E, TEMPCOEF, nu]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if matl_key not in data:
        raise KeyError(f"Key '{matl_key}' not found in the JSON file.")

    raw_materials = data[matl_key]
    materials = {}

    for matl_id_str, matl_data in raw_materials.items():
        matl_id = int(matl_id_str)

        E = matl_data.get("E", 0.0)
        tempcoef = matl_data.get("TEMPCOEF", 0.0)
        nu = matl_data.get("nu", 0.0)

        materials[matl_id] = [E, tempcoef, nu]

    return materials


def read_sections(json_file, sect_key="SECT"):
    """
    Read section properties from a JSON file.

    Output format:
    {
        1: [A, Iy, Iz, J],
        2: [A, Iy, Iz, J],
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    sect_key : str
        Top-level key storing the section data.

    Returns
    -------
    dict
        Dictionary whose keys are section IDs (int),
        and whose values are lists of 4 numbers:
        [A, Iy, Iz, J]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if sect_key not in data:
        raise KeyError(f"Key '{sect_key}' not found in the JSON file.")

    raw_sections = data[sect_key]
    sections = {}

    for sect_id_str, sect_data in raw_sections.items():
        sect_id = int(sect_id_str)

        A = sect_data.get("A", 0.0)
        Iy = sect_data.get("Iy", 0.0)
        Iz = sect_data.get("Iz", 0.0)
        J = sect_data.get("J", 0.0)

        sections[sect_id] = [A, Iy, Iz, J]

    return sections


def read_nodal_loads(json_file, load_key="NDLD"):
    """
    Read nodal loads from a JSON file.

    Output format:
    {
        1: [Fx, Fy, Fz, Mx, My, Mz],
        2: [Fx, Fy, Fz, Mx, My, Mz],
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    load_key : str
        Top-level key storing the nodal load data.

    Returns
    -------
    dict
        Dictionary whose keys are node IDs (int),
        and whose values are lists of 6 numbers:
        [Fx, Fy, Fz, Mx, My, Mz]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if load_key not in data:
        raise KeyError(f"Key '{load_key}' not found in the JSON file.")

    raw_nodal_loads = data[load_key]
    nodal_loads = {}

    for node_id_str, load_data in raw_nodal_loads.items():
        node_id = int(node_id_str)

        fx = load_data.get("Fx", 0.0)
        fy = load_data.get("Fy", 0.0)
        fz = load_data.get("Fz", 0.0)
        mx = load_data.get("Mx", 0.0)
        my = load_data.get("My", 0.0)
        mz = load_data.get("Mz", 0.0)

        nodal_loads[node_id] = [fx, fy, fz, mx, my, mz]

    return nodal_loads


def read_element_loads(json_file, load_key="MBLD"):
    """
    Read element loads from a JSON file.

    Output format:
    {
        1: [Tx, T_location,
            qy, qyANGLE, qz, qzANGLE,
            Py, PyLOCATION, PyANGLE,
            Pz, PzLOCATION, PzANGLE],
        2: [Tx, T_location,
            qy, qyANGLE, qz, qzANGLE,
            Py, PyLOCATION, PyANGLE,
            Pz, PzLOCATION, PzANGLE],
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    load_key : str
        Top-level key storing the element load data.

    Returns
    -------
    dict
        Dictionary whose keys are element IDs (int),
        and whose values are lists of 12 numbers:
        [Tx, T_location,
        qy, qyANGLE, qz, qzANGLE,
        Py, PyLOCATION, PyANGLE,
        Pz, PzLOCATION, PzANGLE]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if load_key not in data:
        raise KeyError(f"Key '{load_key}' not found in the JSON file.")

    raw_elem_loads = data[load_key]
    element_loads = {}

    for elem_id_str, load_data in raw_elem_loads.items():
        elem_id = int(elem_id_str)

        Tx = load_data.get("Tx", 0.0)
        T_location = load_data.get("TLOCATION", 0.0)
        qy = load_data.get("qy", 0.0)
        qy_angle = load_data.get("qyANGLE", 0.0)
        qz = load_data.get("qz", 0.0)
        qz_angle = load_data.get("qzANGLE", 0.0)
        py = load_data.get("P", 0.0)
        py_location = load_data.get("PLOCATION", 0.0)
        py_angle = load_data.get("PANGLE", 0.0)
        pz = load_data.get("P", 0.0)
        pz_location = load_data.get("PLOCATION", 0.0)
        pz_angle = load_data.get("PANGLE", 0.0)

        element_loads[elem_id] = [
            Tx,
            T_location,
            qy,
            qy_angle,
            qz,
            qz_angle,
            py,
            py_location,
            py_angle,
            pz,
            pz_location,
            pz_angle,
        ]

    return element_loads


def read_temperature_loads(json_file, tpld_key="TPLD"):
    """
    Read element temperature loads from a JSON file.

    Output format:
    {
        1: 0.0,
        2: 0.0,
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    tpld_key : str
        Top-level key storing the temperature load data.

    Returns
    -------
    dict
        Dictionary whose keys are element IDs (int),
        and whose values are temperature load values.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if tpld_key not in data:
        raise KeyError(f"Key '{tpld_key}' not found in the JSON file.")

    raw_temperature_loads = data[tpld_key]
    temperature_loads = {}

    for elem_id_str, load_data in raw_temperature_loads.items():
        elem_id = int(elem_id_str)
        temp = load_data.get("TEMP", 0.0)
        temperature_loads[elem_id] = temp

    return temperature_loads


def read_fabrication_errors(json_file, fabr_key="FABR"):
    """
    Read element fabrication error equivalent loads from a JSON file.

    Output format:
    {
        1: 0.0,
        2: 0.0,
        ...
    }

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    fabr_key : str
        Top-level key storing the fabrication error data.

    Returns
    -------
    dict
        Dictionary whose keys are element IDs (int),
        and whose values are fabrication error values.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if fabr_key not in data:
        raise KeyError(f"Key '{fabr_key}' not found in the JSON file.")

    raw_fabrication_errors = data[fabr_key]
    fabrication_errors = {}

    for elem_id_str, error_data in raw_fabrication_errors.items():
        elem_id = int(elem_id_str)
        error = error_data.get("ERROR", 0.0)
        fabrication_errors[elem_id] = error

    return fabrication_errors
