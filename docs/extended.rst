Extended examples
=================

autodoc without members option
------------------------------

All elements of :code:`../examples.stan` should appear twice below.

.. stan:autodoc:: all-functions.stan

.. stan:autodoc:: all-functions.stan
    :members:

autodoc with multi-line signatures
----------------------------------

.. stan:autodoc:: multiline-signature.stan

unqualified overloaded references
---------------------------------

:stan:func:`log`
