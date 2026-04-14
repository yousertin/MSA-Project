import assembly
import element
import interfaces
import partition
import preprocess
import numpy as np


def truss_solver(
    nodes,
    elements,
    constraints,
    materials,
    sections,
    nodal_loads,
    element_loads,
    temperature_loads,
    fabrication_loads,
):
    """
    A simple solver for truss structures. It assembles the global stiffness matrix,
    applies boundary conditions, and solves for displacements.

    Parameters
    ----------
    nodes : dict
        A dictionary of node IDs and their coordinates.
    """

    k_list = []
    T_list = []
    Qf_list = []
    Qh_list = []
    Qe_list = []
    map_list = []

    element_paras = element.build_elements_para(nodes, elements, materials, sections)

    for e_id in elements:
        L, etype, E, G, A, Iy, Iz, J, mt, alpha = element_paras[e_id]
        kl = element.element_kl(E, G, A, Iy, Iz, J, L)
        gamma = element.build_gamma_3d(
            nodes[elements[e_id][3][0]],
            nodes[elements[e_id][3][1]],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)
        Qf = preprocess.fef_cal(element_loads.get(e_id), L, angle_unit="deg")
        Qh = preprocess.heat_cal(temperature_loads.get(e_id), E, A, alpha)
        Qe = preprocess.fabrication_error_cal(fabrication_loads.get(e_id), E, A, L)
        m = element.element_dof_map_1based(elements[e_id][3][0], elements[e_id][3][1])

        k_list.append(kl)
        T_list.append(T)
        Qf_list.append(Qf)
        Qh_list.append(Qh)
        Qe_list.append(Qe)
        map_list.append(m)

    Qt_list = [x + y + z for x, y, z in zip(Qf_list, Qh_list, Qe_list)]

    ndof = int(np.max(np.concatenate(map_list)))

    dof_restrained_1based = element.restrained_dofs_1based(
        constraints, element.node_dofs_1based
    )
    dof_fictitious_1based = np.array([], dtype=int)

    dof_restrained_1based = np.sort(
        np.concatenate((dof_restrained_1based, dof_fictitious_1based))
    )

    F_global = np.zeros(ndof, dtype=float)
    u_global = np.zeros(ndof, dtype=float)

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
        K_global, F_global, u_global, F_fef_global, dof_restrained_1based
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
