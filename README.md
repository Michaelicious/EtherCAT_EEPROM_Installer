Software Information
Verison:    V1.2
Author:     Michael.grinberg@stxim.com

UI for writting EtherCAT EEPROM .bin files.

Dependencies:
- Works only with .bin files, can be created in TwinCAT from .xml file.
- Network Card must be real-time supporting (Usually intel chipsets), otherwise software will return writeSDO expections.
- Install NPCAP (npcap.com) in API Compatible Mode (Checkmark during installation)

Changelog:
V1.2:
	Added Human Readble translation of EEPROM binary contant
V1.1:
	Create UI
	Fixed no result variable
V1.1 :
	option of getting eeprom file location as an input, or using default name
