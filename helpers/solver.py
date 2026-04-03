import assembly
import elements
import interfaces
import partition
import preprocess
import numpy as np

k_list = []
T_list = []
Qf_list = []
map_list = []
for e_id in elements:
    c, s, L = elements_csl[e_id]
    load_type, Fx, Fy, M = elements_loaded[e_id]

    kl = frame_element_kl(E, A, I, L)
    T = frame_transformation_matrix(c, s)
    Qf = FEF_cal(load_type, Fx, Fy, M, L)
    m = element_dof_map_1based(elements[e_id][0], elements[e_id][1])

    k_list.append(kl)
    T_list.append(T)
    Qf_list.append(Qf)
    map_list.append(m)

print(k_list)
print(T_list)
print(Qf_list)
print(map_list)

ndof = int(np.max(np.concatenate(map_list)))


def solve_unknown(ndof, k_list, T_list, map_list,
                  Qf_list, Qh_list, Qe_list,
                  ):
    Qt_list = [x + y + z for x, y, z in zip(Qf_list, Qh_list, Qe_list)]

    dof_restrained_1based = restrained_dofs_1based(nodes_restrained, node_dofs_1based)
    dof_fictitious_1based = np.array([], dtype=int)

    dof_restrained_1based = np.sort(
        np.concatenate((dof_restrained_1based, dof_fictitious_1based))
    )

    F_global = np.zeros(ndof, dtype=float)
    u_global = np.zeros(ndof, dtype=float)

    K_global, F_fef_global = assembly.assemble_global_stiffness_and_fef(
        ndof,
        k_list,
        T_list,
        Qt_list,
        map_list
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
        K_global,
        F_global,
        u_global,
        F_fef_global,
        dof_restrained_1based
    )
    
    u_global = assembly.assemble_global_displacements(
        u_f,
        u_r,
        free_dofs,
        restrained_dofs
        )
    
    f_global_complete = assembly.assemble_global_forces(
        f_f,
        F_r,
        free_dofs,
        restrained_dofs
        )

    rhs = f_f - f_fef_f - K_fr @ u_r
    u_f = np.linalg.solve(K_ff, rhs)

    F_r = K_rf @ u_f + K_rr @ u_r + f_fef_r











