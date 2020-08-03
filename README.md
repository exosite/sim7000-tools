# sim7000-tools
A few scripts for testing the SIM7000E cellular module.

## Installation
  * Install python3
  * Install Dependency by `pip install -r requirements.txt`


## Usage

  * Put your credentials under the cert folder.

  * Run the script with a command option.
    * i.e. ```python3 sim7000.py ping```

## Commands

  * ```python3 sim7000.py --reboot```
    * Reboot the chipset
    (Note: the chipset will disconnect the serial port temporary which will breaking the python script)

  * ```python3 sim7000.py ping```
    * Check we can ping google


  * ```python3 sim7000.py ntp```
    * Get the time from an NTP server


  * ```python3 sim7000.py certs-check```
      * Check if the 3 certs (defined by variables at near the top of the script) are present on the device.
      * It will report the size in bytes if it is present, or an error if it isn't there.
      * Doesn't seem to be a list files function on the sim7000 :-(.


  * ```python3 sim7000.py certs-delete```
      * Delete the 3 certs (defined by variables at near the top of the script) from the device.


  * ```python3 sim7000.py certs-load```
    * Load the 3 certs (defined by variables at near the top of the script) from the folder (specified by variable) to the correct location on the device.


  * ```python3 sim7000.py mqtt-cacert```
    * Use the certs that being loaded into the flash to make connection to my testing IoT Connector mqtt://f10310uj1y9sw0000.m2.exosite.io
