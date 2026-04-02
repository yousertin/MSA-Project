import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def print_dsm_results(
    u_global,
    f_global_complete,
    dof_restrained_1based,
    dof_fictitious_1based=None,  # ← optional kwarg
    disp_in_mm=False,
):

    ndof = len(u_global)
    rows = []

    # Ensure arrays
    dof_restrained_1based = np.atleast_1d(dof_restrained_1based)

    if dof_fictitious_1based is None:
        dof_fictitious_1based = np.array([], dtype=int)
    else:
        dof_fictitious_1based = np.atleast_1d(dof_fictitious_1based)

    restrained_set = {int(d) for d in dof_restrained_1based}
    fictitious_set = {int(d) for d in dof_fictitious_1based}

    for i in range(ndof):
        dof_1based = i + 1
        mod = i % 3

        if mod == 0:
            dof_type = "u_x"
            disp = u_global[i] * (1000 if disp_in_mm else 1)
        elif mod == 1:
            dof_type = "u_y"
            disp = u_global[i] * (1000 if disp_in_mm else 1)
        else:
            dof_type = "theta"
            disp = u_global[i]

        if dof_1based in fictitious_set:
            status = "Fictitious"
        elif dof_1based in restrained_set:
            status = "Fixed"
        else:
            status = "Free"

        rows.append([dof_1based, dof_type, status, disp, f_global_complete[i]])

    disp_unit = "mm" if disp_in_mm else "m"

    df = pd.DataFrame(
        rows,
        columns=[
            "DOF",
            "Type",
            "Status",
            f"Disp ({disp_unit} / rad)",
            "Load (kN / kN·m)",
        ],
    )

    print(df.to_string(index=False, float_format="%.3f"))


def print_element(
    e, u_global, m_1based, T, k, Qf, disp_in_mm=False, dec=3, rad_dec=4
):

    idx = m_1based - 1
    u = u_global[idx]
    v = T @ u
    q = k @ v + Qf

    scale = 1000 if disp_in_mm else 1
    unit = "mm" if disp_in_mm else "m"

    # Scale translations only (0,1,3,4) — rotations (2,5) untouched
    u_out = u.copy()
    v_out = v.copy()
    for j in [0, 1, 3, 4]:
        u_out[j] *= scale
        v_out[j] *= scale

    def fmt_disp(vec):
        parts = []
        for j, val in enumerate(vec):
            if j % 3 == 2:  # rotation (rad)
                parts.append(f"{val:.{rad_dec}f}")
            else:  # translation
                parts.append(f"{val:.{dec}f}")
        return "[" + ", ".join(parts) + "]"

    def fmt_force(vec):
        # forces (kN) and moments (kN·m) both use dec
        return "[" + ", ".join(f"{val:.{dec}f}" for val in vec) + "]"

    print(f"\nE{e}")
    print(f"u [{unit},rad]: {fmt_disp(u_out)}")
    print(f"v [{unit},rad]: {fmt_disp(v_out)}")
    print(f"q [kN,kN·m]: {fmt_force(q)}")


def print_element_truss(
    e,
    u_global,
    m_1based,
    T,
    k_local,
    Qf_local=None,
    disp_in_mm=False,
    dec=3,
):
    """
    Print element-level results for a 2D truss element.

    Parameters
    ----------
    e : int
        Element number for printing.
    u_global : (ndof,) array
        Global displacement vector.
    m_1based : (4,) array-like
        Global DOF map for this element (1-based indexing).
    T : (4,4) array
        Transformation matrix (global -> local).
    k_local : (4,4) array
        Local truss stiffness matrix (typically axial-only with 1/-1 pattern).
    Qf_local : (4,) array or None
        Local fixed-end / initial-force vector. If None, assumed zero.
        (Usually zero for trusses unless you model prestrain/temperature/etc.)
    disp_in_mm : bool
        If True, print translations in mm.
    dec : int
        Decimal places for printing.

    Prints
    ------
    - Element global displacement subvector u_e (translations)
    - Element local displacement vector u'_e
    - Element local end force vector q'_e
    - Axial force N (tension positive), computed as N = Fx_j' = -Fx_i'
    """

    idx = np.asarray(m_1based, dtype=int) - 1
    u_e = u_global[idx]  # [uix, uiy, ujx, ujy]

    if Qf_local is None:
        Qf_local = np.zeros(4, dtype=float)

    u_loc = T @ u_e
    q_loc = k_local @ u_loc + Qf_local  # [Fx_i', Fy_i', Fx_j', Fy_j']

    # scale translations for printing
    scale = 1000 if disp_in_mm else 1
    unit = "mm" if disp_in_mm else "m"
    u_out = u_e * scale
    uloc_out = u_loc * scale

    def fmt(vec):
        return "[" + ", ".join(f"{v:.{dec}f}" for v in vec) + "]"

    # axial force (tension +): for a pure truss, Fy' should be ~0
    # N_i = q_loc[0]  # Fx at i in local axis
    N_j = q_loc[2]  # Fx at j in local axis
    N = N_j  # report axial as end force at j (should equal -N_i)

    print(f"\nE{e} (Truss)")
    print(f"u_global [{unit}]: {fmt(u_out)}")
    print(f"u_local  [{unit}]: {fmt(uloc_out)}")
    print(f"q_local  [kN]: {fmt(q_loc)}")
    print(f"N (tension +) = {N:.{dec}f} kN\n")


def print_matrix_scaled(K, scale=1000, decimals=1, col_width=3):
    fmt = f"{{:{col_width}.{decimals}f}}"
    print(f"K = {scale:.0e} ×")
    for i, row in enumerate(K, start=1):
        row_scaled = row / scale
        row_str = " ".join(fmt.format(val) for val in row_scaled)
        print(f"{i:02d} | {row_str}")


def plot_truss_deformation(nodes, elements, u_global, scale=1.0):
    """
    Plot original (black) and deformed (red) truss geometry.
    """
    plt.figure()

    for e_id, (i, j, *_) in elements.items():
        xi, yi = nodes[i]
        xj, yj = nodes[j]

        ui = u_global[2 * (i - 1) : 2 * (i - 1) + 2]
        uj = u_global[2 * (j - 1) : 2 * (j - 1) + 2]

        # original
        plt.plot([xi, xj], [yi, yj], "k-", lw=2)

        # deformed
        plt.plot(
            [xi + scale * ui[0], xj + scale * uj[0]],
            [yi + scale * ui[1], yj + scale * uj[1]],
            "r-",
            lw=2,
        )

    plt.axis("equal")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title(f"Original (black) and deformed (red), scale={scale}")
    plt.show()
