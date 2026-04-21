import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import element
from . import interfaces
from . import preprocess

try:
    from IPython.display import display
except Exception:  # pragma: no cover
    display = None


### --------- Shared utilities --------- ###


def _read_units(filepath):
    """Read UNIT block from json file. Falls back to generic labels."""
    force_unit = "force"
    dist_unit = "length"
    temper_unit = "temperature"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        unit = data.get("UNIT", {})
        force_unit = unit.get("FORCE", force_unit)
        dist_unit = unit.get("DIST", dist_unit)
        temper_unit = unit.get("TEMPER", temper_unit)
    except Exception:
        pass

    return {
        "force": force_unit,
        "dist": dist_unit,
        "stress": f"{force_unit}/{dist_unit}^2",
        "temper": temper_unit,
    }


def display_compact(df, decimals=4):
    """Return a compact Styler for notebook display."""
    fmt = {
        col: f"{{:.{decimals}f}}"
        for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    }

    return (
        df.style.format(fmt)
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


def _show_df(df, decimals=4):
    styler = display_compact(df, decimals=decimals)
    if display is not None:
        display(styler)
    else:  # pragma: no cover
        print(df)
    return styler


def _safe_excel_sheet_name(name, used_names=None):
    """
    Make a valid Excel sheet name:
    - remove invalid characters: : \\ / ? * [ ]
    - limit length to 31
    - avoid duplicate names
    """
    if used_names is None:
        used_names = set()

    invalid_chars = [":", "\\", "/", "?", "*", "[", "]"]
    sheet_name = str(name)

    for ch in invalid_chars:
        sheet_name = sheet_name.replace(ch, "_")

    sheet_name = sheet_name.strip()
    if not sheet_name:
        sheet_name = "Sheet"

    base_name = sheet_name[:31]
    sheet_name = base_name

    counter = 1
    while sheet_name in used_names:
        suffix = f"_{counter}"
        sheet_name = base_name[: 31 - len(suffix)] + suffix
        counter += 1

    used_names.add(sheet_name)
    return sheet_name


def _export_tables_to_excel(
    json_filepath,
    tables,
    xlsx_filepath=None,
    output_dir=Path("outputs/"),
):
    """
    Export multiple DataFrames into one Excel file, one sheet per table.

    If xlsx_filepath is None, export to:
        examples/validation_results/<json_file_stem>.xlsx
    """
    json_path = Path(json_filepath)

    if xlsx_filepath is None:
        output_dir.mkdir(parents=True, exist_ok=True)
        xlsx_filepath = output_dir / f"{json_path.stem}.xlsx"
    else:
        xlsx_filepath = Path(xlsx_filepath)

    used_names = set()

    with pd.ExcelWriter(xlsx_filepath, engine="openpyxl") as writer:
        for title, df in tables:
            sheet_name = _safe_excel_sheet_name(title, used_names=used_names)

            if df is None or (df.empty and len(df.columns) == 0):
                pd.DataFrame({"info": ["empty"]}).to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                )
            else:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    return str(xlsx_filepath)


### --------- Basic DOF helpers --------- ###


def node_dofs_1based(node_id):
    """Return 1-based 6 dofs of one node: [Ux, Uy, Uz, Rx, Ry, Rz]."""
    base = 6 * (node_id - 1)
    return np.array(
        [base + 1, base + 2, base + 3, base + 4, base + 5, base + 6],
        dtype=int,
    )


def extract_element_displacements(u_global, i_node, j_node):
    """Extract 12 global dofs of one element from the full displacement vector."""
    m = np.concatenate((node_dofs_1based(i_node), node_dofs_1based(j_node)))
    return np.asarray(u_global, dtype=float)[m - 1]


def _parse_element_nodes(element_record):
    """
    Robustly extract (i_node, j_node) from one element record.

    Supported common formats:
    1) [TYPE, MATL, SECT, [i, j], ...]
    2) (TYPE, MATL, SECT, [i, j], ...)
    3) [i, j, ...]
    4) (i, j, ...)
    """
    if isinstance(element_record, (list, tuple)):
        if len(element_record) >= 4 and isinstance(element_record[3], (list, tuple)):
            return int(element_record[3][0]), int(element_record[3][1])
        if len(element_record) >= 2:
            return int(element_record[0]), int(element_record[1])
    raise ValueError(f"Cannot parse element nodes from record: {element_record}")


def _model_extent(nodes):
    coords = np.array([nodes[nid] for nid in sorted(nodes.keys())], dtype=float)
    if coords.ndim != 2 or coords.shape[1] < 3:
        raise ValueError("Nodes must be 3D coordinates.")
    spans = coords.max(axis=0) - coords.min(axis=0)
    return float(max(spans.max(), 1.0))


def suggest_deformation_scale(nodes, u_global, target_ratio=0.10):
    """Auto-select a deformation scale so the deformed shape is readable."""
    u_global = np.asarray(u_global, dtype=float)
    if u_global.size == 0:
        return 1.0

    u_xyz = u_global.reshape(-1, 6)[:, :3]
    max_disp = float(np.max(np.linalg.norm(u_xyz, axis=1)))
    if max_disp <= 0.0:
        return 1.0

    extent = _model_extent(nodes)
    return target_ratio * extent / max_disp


def suggest_load_scale(nodes, nodal_loads_xyz, target_ratio=0.12):
    """Auto-select a load-arrow scale for plotly cones."""
    if not nodal_loads_xyz:
        return 1.0

    max_load = 0.0
    for vec in nodal_loads_xyz.values():
        max_load = max(max_load, float(np.linalg.norm(np.asarray(vec, dtype=float))))

    if max_load <= 0.0:
        return 1.0

    extent = _model_extent(nodes)
    return target_ratio * extent / max_load


### --------- Solver-result adapter --------- ###


def _normalize_solver_result(solver_result):
    """
    Accept either:
    1) dict returned by the revised solver
    2) tuple/list like (K_global, u_global, f_global_complete)
    """
    if isinstance(solver_result, dict):
        return solver_result

    if isinstance(solver_result, (tuple, list)):
        if len(solver_result) < 3:
            raise ValueError(
                "solver_result tuple/list must contain at least "
                "(K_global, u_global, f_global_complete)."
            )
        return {
            "K_global": np.asarray(solver_result[0], dtype=float),
            "u_global": np.asarray(solver_result[1], dtype=float),
            "f_global_complete": np.asarray(solver_result[2], dtype=float),
        }

    raise TypeError("solver_result must be a dict or a tuple/list.")


### --------- Input reconstruction from json --------- ###


def _read_raw_inputs(filepath):
    nodes = interfaces.read_nodes(filepath)
    elements = interfaces.read_elements(filepath)
    constraints = interfaces.read_constraints(filepath)
    materials = interfaces.read_materials(filepath)
    sections = interfaces.read_sections(filepath)

    # These loaders may return full vectors or dictionaries depending on your implementation.
    F_global = interfaces.read_nodal_loads(filepath)
    element_loads = interfaces.read_element_loads(filepath)
    temperature_loads = interfaces.read_temperature_loads(filepath)
    fabrication_loads = interfaces.read_fabrication_errors(filepath)

    return {
        "nodes": nodes,
        "elements": elements,
        "constraints": constraints,
        "materials": materials,
        "sections": sections,
        "F_global": F_global,
        "element_loads": element_loads,
        "temperature_loads": temperature_loads,
        "fabrication_loads": fabrication_loads,
    }


def _vector_to_nodal_xyz(F_global, nodes):
    """Convert a full global nodal force vector to {node: (Fx,Fy,Fz)}."""
    if F_global is None:
        return {}

    # case 1: already a dict of node loads
    if isinstance(F_global, dict):
        nodal = {}
        for nid, values in F_global.items():
            vals = list(values)
            while len(vals) < 3:
                vals.append(0.0)
            nodal[int(nid)] = (float(vals[0]), float(vals[1]), float(vals[2]))
        return nodal

    # case 2: assembled full vector
    F = np.asarray(F_global, dtype=float).reshape(-1)
    nodal = {}
    for nid in sorted(nodes.keys()):
        dofs = node_dofs_1based(int(nid))
        nodal[int(nid)] = (
            float(F[dofs[0] - 1]),
            float(F[dofs[1] - 1]),
            float(F[dofs[2] - 1]),
        )
    return nodal


### --------- Element-level recovery --------- ###


def _build_element_cache(filepath):
    """Rebuild element-wise quantities needed by postprocess from the json model."""
    raw = _read_raw_inputs(filepath)
    nodes = raw["nodes"]
    elements = raw["elements"]
    materials = raw["materials"]
    sections = raw["sections"]
    element_loads = raw["element_loads"]
    temperature_loads = raw["temperature_loads"]
    fabrication_loads = raw["fabrication_loads"]

    element_paras = element.build_elements_para(nodes, elements, materials, sections)

    cache = {}
    for e_id in sorted(elements.keys()):
        rec = elements[e_id]
        i_node, j_node = _parse_element_nodes(rec)

        L, etype, E, G, A, Iy, Iz, J, mt, alpha = element_paras[e_id]
        gamma = element.build_gamma_3d(
            nodes[i_node],
            nodes[j_node],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)
        k_local = element.element_kl(E, G, A, Iy, Iz, J, L)

        elem_load_global = element_loads.get(e_id)

        Qf = np.asarray(
            preprocess.fef_cal_global(elem_load_global, T, L, angle_unit="deg"),
            dtype=float,
        )
        Qh = np.asarray(
            preprocess.heat_cal(temperature_loads.get(e_id), E, A, alpha),
            dtype=float,
        )
        Qe = np.asarray(
            preprocess.fabrication_error_cal(fabrication_loads.get(e_id), E, A, L),
            dtype=float,
        )
        Qt = Qf + Qh + Qe

        cache[e_id] = {
            "i_node": i_node,
            "j_node": j_node,
            "etype": etype,
            "L": float(L),
            "E": float(E),
            "A": float(A),
            "Iy": float(Iy),
            "Iz": float(Iz),
            "J": float(J),
            "alpha": float(alpha),
            "gamma": np.asarray(gamma, dtype=float),
            "T": np.asarray(T, dtype=float),
            "k_local": np.asarray(k_local, dtype=float),
            "Qf": Qf,
            "Qh": Qh,
            "Qe": Qe,
            "Qt": Qt,
            "map_1based": np.asarray(
                element.element_dof_map_1based(i_node, j_node),
                dtype=int,
            ),
        }

    return raw, cache


def recover_frame_element_results(filepath, u_global):
    """
    Recover 3D frame element local/global displacement vectors and local end actions.

    For each element:
        u_e_global = extracted 12x1 global displacement vector
        u_e_local  = T @ u_e_global
        q_local    = k_local @ u_e_local + Qt
    """
    u_global = np.asarray(u_global, dtype=float).reshape(-1)
    raw, cache = _build_element_cache(filepath)

    results = {}
    for e_id in sorted(cache.keys()):
        info = cache[e_id]
        i_node = info["i_node"]
        j_node = info["j_node"]
        L = info["L"]
        E = info["E"]
        A = info["A"]
        T = info["T"]
        k_local = info["k_local"]
        Qt = info["Qt"]

        u_e_global = extract_element_displacements(u_global, i_node, j_node)
        u_e_local = T @ u_e_global
        q_local = k_local @ u_e_local + Qt

        axial_delta = float(u_e_local[6] - u_e_local[0])
        axial_strain = axial_delta / L if abs(L) > 0.0 else 0.0
        axial_force = (E * A / L) * axial_delta if abs(L) > 0.0 else 0.0
        axial_stress = axial_force / A if abs(A) > 0.0 else 0.0

        results[e_id] = {
            **info,
            "u_e_global": u_e_global,
            "u_e_local": u_e_local,
            "q_local": q_local,
            "axial_delta": axial_delta,
            "axial_strain": axial_strain,
            "N": float(axial_force),
            "sigma": float(axial_stress),
        }

    return raw, results


def recover_truss_element_results(filepath, u_global):
    """
    Recover truss quantities using the same 12-dof frame-format quantities.

    This function reuses the generic frame-style recovery and keeps the original
    truss-facing API unchanged.
    """
    return recover_frame_element_results(filepath, u_global)


def build_truss_member_summary_df(results, units):
    rows = []
    for e_id in sorted(results.keys()):
        r = results[e_id]
        rows.append(
            {
                "element": int(e_id),
                "type": r["etype"],
                "i": int(r["i_node"]),
                "j": int(r["j_node"]),
                f"L ({units['dist']})": r["L"],
                f"Δu_local_x ({units['dist']})": r["axial_delta"],
                "axial strain": r["axial_strain"],
                f"N_tension (+) ({units['force']})": r["N"],
                f"sigma ({units['stress']})": r["sigma"],
            }
        )
    return pd.DataFrame(rows)


def build_truss_member_full_df(results, units):
    rows = []
    for e_id in sorted(results.keys()):
        r = results[e_id]
        row = {
            "element": int(e_id),
            "i": int(r["i_node"]),
            "j": int(r["j_node"]),
            f"L ({units['dist']})": r["L"],
            f"N_tension (+) ({units['force']})": r["N"],
            f"sigma ({units['stress']})": r["sigma"],
        }

        row.update(
            {
                f"u_g_{k + 1} ({units['dist'] if k in [0, 1, 2, 6, 7, 8] else 'rad'})": float(
                    r["u_e_global"][k]
                )
                for k in range(12)
            }
        )
        row.update(
            {
                f"u_l_{k + 1} ({units['dist'] if k in [0, 1, 2, 6, 7, 8] else 'rad'})": float(
                    r["u_e_local"][k]
                )
                for k in range(12)
            }
        )
        row.update(
            {
                f"q_l_{k + 1} ({units['force'] if k in [0, 1, 2, 6, 7, 8] else units['force'] + '*' + units['dist']})": float(
                    r["q_local"][k]
                )
                for k in range(12)
            }
        )

        rows.append(row)

    return pd.DataFrame(rows)


def build_frame_member_summary_df(results, units):
    rows = []
    force_unit = units["force"]
    moment_unit = f"{units['force']}*{units['dist']}"

    for e_id in sorted(results.keys()):
        r = results[e_id]
        q = r["q_local"]
        rows.append(
            {
                "element": int(e_id),
                "type": r["etype"],
                "i": int(r["i_node"]),
                "j": int(r["j_node"]),
                f"L ({units['dist']})": r["L"],
                f"Δu_local_x ({units['dist']})": r["axial_delta"],
                "axial strain": r["axial_strain"],
                f"N ({force_unit})": r["N"],
                f"sigma ({units['stress']})": r["sigma"],
                f"Fx_i ({force_unit})": float(q[0]),
                f"Fy_i ({force_unit})": float(q[1]),
                f"Fz_i ({force_unit})": float(q[2]),
                f"Mx_i ({moment_unit})": float(q[3]),
                f"My_i ({moment_unit})": float(q[4]),
                f"Mz_i ({moment_unit})": float(q[5]),
                f"Fx_j ({force_unit})": float(q[6]),
                f"Fy_j ({force_unit})": float(q[7]),
                f"Fz_j ({force_unit})": float(q[8]),
                f"Mx_j ({moment_unit})": float(q[9]),
                f"My_j ({moment_unit})": float(q[10]),
                f"Mz_j ({moment_unit})": float(q[11]),
            }
        )
    return pd.DataFrame(rows)


def build_frame_member_full_df(results, units):
    rows = []
    for e_id in sorted(results.keys()):
        r = results[e_id]
        row = {
            "element": int(e_id),
            "type": r["etype"],
            "i": int(r["i_node"]),
            "j": int(r["j_node"]),
            f"L ({units['dist']})": r["L"],
            f"Δu_local_x ({units['dist']})": r["axial_delta"],
            "axial strain": r["axial_strain"],
            f"N ({units['force']})": r["N"],
            f"sigma ({units['stress']})": r["sigma"],
        }

        row.update(
            {
                f"u_g_{k + 1} ({units['dist'] if k in [0, 1, 2, 6, 7, 8] else 'rad'})": float(
                    r["u_e_global"][k]
                )
                for k in range(12)
            }
        )
        row.update(
            {
                f"u_l_{k + 1} ({units['dist'] if k in [0, 1, 2, 6, 7, 8] else 'rad'})": float(
                    r["u_e_local"][k]
                )
                for k in range(12)
            }
        )
        row.update(
            {
                f"q_l_{k + 1} ({units['force'] if k in [0, 1, 2, 6, 7, 8] else units['force'] + '*' + units['dist']})": float(
                    r["q_local"][k]
                )
                for k in range(12)
            }
        )

        rows.append(row)

    return pd.DataFrame(rows)


### --------- Node-level results --------- ###


def build_node_displacement_df(nodes, u_global, units):
    u_global = np.asarray(u_global, dtype=float).reshape(-1)
    rows = []
    for nid in sorted(nodes.keys()):
        x, y, z = nodes[nid]
        dofs = node_dofs_1based(int(nid))

        ux, uy, uz, rx, ry, rz = [float(u_global[d - 1]) for d in dofs]
        umag = float(np.linalg.norm([ux, uy, uz]))

        rows.append(
            {
                "node": int(nid),
                f"x ({units['dist']})": float(x),
                f"y ({units['dist']})": float(y),
                f"z ({units['dist']})": float(z),
                f"ux ({units['dist']})": ux,
                f"uy ({units['dist']})": uy,
                f"uz ({units['dist']})": uz,
                "rx (rad)": rx,
                "ry (rad)": ry,
                "rz (rad)": rz,
                f"|u| ({units['dist']})": umag,
            }
        )

    return pd.DataFrame(rows)


def build_max_displacement_summary(df_disp, units):
    mag_col = f"|u| ({units['dist']})"
    ux_col = f"ux ({units['dist']})"
    uy_col = f"uy ({units['dist']})"
    uz_col = f"uz ({units['dist']})"

    rows = []
    i_mag = df_disp[mag_col].abs().idxmax()
    rows.append(
        {
            "metric": "max |u|",
            "node": int(df_disp.loc[i_mag, "node"]),
            f"value ({units['dist']})": float(df_disp.loc[i_mag, mag_col]),
            ux_col: float(df_disp.loc[i_mag, ux_col]),
            uy_col: float(df_disp.loc[i_mag, uy_col]),
            uz_col: float(df_disp.loc[i_mag, uz_col]),
        }
    )

    for col in [ux_col, uy_col, uz_col]:
        idx = df_disp[col].abs().idxmax()
        rows.append(
            {
                "metric": f"max |{col.split()[0]}|",
                "node": int(df_disp.loc[idx, "node"]),
                f"value ({units['dist']})": float(df_disp.loc[idx, col]),
                ux_col: float(df_disp.loc[idx, ux_col]),
                uy_col: float(df_disp.loc[idx, uy_col]),
                uz_col: float(df_disp.loc[idx, uz_col]),
            }
        )

    return pd.DataFrame(rows)


def build_reaction_df(constraints, f_global_complete, units):
    """
    Build reaction force DataFrame from constraint definitions.
    """
    force_unit = units.get("force", units.get("FORCE", ""))
    dist_unit = units.get("dist", units.get("DIST", ""))

    dof_names = ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]
    col_labels = {
        "Ux": f"Fx ({force_unit})",
        "Uy": f"Fy ({force_unit})",
        "Uz": f"Fz ({force_unit})",
        "Rx": f"Mx ({force_unit}*{dist_unit})",
        "Ry": f"My ({force_unit}*{dist_unit})",
        "Rz": f"Mz ({force_unit}*{dist_unit})",
    }

    rows = []

    for node in sorted(constraints.keys()):
        restrained_dofs = constraints[node]
        restrained_set = {str(x).strip() for x in restrained_dofs}

        row = {"node": node}
        has_reaction = False

        for local_idx, dof_name in enumerate(dof_names):
            if dof_name in restrained_set:
                global_dof_1based = 6 * (node - 1) + (local_idx + 1)
                row[col_labels[dof_name]] = float(
                    f_global_complete[global_dof_1based - 1]
                )
                has_reaction = True

        if has_reaction:
            rows.append(row)

    return pd.DataFrame(rows)


### --------- 3D frame shape functions --------- ###


def axial_shape_functions(x, L):
    """Linear shape functions for local axial displacement u(x)."""
    x = np.asarray(x, dtype=float)
    N1 = 1.0 - x / L
    N2 = x / L
    return N1, N2


def cubic_shape_functions(x, L):
    """Cubic Hermite shape functions for local transverse displacement."""
    x = np.asarray(x, dtype=float)
    xi = x / L

    H1 = 1.0 - 3.0 * xi**2 + 2.0 * xi**3
    H2 = L * (xi - 2.0 * xi**2 + xi**3)
    H3 = 3.0 * xi**2 - 2.0 * xi**3
    H4 = L * (-(xi**2) + xi**3)

    return H1, H2, H3, H4


def frame_shape_functions_3d(x, L, use_minus_for_ry=True):
    """
    Build the 3x12 centerline interpolation matrix N(x) for a 3D frame element.

    Local dof order
    ---------------
    [u_i, v_i, w_i, thx_i, thy_i, thz_i,
     u_j, v_j, w_j, thx_j, thy_j, thz_j]

    Returns
    -------
    ndarray
        - shape (3, 12) if x is scalar
        - shape (n, 3, 12) if x is an array
    """
    x = np.asarray(x, dtype=float)
    scalar_input = x.ndim == 0
    x = np.atleast_1d(x)

    Na1, Na2 = axial_shape_functions(x, L)
    H1, H2, H3, H4 = cubic_shape_functions(x, L)
    sign = -1.0 if use_minus_for_ry else 1.0

    N = np.zeros((x.size, 3, 12), dtype=float)

    # u(x)
    N[:, 0, 0] = Na1
    N[:, 0, 6] = Na2

    # v(x) in local y direction, coupled with thz
    N[:, 1, 1] = H1
    N[:, 1, 5] = H2
    N[:, 1, 7] = H3
    N[:, 1, 11] = H4

    # w(x) in local z direction, coupled with thy
    N[:, 2, 2] = H1
    N[:, 2, 4] = sign * H2
    N[:, 2, 8] = H3
    N[:, 2, 10] = sign * H4

    if scalar_input:
        return N[0]
    return N


def frame_centerline_local_3d(x, L, d_local, use_minus_for_ry=True):
    """
    Interpolate the 3D frame centerline displacement in the local system.

    Returns
    -------
    u, v, w, thx : ndarray
        Local axial displacement, two transverse displacements,
        and interpolated torsional rotation.
    """
    d_local = np.asarray(d_local, dtype=float).reshape(12)
    N = frame_shape_functions_3d(x, L, use_minus_for_ry=use_minus_for_ry)

    if N.ndim == 2:
        uvw = N @ d_local
        u = np.asarray(uvw[0], dtype=float)
        v = np.asarray(uvw[1], dtype=float)
        w = np.asarray(uvw[2], dtype=float)
    else:
        uvw = np.einsum("nij,j->ni", N, d_local)
        u = uvw[:, 0]
        v = uvw[:, 1]
        w = uvw[:, 2]

    x = np.asarray(x, dtype=float)
    Na1, Na2 = axial_shape_functions(x, L)
    thx = Na1 * d_local[3] + Na2 * d_local[9]

    return u, v, w, thx


def _local_points_to_global(points_local, origin_global, gamma):
    """Convert local point rows to global coordinates using gamma."""
    points_local = np.asarray(points_local, dtype=float)
    origin_global = np.asarray(origin_global, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    return origin_global + points_local @ gamma


### --------- Plotting --------- ###


def _plot_line_model(
    nodes,
    elements,
    constraints=None,
    nodal_loads_xyz=None,
    show_node_ids=True,
    show_member_ids=False,
    load_scale=None,
    title="3D Model",
):
    """Shared undeformed-model plot for both truss and frame."""
    if load_scale is None:
        load_scale = suggest_load_scale(nodes, nodal_loads_xyz)

    fig = go.Figure()

    xs, ys, zs = [], [], []
    mid_x, mid_y, mid_z, mid_txt = [], [], [], []
    for e_id in sorted(elements.keys()):
        i_node, j_node = _parse_element_nodes(elements[e_id])
        xi, yi, zi = nodes[i_node]
        xj, yj, zj = nodes[j_node]

        xs += [xi, xj, None]
        ys += [yi, yj, None]
        zs += [zi, zj, None]

        if show_member_ids:
            mid_x.append((xi + xj) / 2.0)
            mid_y.append((yi + yj) / 2.0)
            mid_z.append((zi + zj) / 2.0)
            mid_txt.append(str(e_id))

    fig.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="lines",
            line=dict(width=4),
            name="Members",
        )
    )

    if show_member_ids and mid_txt:
        fig.add_trace(
            go.Scatter3d(
                x=mid_x,
                y=mid_y,
                z=mid_z,
                mode="text",
                text=mid_txt,
                name="Member IDs",
            )
        )

    nx = [nodes[nid][0] for nid in sorted(nodes.keys())]
    ny = [nodes[nid][1] for nid in sorted(nodes.keys())]
    nz = [nodes[nid][2] for nid in sorted(nodes.keys())]
    nt = [str(nid) for nid in sorted(nodes.keys())]

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
                text=nt,
                textposition="top center",
                name="Node IDs",
            )
        )

    if constraints:
        sx, sy, sz = [], [], []
        for nid, flags in constraints.items():
            restrained_set = {str(v).strip().lower() for v in flags}
            if any(dof in restrained_set for dof in ["ux", "uy", "uz"]):
                x, y, z = nodes[nid]
                sx.append(x)
                sy.append(y)
                sz.append(z)

        if sx:
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

    if nodal_loads_xyz:
        lx, ly, lz, u, v, w = [], [], [], [], [], []
        for nid in sorted(nodal_loads_xyz.keys()):
            Fx, Fy, Fz = nodal_loads_xyz[nid]
            if np.linalg.norm([Fx, Fy, Fz]) <= 0.0:
                continue
            x, y, z = nodes[nid]
            lx.append(x)
            ly.append(y)
            lz.append(z)
            u.append(load_scale * Fx)
            v.append(load_scale * Fy)
            w.append(load_scale * Fz)

        if lx:
            fig.add_trace(
                go.Cone(
                    x=lx,
                    y=ly,
                    z=lz,
                    u=u,
                    v=v,
                    w=w,
                    anchor="tail",
                    sizemode="absolute",
                    sizeref=0.2,
                    showscale=False,
                    name="Loads",
                )
            )

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=True,
    )

    fig.show()
    return fig


def plot_truss_model(
    nodes,
    elements,
    constraints=None,
    nodal_loads_xyz=None,
    show_node_ids=True,
    show_member_ids=False,
    load_scale=None,
):
    """Plot undeformed truss model, supports, and nodal loads."""
    return _plot_line_model(
        nodes,
        elements,
        constraints=constraints,
        nodal_loads_xyz=nodal_loads_xyz,
        show_node_ids=show_node_ids,
        show_member_ids=show_member_ids,
        load_scale=load_scale,
        title="3D Truss Model",
    )


def plot_frame_model(
    nodes,
    elements,
    constraints=None,
    nodal_loads_xyz=None,
    show_node_ids=True,
    show_member_ids=False,
    load_scale=None,
):
    """Plot undeformed frame model, supports, and nodal loads."""
    return _plot_line_model(
        nodes,
        elements,
        constraints=constraints,
        nodal_loads_xyz=nodal_loads_xyz,
        show_node_ids=show_node_ids,
        show_member_ids=show_member_ids,
        load_scale=load_scale,
        title="3D Frame Model",
    )


def plot_truss_deformation(nodes, elements, u_global, scale=None):
    """Plot undeformed and deformed truss geometry."""
    if scale is None:
        scale = suggest_deformation_scale(nodes, u_global)

    u_global = np.asarray(u_global, dtype=float).reshape(-1)

    fig = go.Figure()

    x0, y0, z0 = [], [], []
    xd, yd, zd = [], [], []

    for e_id in sorted(elements.keys()):
        i_node, j_node = _parse_element_nodes(elements[e_id])
        xi, yi, zi = nodes[i_node]
        xj, yj, zj = nodes[j_node]

        ui = u_global[6 * (i_node - 1) : 6 * (i_node - 1) + 6]
        uj = u_global[6 * (j_node - 1) : 6 * (j_node - 1) + 6]

        x0 += [xi, xj, None]
        y0 += [yi, yj, None]
        z0 += [zi, zj, None]

        xd += [xi + scale * ui[0], xj + scale * uj[0], None]
        yd += [yi + scale * ui[1], yj + scale * uj[1], None]
        zd += [zi + scale * ui[2], zj + scale * uj[2], None]

    fig.add_trace(
        go.Scatter3d(
            x=x0,
            y=y0,
            z=z0,
            mode="lines",
            name="Original",
            line=dict(width=4, color="blue"),
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=xd,
            y=yd,
            z=zd,
            mode="lines",
            name="Deformed",
            line=dict(width=4, color="red"),
        )
    )

    fig.update_layout(
        title=f"Original and Deformed Truss (scale = {scale:.3g})",
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    fig.show()
    return fig


def plot_frame_deformation(
    nodes,
    elements,
    u_global,
    scale=None,
    npts=100,
    use_minus_for_ry=True,
):
    """Plot undeformed and deformed 3D frame geometry with cubic centerline interpolation."""
    if scale is None:
        scale = suggest_deformation_scale(nodes, u_global)

    u_global = np.asarray(u_global, dtype=float).reshape(-1)

    fig = go.Figure()

    x0, y0, z0 = [], [], []
    xd, yd, zd = [], [], []

    for e_id in sorted(elements.keys()):
        i_node, j_node = _parse_element_nodes(elements[e_id])
        Xi = np.asarray(nodes[i_node], dtype=float)
        Xj = np.asarray(nodes[j_node], dtype=float)
        L = float(np.linalg.norm(Xj - Xi))

        gamma = element.build_gamma_3d(
            nodes[i_node],
            nodes[j_node],
            psi=0.0,
            angle_unit="deg",
        )
        T = element.frame_transformation_matrix(gamma)

        d_global = extract_element_displacements(u_global, i_node, j_node)
        d_local = T @ d_global

        x_local = np.linspace(0.0, L, npts)
        u_loc, v_loc, w_loc, _ = frame_centerline_local_3d(
            x_local,
            L,
            d_local,
            use_minus_for_ry=use_minus_for_ry,
        )

        p0_local = np.column_stack(
            [
                x_local,
                np.zeros_like(x_local),
                np.zeros_like(x_local),
            ]
        )
        p1_local = np.column_stack(
            [
                x_local + scale * u_loc,
                scale * v_loc,
                scale * w_loc,
            ]
        )

        p0_global = _local_points_to_global(p0_local, Xi, gamma)
        p1_global = _local_points_to_global(p1_local, Xi, gamma)

        x0 += list(p0_global[:, 0]) + [None]
        y0 += list(p0_global[:, 1]) + [None]
        z0 += list(p0_global[:, 2]) + [None]

        xd += list(p1_global[:, 0]) + [None]
        yd += list(p1_global[:, 1]) + [None]
        zd += list(p1_global[:, 2]) + [None]

    fig.add_trace(
        go.Scatter3d(
            x=x0,
            y=y0,
            z=z0,
            mode="lines",
            name="Original",
            line=dict(width=4, color="blue"),
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=xd,
            y=yd,
            z=zd,
            mode="lines",
            name="Deformed",
            line=dict(width=4, color="red"),
        )
    )

    fig.update_layout(
        title=f"Original and Deformed Frame (scale = {scale:.3g})",
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    fig.show()
    return fig


### --------- Main integrated output --------- ###


def truss_output(
    filepath,
    solver_result,
    deformation_scale=None,
    load_scale=None,
    show_node_ids=True,
    show_member_ids=False,
    show=True,
    table_output=None,
):
    """
    Integrated truss postprocess entry.
    """
    solver_result = _normalize_solver_result(solver_result)
    units = _read_units(filepath)

    raw, member_results = recover_truss_element_results(
        filepath,
        solver_result["u_global"],
    )

    nodes = raw["nodes"]
    elements = raw["elements"]
    constraints = raw["constraints"]
    nodal_loads_xyz = _vector_to_nodal_xyz(raw["F_global"], nodes)

    df_node_disp = build_node_displacement_df(nodes, solver_result["u_global"], units)
    df_disp_summary = build_max_displacement_summary(df_node_disp, units)
    df_reactions = build_reaction_df(
        constraints,
        solver_result.get("f_global_complete"),
        units,
    )
    df_member_summary = build_truss_member_summary_df(member_results, units)
    df_member_full = build_truss_member_full_df(member_results, units)

    fig_model = None
    fig_deformation = None
    xlsx_path = None

    if table_output not in (None, "None", "xlsx"):
        raise ValueError("table_output must be 'xlsx', None, or 'None'.")

    if table_output == "xlsx":
        tables = [
            ("Node Displacements", df_node_disp),
            ("Maximum Displacement Summary", df_disp_summary),
            ("Reaction Forces", df_reactions),
            ("Member Summary", df_member_summary),
            ("Member Full Results", df_member_full),
        ]
        xlsx_path = _export_tables_to_excel(filepath, tables)

    if show:
        fig_model = plot_truss_model(
            nodes,
            elements,
            constraints=constraints,
            nodal_loads_xyz=nodal_loads_xyz,
            show_node_ids=show_node_ids,
            show_member_ids=show_member_ids,
            load_scale=load_scale,
        )
        fig_deformation = plot_truss_deformation(
            nodes,
            elements,
            solver_result["u_global"],
            scale=deformation_scale,
        )

    show_tables = show and (table_output not in ("xlsx",))

    if show_tables:
        _show_df(df_node_disp, decimals=6)
        _show_df(df_disp_summary, decimals=6)
        if not df_reactions.empty:
            _show_df(df_reactions, decimals=6)
        _show_df(df_member_summary, decimals=6)
        _show_df(df_member_full, decimals=6)

    return {
        "fig_model": fig_model,
        "fig_deformation": fig_deformation,
        "df_node_disp": df_node_disp,
        "df_disp_summary": df_disp_summary,
        "df_reactions": df_reactions,
        "df_member_summary": df_member_summary,
        "df_member_full": df_member_full,
        "member_results": member_results,
        "units": units,
        "xlsx_path": xlsx_path,
    }


def frame_output(
    filepath,
    solver_result,
    deformation_scale=None,
    load_scale=None,
    show_node_ids=True,
    show_member_ids=False,
    show=True,
    table_output=None,
    npts=100,
    use_minus_for_ry=True,
):
    """
    Integrated frame postprocess entry.

    This function mirrors truss_output, but the deformed geometry is generated
    with 3D frame shape functions so member bending is visible in the plot.
    """
    solver_result = _normalize_solver_result(solver_result)
    units = _read_units(filepath)

    raw, member_results = recover_frame_element_results(
        filepath,
        solver_result["u_global"],
    )

    nodes = raw["nodes"]
    elements = raw["elements"]
    constraints = raw["constraints"]
    nodal_loads_xyz = _vector_to_nodal_xyz(raw["F_global"], nodes)

    df_node_disp = build_node_displacement_df(nodes, solver_result["u_global"], units)
    df_disp_summary = build_max_displacement_summary(df_node_disp, units)
    df_reactions = build_reaction_df(
        constraints,
        solver_result.get("f_global_complete"),
        units,
    )
    df_member_summary = build_frame_member_summary_df(member_results, units)
    df_member_full = build_frame_member_full_df(member_results, units)

    fig_model = None
    fig_deformation = None
    xlsx_path = None

    if table_output not in (None, "None", "xlsx"):
        raise ValueError("table_output must be 'xlsx', None, or 'None'.")

    if table_output == "xlsx":
        tables = [
            ("Node Displacements", df_node_disp),
            ("Maximum Displacement Summary", df_disp_summary),
            ("Reaction Forces", df_reactions),
            ("Frame Member Summary", df_member_summary),
            ("Frame Member Full Results", df_member_full),
        ]
        xlsx_path = _export_tables_to_excel(filepath, tables)

    if show:
        fig_model = plot_frame_model(
            nodes,
            elements,
            constraints=constraints,
            nodal_loads_xyz=nodal_loads_xyz,
            show_node_ids=show_node_ids,
            show_member_ids=show_member_ids,
            load_scale=load_scale,
        )
        fig_deformation = plot_frame_deformation(
            nodes,
            elements,
            solver_result["u_global"],
            scale=deformation_scale,
            npts=npts,
            use_minus_for_ry=use_minus_for_ry,
        )

    show_tables = show and (table_output not in ("xlsx",))

    if show_tables:
        _show_df(df_node_disp, decimals=6)
        _show_df(df_disp_summary, decimals=6)
        if not df_reactions.empty:
            _show_df(df_reactions, decimals=6)
        _show_df(df_member_summary, decimals=6)
        _show_df(df_member_full, decimals=6)

    return {
        "fig_model": fig_model,
        "fig_deformation": fig_deformation,
        "df_node_disp": df_node_disp,
        "df_disp_summary": df_disp_summary,
        "df_reactions": df_reactions,
        "df_member_summary": df_member_summary,
        "df_member_full": df_member_full,
        "member_results": member_results,
        "units": units,
        "xlsx_path": xlsx_path,
    }
