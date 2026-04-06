import numpy as np


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


def release_dof(dof, k_mod, Q_mod):
    """
    Helper function to apply moment release conditions by modifying the local stiffness matrix
    and the corresponding local load vector.
    """
    k_mod[dof, :] = 0.0
    k_mod[:, dof] = 0.0
    Q_mod[dof] = 0.0

    return k_mod, Q_mod


def moment_release(MT, k, Q):
    """
    Apply 3D moment release conditions to the local element stiffness matrix
    and the corresponding local load vector.

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

    Parameters
    ----------
    MT : int
        Moment release code.
    k : np.ndarray
        12x12 local element stiffness matrix.
    Q : np.ndarray
        12x1 local element load vector.

    Returns
    -------
    k_mod : np.ndarray
        Modified local stiffness matrix.
    Q_mod : np.ndarray
        Modified local load vector.
    """
    k_mod = k.copy()
    Q_mod = Q.copy()

    if k_mod.shape != (12, 12):
        raise ValueError("k must be a 12x12 matrix for a 3D frame element.")

    if Q_mod.shape not in [(12,), (12, 1)]:
        raise ValueError("Q must be a 12-component vector for a 3D frame element.")

    if MT == 0:
        pass
    elif MT == 1:
        release_dof(3, k_mod, Q_mod)
        release_dof(4, k_mod, Q_mod)
        release_dof(5, k_mod, Q_mod)
    elif MT == 2:
        release_dof(9, k_mod, Q_mod)
        release_dof(10, k_mod, Q_mod)
        release_dof(11, k_mod, Q_mod)
    elif MT == 3:
        release_dof(3, k_mod, Q_mod)
        release_dof(4, k_mod, Q_mod)
        release_dof(5, k_mod, Q_mod)
        release_dof(9, k_mod, Q_mod)
        release_dof(10, k_mod, Q_mod)
        release_dof(11, k_mod, Q_mod)
    else:
        raise ValueError("MT can only take the values 0, 1, 2, or 3.")

    return k_mod, Q_mod


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
