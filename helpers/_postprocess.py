import numpy as np
import pandas as pd
import plotly.graph_objects as go
from . import interfaces


### --------- Shared utilities for post-processing --------- ###


def display_compact(df):
    return (
        df.style.format(
            {
                col: "{:.1f}"
                for col in df.columns
                if any(key in col for key in ["(mm)", "(kN)", "(MPa)", "L"])
            }
        )
        .set_properties(
            **{
                "font-size": "9pt",
                "padding": "2px",
                "white-space": "nowrap",
            }
        )
        .set_table_styles(
            [
                {"selector": "th", "props": [("font-size", "9pt")]},
            ]
        )
    )


### --------- Truss utilities for post-processing --------- ###


def extract_element_displacements(u_global, i_node, j_node):
    """
    Extract the 12x1 element global displacement vector u_e.
    Order: [u_ix, u_iy, u_iz, theta_ix, theta_iy, theta_iz,
            u_jx, u_jy, u_jz, theta_jx, theta_jy, theta_jz]
    """
    dofs_1based = [
        6 * i_node - 5,
        6 * i_node - 4,
        6 * i_node - 3,
        6 * i_node - 2,
        6 * i_node - 1,
        6 * i_node,
        6 * j_node - 5,
        6 * j_node - 4,
        6 * j_node - 3,
        6 * j_node - 2,
        6 * j_node - 1,
        6 * j_node,
    ]
    idx = [d - 1 for d in dofs_1based]  # convert to 0-based
    return u_global[idx]


def compute_local_end_forces(E, A, L, u_local):
    k_local = truss_local_stiffness(E, A, L)
    return k_local @ u_local


def compute_axial_force_and_stress(E, A, L, u_local):
    # axial displacements are the local DOFs along the member axis
    u_i_axial = u_local[0]
    u_j_axial = u_local[3]

    N = (E * A / L) * (u_j_axial - u_i_axial)
    sigma = N / A
    return N, sigma


def local_to_global_forces(l, m, n, f_local):
    T = truss_transformation_matrix(l, m, n)
    return T.T @ f_local


def plot_truss_deformation(nodes, elements, u_global, scale=1.0):
    """
    Plot original (black) and deformed (red) truss geometry.
    """
    fig = go.Figure()

    first = True

    for e_id, (i, j, *_) in elements.items():
        xi, yi, zi = nodes[i]
        xj, yj, zj = nodes[j]

        ui = u_global[6 * (i - 1) : 6 * (i - 1) + 6]
        uj = u_global[6 * (j - 1) : 6 * (j - 1) + 6]

        # original
        fig.add_trace(
            go.Scatter3d(
                x=[xi, xj],
                y=[yi, yj],
                z=[zi, zj],
                mode="lines",
                name="Original" if first else None,
                showlegend=first,
                line=dict(width=4),
            )
        )

        # deformed
        fig.add_trace(
            go.Scatter3d(
                x=[xi + scale * ui[0], xj + scale * uj[0]],
                y=[yi + scale * ui[1], yj + scale * uj[1]],
                z=[zi + scale * ui[2], zj + scale * uj[2]],
                mode="lines",
                name="Deformed" if first else None,
                showlegend=first,
                line=dict(width=4),
            )
        )

        first = False

    fig.update_layout(
        title=f"Original and deformed truss, scale={scale}",
        scene=dict(
            xaxis_title="x",
            yaxis_title="y",
            zaxis_title="z",
            aspectmode="data",  # equal
        ),
    )

    fig.show()
    return fig


def recover_element_results(elements, elements_lmnL, u_global):
    results = {}

    for e_id, (i, j, E_e, A_e) in elements.items():
        l, m, n, L = elements_lmnL[e_id]

        u_e = extract_element_displacements(u_global, i, j)
        u_local = compute_local_displacements(l, m, n, u_e)
        f_local = compute_local_end_forces(E_e, A_e, L, u_local)
        N, sigma = compute_axial_force_and_stress(E_e, A_e, L, u_local)

        results[e_id] = {
            "u_e": u_e,
            "u_local": u_local,
            "f_local": f_local,
            "N": N,  # kN
            "sigma": sigma,  # GPa
        }

    return results


def build_element_results_dataframe(elements, elements_lmnL, results):
    """Return pandas DataFrame of element-level results."""
    rows = []

    for e_id in sorted(elements.keys()):
        i, j, _, _ = elements[e_id]
        _, _, _, L = elements_lmnL[e_id]
        r = results[e_id]

        row = {
            "ele": e_id,
            "i": i,
            "j": j,
            "L (mm)": round(L, 1),
            "N (kN)": round(r["N"], 1),
            "sigma (MPa)": round(r["sigma"] * 1000, 1),
        }

        # global displacements u_e
        row.update({f"u_{k+1} (mm)": round(r["u_e"][k], 1) for k in range(12)})
        # local displacements u'
        row.update({f"u_{k+1}' (mm)": round(r["u_local"][k], 1) for k in range(12)})
        # local end forces f'
        row.update({f"f_{k+1}' (kN)": round(r["f_local"][k], 1) for k in range(12)})

        rows.append(row)

    return pd.DataFrame(rows)


def print_matrix_scaled(K, scale=1, decimals=2, col_width=7):
    """
    Print K/scale row-by-row, compact, with DOF labels.
    """
    fmt = f"{{:{col_width}.{decimals}f}}"
    print(f"K = {scale:.0e} ×")
    for i, row in enumerate(K, start=1):
        row_scaled = row / scale
        row_str = " ".join(fmt.format(val) for val in row_scaled)
        print(f"{i:2d} | {row_str}")


def build_global_load_vector(n_dof, dof_loaded_1based):
    """dof_loaded_1based: {dof(1-based): value}  ->  F (0-based numpy vector)"""
    F = np.zeros(n_dof, dtype=float)
    for dof1, val in dof_loaded_1based.items():
        F[dof1 - 1] += val
    return F


def build_reaction_df(
    nodes_restrained,
    node_dofs_1based,
    K_global,
    u_global,
    dof_loaded_1based,
    decimals=1,
):
    """
    Return a DataFrame with support reactions at restrained nodes.
    Units: same as your loads (e.g., kN).
    """
    n_dof = K_global.shape[0]
    F = build_global_load_vector(n_dof, dof_loaded_1based)

    R = K_global @ u_global - F

    rows = []
    for node in sorted(nodes_restrained.keys()):
        ux, uy, uz = node_dofs_1based(node)

        Rx = R[ux - 1]
        Ry = R[uy - 1]
        Rz = R[uz - 1]

        rows.append(
            {
                "node": node,
                "Rx (kN)": round(Rx, decimals),
                "Ry (kN)": round(Ry, decimals),
                "Rz (kN)": round(Rz, decimals),
            }
        )

    return pd.DataFrame(rows)


def build_node_displacement_df(nodes, node_dofs_1based, u_global):
    """
    nodes: {node_id: (x,y,z)}
    node_dofs_1based(node) -> (ux_dof, uy_dof, uz_dof)  1-based
    u_global: full displacement vector
    """
    rows = []
    for n in sorted(nodes.keys()):
        coord = nodes[n]
        dofs = node_dofs_1based(n)

        ux = float(u_global[dofs[0] - 1])
        uy = float(u_global[dofs[1] - 1])
        uz = float(u_global[dofs[2] - 1])

        umag = float(np.sqrt(ux**2 + uy**2 + uz**2))

        row = {
            "node": n,
            "x": coord[0],
            "y": coord[1],
            "ux (mm)": ux,
            "uy (mm)": uy,
            "uz (mm)": uz,
            "|u| (mm)": umag,
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    for c in df.columns:
        df[c] = df[c].astype(float).round(1)

    return df


def build_max_displacement_summary(df_disp):
    """
    Extract the maximum displacement (modulus length) and the positions of the maximum absolute values for each component from the node displacement table.
    """
    cols = df_disp.columns

    i_mag = df_disp["|u| (mm)"].astype(float).idxmax()
    r_mag = df_disp.loc[i_mag]

    summary_rows = [
        {
            "metric": "max |u|",
            "node": int(r_mag["node"]),
            "value (mm)": float(r_mag["|u| (mm)"]),
            "ux (mm)": float(r_mag["ux (mm)"]),
            "uy (mm)": float(r_mag["uy (mm)"]),
            "uz (mm)": float(r_mag["uz (mm)"]),
        }
    ]

    for comp in ["ux (mm)", "uy (mm)", "uz (mm)"]:
        if comp not in cols:
            continue
        i_c = df_disp[comp].astype(float).abs().idxmax()
        r_c = df_disp.loc[i_c]
        summary_rows.append(
            {
                "metric": f"max |{comp.split()[0]}|",
                "node": int(r_c["node"]),
                "value (mm)": float(r_c[comp]),
                "ux (mm)": float(r_c["ux (mm)"]),
                "uy (mm)": float(r_c["uy (mm)"]),
                "uz (mm)": float(r_c["uz (mm)"]),
            }
        )

    return pd.DataFrame(summary_rows)


def plot_truss_3d_plotly(
    nodes,
    elements,
    nodes_restrained=None,
    nodes_loaded=None,
    show_node_ids=True,
    show_member_ids=False,
    load_scale=0.02,
):
    """
    nodes: {nid: (x,y,z)}
    elements: {eid: (i,j,E,A)}
    nodes_restrained: {nid: ["ux","uy","uz"], ...}
    nodes_loaded: {nid: (Fx,Fy,Fz)}
    """

    # ---- normalize nodes to 3D ----
    nodes3 = {}
    for nid, xyz in nodes.items():
        if len(xyz) == 2:
            x, y = xyz
            z = 0.0
        else:
            x, y, z = xyz
        nodes3[nid] = (float(x), float(y), float(z))

    fig = go.Figure()

    # =========================================================
    # Members (lines)
    # =========================================================
    xs, ys, zs = [], [], []
    for eid, (i, j, E, A) in elements.items():
        xi, yi, zi = nodes3[i]
        xj, yj, zj = nodes3[j]
        xs += [xi, xj, None]
        ys += [yi, yj, None]
        zs += [zi, zj, None]

    fig.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="lines",
            line=dict(width=3),
            name="Members",
        )
    )

    # Optional member IDs (text at midpoints)
    if show_member_ids:
        mx, my, mz, mt = [], [], [], []
        for eid, (i, j, E, A) in elements.items():
            xi, yi, zi = nodes3[i]
            xj, yj, zj = nodes3[j]
            mx.append((xi + xj) / 2)
            my.append((yi + yj) / 2)
            mz.append((zi + zj) / 2)
            mt.append(str(eid))

        fig.add_trace(
            go.Scatter3d(
                x=mx,
                y=my,
                z=mz,
                mode="text",
                text=mt,
                name="Member IDs",
            )
        )

    # =========================================================
    # Nodes
    # =========================================================
    nx = [p[0] for p in nodes3.values()]
    ny = [p[1] for p in nodes3.values()]
    nz = [p[2] for p in nodes3.values()]

    fig.add_trace(
        go.Scatter3d(
            x=nx,
            y=ny,
            z=nz,
            mode="markers",
            marker=dict(size=4),
            name="Nodes",
        )
    )

    if show_node_ids:
        fig.add_trace(
            go.Scatter3d(
                x=nx,
                y=ny,
                z=nz,
                mode="text",
                text=[str(nid) for nid in nodes3.keys()],
                textposition="top center",
                name="Node IDs",
            )
        )

    # =========================================================
    # Supports
    # =========================================================
    if nodes_restrained:
        sx, sy, sz = [], [], []
        for nid in nodes_restrained.keys():
            x, y, z = nodes3[nid]
            sx.append(x)
            sy.append(y)
            sz.append(z)

        fig.add_trace(
            go.Scatter3d(
                x=sx,
                y=sy,
                z=sz,
                mode="markers",
                marker=dict(size=7),
                name="Supports",
            )
        )

    # =========================================================
    # Loads (true arrows using cones)
    # =========================================================
    if nodes_loaded:
        lx, ly, lz = [], [], []
        u, v, w = [], [], []

        for nid, (Fx, Fy, Fz) in nodes_loaded.items():
            x, y, z = nodes3[nid]
            lx.append(x)
            ly.append(y)
            lz.append(z)

            # direction + magnitude
            u.append(load_scale * Fx)
            v.append(load_scale * Fy)
            w.append(load_scale * Fz)

        fig.add_trace(
            go.Cone(
                x=lx,
                y=ly,
                z=lz,
                u=u,
                v=v,
                w=w,
                anchor="tail",  # arrow starts at node
                sizemode="absolute",
                sizeref=0.2,  # adjust arrowhead size
                showscale=False,
                name="Loads",
            )
        )

    # =========================================================
    # Layout (mirrors Matplotlib intent)
    # =========================================================
    fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",  # equal-ish aspect
            camera=dict(eye=dict(x=1.4, y=1.4, z=0.9)),  # similar to elev=20, azim=30
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title="3D Truss",
        showlegend=True,
    )

    fig.show()


def truss_output(
    filepath, K_global, u_global, nodes_restrained, node_dofs_1based, dof_loaded_1based
):

    nodes = interfaces.read_nodes(filepath)
    elements = interfaces.read_elements(filepath)

    plot_truss_3d_plotly(
        nodes,
        elements,
        nodes_restrained,
        nodes_loaded,
        show_node_ids=True,
        show_member_ids=False,
        load_scale=0.015,
    )

    plot_truss_deformation(nodes, elements, u_global, scale=100)

    results = recover_element_results(elements, elements_lmnL, u_global)
    df_members = build_element_results_dataframe(elements, elements_lmnL, results)
    display_compact(df_members)

    R_df = build_reaction_df(
        nodes_restrained=nodes_restrained,
        node_dofs_1based=node_dofs_1based,
        K_global=K_global,
        u_global=u_global,
        dof_loaded_1based=dof_loaded_1based,
        decimals=3,
    )

    display_compact(R_df)

    df_disp = build_node_displacement_df(nodes, node_dofs_1based, u_global)

    df_umax = build_max_displacement_summary(df_disp)

    display_compact(df_umax)


### --------- Frame utilities for post-processing --------- ###
