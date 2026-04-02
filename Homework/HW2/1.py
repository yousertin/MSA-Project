import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

x = np.array([1, 2])
T1 = np.array([[2, 0],[0, 1]])
T2 = np.array([[0, -3],[3, 0]])
T3 = np.array([[1, 1],[0, 1]])

y1, y2, y3 = T1@x, T2@x, T3@x

A = np.array([[1, -2],[0, 3],[4, 1],[-1, 2]])
B = np.array([[2, 0, -1, 3, 1],[-2, 4, 5, 0, -3]])
C = A@B
print(C)