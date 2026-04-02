import numpy as np
import json


def read_nodes(json_file, node_key="NODE"):
    """
    Read node coordinates from a JSON file.

    Output format:
    {
        1: (x, y, z),
        2: (x, y, z),
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
        and whose values are 3D coordinate tuples:
        (x, y, z)
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

        nodes[node_id] = (x, y, z)

    return nodes


def read_elements(json_file, elem_key="ELEM"):
    """
    Read element data from a JSON file.

    Output format:
    {
        1: ["B", 1, 1, [1, 2], 0, 0],
        2: ["T", 2, 1, [2, 3], 1, 0],
        ...
    }

    The list order is:
    [TYPE_initial, MATL, SECT, NODE, MTY, MTZ]

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
        [TYPE_initial, MATL, SECT, NODE, MTY, MTZ]
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
        mty = elem_data.get("MTY", 0)
        mtz = elem_data.get("MTZ", 0)

        elements[elem_id] = [elem_type_initial, matl, sect, node, mty, mtz]

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
        1: [E, TEMPCOEF],
        2: [E, TEMPCOEF],
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
        and whose values are lists of 2 numbers:
        [E, TEMPCOEF]
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

        materials[matl_id] = [E, tempcoef]

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


def read_element_loads(json_file, load_key="ELEMLOAD"):
    """
    Read element loads from a JSON file.

    Output format:
    {
        1: [q, qANGLE, P, PLOCATION, PANGLE],
        2: [q, qANGLE, P, PLOCATION, PANGLE],
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
        and whose values are lists of 5 numbers:
        [q, qANGLE, P, PLOCATION, PANGLE]
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if load_key not in data:
        raise KeyError(f"Key '{load_key}' not found in the JSON file.")

    raw_elem_loads = data[load_key]
    element_loads = {}

    for elem_id_str, load_data in raw_elem_loads.items():
        elem_id = int(elem_id_str)

        q = load_data.get("q", 0.0)
        q_angle = load_data.get("qANGLE", 0.0)
        p = load_data.get("P", 0.0)
        p_location = load_data.get("PLOCATION", 0.0)
        p_angle = load_data.get("PANGLE", 0.0)

        element_loads[elem_id] = [q, q_angle, p, p_location, p_angle]

    return element_loads
