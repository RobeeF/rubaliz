# RUBALIZ
<div align="center">
  <img src="images/RUBALIZ_logo.png" alt="RUBALIZ_logo"/>
</div>

<br/>

<div align="center">
  <!-- Python version -->
  <a href="https://pypi.python.org/pypi/rubaliz">
    <img src="https://img.shields.io/badge/python-3.7-blue.svg?style=for-the-badge" alt="PyPI version"/>
  </a>
  <!-- PyPi -->
  <a href="https://pypi.python.org/pypi/rubaliz">
    <img src="https://img.shields.io/pypi/v/rubaliz.svg?style=for-the-badge" alt="pypi" />
  </a>
  <!-- Zenodo -->
  <a href="https://doi.org/10.5281/zenodo.6425451">
    <img src="https://zenodo.org/badge/doi/10.5281/zenodo.6425452.svg" alt="pypi" />
  </a>
  <!-- License -->
  <a href="https://opensource.org/licenses/MIT">
    <img src="http://img.shields.io/:license-mit-ff69b4.svg?style=for-the-badge" alt="license"/>
  </a>
</div>

<br/>

RUBALIZ stands for RUpture-Based detection method for the Active mesopeLagIc Zone.
It determines the active mesopelagic zone boundaries from CTD casts, using five variables:
- Fluorescence
- [0<sub>2</sub>]
- Potential temperature
- Salinity
- Density

RUBALIZ was introduced in Fuchs, Baumas et al. (2022).

## Installation
The package can be installed using pip or conda.
If you do not have python installed, the simplest is to install [Anaconda3](https://www.anaconda.com/products/distribution) on the host machine. During the installation: Please make sure to tick the "Add Anaconda3 to my Path" box, even if Anaconda displays a red message (see screenshot below). If you did not, please uninstall and reinstall Anaconda3.
<div align="center">
  <img src="images/conda_install.PNG" alt="conda_install"/>
</div>

<div align="center">
  <img src="images/conda_install2.png" alt="conda_install2"/>
</div>


Then, open a command-line console (e.g. cmd, prompt, bash, etc.) and please copy-paste the corresponding line in it:
Using pip:
```python
pip install rubaliz
```

or alternatively using conda (from Anaconda3):
```python
conda install rubaliz
```

## Getting started
The metadata have to be filled in a dictionary as shown below:

```python
from rubaliz import rubaliz

# Define CTD files info
info_dict = {'cruise_name': 'DY032',
'station_name': 'PAP',
'ub_range': [280, 320],
'lb_range': [1000, 1300],
'pres_col': 'PRES',
'Fluorescence': 'flC',
'Oxygen': 'oxygen',
'Pot. temp.': 'potemperature',
'Salinity': 'PSAL',   
'Density': 'sigma-é00',
'files_format': '.cnv',
'sep': None,
'data_folder': 'your_path_to_data'}
```

The cruise and station names are optional, one can set them to None if not wanted.
The maximum depth ranges to look for the upper bound and lower boundaries of the active mesopelagic zone, ub_range and lb_range, are set to [280, 320] and [1000, 1300] by default, respectively. These values have been chosen as the mesopelagic layer is classically assumed to lie between 200 and 1000 meters. These maximum ranges take into account this a priori knowledge with a security margin (max. 280m deep instead of 200m for the upper boundary.)

The pres_col is the name of the column containing the pressure data in the CTD cast.
Similarly, the Fluorescence, Oxygen, Pot. temp., Salinity and Density stand for the column names of the fluorescence, oxygen, potential temperature, salinity data, and density, respectively.
If one of these five signals is missing, please set it to None.
Please ensure that your files contain only CTD downward casts (no upward casts) to avoid potential unexpected behaviors.

The data_folder contains all the CTD casts for a given (cruise, station) couple. An example of such a cast is given in the data folder.
Be careful on Windows machines, you will have to replace "\\" in the path with the standard "/".

RUBALIZ can handle '.cnv', '.txt' and '.csv' raw files (please do not use pre-processed files such as bodc-processed files).
For '.csv' and '.txt' files, a separator (sep) has to be set (e.g. "," or ";" or "\s+" or "\t").
CTD casts present a significant format variety and this package has tried to handle most of them.
Yet, it might be the case that you need to pre-process your CTD casts a bit to make things work.

The model can be run in the following way in Spyder/via the console, etc.:
```python
ruba = rubaliz(info_dict) # Fetch the pieces of information
ruba.fit() # Adjust the mode
```

Then the results are accessible in this way:
```python
print(ruba.boundaries) # Upper and lower boundaries estimates and standard deviations.
print(ruba.nb_ctd_ub) # The number of ctd used for the upper boundary determination
print(ruba.nb_ctd_lb) # The number of ctd used for the lower boundary determination
```

<div align="center">
  <img src="images/README_cmd1.PNG" alt="README_cmd1"/>
</div>

As we are using the example file given in the data_folder, there is only one CTD cast to determine the upper and lower boundaries.

To graphically analyze the boundaries found:
```python
ruba.display_boundaries()
```
<div align="center">
  <img src="images/README_cmd2.png" alt="README_cmd2"/>
</div>

To make an estimation of the sensibility of the boundaries to each input variable:
```python
ruba.sensitivity_analysis()
```

<div align="center">
  <img src="images/README_cmd3.png" alt="README_cmd3"/>
</div>

Finally, users interested in only determining the upper bound of the active mesopelagic layer (i.e. the limit of the upper ocean zone) can do it by running:
```python
ruba = rubaliz(info_dict)
ruba.fit()
upper_data = ruba.format_data([0, ruba.ub_range[1]])
upper_bound= ruba.rupture_confidence_interval(ruba.ub_data, 1, [ruba.ub_range[0], ruba.ub_range[1]])
print(upper_bound)
```

<div align="center">
  <img src="images/README_cmd4.PNG" alt="README_cmd4"/>
</div>
