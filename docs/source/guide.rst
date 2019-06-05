.. PlenoptiCam documentation master file, created by
   sphinx-quickstart on Sun Mar 17 00:36:29 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========
User Guide
==========

.. toctree::
   :maxdepth: 3
   :caption: Contents:

==========

Settings
--------

Once PlenoptiCam is ready for use (whether from source_ or as an app_), you will be provided with a default parameter set. Start off varying these parameters as you like to see their impact on the light field geometry.
	
.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Description
   * - *Light field image*
     - Path to plenoptic image file
   * - *Calibration source*
     - Path to white image calibration file
   * - *Metadata file*
     - Path to file where calibration properties are stored (contents are specific to *PlenoptiCam*)
   * - *Micro image patch size*
     - One-dimensional micro image size in pixels (detected maximum is reduced via cropping)
   * - *Force re-calibration*
     - Redo calibration process
   * - *Automatic white balance*
     - Implementation based on least-squares fit
   * - *Refocus refinement*
     - Enable sub-pixel precise refocusing
   * - *Scheimpflug focus*
     - Imitates tilted sensor focus with 'horizontal', 'vertical', just as upwards and downwards 'skew'
   * - *Override output folder*
     - Entire folder gets removed if checked 

Using your own Lytro Illum
--------------------------

In order to acquire the tar-archive from your own Illum camera, use the following steps:

1. Go to *SETTINGS* => *GENERAL* in your camera's menu
2. Press *TRANSFER PAIRING DATA TO SD CARD*
3. Copy the *xxx.tar* file to your desired calibration folder (Note: keep the original tar filename)
4. Point to the tar-file at *calibration source* using the *Browse* button (point to parent folder if *Pick folder* is checked)
5. Select your *xxx.lfr* file from the SD card using the *Browse* button at *light field image*

|illumtar|

.. If something fails
.. ------------------
.. 
.. on macOS: 
.. 1. right-click on plenopticam app and *Show Package Contents*
.. 2. Go to *Contents* => *MacOS*
.. 3. open *plenopticam*
.. 4. start the *Process* and watch the output on the Terminal window
.. 5. copy the last few lines and open an issue_ on GitHub and
.. 	- provide links to the files you used (lightfield image + calibration image)
.. 	- paste the last few lines of the console window

.. Image substitutions

.. |illumtar| raw:: html

    <img src="https://raw.githubusercontent.com/hahnec/plenopticam/master/docs/img/illum_menu_settings.png" max-width="100%">


.. Hyperlink aliases

.. _source: https://github.com/hahnec/plenopticam/archive/master.zip
.. _app: https://github.com/hahnec/plenopticam/releases/
.. _issue: https://github.com/hahnec/plenopticam/issues/new

.. Indices and tables
.. ==================
.. 
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
