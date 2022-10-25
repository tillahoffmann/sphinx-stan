from setuptools import find_namespace_packages, setup
from version_wizard import from_github_tag


setup(
    name="sphinx-stan",
    packages=find_namespace_packages(),
    install_requires=[
        "sphinx",
        "version-wizard",
    ],
    extras_require={
        "tests": [
            "flake8",
            "pytest",
            "twine",
        ]
    },
    version=from_github_tag(),
    long_description_content_type="text/x-rst",
    long_description="Please see https://sphinx-stan.readthedocs.io/.",
)
