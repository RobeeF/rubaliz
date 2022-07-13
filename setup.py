import os
from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

REQUIRES_PYTHON = '>=3.7.0'
requirements = [
    'numpy>=1.17.1',
    'pandas>=1.0.3',
    'ruptures>=1.1.5',
    'matplotlib>=3.0.1'
]

# Load the package's __version__.py module as a dictionary.
about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'rubaliz', '__version__.py')) as f:
        exec(f.read(), about)

setup(
    name="rubaliz",
    version=about['__version__'],
    author="Robin Fuchs",
    author_email="robin.fuchs92@gmail.com",
    description="A package to detect the boundaries of the active mesopelagic zone",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/RobeeF/rubaliz/",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)
