import numpy as np


def all_nodes_rotational_dofs_1based(nodes):
    """
    Return all rotational DOFs [Rx, Ry, Rz] for all nodes in 1-based numbering.
    Suitable for a pure truss model stored in a 6-DOF-per-node framework.
    """
    dofs = []

    for node_id in sorted(nodes):
        base = 6 * (node_id - 1)
        dofs.extend([base + 4, base + 5, base + 6])

    return np.array(dofs, dtype=int)


def zero_stiffness_dofs_1based(K_global, candidate_dofs_1based, tol=1e-12):
    """
    From candidate DOFs, keep only those whose row and column in K_global
    are both numerically zero.
    """
    K_global = np.asarray(K_global, dtype=float)
    candidate_dofs_1based = np.asarray(candidate_dofs_1based, dtype=int)

    zero_dofs = []

    for dof in candidate_dofs_1based:
        idx = dof - 1
        row_zero = np.all(np.abs(K_global[idx, :]) <= tol)
        col_zero = np.all(np.abs(K_global[:, idx]) <= tol)

        if row_zero and col_zero:
            zero_dofs.append(dof)

    return np.array(sorted(zero_dofs), dtype=int)


def zero_stiffness_rotational_dofs_1based(K_global, nodes, tol=1e-12):
    """
    Find rotational DOFs with zero global stiffness.

    This function is used to create fictitious restraints for:
    1. 12-DOF truss elements, whose rotational DOFs have no stiffness.
    2. Frame models where moment releases leave some rotational DOFs
       with no remaining stiffness.
    3. Mixed truss-frame models.

    The fictitious restraints are only numerical constraints. They prevent
    zero-stiffness rotational DOFs from entering K_ff.
    """
    candidate_rot_dofs = all_nodes_rotational_dofs_1based(nodes)

    return zero_stiffness_dofs_1based(
        K_global,
        candidate_rot_dofs,
        tol=tol,
    )


def fef_cal(elem_load, L, angle_unit="deg"):
    """
    Calculate the local fixed-end force vector for one element load entry.

    Input
    -----
    elem_load : list
        One value taken from the element-load dictionary, with format:
        [Tx, TLOCATION, qy, qyANGLE, qz, qzANGLE, Py, PyLOCATION, PyANGLE, Pz, PzLOCATION, PzANGLE]

    L : float
        Element length.

    angle_unit : str
        "deg" or "rad"

    Angle definition
    ----------------
    Angles follow the Cartesian convention in the corresponding local plane:

    - In the local x-y plane:
        0°   -> +x
        90°  -> +y

    - In the local x-z plane:
        0°   -> +x
        90°  -> +z

    Output order
    ------------
    [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i, Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
    """
    if elem_load is None:
        return np.zeros(12, dtype=float)

    if len(elem_load) != 12:
        raise ValueError(
            "elem_load must be "
            "[Tx, TLOCATION, qy, qyANGLE, qz, qzANGLE, Py, PyLOCATION, PyANGLE, Pz, PzLOCATION, PzANGLE]"
        )

    if L <= 0.0:
        raise ValueError("L must be positive.")

    (
        Tx,
        T_loc,
        qy,
        qy_angle,
        qz,
        qz_angle,
        Py,
        Py_loc,
        Py_angle,
        Pz,
        Pz_loc,
        Pz_angle,
    ) = elem_load

    if not (0.0 <= T_loc <= 1.0):
        raise ValueError("TLOCATION must be in [0, 1].")

    if not (0.0 <= Py_loc <= 1.0):
        raise ValueError("PyLOCATION must be in [0, 1].")

    if not (0.0 <= Pz_loc <= 1.0):
        raise ValueError("PzLOCATION must be in [0, 1].")

    if angle_unit == "deg":
        qy_angle = np.deg2rad(qy_angle)
        qz_angle = np.deg2rad(qz_angle)
        Py_angle = np.deg2rad(Py_angle)
        Pz_angle = np.deg2rad(Pz_angle)
    elif angle_unit != "rad":
        raise ValueError('angle_unit must be "deg" or "rad".')

    # output:
    # [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i, Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
    fef_local = np.zeros(12, dtype=float)

    # 1. decompose distributed loads

    # qy acts in local x-y plane
    qy_x = qy * np.cos(qy_angle)
    qy_y = qy * np.sin(qy_angle)

    # qz acts in local x-z plane
    qz_x = qz * np.cos(qz_angle)
    qz_z = qz * np.sin(qz_angle)

    # axial distributed load from both planes
    qx = qy_x + qz_x

    # full-span distributed axial load
    fef_local[0] += -qx * L / 2.0
    fef_local[6] += -qx * L / 2.0

    # full-span distributed load in local y direction
    # causes bending about local z
    fef_local[1] += -qy_y * L / 2.0
    fef_local[5] += -qy_y * L**2 / 12.0
    fef_local[7] += -qy_y * L / 2.0
    fef_local[11] += qy_y * L**2 / 12.0

    # full-span distributed load in local z direction
    # causes bending about local y
    fef_local[2] += -qz_z * L / 2.0
    fef_local[4] += qz_z * L**2 / 12.0
    fef_local[8] += -qz_z * L / 2.0
    fef_local[10] += -qz_z * L**2 / 12.0

    # 2. concentrated load in local x-y plane

    a = Py_loc * L
    b = L - a

    Py_x = Py * np.cos(Py_angle)
    Py_y = Py * np.sin(Py_angle)

    # axial component
    fef_local[0] += -Py_x * b / L
    fef_local[6] += -Py_x * a / L

    # transverse y component -> bending about z
    fef_local[1] += -Py_y * b**2 * (3.0 * a + b) / L**3
    fef_local[5] += -Py_y * a * b**2 / L**2
    fef_local[7] += -Py_y * a**2 * (a + 3.0 * b) / L**3
    fef_local[11] += Py_y * a**2 * b / L**2

    # 3. concentrated load in local x-z plane

    a = Pz_loc * L
    b = L - a

    Pz_x = Pz * np.cos(Pz_angle)
    Pz_z = Pz * np.sin(Pz_angle)

    # axial component
    fef_local[0] += -Pz_x * b / L
    fef_local[6] += -Pz_x * a / L

    # transverse z component -> bending about y
    fef_local[2] += -Pz_z * b**2 * (3.0 * a + b) / L**3
    fef_local[4] += Pz_z * a * b**2 / L**2
    fef_local[8] += -Pz_z * a**2 * (a + 3.0 * b) / L**3
    fef_local[10] += -Pz_z * a**2 * b / L**2

    # 4. concentrated torque about local x-axis

    a = T_loc * L
    b = L - a

    fef_local[3] += -Tx * b / L
    fef_local[9] += -Tx * a / L

    return fef_local


def fef_cal_global(elem_load_global, T, L, angle_unit="deg", tol=1e-12):
    """
    Calculate the local fixed-end force vector directly from member loads
    given in the global coordinate system.

    Parameters
    ----------
    elem_load_global : dict or None
        Dictionary format:

        {
            "q_global": [qx, qy, qz],   # full-span uniform distributed load
            "P_global": [Px, Py, Pz],   # one concentrated force
            "P_loc": 0.0,               # relative location in [0, 1]
            "M_global": [Mx, My, Mz],   # concentrated moment
            "M_loc": 0.0                # relative location in [0, 1]
        }

        Any missing item is treated as zero.

        Notes
        -----
        1. q_global is one full-span uniform distributed load vector.
        2. P_global is one concentrated force entry.
        3. M_global is only supported when its local equivalent has
           moment about local x-axis only.

    T : np.ndarray
        12x12 transformation matrix defined by:
        T = block_diag(gamma, gamma, gamma, gamma)

        where gamma satisfies:
        local_vector = gamma @ global_vector

    L : float
        Element length.

    angle_unit : str
        Kept for interface consistency. Not used in this function,
        because global loads are given directly by Cartesian components.

    tol : float
        Tolerance for zero check.

    Returns
    -------
    np.ndarray
        Local fixed-end force vector:
        [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i,
         Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
    """
    if elem_load_global is None:
        return np.zeros(12, dtype=float)

    if L <= 0.0:
        raise ValueError("L must be positive.")

    T = np.asarray(T, dtype=float)

    if T.shape != (12, 12):
        raise ValueError("T must be a 12x12 transformation matrix.")

    gamma = T[0:3, 0:3]

    q_global = np.asarray(
        elem_load_global.get("q_global", [0.0, 0.0, 0.0]), dtype=float
    )
    P_global = np.asarray(
        elem_load_global.get("P_global", [0.0, 0.0, 0.0]), dtype=float
    )
    M_global = np.asarray(
        elem_load_global.get("M_global", [0.0, 0.0, 0.0]), dtype=float
    )

    if q_global.shape != (3,):
        raise ValueError('"q_global" must have 3 components.')
    if P_global.shape != (3,):
        raise ValueError('"P_global" must have 3 components.')
    if M_global.shape != (3,):
        raise ValueError('"M_global" must have 3 components.')

    P_loc = float(elem_load_global.get("P_loc", 0.0))
    M_loc = float(elem_load_global.get("M_loc", 0.0))

    if not (0.0 <= P_loc <= 1.0):
        raise ValueError("P_loc must be in [0, 1].")
    if not (0.0 <= M_loc <= 1.0):
        raise ValueError("M_loc must be in [0, 1].")

    # global -> local
    q_local = gamma @ q_global
    P_local = gamma @ P_global
    M_local = gamma @ M_global

    fef_local = np.zeros(12, dtype=float)

    # ---------------------------------------------------------
    # 1. Full-span uniform distributed load
    # local components: [qx, qy, qz]
    # ---------------------------------------------------------
    qx, qy, qz = q_local

    # axial distributed load
    fef_local[0] += -qx * L / 2.0
    fef_local[6] += -qx * L / 2.0

    # transverse y component -> bending about local z
    fef_local[1] += -qy * L / 2.0
    fef_local[5] += -qy * L**2 / 12.0
    fef_local[7] += -qy * L / 2.0
    fef_local[11] += qy * L**2 / 12.0

    # transverse z component -> bending about local y
    fef_local[2] += -qz * L / 2.0
    fef_local[4] += qz * L**2 / 12.0
    fef_local[8] += -qz * L / 2.0
    fef_local[10] += -qz * L**2 / 12.0

    # ---------------------------------------------------------
    # 2. One concentrated force
    # local components: [Px, Py, Pz]
    # ---------------------------------------------------------
    a = P_loc * L
    b = L - a

    Px, Py, Pz = P_local

    # axial component
    fef_local[0] += -Px * b / L
    fef_local[6] += -Px * a / L

    # transverse y component -> bending about local z
    fef_local[1] += -Py * b**2 * (3.0 * a + b) / L**3
    fef_local[5] += -Py * a * b**2 / L**2
    fef_local[7] += -Py * a**2 * (a + 3.0 * b) / L**3
    fef_local[11] += Py * a**2 * b / L**2

    # transverse z component -> bending about local y
    fef_local[2] += -Pz * b**2 * (3.0 * a + b) / L**3
    fef_local[4] += Pz * a * b**2 / L**2
    fef_local[8] += -Pz * a**2 * (a + 3.0 * b) / L**3
    fef_local[10] += -Pz * a**2 * b / L**2

    # ---------------------------------------------------------
    # 3. One concentrated moment
    # only torsion about local x-axis is supported
    # ---------------------------------------------------------
    a = M_loc * L
    b = L - a

    Mx, My, Mz = M_local

    if not np.isclose(My, 0.0, atol=tol) or not np.isclose(Mz, 0.0, atol=tol):
        raise NotImplementedError(
            "Only concentrated moment about local x-axis is supported."
        )

    fef_local[3] += -Mx * b / L
    fef_local[9] += -Mx * a / L

    return fef_local


def _static_condense_release(k, q, released_dofs):
    """
    Apply end release by static condensation for one local load vector.

    Parameters
    ----------
    k : np.ndarray
        12x12 local stiffness matrix.
    q : array_like
        12-component local load vector.
    released_dofs : list[int]
        Released local DOF indices (0-based).

    Returns
    -------
    k_out : np.ndarray
        12x12 released local stiffness matrix.
    q_out : list
        12-component released local load vector.
    """
    k = np.asarray(k, dtype=float)
    q = np.asarray(q, dtype=float)

    if k.shape != (12, 12):
        raise ValueError("k must be a 12x12 matrix for a 3D frame element.")

    if q.shape != (12,):
        raise ValueError("q must be a 12-component vector for a 3D frame element.")

    if not released_dofs:
        return k.copy(), q.tolist()

    all_dofs = list(range(12))
    kept_dofs = [d for d in all_dofs if d not in released_dofs]

    Kaa = k[np.ix_(kept_dofs, kept_dofs)]
    Kab = k[np.ix_(kept_dofs, released_dofs)]
    Kba = k[np.ix_(released_dofs, kept_dofs)]
    Kbb = k[np.ix_(released_dofs, released_dofs)]

    qa = q[kept_dofs]
    qb = q[released_dofs]

    if np.linalg.matrix_rank(Kbb) < len(released_dofs):
        raise ValueError(
            "Released DOF submatrix Kbb is singular. "
            "Check element stiffness or release definition."
        )

    Kbb_inv_Kba = np.linalg.solve(Kbb, Kba)
    Kbb_inv_qb = np.linalg.solve(Kbb, qb)

    Kaa_rel = Kaa - Kab @ Kbb_inv_Kba
    qa_rel = qa - Kab @ Kbb_inv_qb

    k_out = np.zeros((12, 12), dtype=float)
    q_out = np.zeros(12, dtype=float)

    k_out[np.ix_(kept_dofs, kept_dofs)] = Kaa_rel
    q_out[kept_dofs] = qa_rel

    return k_out, q_out.tolist()


def moment_release(MT, k, Qf, Qh, Qe):
    """
    Apply 3D spherical end release conditions by static condensation.

    Local DOF order
    ---------------
    [u_i, v_i, w_i, thx_i, thy_i, thz_i,
     u_j, v_j, w_j, thx_j, thy_j, thz_j]

    Release definition
    ------------------
    For MT:
    0 : no release
    1 : release i-end
    2 : release j-end
    3 : release both ends

    Notes
    -----
    Here "release" means spherical hinge release, so all three rotational DOFs
    at the released end are released:
    - i-end : [3, 4, 5]
    - j-end : [9, 10, 11]
    """
    k = np.asarray(k, dtype=float)
    Qf = np.asarray(Qf, dtype=float)
    Qh = np.asarray(Qh, dtype=float)
    Qe = np.asarray(Qe, dtype=float)

    if k.shape != (12, 12):
        raise ValueError("k must be a 12x12 matrix for a 3D frame element.")

    if Qf.shape != (12,) or Qh.shape != (12,) or Qe.shape != (12,):
        raise ValueError("Qf, Qh, and Qe must all be 12-component vectors.")

    if MT == 0:
        released_dofs = []

    elif MT == 1:
        released_dofs = [3, 4, 5]

    elif MT == 2:
        released_dofs = [9, 10, 11]

    elif MT == 3:
        released_dofs = [3, 4, 5, 9, 10, 11]

    else:
        raise ValueError("MT can only take the values 0, 1, 2, or 3.")

    if not released_dofs:
        return k.copy(), Qf.tolist(), Qh.tolist(), Qe.tolist()

    k_mod, Qf_mod = _static_condense_release(k, Qf, released_dofs)
    _, Qh_mod = _static_condense_release(k, Qh, released_dofs)
    _, Qe_mod = _static_condense_release(k, Qe, released_dofs)

    return k_mod, Qf_mod, Qh_mod, Qe_mod


def heat_cal(temp, E, A, alpha):
    """
    Calculate local fixed-end force vector for a 3D frame member
    caused by uniform temperature change.

    Parameters
    ----------
    team_loads : float
        Uniform temperature change.
    E : float
        Young's modulus.
    A : float
        Cross-sectional area.
    I : float
        Not used here, kept only for interface compatibility.
    d : float
        Not used here, kept only for interface compatibility.
    alpha : float
        Coefficient of thermal expansion.

    Returns
    -------
    Qh : list
        Local fixed-end force vector in the order:
        [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i,
         Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
    """
    if temp is None:
        return np.zeros(12, dtype=float)

    N_h = E * alpha * A * temp

    Qh = [N_h, 0.0, 0.0, 0.0, 0.0, 0.0, -N_h, 0.0, 0.0, 0.0, 0.0, 0.0]

    return Qh


def fabrication_error_cal(e_a, E, A, L):
    """
    Calculate local fixed-end force vector for a 3D frame member
    caused by axial fabrication error.

    Parameters
    ----------
    e_a : float
        Axial fabrication error (local x direction).
    E : float
        Young's modulus.
    A : float
        Cross-sectional area.
    L : float
        Member length.

    Returns
    -------
    Qe : list
        Local fixed-end force vector in the order:
        [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i,
         Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
    """
    if e_a is None:
        return np.zeros(12, dtype=float)

    N_e = E * A * e_a / L

    Qe = [N_e, 0.0, 0.0, 0.0, 0.0, 0.0, -N_e, 0.0, 0.0, 0.0, 0.0, 0.0]

    return Qe
