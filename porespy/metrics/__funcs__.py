import scipy as sp
from skimage.segmentation import clear_border
import scipy.ndimage as spim
import scipy.spatial as sptl


def porosity(im):
    r"""
    Calculates the porosity of an image as the number of non-zeros (assumed to
    be void space) divided by the total number of voxels in the image.
    """
    e = sp.sum(im > 0)/im.size
    return e


def two_point_correlation_bf(im, spacing=10):
    r"""
    Calculates the two-point correlation function using brute-force (see Notes)

    Parameters
    ----------
    im : ND-array
        The image of the void space on which the 2-point correlation is desired

    spacing : int
        The space between points on the regular grid that is used to generate
        the correlation (see Notes)

    Returns
    -------
    A tuple containing the x and y data for plotting the two-point correlation
    function.  The x array is the distances between points and the y array is
    corresponding probabilities that points of a given distance both lie in the
    void space.  The distance values are binned as follows:

        bins = range(start=0, stop=sp.amin(im.shape)/2, stride=spacing)

    Notes
    -----
    The brute-force approach means overlaying a grid of equally spaced points
    onto the image, calculating the distance between each and every pair of
    points, then counting the instances where both pairs lie in the void space.
    """
    if im.ndim == 2:
        pts = sp.meshgrid(range(0, im.shape[0], spacing),
                          range(0, im.shape[1], spacing))
        crds = sp.vstack([pts[0].flatten(),
                          pts[1].flatten()]).T
    elif im.ndim == 3:
        pts = sp.meshgrid(range(0, im.shape[0], spacing),
                          range(0, im.shape[1], spacing),
                          range(0, im.shape[2], spacing))
        crds = sp.vstack([pts[0].flatten(),
                          pts[1].flatten(),
                          pts[2].flatten()]).T
    dmat = sptl.distance.cdist(XA=crds, XB=crds)
    hits = im[pts].flatten()
    dmat = dmat[hits, :]
    h1 = sp.histogram(dmat, bins=range(0, int(sp.amin(im.shape)/2), spacing))
    dmat = dmat[:, hits]
    h2 = sp.histogram(dmat, bins=h1[1])
    h2 = (h2[1][:-1], h2[0]/h1[0])
    return h2


def apply_chords(im, spacing=0, axis=0, trim_edges=True):
    r"""
    Adds chords to the void space in the specified direction.  The chords are
    separated by 1 voxels plus the provided spacing.

    Parameters
    ----------
    im : ND-array
        A 2D image of the porous material with void marked as True.

    spacing : int (default = 0)
        Chords are automatically separated by 1 voxel and this argument
        increases
        the separation.

    axis : int (default = 0)
        The axis along which the chords are drawn.

    trim_edges : bool (default = True)
        Whether or not to remove chords that touch the edges of the image.
        These chords are artifically shortened, so skew the chord length
        distribution

    Returns
    -------
    An ND-array of the same size as ```im``` with True values indicating the
    chords.

    See Also
    --------
    apply_chords_3D

    """
    if spacing < 0:
        raise Exception('Spacing cannot be less than 0')
    dims1 = sp.arange(0, im.ndim)
    dims2 = sp.copy(dims1)
    dims2[axis] = 0
    dims2[0] = axis
    im = sp.moveaxis(a=im, source=dims1, destination=dims2)
    im = sp.atleast_3d(im)
    ch = sp.zeros_like(im, dtype=bool)
    ch[:, ::4+2*spacing, ::4+2*spacing] = 1
    chords = im*ch
    chords = sp.squeeze(chords)
    if trim_edges:
        temp = clear_border(spim.label(chords == 1)[0]) > 0
        chords = temp*chords
    chords = sp.moveaxis(a=chords, source=dims1, destination=dims2)
    return chords


def apply_chords_3D(im, spacing=0, trim_edges=True):
    r"""
    Adds chords to the void space in all three principle directions.  The
    chords are seprated by 1 voxel plus the provided spacing.  Chords in the X,
    Y and Z directions are labelled 1, 2 and 3 resepctively.

    Parameters
    ----------
    im : ND-array
        A 3D image of the porous material with void space marked as True.

    spacing : int (default = 0)
        Chords are automatically separed by 1 voxel on all sides, and this
        argument increases the separation.

    trim_edges : bool (default = True)
        Whether or not to remove chords that touch the edges of the image.
        These chords are artifically shortened, so skew the chord length
        distribution

    Returns
    -------
    An ND-array of the same size as ```im``` with values of 1 indicating
    x-direction chords, 2 indicating y-direction chords, and 3 indicating
    z-direction chords.

    """
    if im.ndim < 3:
        raise Exception('Must be a 3D image to use this function')
    if spacing < 0:
        raise Exception('Spacing cannot be less than 0')
    ch = sp.zeros_like(im, dtype=int)
    ch[:, ::4+2*spacing, ::4+2*spacing] = 1  # X-direction
    ch[::4+2*spacing, :, 2::4+2*spacing] = 2  # Y-direction
    ch[2::4+2*spacing, 2::4+2*spacing, :] = 3  # Z-direction
    chords = ch*im
    if trim_edges:
        temp = clear_border(spim.label(chords > 0)[0]) > 0
        chords = temp*chords
    return chords


def size_distribution(im, bins=None):
    r"""
    Given an image containing the size of the feature to which each voxel
    belongs (as produced by ```simulations.feature_size```), this determines
    the total volume of each feature and returns a tuple containing *radii* and
    *counts* suitable for plotting.

    Parameters
    ----------
    im : array_like
        An array containing the local feature size

    Returns
    -------
    Tuple containing radii, counts
        Two arrays containing the radii of the largest spheres, and the number
        of voxels that are encompassed by spheres of each radii.

    Notes
    -----
    The term *foreground* is used since this function can be applied to both
    pore space or the solid, whichever is set to True.

    """
    inds = sp.where(im > 0)
    bins = sp.unique(im)[1:]
    hist = sp.histogram(a=im[inds], bins=bins)
    radii = hist[1][0:-1]
    counts = hist[0]
    return radii, counts


def chord_length_distribution(im):
    r"""
    Determines the length of each chord in the supplied image by looking at
    its size.

    Parameters
    ----------
    im : ND-array
        An image containing chords drawn in the void space.

    Returns
    -------
    A 1D array with one element for each chord, containing the length.

    Notes
    ----
    The returned array can be passed to ```plt.hist``` as is to plot the
    histogram, or to ```sp.histogram``` to get the histogram data directly.
    Another useful function is ```sp.bincount``` which gives the number of
    chords of each length in a format suitable for ```plt.plot```.
    """
    labels, N = spim.label(im)
    slices = spim.find_objects(labels)
    chord_lens = sp.zeros(N, dtype=int)
    for i in range(len(slices)):
        s = slices[i]
        chord_lens[i] = sp.amax([item.stop-item.start for item in s])
    return chord_lens
