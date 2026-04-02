import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

x = np.array([1, 2])
T1 = np.array([[2, 0],[0, 1]])
T2 = np.array([[0, -3],[3, 0]])
T3 = np.array([[1, 1],[0, 1]])

y1, y2, y3 = T1@x, T2@x, T3@x

fig, ax = plt.subplots(figsize=(8, 3.6))
ax.axhline(0, linewidth=1.5)
ax.axvline(0, linewidth=1.5)
ax.grid(True)
ax.set_aspect('equal', adjustable='box')

pts = np.vstack([x, y1, y2, y3])
xmin, ymin = pts.min(axis=0) - 3
xmax, ymax = pts.max(axis=0) + 3
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

def draw_vec(v, color, label, offset=(10,10)):
    # arrow
    ax.annotate(
        "", xy=v, xytext=(0, 0),
        arrowprops=dict(arrowstyle="->", lw=2, color=color)
    )
    # label with pixel offset
    ax.annotate(
        label, xy=v, xycoords="data",
        xytext=offset, textcoords="offset points",
        color=color, fontsize=11,
        ha="left" if offset[0] >= 0 else "right",
        va="bottom" if offset[1] >= 0 else "top"
    )

# 关键：给容易重叠的标签不同 offset
draw_vec(x,  "black",  "x",           offset=(8, 8))
draw_vec(y1, "red",    "y1 = T1 x",    offset=(10, 0))
draw_vec(y3, "purple", "y3 = T3 x",    offset=(10, 14))  # 往上挪一点
draw_vec(y2, "green",  "y2 = T2 x",    offset=(-10, 10)) # 往左上

ax.set_title("2D Linear Transformations (Single Axes)")

handles = [
    Line2D([0],[0], color="black", lw=6, label="x"),
    Line2D([0],[0], color="red",   lw=6, label="y1 = T1 x"),
    Line2D([0],[0], color="green", lw=6, label="y2 = T2 x"),
    Line2D([0],[0], color="purple",lw=6, label="y3 = T3 x"),
]
ax.legend(handles=handles, loc="upper right")

plt.tight_layout()
plt.show()
