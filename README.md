UI for writting EtherCAT EEPROM .bin files.


Verison:    V1.3

Author:     Michael.grinberg@stxim.com

Dependencies:
- Works only with .bin files, can be created in TwinCAT from .xml file.
- Network Card must be real-time supporting (Usually intel chipsets), otherwise software will return writeSDO expections.
- Install latest [NPCAP](https://npcap.com/#download) Packet Sniffer in API-Compatible Mode (Checkmark during installation) 


Changelog:
V1.3:
Updated UI
Added option to read from drive

V1.2:
Added Human Readble translation of EEPROM binary contant

V1.1:
Create UI, Fixed no result variable

V1 : 
Script, option added of getting eeprom file location as an input, or using default name