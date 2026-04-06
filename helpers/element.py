import numpy as np


def G_cal(E, nu):
    """
    Calculate shear modulus G from Young's modulus E and Poisson's ratio nu.
    """
    if E <= 0.0:
        raise ValueError("E must be positive.")
    if not (0.0 <= nu < 0.5):
        raise ValueError("nu must be in the range [0, 0.5).")

    G = E / (2.0 * (1.0 + nu))
    return G


def node_dofs_1based(node_id):
    """Return engineering DOF numbers (1-based): [ux_dof, uy_dof, uz_dof, rx_dof, ry_dof, rz_dof]."""
    return [
        6 * node_id - 5,
        6 * node_id - 4,
        6 * node_id - 3,
        6 * node_id - 2,
        6 * node_id - 1,
        6 * node_id,
    ]


def restrained_dofs_1based(nodes_restrained, node_dofs_1based):
    """Return sorted list of restrained DOF numbers (1-based) based on the provided node restraint conditions."""
    dof_restrained = []

    for node, restraints in nodes_restrained.items():
        ux_dof, uy_dof, uz_dof, rx_dof, ry_dof, rz_dof = node_dofs_1based(node)
        if "Ux" in restraints:
            dof_restrained.append(ux_dof)
        if "Uy" in restraints:
            dof_restrained.append(uy_dof)
        if "Uz" in restraints:
            dof_restrained.append(uz_dof)
        if "Rx" in restraints:
            dof_restrained.append(rx_dof)
        if "Ry" in restraints:
            dof_restrained.append(ry_dof)
        if "Rz" in restraints:
            dof_restrained.append(rz_dof)

    return sorted(dof_restrained)


def build_elements_para(nodes, elements, materials, sections):
    """Calculate and return a dictionary of element parameters for all elements."""
    element_paras = {}

    for elem_id, (elem_type_initial, matl, sect, node, mt) in elements.items():
        node_i, node_j = node
        dx = nodes[node_j][0] - nodes[node_i][0]
        dy = nodes[node_j][1] - nodes[node_i][1]
        dz = nodes[node_j][2] - nodes[node_i][2]
        L = float(np.sqrt(dx * dx + dy * dy + dz * dz))
        etype = elem_type_initial
        E, alpha, nu = materials[matl]
        A, Iy, Iz, J = sections[sect]
        G = G_cal(E, nu)
        element_paras[elem_id] = (L, etype, E, G, A, Iy, Iz, J, mt, alpha)
    return element_paras


def element_kl(E, G, A, Iy, Iz, J, L):
    """
    Return the 12x12 local stiffness matrix of a 3D frame element.

    Local DOF order
    ---------------
    [
        ux_b, uy_b, uz_b, thx_b, thy_b, thz_b,
        ux_e, uy_e, uz_e, thx_e, thy_e, thz_e
    ]

    Parameters
    ----------
    E : float
        Young's modulus.
    G : float
        Shear modulus.
    A : float
        Cross-sectional area.
    Iy : float
        Second moment of area about local y-axis.
    Iz : float
        Second moment of area about local z-axis.
    J : float
        Torsional constant.
    L : float
        Element length.

    Returns
    -------
    np.ndarray
        12x12 local stiffness matrix.
    """

    kl = (E / L**3) * np.array(
        [
            [A * L**2, 0.0, 0.0, 0.0, 0.0, 0.0, -A * L**2, 0.0, 0.0, 0.0, 0.0, 0.0],
            [
                0.0,
                12.0 * Iz,
                0.0,
                0.0,
                0.0,
                6.0 * L * Iz,
                0.0,
                -12.0 * Iz,
                0.0,
                0.0,
                0.0,
                6.0 * L * Iz,
            ],
            [
                0.0,
                0.0,
                12.0 * Iy,
                0.0,
                -6.0 * L * Iy,
                0.0,
                0.0,
                0.0,
                -12.0 * Iy,
                0.0,
                -6.0 * L * Iy,
                0.0,
            ],
            [
                0.0,
                0.0,
                0.0,
                G * J * L**2 / E,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                -G * J * L**2 / E,
                0.0,
                0.0,
            ],
            [
                0.0,
                0.0,
                -6.0 * L * Iy,
                0.0,
                4.0 * L**2 * Iy,
                0.0,
                0.0,
                0.0,
                6.0 * L * Iy,
                0.0,
                2.0 * L**2 * Iy,
                0.0,
            ],
            [
                0.0,
                6.0 * L * Iz,
                0.0,
                0.0,
                0.0,
                4.0 * L**2 * Iz,
                0.0,
                -6.0 * L * Iz,
                0.0,
                0.0,
                0.0,
                2.0 * L**2 * Iz,
            ],
            [-A * L**2, 0.0, 0.0, 0.0, 0.0, 0.0, A * L**2, 0.0, 0.0, 0.0, 0.0, 0.0],
            [
                0.0,
                -12.0 * Iz,
                0.0,
                0.0,
                0.0,
                -6.0 * L * Iz,
                0.0,
                12.0 * Iz,
                0.0,
                0.0,
                0.0,
                -6.0 * L * Iz,
            ],
            [
                0.0,
                0.0,
                -12.0 * Iy,
                0.0,
                6.0 * L * Iy,
                0.0,
                0.0,
                0.0,
                12.0 * Iy,
                0.0,
                6.0 * L * Iy,
                0.0,
            ],
            [
                0.0,
                0.0,
                0.0,
                -G * J * L**2 / E,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                G * J * L**2 / E,
                0.0,
                0.0,
            ],
            [
                0.0,
                0.0,
                -6.0 * L * Iy,
                0.0,
                2.0 * L**2 * Iy,
                0.0,
                0.0,
                0.0,
                6.0 * L * Iy,
                0.0,
                4.0 * L**2 * Iy,
                0.0,
            ],
            [
                0.0,
                6.0 * L * Iz,
                0.0,
                0.0,
                0.0,
                2.0 * L**2 * Iz,
                0.0,
                -6.0 * L * Iz,
                0.0,
                0.0,
                0.0,
                4.0 * L**2 * Iz,
            ],
        ],
        dtype=float,
    )

    return kl


def initialize_global_stiffness(nodes):
    """Return zero-initialized global stiffness matrix."""
    ndof_total = 6 * len(nodes)
    return np.zeros((ndof_total, ndof_total), dtype=float)


def build_gamma_3d(node_i, node_j, psi=0.0, angle_unit="deg"):
    """
    Build the 3x3 rotation matrix gamma for a 3D frame element
    according to the roll-angle formulation in the lecture notes.

    Parameters
    ----------
    node_i : array_like
        Global coordinates of start node [Xi, Yi, Zi].
    node_j : array_like
        Global coordinates of end node [Xj, Yj, Zj].
    psi : float, optional
        Roll angle about the local x-axis.
    angle_unit : str, optional
        "rad" or "deg".

    Returns
    -------
    gamma : np.ndarray
        3x3 direction cosine / rotation matrix such that
        local_vector = gamma @ global_vector

        Rows of gamma are:
        [local x-axis in global components
         local y-axis in global components
         local z-axis in global components]
    """

    node_i = np.asarray(node_i, dtype=float)
    node_j = np.asarray(node_j, dtype=float)

    d = node_j - node_i
    L = np.linalg.norm(d)
    if L == 0.0:
        raise ValueError("node_i and node_j cannot be the same point.")

    if angle_unit == "deg":
        psi = np.deg2rad(psi)
    elif angle_unit != "rad":
        raise ValueError("angle_unit must be 'rad' or 'deg'.")

    # local x-axis direction cosines
    rxX = d[0] / L
    rxY = d[1] / L
    rxZ = d[2] / L

    cpsi = np.cos(psi)
    spsi = np.sin(psi)

    denom = np.sqrt(rxX**2 + rxZ**2)

    # general case: use the exact lecture-note formula
    if denom > 1e-12:
        gamma = np.array(
            [
                [rxX, rxY, rxZ],
                [
                    (-rxX * rxY * cpsi - rxZ * spsi) / denom,
                    denom * cpsi,
                    (-rxY * rxZ * cpsi + rxX * spsi) / denom,
                ],
                [
                    (rxX * rxY * spsi - rxZ * cpsi) / denom,
                    -denom * spsi,
                    (rxY * rxZ * spsi + rxX * cpsi) / denom,
                ],
            ],
            dtype=float,
        )

    # special case: member parallel to global Y-axis
    else:
        # rxX = 0 and rxZ = 0 => local x is along +/- global Y
        # need a separate consistent definition
        sign_y = 1.0 if rxY >= 0.0 else -1.0

        gamma = np.array(
            [
                [0.0, sign_y, 0.0],
                [-sign_y * cpsi, 0.0, spsi],
                [sign_y * spsi, 0.0, cpsi],
            ],
            dtype=float,
        )

    return gamma


def frame_transformation_matrix(gamma):
    """
    Return the 12x12 transformation matrix for a 3D frame element.

    Parameters
    ----------
    gamma : np.ndarray
        3x3 direction cosine matrix from global axes to local axes.

    Returns
    -------
    np.ndarray
        12x12 transformation matrix.

    Local/global DOF order
    ----------------------
    [
        ux_b, uy_b, uz_b, thx_b, thy_b, thz_b,
        ux_e, uy_e, uz_e, thx_e, thy_e, thz_e
    ]
    """

    T = np.zeros((12, 12), dtype=float)

    T[0:3, 0:3] = gamma
    T[3:6, 3:6] = gamma
    T[6:9, 6:9] = gamma
    T[9:12, 9:12] = gamma

    return T


def element_dof_map_1based(i_node, j_node):
    """Return the 6 global DOF indices (1-based) for element (i, j).

    Order matches the 6x6 element stiffness matrix:
    [u_ix, u_iy, theta_i, u_jx, u_jy, theta_j]
    """
    # Engineering DOF numbers (1-based)
    dofs_i_1 = [
        6 * i_node - 5,
        6 * i_node - 4,
        6 * i_node - 3,
        6 * i_node - 2,
        6 * i_node - 1,
        6 * i_node,
    ]
    dofs_j_1 = [
        6 * j_node - 5,
        6 * j_node - 4,
        6 * j_node - 3,
        6 * j_node - 2,
        6 * j_node - 1,
        6 * j_node,
    ]
    dofs_1based = dofs_i_1 + dofs_j_1
    return dofs_1based
