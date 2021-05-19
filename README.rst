===========
PlenoptiCam
===========
.. A light field photography application (macOS_ or Win_) for computational change of perspective view and synthetic focus based on a Standard Plenoptic Camera (SPC).

Description
===========

*PlenoptiCam* is an open-source software (macOS_, Win_ or Linux_) for scientific light field computation with cross-platform compatibility, few dependencies and a lean graphical user interface.
Raw exposures from a plenoptic camera require four-dimensional image alignment in order to be decoded as a light field. Provided software addresses this by its ability to calibrate an image taken by a plenoptic camera and extract sub-aperture images or synthetically focused photographs.
This application is meant for researchers, developers, beginners and other fiddlers who like to experiment with light field technology. Its scope comprises custom-types of plenoptic cameras and is thus not limited to Lytro's image data.

|release| |license| |travis| |coverage| |downloads| |pypi|

|paper|

|colab|

Results
=======

Datesets
--------

.. list-table::
   :widths: 8 8
   :header-rows: 1
   :stub-columns: 0

   * - |OpEx|_
     - |INRIA|_
   * - |opex_demo|
     - |inria_demo|
   * - Custom-built (png, jpg, bmp files)
     - Lytro Illum (lfp, lfr, tar files)
   * - |binder|
     - |colab|

Color equalization
------------------

.. list-table::
   :widths: 8 8 8
   :header-rows: 1
   :stub-columns: 0

   * - Before
     - Target
     - After
   * - |src_lfp|
     - |ref_lfp|
     - |res_lfp|

Depth
-----
.. list-table::
   :widths: 8 8
   :header-rows: 1
   :stub-columns: 0

   * - 2-D depth map
     - 3-D point cloud
   * - |depth_demo|
     - |depth_anim|
   * - pfm file format
     - ply file format

Installation
============

* executable:
    1. download bundled apps_ for macOS_, Win_ or Linux_
    2. run installer / extract archive
    3. work around |WinExeDoc|_ or |MacAppDoc|_ issue
    4. run executable (may take a while on first start-up)
    5. user interface will show up (see below)

|

* via pip:
    1. install with ``$ python3 -m pip install plenopticam``
    2. type ``$ plenopticam -g`` to the command line once installation finished

|

* from source:
    1. install Python from https://www.python.org/
    2. download the source_ using ``$ git clone https://github.com/hahnec/plenopticam.git``
    3. go to the root directory ``$ cd plenopticam``
    4. load other packages ``$ python3 -m pip install -r requirements.txt``
    5. install with ``$ sudo python3 setup.py install`` from root directory
    6. if installation ran smoothly, enter ``$ sudo plenopticam -g`` to the command line

Usage
=====

Application
-----------

|gui|

.. |gui| raw:: html

    <p align="center">
        <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/gui_linux.png" width="66%">
    <p>

.. note::
    "Pick folder" checkbox is useful to point to a directory containing calibration archive files of Lytro Illum cameras.
    In such case, the white image calibration file corresponding to the Lytro Illum image is found automatically.

|

0. Download a dataset if you don't call a plenoptic camera your own, e.g.:
    - |OpEx|_
    - |INRIA|_

|

1. Choose your light field photograph using upper **Browse** button. Supported file types are:
    - *bmp*, *jpg* or *png* file from custom-built plenoptic camera
    - *lfr*, *lfp* and *raw* files from Lytro Illum

|

2. Choose calibration source data using lower **Browse** button. Supported file types are:
    - *bmp*, *jpg* or *png* file from custom-built plenoptic camera
    - *caldata-XXX.tar* archive or respective *raw* file from Lytro Illum
    - tick "Pick folder" and point to a directory containing all *tar* files or extracted folders (calibration file will be found automatically)

.. note::
    If you are `using your own Lytro Illum <https://hahnec.github.io/plenopticam/build/html/guide.html#using-your-own-lytro-illum>`__ camera, you first need to extract camera calibration data as a *tar*-archive. To do so, please follow the `instructions guide <https://hahnec.github.io/plenopticam/build/html/guide.html>`__.

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

Command Line
------------

For computing a stack of light-field images, it may be convenient to iterate through them. This can be done by:

``$ sudo plenopticam -f '/Users/../Folder/' -c 'Users/../caldata-B5144000XXX.tar'``

with necessary write privileges on Unix Systems. A Windows-equivalent command would be as follows:

``plenopticam --file="C:\\..\\Folder\\" --cali="C:\\..\\caldata-B5144000XXX.tar"``

More information on optional arguments, can be found using the help parameter

``plenopticam -h``

Results can be found inside a folder named after your light field file which is located in the same directory path.
Depending on provided files and settings, your results folder may contain the following data:

    - sub-aperture images (see *viewpoints_xxx* folder) and view animation given as gif
    - refocused images (see *refo_xxx* folder) and refocus animation given as gif
    - depth map given as pfm and ply file
    - raw image file given as tiff
    - aligned light field as pkl (pickle) file
    - light field metadata as json file (for Lytro files only)
    - scheimpflug focus files

API usage
---------

Usage of PlenoptiCam modules is demonstrated in the following Jupyter notebooks:

`1. Calibration Demo <https://github.com/hahnec/plenopticam/blob/master/examples/01_calib_demo.ipynb>`__

`2. Alignment Demo <https://github.com/hahnec/plenopticam/blob/master/examples/02_align_demo.ipynb>`__

`3. Extraction Demo <https://github.com/hahnec/plenopticam/blob/master/examples/03_xtract_demo.ipynb>`__

`4. Lytro Illum Demo <https://github.com/hahnec/plenopticam/blob/master/examples/04_illum_demo.ipynb>`__

Citation
========

.. code-block:: BibTeX

    @misc{hahne2020plenopticam,
          title={PlenoptiCam v1.0: A light-field imaging framework},
          author={Christopher Hahne and Amar Aggoun},
          year={2020},
          eprint={2010.11687},
          archivePrefix={arXiv},
          primaryClass={eess.IV}
    }

Further information
===================

* check out PlenoptiCam's partner project PlenoptiSign_ capable of estimating metric light field geometries
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

.. |downloads| image:: https://img.shields.io/github/downloads/hahnec/plenopticam/total?label=Release%20downloads&style=flat-square
    :target: https://github.com/hahnec/plenopticam/releases/
    :alt: Release Downloads

.. |travis| image:: https://img.shields.io/travis/com/hahnec/plenopticam/master?style=flat-square
    :target: https://travis-ci.com/github/hahnec/plenopticam

.. |coverage| image:: https://img.shields.io/coveralls/github/hahnec/plenopticam?style=flat-square
    :target: https://coveralls.io/github/hahnec/plenopticam

.. |pypi| image:: https://img.shields.io/pypi/dm/plenopticam?label=PyPI%20downloads&style=flat-square
    :target: https://pypi.org/project/plenopticam/
    :alt: PyPI Downloads

.. |binder| image:: https://img.shields.io/badge/launch-binder-E66581.svg?style=flat-square&logo=data:image/png;base64,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
    :target: https://mybinder.org/v2/gh/hahnec/plenopticam/master?urlpath=lab
    :width: 175

.. |colab| image:: https://colab.research.google.com/assets/colab-badge.svg?style=flat-square
    :target: https://colab.research.google.com/github/hahnec/plenopticam/blob/master/examples/04_illum_demo.ipynb
    :width: 175

.. |paper| image:: http://img.shields.io/badge/paper-arxiv.2010.11687-red.svg?style=flat-square
    :target: https://arxiv.org/pdf/2010.11687.pdf
    :alt: arXiv link

.. |depth_anim| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/depth_anim.gif">

.. |depth_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/depth_demo_lores.png" max-width:"100%">

.. |pflug_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/pflug_demo_lores.png" max-width:"100%">

.. |views_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/views_demo_lores.gif" max-width:"100%">

.. |refoc_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/refoc_demo_lores.gif" max-width:"100%">

.. |src_lfp| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/color-matcher/master/tests/data/view_animation_7px.gif" width="200px" max-width:"100%">

.. |ref_lfp| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/color-matcher/master/tests/data/bee_2.png" width="200px" max-width:"100%">

.. |res_lfp| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/color-matcher/master/tests/data/view_animation_7px_hm-mkl-hm.gif" width="200px" max-width:"100%">

.. |opex_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/demo_custom.gif" height="187px" max-width:"100%">

.. |inria_demo| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/demo_illum.gif" height="187px" max-width:"100%">

.. |UoB| raw:: html

    <img src="https://3tkh0x1zl0mb1ta92c2mrvv2-wpengine.netdna-ssl.com/wp-content/uploads/2015/12/LO_KukriGB_Universities_Bedfordshire.png" width="70px">

.. |EUFramework| raw:: html

    <img src="http://www.gsa.europa.eu/sites/default/files/Seventh_Framework_Programme_logo.png" width="100px">

.. |Hahne| raw:: html

    <img src="http://www.christopherhahne.de/images/about_alt.jpg" width="15%">

.. |br| raw:: html

    <br />

.. Hyperlink aliases

.. _source: https://github.com/hahnec/plenopticam/archive/master.zip
.. _macOS: https://github.com/hahnec/plenopticam/releases/download/v0.8.0-beta/plenopticam_0.8.0.dmg
.. _Win: https://github.com/hahnec/plenopticam/releases/download/v0.8.0-beta/plenopticam_0.8.0.msi
.. _Linux: https://github.com/hahnec/plenopticam/releases/download/v0.8.0-beta/plenopticam_0.8.0.tar.gz
.. _PlenoptiSign: https://github.com/hahnec/plenoptisign/
.. _apps: https://github.com/hahnec/plenopticam/releases/

.. |WinExeDoc| replace:: **Windows protection**
.. _WinExeDoc: https://stackoverflow.com/a/65488937/10874787

.. |MacAppDoc| replace:: **macOS unidentified developer**
.. _MacAppDoc: https://osxdaily.com/2015/05/04/disable-gatekeeper-command-line-mac-osx/

.. |OpEx| replace:: **OpEx dataset**
.. _OpEx: https://ndownloader.figshare.com/files/5201452

.. |INRIA| replace:: **INRIA dataset**
.. _INRIA: https://www.irisa.fr/temics/demos/IllumDatasetLF/index.html

.. |Stanford| replace:: **Stanford dataset**
.. _Stanford: http://lightfields.stanford.edu/mvlf/

.. |IllumTar| replace:: *using your own Illum data*
.. _IllumTar: https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/build/html/guide.html