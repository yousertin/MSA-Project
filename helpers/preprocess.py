import numpy as np


def FEF_cal(load_type, Fx, Fy, M, L):

    if load_type == "p":
        f_local = np.array([
            -Fx / 2.0,
            3.0 * M / (2.0 * L) - Fy / 2.0,
            M / 4.0 - Fy * L / 8.0,
            -Fx / 2.0,
            -3.0 * M / (2.0 * L) - Fy / 2.0,
            M / 4.0 + Fy * L / 8.0
        ], dtype=float)

    elif load_type == "d":
        f_local = np.array([
            -Fx * L / 2.0,
            M - Fy * L / 2.0,
            -Fy * L**2 / 12.0,
            -Fx * L / 2.0,
            -M - Fy * L / 2.0,
            Fy * L**2 / 12.0
        ], dtype=float)

    else:
        raise ValueError('load_type must be "p" or "d".')

    Fx_i, Fy_i, M_i, Fx_j, Fy_j, M_j = f_local

    FEF_loaded = np.array([Fx_i, Fy_i, M_i, Fx_j, Fy_j, M_j])

    return FEF_loaded


def moment_release(MT, k, Q):
    k_mod = k.copy()
    Q_mod = Q.copy()

    if MT == 0:
        pass
    elif MT == 1:
        k_mod[2, :] = 0
        k_mod[:, 2] = 0
        Q_mod[2] = 0
    elif MT == 2:
        k_mod[5, :] = 0
        k_mod[:, 5] = 0
        Q_mod[5] = 0
    elif MT == 3:
        k_mod[2, :] = 0
        k_mod[:, 2] = 0
        Q_mod[2] = 0
        k_mod[5, :] = 0
        k_mod[:, 5] = 0
        Q_mod[5] = 0
    else:
        raise ValueError("MT can only take the values 0, 1, 2, or 3")

    return k_mod, Q_mod
