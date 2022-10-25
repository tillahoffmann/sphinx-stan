import doit_interface as di

manager = di.Manager.get_instance()

manager(basename="docs", actions=[["sphinx-build", ".", "docs/_build"]])
manager(basename="requirements", targets=["requirements.txt"], actions=[["pip-compile"]],
        file_dep=["requirements.in", "setup.py"])
manager(basename="tests", actions=[["pytest"]])
manager(basename="lint", actions=[["flake8"]])

with di.defaults(basename="package"):
    task = manager(name="sdist", actions=[["python", "setup.py", "sdist"]])
    manager(name="check", actions=["twine check dist/*"], task_dep=[task])
