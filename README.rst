sphinx-stan
===========

sphinx-stan is a `Sphinx <https://www.sphinx-doc.org>`_ extension for documenting `Stan <https://mc-stan.org>`_ code. It supports both standard Sphinx fields as well as the `doxygen <https://doxygen.nl>`_ syntax `recommended by the Stan user guide <https://mc-stan.org/docs/stan-users-guide/documenting-functions.html>`_.

Examples
--------

.. stan:function:: array [,] vector fancy_function(vector x, array[,,] int y)

    This function does something fancy. Also see :stan:func:`doxygen_function` and :stan:func:`overloaded(real)`.

    :param x: A vector.
    :param y: A two-dimensional array of integers.
    :returns: A two-dimensional array of vectors.
    :throws:

        - An error if something is wrong.
        - Another error if something else is wrong.


.. stan:function:: real doxygen_function(int x, matrix y)

    /**
    * This function uses doxygen syntax for documentation.
    *
    * @param x An integer.
    * @param y A matrix.
    * @returns A value.
    * @throws
    *
    *  - first error
    *  - second error
    */


.. stan:function:: real overloaded()

.. stan:function:: real overloaded(real value)

.. stan:autodoc:: example.stan
    :members: another_fancy_function
