# Answer

Local element force-displacement relationship:

$$
\boldsymbol{Q} = \boldsymbol{k}\boldsymbol{u} + \boldsymbol{Q}^F
$$

For the beam element,

$$
Q_2 = \frac{EI}{L^3}\left(12u_2 + 6Lu_3 - 12u_5 + 6Lu_6\right) + Q_{yb}^F
$$

$$
Q_3 = \frac{EI}{L^3}\left(6Lu_2 + 4L^2u_3 - 6Lu_5 + 2L^2u_6\right) + Q_{mb}^F
$$

$$
Q_5 = \frac{EI}{L^3}\left(-12u_2 - 6Lu_3 + 12u_5 - 6Lu_6\right) + Q_{ye}^F
$$

$$
Q_6 = \frac{EI}{L^3}\left(6Lu_2 + 2L^2u_3 - 6Lu_5 + 4L^2u_6\right) + Q_{me}^F
$$

Because the two ends are pinned, the moments there must be zero:

$$
Q_3 = 0, \qquad Q_6 = 0
$$

Thus,

$$
\begin{cases}
0 = 6Lu_2 + 4L^2u_3 - 6Lu_5 + 2L^2u_6 + \dfrac{L^3}{EI}Q_{mb}^F \\[6pt]
0 = 6Lu_2 + 2L^2u_3 - 6Lu_5 + 4L^2u_6 + \dfrac{L^3}{EI}Q_{me}^F
\end{cases}
$$

Subtracting the two equations gives

$$
2L^2u_3 - 2L^2u_6 + \frac{L^3}{EI}\left(Q_{mb}^F - Q_{me}^F\right) = 0
$$

therefore

$$
u_3 = u_6 - \frac{L}{2EI}\left(Q_{mb}^F - Q_{me}^F\right)
$$

Substituting this into the first equation,

$$
0 = 6Lu_2 + 4L^2u_6 - \frac{2L^3}{EI}\left(Q_{mb}^F - Q_{me}^F\right) - 6Lu_5 + 2L^2u_6 + \frac{L^3}{EI}Q_{mb}^F
$$

$$
-6L^2u_6 = 6L(u_2-u_5) + \frac{L^3}{EI}\left(2Q_{me}^F - Q_{mb}^F\right)
$$

therefore,

$$
u_6 = -\frac{1}{L}(u_2-u_5) - \frac{L}{6EI}\left(2Q_{me}^F - Q_{mb}^F\right)
$$

therefore,

$$
u_3 = -\frac{1}{L}(u_2-u_5) - \frac{L}{6EI}\left(2Q_{mb}^F - Q_{me}^F\right)
$$

Adding the two expressions,

$$
u_3 + u_6 = -\frac{2}{L}(u_2-u_5) - \frac{L}{6EI}\left(Q_{mb}^F + Q_{me}^F\right)
$$

so that

$$
6L(u_3+u_6) = -12(u_2-u_5) - \frac{L^2}{EI}\left(Q_{mb}^F + Q_{me}^F\right)
$$

Now substitute into the expression for $Q_2$:

$$
\begin{aligned}
Q_2
&= \frac{EI}{L^3}\left(12(u_2-u_5) + 6L(u_3+u_6)\right) + Q_{yb}^F \\
&= \frac{EI}{L^3}\left(12(u_2-u_5) - 12(u_2-u_5) - \frac{L^2}{EI}\left(Q_{mb}^F + Q_{me}^F\right)\right) + Q_{yb}^F \\
&= Q_{yb}^F - \frac{1}{L}\left(Q_{mb}^F + Q_{me}^F\right)
\end{aligned}
$$

Therefore, $Q_2$ contains only fixed-end-force terms and does not depend on $EI$.
