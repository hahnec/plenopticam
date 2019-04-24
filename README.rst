===========
Plenopticam
===========

A light field photograph application for computational change of perspective view and synthetic focus based on a Standard Plenoptic Camera (SPC).

|license| |code| |repo| |downloads|

Installation
------------

    1. install Python from https://www.python.org/
    2. download the source_ using ``$ git clone https://github.com/hahnec/plenopticam.git``
    3. go to the root directory ``$ cd plenopticam``
    4. install with ``$ python setup.py install`` from the root directory


Usage
-----

If installation ran smoothly, enter the following

    ``$ plenopticam -g``

to the command line after which a tidy and instructive user interface will pop up (see below).

|gui|

.. |gui| raw:: html

    <img src="./docs/img/gui_v3.png" width="700px">

Results
-------

|OPEX|_
=============================

|spiderman|

* custom plenoptic camera built at the Univ. of Bedfordshire

.. |spiderman| image:: ./docs/img/spiderman.gif

.. |OPEX| replace:: Optics Express dataset
.. _OPEX: https://ndownloader.figshare.com/files/5201452

|Irisa|_
========================

|fruits|

.. |fruits| raw:: html

    <img src="./docs/img/fruits.gif" height="200px">

.. * |Stanford|_

.. |Irisa| replace:: Irisa dataset
.. _Irisa: https://www.irisa.fr/temics/demos/IllumDatasetLF/index.html

.. |Stanford| replace:: Stanford dataset
.. _Stanford: http://lightfields.stanford.edu/mvlf/


Further information
-------------------

* visit `plenoptic.info <http://www.plenoptic.info>`__ for technical details, animated figures and theoretical background

Credits
-------

Contributors
============
* `Christopher Hahne <http://www.christopherhahne.de/>`__

Sponsors
========
* `IRAC at University of Bedfordshire <https://www.beds.ac.uk/research-ref/irac/about>`__
* `7th Framework Programme under Grant EU-FP7 ICT-2010-248420 <https://cordis.europa.eu/project/rcn/94148_en.html>`__

Citation
========
If you find this work helpful, please cite the following publications:

* `Refocusing distance of a standard plenoptic camera <https://doi.org/10.1364/OE.24.021521>`__, *OpticsExpress*, `[BibTeX] <http://www.plenoptic.info/bibtex/HAHNE-OPEX.2016.bib>`__

* `Baseline and triangulation geometry in a standard plenoptic camera <https://www.plenoptic.info/IJCV_Hahne17_final.pdf>`__, *Int. J. of Comp. Vis.*, `[BibTeX] <http://plenoptic.info/bibtex/HAHNE-IJCV.2017.bib>`__



.. Image substitutions

.. |release| image:: https://img.shields.io/github/release/hahnec/plenopticam.svg?style=flat-square
    :target: https://github.com/hahnec/plenopticam/archive/master.zip
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

.. Hyperlink aliases

.. _source: https://github.com/hahnec/plenopticam/archive/master.zip