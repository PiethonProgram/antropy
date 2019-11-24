import numpy as np
from numba import jit
from math import factorial, log
from sklearn.neighbors import KDTree
from scipy.signal import periodogram, welch

from .utils import _embed

all = ['perm_entropy', 'spectral_entropy', 'svd_entropy', 'app_entropy',
       'sample_entropy', 'lziv_complexity']


def perm_entropy(x, order=3, delay=1, normalize=False):
    """Permutation Entropy.

    Parameters
    ----------
    x : list or np.array
        One-dimensional time series of shape (n_times)
    order : int
        Order of permutation entropy
    delay : int
        Time delay
    normalize : bool
        If True, divide by log2(order!) to normalize the entropy between 0
        and 1. Otherwise, return the permutation entropy in bit.

    Returns
    -------
    pe : float
        Permutation Entropy

    Notes
    -----
    The permutation entropy is a complexity measure for time-series first
    introduced by Bandt and Pompe in 2002 [1]_.

    The permutation entropy of a signal :math:`x` is defined as:

    .. math:: H = -\\sum p(\\pi)log_2(\\pi)

    where the sum runs over all :math:`n!` permutations :math:`\\pi` of order
    :math:`n`. This is the information contained in comparing :math:`n`
    consecutive values of the time series. It is clear that
    :math:`0 ≤ H (n) ≤ log_2(n!)` where the lower bound is attained for an
    increasing or decreasing sequence of values, and the upper bound for a
    completely random system where all :math:`n!` possible permutations appear
    with the same probability.

    The embedded matrix :math:`Y` is created by:

    .. math:: y(i)=[x_i,x_{i+delay}, ...,x_{i+(order-1) * delay}]

    .. math:: Y=[y(1),y(2),...,y(N-(order-1))*delay)]^T


    References
    ----------
    .. [1] Bandt, Christoph, and Bernd Pompe. "Permutation entropy: a
           natural complexity measure for time series." Physical review letters
           88.17 (2002): 174102.

    Examples
    --------
    Permutation entropy with order 2

    >>> from entropy import perm_entropy
    >>> x = [4, 7, 9, 10, 6, 11, 3]
    >>> # Return a value in bit between 0 and log2(factorial(order))
    >>> print(perm_entropy(x, order=2))
    0.9182958340544896

    Normalized permutation entropy with order 3

    >>> from entropy import perm_entropy
    >>> x = [4, 7, 9, 10, 6, 11, 3]
    >>> # Return a value comprised between 0 and 1.
    >>> print(perm_entropy(x, order=3, normalize=True))
    0.5887621559162939
    """
    x = np.array(x)
    ran_order = range(order)
    hashmult = np.power(order, ran_order)
    # Embed x and sort the order of permutations
    sorted_idx = _embed(x, order=order, delay=delay).argsort(kind='quicksort')
    # Associate unique integer to each permutations
    hashval = (np.multiply(sorted_idx, hashmult)).sum(1)
    # Return the counts
    _, c = np.unique(hashval, return_counts=True)
    # Use np.true_divide for Python 2 compatibility
    p = np.true_divide(c, c.sum())
    pe = -np.multiply(p, np.log2(p)).sum()
    if normalize:
        pe /= np.log2(factorial(order))
    return pe


def spectral_entropy(x, sf, method='fft', nperseg=None, normalize=False):
    """Spectral Entropy.

    Parameters
    ----------
    x : list or np.array
        One-dimensional time series of shape (n_times)
    sf : float
        Sampling frequency
    method : str
        Spectral estimation method ::

        'fft' : Fourier Transform (via scipy.signal.periodogram)
        'welch' : Welch periodogram (via scipy.signal.welch)

    nperseg : str or int
        Length of each FFT segment for Welch method.
        If None, uses scipy default of 256 samples.
    normalize : bool
        If True, divide by log2(psd.size) to normalize the spectral entropy
        between 0 and 1. Otherwise, return the spectral entropy in bit.

    Returns
    -------
    se : float
        Spectral Entropy

    Notes
    -----
    Spectral Entropy is defined to be the Shannon Entropy of the Power
    Spectral Density (PSD) of the data:

    .. math:: H(x, sf) =  -\\sum_{f=0}^{f_s/2} PSD(f) log_2[PSD(f)]

    Where :math:`PSD` is the normalised PSD, and :math:`f_s` is the sampling
    frequency.

    References
    ----------
    .. [1] Inouye, T. et al. (1991). Quantification of EEG irregularity by
       use of the entropy of the power spectrum. Electroencephalography
       and clinical neurophysiology, 79(3), 204-210.

    Examples
    --------
    Spectral entropy of a pure sine using FFT

    >>> from entropy import spectral_entropy
    >>> import numpy as np
    >>> sf, f, dur = 100, 1, 4
    >>> N = sf * dur # Total number of discrete samples
    >>> t = np.arange(N) / sf # Time vector
    >>> x = np.sin(2 * np.pi * f * t)
    >>> np.round(spectral_entropy(x, sf, method='fft'), 2)
    0.0

    Spectral entropy of a random signal using Welch's method

    >>> from entropy import spectral_entropy
    >>> import numpy as np
    >>> np.random.seed(42)
    >>> x = np.random.rand(3000)
    >>> spectral_entropy(x, sf=100, method='welch')
    6.980045662371389

    Normalized spectral entropy

    >>> spectral_entropy(x, sf=100, method='welch', normalize=True)
    0.9955526198316071
    """
    x = np.array(x)
    # Compute and normalize power spectrum
    if method == 'fft':
        _, psd = periodogram(x, sf)
    elif method == 'welch':
        _, psd = welch(x, sf, nperseg=nperseg)
    psd_norm = np.divide(psd, psd.sum())
    se = -np.multiply(psd_norm, np.log2(psd_norm)).sum()
    if normalize:
        se /= np.log2(psd_norm.size)
    return se


def svd_entropy(x, order=3, delay=1, normalize=False):
    """Singular Value Decomposition entropy.

    Parameters
    ----------
    x : list or np.array
        One-dimensional time series of shape (n_times)
    order : int
        Order of permutation entropy
    delay : int
        Time delay
    normalize : bool
        If True, divide by log2(order!) to normalize the entropy between 0
        and 1. Otherwise, return the permutation entropy in bit.

    Returns
    -------
    svd_e : float
        SVD Entropy

    Notes
    -----
    SVD entropy is an indicator of the number of eigenvectors that are needed
    for an adequate explanation of the data set. In other words, it measures
    the dimensionality of the data.

    The SVD entropy of a signal :math:`x` is defined as:

    .. math::
        H = -\\sum_{i=1}^{M} \\overline{\\sigma}_i log_2(\\overline{\\sigma}_i)

    where :math:`M` is the number of singular values of the embedded matrix
    :math:`Y` and :math:`\\sigma_1, \\sigma_2, ..., \\sigma_M` are the
    normalized singular values of :math:`Y`.

    The embedded matrix :math:`Y` is created by:

    .. math:: y(i)=[x_i,x_{i+delay}, ...,x_{i+(order-1) * delay}]

    .. math:: Y=[y(1),y(2),...,y(N-(order-1))*delay)]^T

    Examples
    --------
    SVD entropy with order 2

    >>> from entropy import svd_entropy
    >>> x = [4, 7, 9, 10, 6, 11, 3]
    >>> # Return a value in bit between 0 and log2(factorial(order))
    >>> print(svd_entropy(x, order=2))
    0.7618909465130066

    Normalized SVD entropy with order 3

    >>> from entropy import svd_entropy
    >>> x = [4, 7, 9, 10, 6, 11, 3]
    >>> # Return a value comprised between 0 and 1.
    >>> print(svd_entropy(x, order=3, normalize=True))
    0.6870083043946692
    """
    x = np.array(x)
    mat = _embed(x, order=order, delay=delay)
    W = np.linalg.svd(mat, compute_uv=False)
    # Normalize the singular values
    W /= sum(W)
    svd_e = -np.multiply(W, np.log2(W)).sum()
    if normalize:
        svd_e /= np.log2(order)
    return svd_e


def _app_samp_entropy(x, order, metric='chebyshev', approximate=True):
    """Utility function for `app_entropy`` and `sample_entropy`.
    """
    _all_metrics = KDTree.valid_metrics
    if metric not in _all_metrics:
        raise ValueError('The given metric (%s) is not valid. The valid '
                         'metric names are: %s' % (metric, _all_metrics))
    phi = np.zeros(2)
    r = 0.2 * np.std(x, axis=-1, ddof=1)

    # compute phi(order, r)
    _emb_data1 = _embed(x, order, 1)
    if approximate:
        emb_data1 = _emb_data1
    else:
        emb_data1 = _emb_data1[:-1]
    count1 = KDTree(emb_data1, metric=metric).query_radius(emb_data1, r,
                                                           count_only=True
                                                           ).astype(np.float64)
    # compute phi(order + 1, r)
    emb_data2 = _embed(x, order + 1, 1)
    count2 = KDTree(emb_data2, metric=metric).query_radius(emb_data2, r,
                                                           count_only=True
                                                           ).astype(np.float64)
    if approximate:
        phi[0] = np.mean(np.log(count1 / emb_data1.shape[0]))
        phi[1] = np.mean(np.log(count2 / emb_data2.shape[0]))
    else:
        phi[0] = np.mean((count1 - 1) / (emb_data1.shape[0] - 1))
        phi[1] = np.mean((count2 - 1) / (emb_data2.shape[0] - 1))
    return phi


@jit('f8(f8[:], i4, f8)', nopython=True)
def _numba_sampen(x, mm=2, r=0.2):
    """
    Fast evaluation of the sample entropy using Numba.
    """
    n = x.size
    n1 = n - 1
    mm += 1
    mm_dbld = 2 * mm

    # Define threshold
    r *= x.std()

    # initialize the lists
    run = [0] * n
    run1 = run[:]
    r1 = [0] * (n * mm_dbld)
    a = [0] * mm
    b = a[:]
    p = a[:]

    for i in range(n1):
        nj = n1 - i

        for jj in range(nj):
            j = jj + i + 1
            if abs(x[j] - x[i]) < r:
                run[jj] = run1[jj] + 1
                m1 = mm if mm < run[jj] else run[jj]
                for m in range(m1):
                    a[m] += 1
                    if j < n1:
                        b[m] += 1
            else:
                run[jj] = 0
        for j in range(mm_dbld):
            run1[j] = run[j]
            r1[i + n * j] = run[j]
        if nj > mm_dbld - 1:
            for j in range(mm_dbld, nj):
                run1[j] = run[j]

    m = mm - 1

    while m > 0:
        b[m] = b[m - 1]
        m -= 1

    b[0] = n * n1 / 2
    a = np.array([float(aa) for aa in a])
    b = np.array([float(bb) for bb in b])
    p = np.true_divide(a, b)
    return -log(p[-1])


def app_entropy(x, order=2, metric='chebyshev'):
    """Approximate Entropy.

    Parameters
    ----------
    x : list or np.array
        One-dimensional time series of shape (n_times)
    order : int (default: 2)
        Embedding dimension.
    metric : str (default: chebyshev)
        Name of the metric function used with
        :class:`~sklearn.neighbors.KDTree`. The list of available
        metric functions is given by: ``KDTree.valid_metrics``.

    Returns
    -------
    ae : float
        Approximate Entropy.

    Notes
    -----
    Original code from the mne-features package.

    Approximate entropy is a technique used to quantify the amount of
    regularity and the unpredictability of fluctuations over time-series data.

    Smaller values indicates that the data is more regular and predictable.

    The value of :math:`r` is set to :math:`0.2 * \\text{std}(x)`.

    Code adapted from the mne-features package by Jean-Baptiste Schiratti
    and Alexandre Gramfort.

    References
    ----------
    .. [1] Richman, J. S. et al. (2000). Physiological time-series analysis
           using approximate entropy and sample entropy. American Journal of
           Physiology-Heart and Circulatory Physiology, 278(6), H2039-H2049.

    Examples
    --------
    Approximate entropy with order 2.

    >>> from entropy import app_entropy
    >>> import numpy as np
    >>> np.random.seed(1234567)
    >>> x = np.random.rand(3000)
    >>> print(app_entropy(x, order=2))
    2.0754913760787277
    """
    phi = _app_samp_entropy(x, order=order, metric=metric, approximate=True)
    return np.subtract(phi[0], phi[1])


def sample_entropy(x, order=2, metric='chebyshev'):
    """Sample Entropy.

    Parameters
    ----------
    x : list or np.array
        One-dimensional time series of shape (n_times)
    order : int (default: 2)
        Embedding dimension.
    metric : str (default: chebyshev)
        Name of the metric function used with KDTree. The list of available
        metric functions is given by: `KDTree.valid_metrics`.

    Returns
    -------
    se : float
        Sample Entropy.

    Notes
    -----
    Sample entropy is a modification of approximate entropy, used for assessing
    the complexity of physiological time-series signals. It has two advantages
    over approximate entropy: data length independence and a relatively
    trouble-free implementation. Large values indicate high complexity whereas
    smaller values characterize more self-similar and regular signals.

    Sample entropy of a signal :math:`x` is defined as:

    .. math:: H(x, m, r) = -log\\frac{C(m + 1, r)}{C(m, r)}

    where :math:`m` is the embedding dimension (= order), :math:`r` is
    the radius of the neighbourhood (default = :math:`0.2 * \\text{std}(x)`),
    :math:`C(m + 1, r)` is the number of embedded vectors of length
    :math:`m + 1` having a Chebyshev distance inferior to :math:`r` and
    :math:`C(m, r)` is the number of embedded vectors of length
    :math:`m` having a Chebyshev distance inferior to :math:`r`.

    Note that if metric == 'chebyshev' and x.size < 5000 points, then the
    sample entropy is computed using a fast custom Numba script. For other
    metric types or longer time-series, the sample entropy is computed using
    a code from the mne-features package by Jean-Baptiste Schiratti
    and Alexandre Gramfort (requires sklearn).

    References
    ----------
    .. [1] Richman, J. S. et al. (2000). Physiological time-series analysis
           using approximate entropy and sample entropy. American Journal of
           Physiology-Heart and Circulatory Physiology, 278(6), H2039-H2049.

    Examples
    --------
    Sample entropy with order 2.

    >>> from entropy import sample_entropy
    >>> import numpy as np
    >>> np.random.seed(1234567)
    >>> x = np.random.rand(3000)
    >>> print(sample_entropy(x, order=2))
    2.192416747827227

    Sample entropy with order 3 using the Euclidean distance.

    >>> from entropy import sample_entropy
    >>> import numpy as np
    >>> np.random.seed(1234567)
    >>> x = np.random.rand(3000)
    >>> print(sample_entropy(x, order=3, metric='euclidean'))
    2.7246543561542453
    """
    x = np.asarray(x, dtype=np.float64)
    if metric == 'chebyshev' and x.size < 5000:
        return _numba_sampen(x, mm=order, r=0.2)
    else:
        phi = _app_samp_entropy(x, order=order, metric=metric,
                                approximate=False)
        return -np.log(np.divide(phi[1], phi[0]))


@jit('u8(unicode_type)', nopython=True)
def _lz_complexity(binary_string):
    """
    Internal Numba implementation of the Lempel-Ziv (LZ) complexity.
    https://github.com/Naereen/Lempel-Ziv_Complexity/blob/master/src/lziv_complexity.py
    """
    u, v, w = 0, 1, 1
    v_max = 1
    length = len(binary_string)
    complexity = 1
    while True:
        if binary_string[u + v - 1] == binary_string[w + v - 1]:
            v += 1
            if w + v >= length:
                complexity += 1
                break
        else:
            if v > v_max:
                v_max = v
            u += 1
            if u == w:
                complexity += 1
                w += v_max
                if w > length:
                    break
                else:
                    u = 0
                    v = 1
                    v_max = 1
            else:
                v = 1
    return complexity


def lziv_complexity(binary_sequence, normalize=False):
    """
    Lempel-Ziv (LZ) complexity of binary sequence.

    Parameters
    ----------
    binary_sequence : str or array
        A sequence of 0 and 1, e.g. ``'1001111011000010'`` or
        ``[0, 1, 0, 1, 1]``.
    normalize : bool
        If ``True``, returns the normalized LZ (see Notes).

    Returns
    -------
    lz : int or float
        LZ complexity, which corresponds to the number of different
        substrings encountered as the stream is viewed from the
        beginning to the end. If ``normalize=False``, the output is an
        integer (counts), otherwise the output is a float.

    Notes
    -----
    LZ complexity is defined as the number of different substrings encountered
    as the sequence is viewed from begining to the end.

    Although the raw LZ is an important complexity indicator, it is heavily
    influenced by sequence length (longer sequence will result in higher LZ).
    Zhang and colleagues (2009) have therefore proposed the normalized LZ,
    which is defined by

    .. math:: LZn = \\frac{LZ}{(n / \\log_2{n})}

    where :math:`n` is the length of the binary sequence.

    References
    ----------
    .. [1] Lempel, A., & Ziv, J. (1976). On the Complexity of Finite Sequences.
           IEEE Transactions on Information Theory / Professional Technical
           Group on Information Theory, 22(1), 75–81.
           https://doi.org/10.1109/TIT.1976.1055501

    .. [2] Zhang, Y., Hao, J., Zhou, C., & Chang, K. (2009). Normalized
           Lempel-Ziv complexity and its application in bio-sequence analysis.
           Journal of Mathematical Chemistry, 46(4), 1203–1212.
           https://doi.org/10.1007/s10910-008-9512-2

    .. [3] https://en.wikipedia.org/wiki/Lempel-Ziv_complexity

    .. [4] https://github.com/Naereen/Lempel-Ziv_Complexity

    Examples
    --------
    >>> from entropy import lziv_complexity
    >>> # Substrings = 1 / 0 / 01 / 1110 / 1100 / 0010
    >>> s = '1001111011000010'
    >>> lziv_complexity(s)
    6

    Using a list of integer / boolean instead of a string:

    >>> # 1 / 0 / 10
    >>> lziv_complexity([1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
    3

    With normalization:

    >>> lziv_complexity(s, normalize=True)
    1.5
    """
    assert isinstance(binary_sequence, (str, list, np.ndarray))
    assert isinstance(normalize, bool)
    if isinstance(binary_sequence, (list, np.ndarray)):
        binary_sequence = np.asarray(binary_sequence, dtype=int)
        s = ''.join(binary_sequence.astype(str))
    else:
        s = binary_sequence

    # Check that string only contains 0 and/or 1
    unique_chars = sorted(list(set(s)))
    if len(unique_chars) == 2:
        assert unique_chars == ['0', '1']

    if normalize:
        # 1) Timmermann et al. 2019
        # The sequence is randomly shuffled, and the normalized LZ
        # is calculated as the ratio of the LZ of the original sequence
        # divided by the LZ of the randomly shuffled LZ. However, the final
        # output is dependent on the random seed.
        # sl_shuffled = list(s)
        # rng = np.random.RandomState(None)
        # rng.shuffle(sl_shuffled)
        # s_shuffled = ''.join(sl_shuffled)
        # return _lz_complexity(s) / _lz_complexity(s_shuffled)
        # 2) Zhang et al. 2009
        n = len(s)
        return _lz_complexity(s) / (n / np.log2(n))
    else:
        return _lz_complexity(s)
