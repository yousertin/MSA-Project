import json
import numpy as np


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
        1: ["F", 1, 1, [1, 2], 0],
        2: ["T", 2, 1, [2, 3], 1],
        ...
    }

    The list order is:
    [TYPE_initial, MATL, SECT, NODE, MT]

    Rules
    -----
    - TYPE is converted to its first capital letter:
      "TRUSS" -> "T"
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


def read_constraints(json_file, cons_key="CONS"):
    """
    Read nodal boundary conditions from a JSON file.

    Output format:
    {
        1: ["Ux", "Uy", "Uz"],
        2: ["Ux", "Rx"],
        ...
    }

    Rule
    ----
    - If a restraint value is 0 (or False), do not include that key.
    - If a restraint value is 1 (or True), include that key string in the list.

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    cons_key : str
        Top-level key storing the constraint data.

    Returns
    -------
    dict
        Dictionary whose keys are node IDs (int),
        and whose values are lists of restrained DOF names.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if cons_key not in data:
        raise KeyError(f"Key '{cons_key}' not found in the JSON file.")

    raw_constraints = data[cons_key]
    constraints = {}

    for node_id_str, cons_data in raw_constraints.items():
        node_id = int(node_id_str)
        restrained_dofs = []

        for dof_name, dof_value in cons_data.items():
            if dof_value == 1 or dof_value is True:
                restrained_dofs.append(dof_name)

        constraints[node_id] = restrained_dofs

    return constraints


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


def read_nodal_loads(json_file, node_key="NODE", load_key="NDLD"):
    """
    Read nodal loads from a JSON file and assemble the global load vector F_global.

    Rules
    -----
    1. F_global is a 1D array with length = 6 * number_of_nodes.
    2. Each node has 6 DOFs in the following order:
       [Fx, Fy, Fz, Mx, My, Mz]
    3. If a node is not listed in NDLD, its load entries remain zero.
    4. If a node appears in NDLD but is not defined in NODE, raise an error.

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    node_key : str
        Top-level key for node data.
    load_key : str
        Top-level key for nodal load data.

    Returns
    -------
    np.ndarray
        1D global load vector with shape (6 * n_nodes, ).
    """

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if node_key not in data:
        raise KeyError(f"Key '{node_key}' not found in the JSON file.")
    if load_key not in data:
        raise KeyError(f"Key '{load_key}' not found in the JSON file.")

    nodes_data = data[node_key]
    raw_nodal_loads = data[load_key]

    n_nodes = len(nodes_data)

    # Initialize the global nodal load vector
    F_global = np.zeros(6 * n_nodes, dtype=float)

    # Local load order for each node
    load_map = {
        "Fx": 0,
        "Fy": 1,
        "Fz": 2,
        "Mx": 3,
        "My": 4,
        "Mz": 5,
    }

    for node_id_str, load_data in raw_nodal_loads.items():
        node_id = int(node_id_str)

        # Check whether the node exists in NODE
        if node_id_str not in nodes_data:
            raise ValueError(
                f"Node {node_id} in '{load_key}' is not defined in '{node_key}'."
            )

        for load_name, local_idx in load_map.items():
            val = float(load_data.get(load_name, 0.0))
            global_idx = 6 * (node_id - 1) + local_idx
            F_global[global_idx] += val

    return F_global


def read_element_loads(json_file, load_key="MBLD"):
    """
    Read element loads from a JSON file.

    Output format:
    {
        1: {
            "q_global": [qx, qy, qz],
            "P_global": [Px, Py, Pz],
            "P_loc": 0.0,
            "M_global": [Mx, My, Mz],
            "M_loc": 0.0
        },
        2: {
            "q_global": [qx, qy, qz],
            "P_global": [Px, Py, Pz],
            "P_loc": 0.0,
            "M_global": [Mx, My, Mz],
            "M_loc": 0.0
        },
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
        and whose values are dictionaries:
        {
            "q_global": [qx, qy, qz],
            "P_global": [Px, Py, Pz],
            "P_loc": 0.0,
            "M_global": [Mx, My, Mz],
            "M_loc": 0.0
        }

        If load_key does not exist in the JSON file,
        return an empty dictionary.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if load_key not in data:
        return {}

    raw_elem_loads = data[load_key]
    element_loads = {}

    for elem_id_str, load_data in raw_elem_loads.items():
        elem_id = int(elem_id_str)

        q_global = load_data.get("q_global", [0.0, 0.0, 0.0])
        P_global = load_data.get("P_global", [0.0, 0.0, 0.0])
        P_loc = load_data.get("P_loc", 0.0)
        M_global = load_data.get("M_global", [0.0, 0.0, 0.0])
        M_loc = load_data.get("M_loc", 0.0)

        if len(q_global) != 3:
            raise ValueError(f"Element {elem_id}: q_global must have 3 components.")
        if len(P_global) != 3:
            raise ValueError(f"Element {elem_id}: P_global must have 3 components.")
        if len(M_global) != 3:
            raise ValueError(f"Element {elem_id}: M_global must have 3 components.")

        if not (0.0 <= P_loc <= 1.0):
            raise ValueError(f"Element {elem_id}: P_loc must be in [0, 1].")
        if not (0.0 <= M_loc <= 1.0):
            raise ValueError(f"Element {elem_id}: M_loc must be in [0, 1].")

        element_loads[elem_id] = {
            "q_global": [float(x) for x in q_global],
            "P_global": [float(x) for x in P_global],
            "P_loc": float(P_loc),
            "M_global": [float(x) for x in M_global],
            "M_loc": float(M_loc),
        }

    return element_loads


def read_support_disp(json_file, node_key="NODE", cons_key="CONS", spmv_key="SPMV"):
    """
    Read support prescribed movements (SPMV) from a JSON file and assemble
    the global displacement vector u_global.

    Rules
    -----
    1. u_global is a 1D array with length = 6 * number_of_nodes.
    2. Each node has 6 DOFs in the following order:
       [ux, uy, uz, rx, ry, rz]
    3. A node appearing in SPMV must also appear in CONS to be effective.
       Otherwise, its prescribed movements are ignored and remain zero.
    4. A prescribed movement is only added if the corresponding DOF is
       constrained in CONS (flag = 1). Otherwise, it remains zero.
    5. Node IDs must be consecutive integers: 1, 2, ..., n_nodes.

    Parameters
    ----------
    json_file : str
        Path to the JSON file.
    node_key : str
        Top-level key for node data.
    cons_key : str
        Top-level key for constraint data.
    spmv_key : str
        Top-level key for support prescribed movement data.

    Returns
    -------
    u_global : np.ndarray
        1D global displacement vector with shape (6 * n_nodes, ).
    """

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if node_key not in data:
        raise KeyError(f"Key '{node_key}' not found in the JSON file.")
    if cons_key not in data:
        raise KeyError(f"Key '{cons_key}' not found in the JSON file.")

    nodes_data = data[node_key]
    cons_data = data[cons_key]
    spmv_data = data.get(spmv_key, {})

    node_ids = sorted(int(k) for k in nodes_data.keys())
    n_nodes = len(node_ids)

    # Check whether node IDs are consecutive: 1, 2, ..., n_nodes
    expected_node_ids = list(range(1, n_nodes + 1))
    if node_ids != expected_node_ids:
        raise ValueError(
            f"Node IDs must be consecutive integers from 1 to {n_nodes}. "
            f"Got {node_ids}."
        )

    # Initialize the global prescribed displacement vector
    u_global = np.zeros(6 * n_nodes, dtype=float)

    # Local DOF order for each node
    dof_map = {
        "ux": ("Ux", 0),
        "uy": ("Uy", 1),
        "uz": ("Uz", 2),
        "rx": ("Rx", 3),
        "ry": ("Ry", 4),
        "rz": ("Rz", 5),
    }

    for node_id_str, spmv_node in spmv_data.items():
        node_id = int(node_id_str)

        # Ignore nodes that are not listed in CONS
        if node_id_str not in cons_data:
            continue

        cons_node = cons_data[node_id_str]

        for spmv_dof, (cons_dof, local_idx) in dof_map.items():
            val = float(spmv_node.get(spmv_dof, 0.0))

            # Only add the prescribed movement if the DOF is constrained
            if cons_node.get(cons_dof, 0) == 1:
                global_idx = 6 * (node_id - 1) + local_idx
                u_global[global_idx] += val

    return u_global


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
