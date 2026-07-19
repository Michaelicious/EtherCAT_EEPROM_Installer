UI for writting EtherCAT EEPROM .bin files.


Verison:    V1.6

Author:     Michael.grinberg@stxim.com

Dependencies:
- Works only with .bin files, can be created in TwinCAT from .xml file.
- Network Card must be real-time supporting (Usually intel chipsets), otherwise software will return writeSDO expections.
- Install latest [NPCAP](https://npcap.com/#download) Packet Sniffer in API-Compatible Mode (Checkmark during installation) 


Changelog:
V1.6:
Device EEPROM is now always read at full chip length (4096 bytes) instead of the first 1024 bytes, so 0xFF-padded regions are shown in the hex view
Write/verify comparison unchanged — still judged on the region the BIN file covers
Fixed the command-line script (ec_install_eeprom.py) passing arguments in the wrong order and always exiting on a broken file-type check

V1.5:
Differing bytes between the BIN file and the device EEPROM are now highlighted in orange in both hex views

V1.4:
Fixed post-write verification always failing (device EEPROM read returned double the requested byte count, so it never matched the BIN file)
Added application icon and STXi logo to the UI

V1.3:
Updated UI
Added option to read from drive

V1.2:
Added Human Readble translation of EEPROM binary contant

V1.1:
Create UI, Fixed no result variable

V1 : 
Script, option added of getting eeprom file location as an input, or using default name