===========
Plenopticam
===========
.. A light field photography application (macOS_ or Win_) for computational change of perspective view and synthetic focus based on a Standard Plenoptic Camera (SPC).

Description
-----------

*Plenopticam* is an open-source software (macOS_ or Win_) for scientific light field computation with cross-platform compatibility, few dependencies and a lean graphical user interface.
Raw exposures from a plenoptic camera require four-dimensional image alignment in order to be decoded as a light field. Provided software addresses this by its ability to extract depth by means of sub-aperture images or synthetically focused photographs.
This application is meant for researchers, developers, beginners and other fiddlers who like to experiment with light field technology. Its scope comprises custom-types of plenoptic cameras and is thus not limited to Lytro's image data.

|release| |license| |code| |repo| |downloads|

Installation
------------

* executable:
    1. download bundled apps_ for macOS_ or Win_
    2. extract archive
    3. run app to open up the lean user interface (see below)

|

* from source:
    1. install Python from https://www.python.org/
    2. download the source_ using ``$ git clone https://github.com/hahnec/plenopticam.git``
    3. go to the root directory ``$ cd plenopticam``
    4. install with ``$ sudo python setup.py install`` from the root directory
    5. if installation ran smoothly, enter ``$ sudo plenopticam -g`` to the command line after which a lean user interface will pop up (see below)

Usage
-----

|gui|

.. |gui| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/gui_v3.png" width="75%" align="middle" style="display: block;
    margin: 0 auto;">

.. note::
    "Pick folder" checkbox is useful to point to a directory containing calibration archive files of Lytro Illum cameras.
    In such case, the white image calibration file corresponding to the Illum image is found automatically.

|

0. Download a dataset if you don't call a plenoptic camera your own, e.g.:
    - |OpEx|_
    - |INRIA|_

|

1. Choose your light field photograph using upper **Browse** button. Supported file types are:
    - *lfr*, *lfp* and *raw* files from Lytro Illum
    - *bmp*, *jpg* or *png* file from custom-built plenoptic camera
    - Lytro 1st Generation (to come)

|

2. Choose calibration source data using lower **Browse** button. Supported file types are:
    - *tar* archive or respective *raw* file from Lytro Illum
    - *bmp*, *jpg* or *png* file from custom-built plenoptic camera
    - Lytro 1st Generation (to come)

|

3. Adjust configuration using **Settings** button:
    - *Micro image patch size*: default is estimated maximum
    - *Refocusing range*: range for shift and sum synthesis
    - *Force re-calibration*: option to re-run calibration
    - *Automatic white balance*: option for white balancing
    - *Refocus refinement*: option for sub-pixel precise refocusing
    - *Scheimpflug*: option to mimic tilted sensor

|

4. Press **Process** to start the computation.

|

Results
-------

Results can be found inside a folder named after your light field file which is located in the same directory path.
Depending on provided files and settings, your results folder may contain the following data:

    - sub-aperture images (see *viewpoints_xxx* folder) and view animation given as gif
    - refocused images (see *refo_xxx* folder) and refocus animation given as gif
    - raw image file given as tiff
    - aligned light field as pkl (pickle) file
    - light field metadata as json file (in case of Lytro image file)
    - scheimpflug focus file

Exemplary view animations can be seen below.

.. list-table::
   :widths: 8 8

   * - |OpEx|_
     - |INRIA|_
   * - |spiderman|
     - |fruits|
   * - plenoptic camera built at Univ. of Bedfordshire
     - Lytro Illum camera image from raw capture

.. * |Stanford|_


Credits
-------

Contributors
============

|Hahne|

`Christopher Hahne <http://www.christopherhahne.de/>`__

Sponsors
========
|


.. list-table::
   :widths: 8 8

   * - |EUFramework|
     - |UoB|
   * - `under Grant EU-FP7 ICT-2010-248420 <https://cordis.europa.eu/project/rcn/94148_en.html>`__
     - `Institute for Research in Applicable Computing (IRAC) <https://www.beds.ac.uk/research-ref/irac/about>`__

Citation
--------
If you find this work helpful for your research, please cite as appropriate:

* `Refocusing distance of a standard plenoptic camera <https://doi.org/10.1364/OE.24.021521>`__, *OpticsExpress*, `[BibTeX] <http://www.plenoptic.info/bibtex/HAHNE-OPEX.2016.bib>`__

* `Baseline and triangulation geometry in a standard plenoptic camera <http://www.plenoptic.info/files/IJCV_Hahne17_final.pdf>`__, *Int. J. of Comp. Vis.*, `[BibTeX] <http://plenoptic.info/bibtex/HAHNE-IJCV.2017.bib>`__

Further information
-------------------

* check out Plenopticam's partner project Plenoptisign_ capable of estimating metric light field geometries
* visit `plenoptic.info <http://www.plenoptic.info>`__ for technical details, animated figures and theoretical background

.. Image substitutions

.. |release| image:: https://img.shields.io/github/release/hahnec/plenopticam.svg?style=flat-square
    :target: https://github.com/hahnec/plenopticam/releases/
    :alt: release

.. |license| image:: https://img.shields.io/badge/License-GPL%20v3.0-orange.svg?style=flat-square
    :target: https://www.gnu.org/licenses/gpl-3.0.en.html
    :alt: License

.. |code| image:: https://img.shields.io/github/languages/code-size/hahnec/plenopticam.svg?style=flat-square
    :target: https://github.com/hahnec/plenopticam/archive/master.zip
    :alt: Code size

.. |repo| image:: https://img.shields.io/github/repo-size/hahnec/plenopticam.svg?style=flat-square
    :target: https://github.com/hahnec/plenopticam/archive/master.zip
    :alt: Repo size

.. |downloads| image:: https://img.shields.io/github/downloads/hahnec/plenopticam/total.svg?style=flat-square
    :target: https://github.com/hahnec/plenopticam/archive/master.zip
    :alt: Downloads

.. |spiderman| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/spiderman.gif" height="186px" max-width:"100%">

.. |fruits| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/fruits_r.gif" height="186px" max-width:"100%">

.. |UoB| raw:: html

    <img src="https://3tkh0x1zl0mb1ta92c2mrvv2-wpengine.netdna-ssl.com/wp-content/uploads/2015/12/LO_KukriGB_Universities_Bedfordshire.png" width="70px">

.. |EUFramework| raw:: html

    <img src="http://www.gsa.europa.eu/sites/default/files/Seventh_Framework_Programme_logo.png" width="100px">

.. |Hahne| raw:: html

    <img src="http://www.christopherhahne.de/images/about.jpg" width="15%">

.. |br| raw:: html

    <br />

.. Hyperlink aliases

.. _source: https://github.com/hahnec/plenopticam/archive/master.zip
.. _macOS: https://github.com/hahnec/plenopticam/releases/download/v0.1.1-beta/plenopticam_0.1.1-beta_macOS.zip
.. _Win: https://github.com/hahnec/plenopticam/releases/download/v0.1.1-beta/plenopticam_0.1.1-beta_win.zip
.. _Plenoptisign: https://github.com/hahnec/plenoptisign/
.. _apps: https://github.com/hahnec/plenopticam/releases/

.. |OpEx| replace:: **OpEx dataset**
.. _OpEx: https://ndownloader.figshare.com/files/5201452

.. |INRIA| replace:: **INRIA dataset**
.. _INRIA: https://www.irisa.fr/temics/demos/IllumDatasetLF/index.html

.. |Stanford| replace:: **Stanford dataset**
.. _Stanford: http://lightfields.stanford.edu/mvlf/

.. |IllumTar| replace:: *using your own Illum data*
.. _IllumTar: https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/build/html/guide.html