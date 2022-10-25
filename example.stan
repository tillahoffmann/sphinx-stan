/**
* Raise a matrix to a power (described using doxygen syntax in a separate Stan file).
*
* We can also reference other functions from within *.stan files, such as
* :stan:func:`log(real, real)`.
*
* @param X Matrix to raise to a power.
* @param y Power.
* @return :math:`X^y`
* @throws An error if there's a problem.
*/
matrix mat_pow(matrix X, real y) {
    return ...;
}

/**
Evaluate a series approximation of :math:`\log\left(1 + x\right)` with :math:`n` terms.

.. note::

  The example file contains another function with different signature that does not show up in the
  documentation because it does not match the :code:`:members:` field.
*/
real log1p_series(real x, int n) {
    return ...;
}


/**
This function does not appear in the documentation.
*/
real log1p_series(real x) {
    return ...;
}
