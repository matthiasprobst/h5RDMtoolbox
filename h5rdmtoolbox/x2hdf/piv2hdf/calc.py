import numpy as np


# import scipy.interpolate as interp


def compute_z_derivative_of_z_velocity(dudx, dvdy):
    """
    Computes dwdz from solving continuity equation:
        div(v) = 0
    This is only valid for incompressible flows (=0 on right side of equation)!

    Parameters
    ----------
    dudx : array_like
        derivative of x-velociy u by x
    dvdy : array_like
        derivative of y-velocity v for y

    Returns
    -------
    dwdz : array_like
        derivative of z-velocity w for z
    """
    return -dudx[:] - dvdy[:]


def vorticity_z(u, v, x, y):
    """
    2D-vorticity computed by x- and y-velocity u and v
    """
    dudy = np.gradient(u, y, x)[0]
    dvdx = np.gradient(v, y, x)[1]
    return dvdx - dudy
