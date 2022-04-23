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

Once PlenoptiCam is ready for use (whether from source_ or as an app_), you will be provided with a default parameter set.
Start off varying these parameters as you like to see their impact on the light-field geometry.
A scientific in-depth description of the parameters below is provided in the paper_.
	
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
   * - *Calibration method*
     - Determine micro image center detection method. Use 'grid-fit' for regular MLAs, 'vign_fit' to combat severe micro image vignetting or 'corn-fit' to skip micro image sorting (experimental).
   * - *Resampling method*
     - Determine alignment method for a consistent micro image sampling grid. Use 'global' for fast computation.
   * - *Micro image patch size*
     - One-dimensional micro image size in pixels (your value may be reduced by a detected maximum)
   * - *Refocusing range*
     - Numeric start (left) and end point (right) for the refocus parameter.
   * - *Redo calibration*
     - Enforce re-calibration process
   * - *De-Vignetting*
     - Combat vignetting (white calibration image division by default)
   * - *Auto-Contrast*
     - Histogram alignment based on percentiles in luminance channel
   * - *White balance*
     - Apply channel-wise normalization
   * - *Auto-Saturation*
     - Histogram alignment based on percentiles in saturation channel
   * - *Refocus refinement*
     - Enable sub-pixel precise refocusing in steps 1 divided by *micro image size*
   * - *Scheimpflug focus*
     - Imitates tilted sensor focus with 'horizontal', 'vertical', just as upwards and downwards 'skew'
   * - *Hex-Artifact removal*
     - Rectification of potential artifacts arising from hexagonal micro image arrangements (useful for local resampling).
   * - *Depth map*
     - Disparity computation using depthy_ providing depth as a `*.ply` and `*.pfm` file.
   * - *Remove output folder*
     - Entire folder gets removed for new process if checked

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
.. _depthy: https://github.com/hahnec/depthy
.. _paper: https://arxiv.org/pdf/2010.11687.pdf

.. Indices and tables
.. ==================
.. 
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
