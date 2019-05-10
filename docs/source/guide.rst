.. Plenoptisign documentation master file, created by
   sphinx-quickstart on Sat Mar 16 18:50:44 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========
User Guide
==========

.. toctree::
   :maxdepth: 3
   :caption: Contents:

==========

Once Plenoptisign is ready for use (whether from source_, as an app_ or `CGI demo`_), you will be provided with a default parameter set.
You can start off varying these parameters as you like to see their impact on the light field geometry.
As of version 1.1.0, the input and output parameters are defined as shown in the following.

Optical parameters
------------------

.. list-table:: Input Parameters
   :widths: 4 15
   :header-rows: 1

   * - Notation
     - Description
   * - :math:`p_p`
     - pixel pitch
   * - :math:`f_s`
     - micro lens focal length
   * - :math:`H_{1s}H_{2s}`
     - micro lens principal plane spacing
   * - :math:`p_m`
     - micro lens pitch
   * - :math:`d_{A'}`
     - exit pupil distance
   * - :math:`f_U`
     - main lens focal length
   * - :math:`H_{1U}H_{2U}`
     - main lens principal plane spacing
   * - :math:`d_f`
     - main lens focusing distance
   * - :math:`F\#`
     - F-number
   * - :math:`a`
     - refocusing shift parameter
   * - :math:`M`
     - micro image resolution
   * - :math:`G`
     - virtual camera gap
   * - :math:`\Delta x`
     - triangulation disparity

|

.. list-table:: Geometry Results
   :widths: 4 15
   :header-rows: 1

   * - Notation
     - Description
   * - :math:`d_a`
     - refocusing distance
   * - :math:`DoF`
     - depth of field
   * - :math:`d_{a-}`
     - narrow DoF border
   * - :math:`d_{a+}`
     - narrow DoF border
   * - :math:`B_G`
     - baseline
   * - :math:`\Phi_G`
     - viewpoint tilt angle
   * - :math:`Z_{(G, \Delta x)}`
     - triangulation distance

Design trends
-------------
Generally, it can be stated that the refocusing distance :math:`d_a` and triangulation distance :math:`Z_{(G, \Delta x)}`  drop with

    * ascending shift parameter :math:`a` or ascending disparity :math:`\Delta x`
    * enlarging micro lens focal length :math:`f_s`
    * reducing objective lens focal length :math:`f_U`

and vice versa. Similarly, the baseline :math:`B_G`, a substantial triangulation parameter, grows with

    * larger main lens focal length :math:`f_U`
    * shorter micro lens focal length :math:`f_s`
    * decreasing focusing distance :math:`d_f`
    * increasing absolute virtual camera spacing :math:`|G|`

It is worth noting that depth planes at :math:`a=0` or :math:`\Delta x=0` are located at the focusing distance :math:`d_f`.

In case of the app_ version, graphical plots will be displayed supporting you in the decision making.

.. Hyperlink aliases

.. _source: https://github.com/hahnec/plenoptisign/archive/master.zip
.. _app: https://github.com/hahnec/plenoptisign/releases/tag/v1.0.0-beta
.. _CGI demo: http://www.plenoptic.info/pages/coding.html

.. Indices and tables
.. ==================
.. 
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
