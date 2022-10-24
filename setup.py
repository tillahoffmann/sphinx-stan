from setuptools import find_namespace_packages, setup


setup(
    name="sphinx-stan",
    packages=find_namespace_packages(),
    install_requires=[
        "sphinx",
    ],
    extras_require={
        "tests": [
            "flake8",
            "pytest",
        ]
    }
)
