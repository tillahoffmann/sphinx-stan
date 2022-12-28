import pytest
import re
from sphinx.application import Sphinx
from sphinx.testing.path import path
from pathlib import Path
from typing import Callable


@pytest.fixture
def sphinx_build(make_app: Callable, tmp_path: Path, request: pytest.FixtureRequest) -> Sphinx:
    # Create files.
    filenames = set()
    for mark in request.node.iter_markers("sphinx_file"):
        filename, content = mark.args
        if filename in filenames:
            raise ValueError(f"duplicate file name: {filename}")
        with open(tmp_path / filename, "w") as fp:
            fp.write(content)
        filenames.add(filename)

    # Add default configuration if not given.
    if "conf.py" not in filename:
        with open(tmp_path / "conf.py", "w") as fp:
            fp.writelines([
                "extensions = ['sphinxcontrib.stan']\n",
                "html_theme = 'alabaster'\n",
            ])

    # Create the app and build.
    app: Sphinx = make_app(srcdir=path(tmp_path))
    app.build(force_all=True)
    assert app.statuscode == 0

    # Load the index file and match all patterns we're expecting.
    index_file = app.outdir / "index.html"
    print(f"output in {index_file}")
    with index_file.open() as fp:
        content = fp.read()
    for mark in request.node.iter_markers("sphinx_pattern"):
        if len(mark.args) == 2:
            pattern, num_matches = mark.args
        else:
            pattern, = mark.args
            num_matches = 1
        assert len(re.findall(pattern, content)) == num_matches, \
            f"unexpected number of matches in {index_file}"

    return app


@pytest.mark.sphinx_file("index.rst", """
.. stan:function:: real log_prob(real y, array [,] float x)

    :param y: Something.
    :returns: Something else.
    :throws: Some error.

:stan:func:`log_prob`
:stan:func:`log_prob(real, array [,] float)`
""")
@pytest.mark.sphinx_pattern(r'<dt class="field-\w+">Parameters</dt>')
@pytest.mark.sphinx_pattern(r'<dt class="field-\w+">Returns</dt>')
@pytest.mark.sphinx_pattern(r'<dt class="field-\w+">Throws</dt>')
@pytest.mark.sphinx_pattern(r'<code class="xref.*?"><span class="pre">log_prob</span></code>')
@pytest.mark.sphinx_pattern(r'<code class="xref.*?"><span class="pre">log_prob\(real,</span>')
def test_function_and_ref(sphinx_build) -> None:
    pass


@pytest.mark.sphinx_file("index.stan", """
real log(real x) {}
real add(real x, real y) {}
""")
@pytest.mark.sphinx_file("index.rst", """
    .. stan:autodoc:: index.stan
    .. stan:autodoc:: index.stan
        :members:
""")
@pytest.mark.sphinx_pattern('<span class="pre">log</span>', 2)
@pytest.mark.sphinx_pattern('<span class="pre">add</span>', 2)
def test_autodoc(sphinx_build) -> None:
    pass


@pytest.mark.sphinx_file("index.stan", """
real func(real x) {}
real func(real x, real y) {}
real other() {}
real func2(int x) {}
real func2(int x, int y) {}
""")
@pytest.mark.sphinx_file("index.rst", """
    .. stan:autodoc:: index.stan
        :members: func; func2(int, int); missing
""")
@pytest.mark.sphinx_pattern('<span class="pre">func</span>', 2)
@pytest.mark.sphinx_pattern('<span class="pre">other</span>', 0)
@pytest.mark.sphinx_pattern('<span class="pre">func2</span>', 1)
@pytest.mark.sphinx_pattern('<span class="pre">missing</span>', 0)
def test_autodoc_with_members(sphinx_build) -> None:
    assert "found no match for `missing`" in sphinx_build._warning.getvalue()


@pytest.mark.sphinx_file("index.stan", "")
@pytest.mark.sphinx_file("index.rst", ".. stan:autodoc:: index.stan")
def test_autodoc_empty_file(sphinx_build) -> None:
    assert "no signatures found in" in sphinx_build._warning.getvalue()


@pytest.mark.sphinx_file("index.rst", ".. stan:autodoc:: index.stan")
def test_autodoc_missing_file(sphinx_build) -> None:
    assert "does not exist" in sphinx_build._warning.getvalue()


@pytest.mark.sphinx_file("index.rst", ":stan:func:`missing`")
def test_missing_ref(sphinx_build) -> None:
    assert "Stan func reference target not found" in sphinx_build._warning.getvalue()


@pytest.mark.sphinx_file("index.rst", """
.. stan:function:: real foobar(int x)

.. stan:function:: real foobar(int x, int y)

:stan:func:`foobar`
""")
def test_ambiguous_ref(sphinx_build) -> None:
    value = sphinx_build._warning.getvalue()
    assert "multiple Stan functions found for reference `foobar` at " in value
    assert ": real foobar(int x) at " in value
    assert "; real foobar(int x, int y) at " in value


@pytest.mark.sphinx_file("index.rst", """
.. stan:function:: real foobar(int x)

    There
    are
    multiple
    lines.
""")
@pytest.mark.sphinx_pattern(r"There[\n\s]+are[\n\s]+multiple[\n\s]+lines.")
def test_multiline_doc(sphinx_build) -> None:
    pass


@pytest.mark.sphinx_file("index.rst", """
.. stan:function:: real foobar(int x)

    /**
    * There
    * are
    * multiple
    * lines.
    */
""")
@pytest.mark.sphinx_pattern(r"There[\n\s]+are[\n\s]+multiple[\n\s]+lines.")
def test_multiline_doc_with_doxygen(sphinx_build) -> None:
    pass


@pytest.mark.sphinx_file("index.stan", """
/**
* There
* are
* multiple
* lines.
*/
real foobar(int x) {}
""")
@pytest.mark.sphinx_file("index.rst", ".. stan:autodoc:: index.stan")
@pytest.mark.sphinx_pattern(r"There[\n\s]+are[\n\s]+multiple[\n\s]+lines.")
def test_multiline_autodoc_with_doxygen(sphinx_build) -> None:
    pass


@pytest.mark.sphinx_file("index.rst", """
.. stan:function:: real foobar(int x)

    * This is *important*.
""")
@pytest.mark.sphinx_pattern(r"<em>important</em>")
def test_inline_markup(sphinx_build) -> None:
    pass
