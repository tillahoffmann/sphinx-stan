sphinx-stan
===========

.. image:: https://github.com/tillahoffmann/sphinx-stan/actions/workflows/main.yml/badge.svg
    :target: https://github.com/tillahoffmann/sphinx-stan/actions/workflows/main.yml
.. image:: https://readthedocs.org/projects/sphinx-stan/badge/?version=latest
    :target: https://sphinx-stan.readthedocs.io/en/latest/?badge=latest

sphinx-stan is a `Sphinx <https://www.sphinx-doc.org>`_ extension for documenting `Stan <https://mc-stan.org>`_ code. It supports both standard Sphinx fields as well as the `doxygen <https://doxygen.nl>`_ syntax `recommended by the Stan user guide <https://mc-stan.org/docs/stan-users-guide/documenting-functions.html>`_.

Explicit documentation of functions
-----------------------------------

Functions can be documented explicitly using the :code:`:stan:function:: ...` directive. For example, the following statements generate the documentation shown below.

.. code-block:: rst

    .. stan:function:: real log(real x, real y)

        Evaluate the logarithm of :math:`x` with base :math:`y`.

        :param x: Value to take the logarithm of.
        :param y: Base of the logarithm.
        :return: :math:`\log_y\left(x\right)`.
        :throws: If :math:`x` or :math:`y` are negative.

.. stan:function:: real log(real x, real y)

    Evaluate the logarithm of :math:`x` with base :math:`y`.

    :param x: Value to take the logarithm of.
    :param y: Base of the logarithm.
    :return: :math:`\log_y\left(x\right)`.
    :throws: If :math:`x` or :math:`y` are negative.

Stan supports `overloading <https://mc-stan.org/docs/stan-users-guide/overloading-functions.html>`_, and so does the documentation. For example, the following function evaluates the natural logarithm, implicitly setting :math:`y=e`.

.. stan:function:: real log(real x)

    Evaluate the natural logarithm of :math:`x`.

    :param x: Value to take the logarithm of.
    :return: :math:`\log\left(x\right)`.
    :throws: If :math:`x` is negative.

Using the :code:`:stan:func:\`...\`` role, we can reference specific overloaded implementations (such as :stan:func:`log(real, real)` or :stan:func:`log(real)`) by specifying the argument types.

.. note::

    sphinx-stan will try to resolve unqualified function references (such as :code:`:stan:func:\`log\``). A warning will be issued if the unqualified reference is ambiguous and the reference may point to any of the overloaded functions.

Automatic documentation
-----------------------

Functions can also be documented by loading them from a :code:`*.stan` file. For example, the following statements document two functions stored in :code:`example.stan`.

.. code-block:: rst

    .. stan:autodoc:: example.stan
        :members: mat_pow; log1p_series(real, int)

.. stan:autodoc:: example.stan
    :members: mat_pow; log1p_series(real, int)

Documentation for each function must preceed it and be wrapped in :code:`/** ... */` comments.

Syntax
------

.. code-block:: rst

    .. stan:function:: <signature of the function>

        <general documentation that supports any reST syntax>

        :param <parameter name>: <parameter description>
        :param <parameter name>: <parameter description>
        :return: <return value description>
        :throws:

          - <first error condition>
          - <second error condition>

Alternatively, functions may also be documented using the doxygen syntax (see the `Stan user guide <https://mc-stan.org/docs/stan-users-guide/documenting-functions.html>`_ for details).

.. code-block:: rst

    .. stan:autodoc:: <path to stan file>
        :members: <semi-colon separated list of functions to document>

If :code:`:members:` is omitted, all functions in the file are documented in the order they appear. Function names are matched using the same logic as for the :code:`:stan:func:\`...\`` cross-referencing logic. If the file contains overloaded functions and only an unqualified name is provided (i.e., without argument types), all overloaded functions with the given identifier will be documented in the order they appear.
