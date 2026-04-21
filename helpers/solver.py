from . import assembly
from . import element
from . import interfaces
from . import partition
from . import preprocess
import numpy as np


def truss_solver(filepath):
    """
    Solve the truss model using the 3D-frame-format pipeline and return a rich result dict.

    Why return a dict instead of only three arrays?
    -----------------------------------------------
    Because postprocess usually needs more than only K_global and u_global:
    - reactions
    - full nodal force vector
    - element transformation matrices
    - local stiffness matrices
    - equivalent nodal load vectors (Qf/Qh/Qe/Qt)
    - dof maps and support dofs

    Returning them once from solver avoids recomputing or guessing later.
    """

    nodes = interfaces.read_nodes(filepath)
    elements = interfaces.read_elements(filepath)
    constraints = interfaces.read_constraints(filepath)
    materials = interfaces.read_materials(filepath)
    sections = interfaces.read_sections(filepath)
    F_global = interfaces.read_nodal_loads(filepath)
    element_loads = interfaces.read_element_loads(filepath)
    u_support = interfaces.read_support_disp(filepath)
    temperature_loads = interfaces.read_temperature_loads(filepath)
    fabrication_loads = interfaces.read_fabrication_errors(filepath)

    k_list = []
    T_list = []
    Qf_list = []
    Qh_list = []
    Qe_list = []
    map_list = []

    element_paras = element.build_elements_para(nodes, elements, materials, sections)

    for e_id in elements:
        i_node = elements[e_id][3][0]
        j_node = elements[e_id][3][1]

        L, etype, E, G, A, Iy, Iz, J, mt, alpha = element_paras[e_id]
        kl = element.element_kl(E, G, A, Iy, Iz, J, L)

        gamma = element.build_gamma_3d(
            nodes[i_node],
            nodes[j_node],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)

        elem_load_global = element_loads.get(e_id)
        Qf = preprocess.fef_cal_global(elem_load_global, T, L)
        Qh = preprocess.heat_cal(temperature_loads.get(e_id), E, A, alpha)
        Qe = preprocess.fabrication_error_cal(fabrication_loads.get(e_id), E, A, L)
        m = element.element_dof_map_1based(i_node, j_node)

        k_list.append(np.asarray(kl, dtype=float))
        T_list.append(np.asarray(T, dtype=float))
        Qf_list.append(np.asarray(Qf, dtype=float))
        Qh_list.append(np.asarray(Qh, dtype=float))
        Qe_list.append(np.asarray(Qe, dtype=float))
        map_list.append(np.asarray(m, dtype=int))

    Qt_list = [x + y + z for x, y, z in zip(Qf_list, Qh_list, Qe_list)]

    ndof = int(np.max(np.concatenate(map_list)))

    dof_restrained_1based = np.asarray(
        element.restrained_dofs_1based(constraints, element.node_dofs_1based),
        dtype=int,
    )

    K_global, F_fef_global = assembly.assemble_global_stiffness_and_fef(
        ndof, k_list, T_list, Qt_list, map_list
    )

    candidate_rot_dofs = preprocess.all_nodes_rotational_dofs_1based(nodes)

    dof_fictitious_1based = preprocess.zero_stiffness_dofs_1based(
        K_global,
        candidate_rot_dofs,
    )

    dof_restrained_1based = np.sort(
        np.unique(np.concatenate((dof_restrained_1based, dof_fictitious_1based)))
    )

    (
        K_ff,
        K_fr,
        K_rf,
        K_rr,
        f_f,
        f_r,
        u_r,
        f_fef_f,
        f_fef_r,
        free_dofs,
        restrained_dofs,
    ) = partition.partition_system(
        K_global, F_global, u_support, F_fef_global, dof_restrained_1based
    )

    rhs = f_f - f_fef_f - K_fr @ u_r
    u_f = np.linalg.solve(K_ff, rhs)

    F_r = K_rf @ u_f + K_rr @ u_r + f_fef_r

    u_global = assembly.assemble_global_displacements(
        u_f, u_r, free_dofs, restrained_dofs
    )

    f_global_complete = assembly.assemble_global_forces(
        f_f, F_r, free_dofs, restrained_dofs
    )

    return {
        "filepath": filepath,
        "nodes": nodes,
        "elements": elements,
        "constraints": constraints,
        "materials": materials,
        "sections": sections,
        "F_global": F_global,
        "u_support": u_support,
        "element_loads": element_loads,
        "temperature_loads": temperature_loads,
        "fabrication_loads": fabrication_loads,
        "element_paras": element_paras,
        "k_list": k_list,
        "T_list": T_list,
        "Qf_list": Qf_list,
        "Qh_list": Qh_list,
        "Qe_list": Qe_list,
        "Qt_list": Qt_list,
        "map_list": map_list,
        "ndof": ndof,
        "dof_restrained_1based": dof_restrained_1based,
        "K_global": K_global,
        "F_fef_global": F_fef_global,
        "K_ff": K_ff,
        "K_fr": K_fr,
        "K_rf": K_rf,
        "K_rr": K_rr,
        "f_f": f_f,
        "f_r": f_r,
        "u_r": u_r,
        "f_fef_f": f_fef_f,
        "f_fef_r": f_fef_r,
        "free_dofs": free_dofs,
        "restrained_dofs": restrained_dofs,
        "rhs": rhs,
        "u_f": u_f,
        "F_r": F_r,
        "u_global": u_global,
        "f_global_complete": f_global_complete,
    }


def frame_solver(filepath):
    """
    Solve the 3D frame model and return a rich result dict.

    Why return a dict instead of only three arrays?
    -----------------------------------------------
    Because postprocess usually needs more than only K_global and u_global:
    - reactions
    - full nodal force vector
    - element transformation matrices
    - local stiffness matrices
    - equivalent nodal load vectors (Qf/Qh/Qe/Qt)
    - dof maps and support dofs

    Returning them once from solver avoids recomputing or guessing later.
    """

    nodes = interfaces.read_nodes(filepath)
    elements = interfaces.read_elements(filepath)
    constraints = interfaces.read_constraints(filepath)
    materials = interfaces.read_materials(filepath)
    sections = interfaces.read_sections(filepath)
    F_global = interfaces.read_nodal_loads(filepath)
    element_loads = interfaces.read_element_loads(filepath)
    u_support = interfaces.read_support_disp(filepath)
    temperature_loads = interfaces.read_temperature_loads(filepath)
    fabrication_loads = interfaces.read_fabrication_errors(filepath)

    k_list = []
    T_list = []
    Qf_list = []
    Qh_list = []
    Qe_list = []
    map_list = []

    element_paras = element.build_elements_para(nodes, elements, materials, sections)

    for e_id in elements:
        i_node = elements[e_id][3][0]
        j_node = elements[e_id][3][1]

        L, etype, E, G, A, Iy, Iz, J, MT, alpha = element_paras[e_id]
        kl = element.element_kl(E, G, A, Iy, Iz, J, L)

        gamma = element.build_gamma_3d(
            nodes[i_node],
            nodes[j_node],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)

        elem_load_global = element_loads.get(e_id)
        Qf = preprocess.fef_cal_global(elem_load_global, T, L)
        Qh = preprocess.heat_cal(temperature_loads.get(e_id), E, A, alpha)
        Qe = preprocess.fabrication_error_cal(fabrication_loads.get(e_id), E, A, L)
        m = element.element_dof_map_1based(i_node, j_node)

        kl, Qf, Qh, Qe = preprocess.moment_release(MT, kl, Qf, Qh, Qe)

        k_list.append(np.asarray(kl, dtype=float))
        T_list.append(np.asarray(T, dtype=float))
        Qf_list.append(np.asarray(Qf, dtype=float))
        Qh_list.append(np.asarray(Qh, dtype=float))
        Qe_list.append(np.asarray(Qe, dtype=float))
        map_list.append(np.asarray(m, dtype=int))

    Qt_list = [x + y + z for x, y, z in zip(Qf_list, Qh_list, Qe_list)]

    ndof = int(np.max(np.concatenate(map_list)))

    dof_restrained_1based = element.restrained_dofs_1based(
        constraints, element.node_dofs_1based
    )

    fully_released_nodes = preprocess.find_fully_released_nodes(elements, element_paras)
    dof_fictitious_1based = preprocess.fictitious_rotational_dofs_1based(
        fully_released_nodes
    )

    dof_restrained_1based = np.sort(
        np.unique(np.concatenate((dof_restrained_1based, dof_fictitious_1based)))
    )

    K_global, F_fef_global = assembly.assemble_global_stiffness_and_fef(
        ndof, k_list, T_list, Qt_list, map_list
    )

    (
        K_ff,
        K_fr,
        K_rf,
        K_rr,
        f_f,
        f_r,
        u_r,
        f_fef_f,
        f_fef_r,
        free_dofs,
        restrained_dofs,
    ) = partition.partition_system(
        K_global, F_global, u_support, F_fef_global, dof_restrained_1based
    )

    rhs = f_f - f_fef_f - K_fr @ u_r
    u_f = np.linalg.solve(K_ff, rhs)

    F_r = K_rf @ u_f + K_rr @ u_r + f_fef_r

    fictitious_mask = np.isin(restrained_dofs, dof_fictitious_1based)
    F_r[fictitious_mask] = 0.0

    u_global = assembly.assemble_global_displacements(
        u_f, u_r, free_dofs, restrained_dofs
    )

    f_global_complete = assembly.assemble_global_forces(
        f_f, F_r, free_dofs, restrained_dofs
    )

    return {
        "filepath": filepath,
        "nodes": nodes,
        "elements": elements,
        "constraints": constraints,
        "materials": materials,
        "sections": sections,
        "F_global": F_global,
        "u_support": u_support,
        "element_loads": element_loads,
        "temperature_loads": temperature_loads,
        "fabrication_loads": fabrication_loads,
        "element_paras": element_paras,
        "k_list": k_list,
        "T_list": T_list,
        "Qf_list": Qf_list,
        "Qh_list": Qh_list,
        "Qe_list": Qe_list,
        "Qt_list": Qt_list,
        "map_list": map_list,
        "ndof": ndof,
        "fully_released_nodes": fully_released_nodes,
        "dof_fictitious_1based": dof_fictitious_1based,
        "dof_restrained_1based": dof_restrained_1based,
        "K_global": K_global,
        "F_fef_global": F_fef_global,
        "K_ff": K_ff,
        "K_fr": K_fr,
        "K_rf": K_rf,
        "K_rr": K_rr,
        "f_f": f_f,
        "f_r": f_r,
        "u_r": u_r,
        "f_fef_f": f_fef_f,
        "f_fef_r": f_fef_r,
        "free_dofs": free_dofs,
        "restrained_dofs": restrained_dofs,
        "rhs": rhs,
        "u_f": u_f,
        "F_r": F_r,
        "u_global": u_global,
        "f_global_complete": f_global_complete,
    }


def hybrid_solver(filepath):
    """
    Solve a mixed 3D structure model and return a rich result dict.

    Supported element types
    -----------------------
    - T : treated as truss element
    - F : treated as frame element

    Notes
    -----
    1. The element type is read from etype in element_paras.
    2. Each element is processed according to its own type first.
    3. All element contributions are then assembled into one global system.
    4. Rotational DOFs with zero global stiffness are added as fictitious
       restrained DOFs so the mixed model can be solved safely.
    """

    nodes = interfaces.read_nodes(filepath)
    elements = interfaces.read_elements(filepath)
    constraints = interfaces.read_constraints(filepath)
    materials = interfaces.read_materials(filepath)
    sections = interfaces.read_sections(filepath)
    F_global = interfaces.read_nodal_loads(filepath)
    element_loads = interfaces.read_element_loads(filepath)
    u_support = interfaces.read_support_disp(filepath)
    temperature_loads = interfaces.read_temperature_loads(filepath)
    fabrication_loads = interfaces.read_fabrication_errors(filepath)

    k_list = []
    T_list = []
    Qf_list = []
    Qh_list = []
    Qe_list = []
    map_list = []

    truss_element_ids = []
    frame_element_ids = []
    element_type_map = {}

    element_paras = element.build_elements_para(nodes, elements, materials, sections)

    for e_id in elements:
        i_node = elements[e_id][3][0]
        j_node = elements[e_id][3][1]

        L, etype, E, G, A, Iy, Iz, J, MT, alpha = element_paras[e_id]
        etype_upper = str(etype).strip().upper()
        element_type_map[e_id] = etype_upper

        kl = element.element_kl(E, G, A, Iy, Iz, J, L)

        gamma = element.build_gamma_3d(
            nodes[i_node],
            nodes[j_node],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)

        elem_load_global = element_loads.get(e_id)
        Qf = preprocess.fef_cal_global(elem_load_global, T, L)
        Qh = preprocess.heat_cal(temperature_loads.get(e_id), E, A, alpha)
        Qe = preprocess.fabrication_error_cal(fabrication_loads.get(e_id), E, A, L)
        m = element.element_dof_map_1based(i_node, j_node)

        if etype_upper == "T":
            truss_element_ids.append(e_id)

        elif etype_upper == "F":
            kl, Qf, Qh, Qe = preprocess.moment_release(MT, kl, Qf, Qh, Qe)
            frame_element_ids.append(e_id)

        else:
            raise ValueError(
                f"Unsupported element type for element {e_id}: {etype}. "
                "Supported types are T and F."
            )

        k_list.append(np.asarray(kl, dtype=float))
        T_list.append(np.asarray(T, dtype=float))
        Qf_list.append(np.asarray(Qf, dtype=float))
        Qh_list.append(np.asarray(Qh, dtype=float))
        Qe_list.append(np.asarray(Qe, dtype=float))
        map_list.append(np.asarray(m, dtype=int))

    Qt_list = [x + y + z for x, y, z in zip(Qf_list, Qh_list, Qe_list)]

    ndof = int(np.max(np.concatenate(map_list)))

    dof_restrained_1based = np.asarray(
        element.restrained_dofs_1based(constraints, element.node_dofs_1based),
        dtype=int,
    )

    K_global, F_fef_global = assembly.assemble_global_stiffness_and_fef(
        ndof, k_list, T_list, Qt_list, map_list
    )

    candidate_rot_dofs = preprocess.all_nodes_rotational_dofs_1based(nodes)
    dof_fictitious_1based = preprocess.zero_stiffness_dofs_1based(
        K_global,
        candidate_rot_dofs,
    )

    dof_restrained_1based = np.sort(
        np.unique(np.concatenate((dof_restrained_1based, dof_fictitious_1based)))
    )

    (
        K_ff,
        K_fr,
        K_rf,
        K_rr,
        f_f,
        f_r,
        u_r,
        f_fef_f,
        f_fef_r,
        free_dofs,
        restrained_dofs,
    ) = partition.partition_system(
        K_global, F_global, u_support, F_fef_global, dof_restrained_1based
    )

    rhs = f_f - f_fef_f - K_fr @ u_r
    u_f = np.linalg.solve(K_ff, rhs)

    F_r = K_rf @ u_f + K_rr @ u_r + f_fef_r

    fictitious_mask = np.isin(restrained_dofs, dof_fictitious_1based)
    F_r[fictitious_mask] = 0.0

    u_global = assembly.assemble_global_displacements(
        u_f, u_r, free_dofs, restrained_dofs
    )

    f_global_complete = assembly.assemble_global_forces(
        f_f, F_r, free_dofs, restrained_dofs
    )

    return {
        "filepath": filepath,
        "nodes": nodes,
        "elements": elements,
        "constraints": constraints,
        "materials": materials,
        "sections": sections,
        "F_global": F_global,
        "u_support": u_support,
        "element_loads": element_loads,
        "temperature_loads": temperature_loads,
        "fabrication_loads": fabrication_loads,
        "element_paras": element_paras,
        "element_type_map": element_type_map,
        "truss_element_ids": truss_element_ids,
        "frame_element_ids": frame_element_ids,
        "k_list": k_list,
        "T_list": T_list,
        "Qf_list": Qf_list,
        "Qh_list": Qh_list,
        "Qe_list": Qe_list,
        "Qt_list": Qt_list,
        "map_list": map_list,
        "ndof": ndof,
        "dof_fictitious_1based": dof_fictitious_1based,
        "dof_restrained_1based": dof_restrained_1based,
        "K_global": K_global,
        "F_fef_global": F_fef_global,
        "K_ff": K_ff,
        "K_fr": K_fr,
        "K_rf": K_rf,
        "K_rr": K_rr,
        "f_f": f_f,
        "f_r": f_r,
        "u_r": u_r,
        "f_fef_f": f_fef_f,
        "f_fef_r": f_fef_r,
        "free_dofs": free_dofs,
        "restrained_dofs": restrained_dofs,
        "rhs": rhs,
        "u_f": u_f,
        "F_r": F_r,
        "u_global": u_global,
        "f_global_complete": f_global_complete,
    }
