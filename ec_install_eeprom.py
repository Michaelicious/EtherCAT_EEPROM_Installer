import pysoem, time
from typing import Literal
from pysoem.pysoem import CdefSlave, Master


def read_eeprom_bin_file(path)->bytes:
    with open(path, 'rb') as file:
        data = file.read()
        msg = f'EEPROM binary file read: {len(data)} bytes'
        print(msg)
        return data
    return b''

def read_eeprom_data(slave:CdefSlave, eeprom_size:int=1024)->bytearray:
    # eeprom_data = []
    # stop = 0
    binr = bytearray()
    
    # eeprom_read() returns 4 bytes per call and takes a *word* address, so to
    # read `eeprom_size` bytes we step word addresses 0,2,4,… up to eeprom_size//2.
    for i in range(0, eeprom_size // 2, 2):
        read = slave.eeprom_read(i)
        for b in read:
            binr.append(b)
    return binr

def write_eeprom_data(slave:CdefSlave, bin_file:bytes):
    retries = 0
    if not isinstance(bin_file, bytes):
        print(f'Error: bin_file is not bytes, but {type(bin_file)}')
        return False
    
    while True and retries < 3:
        try: 
            it = iter(bin_file) # Single iterable object to bind 2 bin_file objects
            for i, (b1, b2) in enumerate(zip(it, it)):
                slave.eeprom_write(i, bytes([b1, b2])) # type: ignore
            print("eeprom write finished")
            return True
        except Exception as e: 
            print(f'eeprom write exception{e}\nRetrying ...')
            retries += 1
            time.sleep(0.5)
            continue
    print(f'Error: eeprom write failed after {retries} retries')
    return False

def verify_eeprom_data(slave:CdefSlave,eeprom_bin_file):
    # --- 
    eeprom_data_read = read_eeprom_data(slave)
    return eeprom_data_read == eeprom_bin_file

def setup_ethercat()-> Master | Literal[False]:
        def _open_and_config_init(nic):
            try:    
                master.open(nic)  
                return master.config_init()
            except Exception as e:
                print(e)
                return 0
            
        def Connection()->bool:
            nic_list = pysoem.find_adapters()
            for nic in nic_list:
                device_count = _open_and_config_init(nic.name)
                if device_count > 0: return True
                else: master.close()
            print(f"No ethercat slaves found. device_count = {device_count}. Master is closing ...")
            return False
        
        master = pysoem.Master()
        tries = 0
        while tries < 5:
            print(f"Connection try No {tries}")
            if Connection():
                print(f"EtherCAT connection found {len(master.slaves)} slaves")
                return master
            else: 
                print(f"Connetion retry No {tries}")
                tries += 1
            time.sleep(1.5)
        print("Connection exit due to too many attempts")
        return False  

import os,sys

BIN_FILE = 'ESCeepromdata.bin'
VERSION = '1.5'

if __name__ == "__main__":
    
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        current_path = os.path.dirname(sys.executable)
    else:
        # Running as a normal script
        current_path = os.path.dirname(os.path.abspath(__file__))
    
    print(current_path)
    bin_file_path_found = os.path.join(current_path, BIN_FILE)
    print(f'found default EEPROM binary file: {bin_file_path_found}: {os.path.exists(bin_file_path_found)}')
    bin_file_path = input(f'Enter the path of EEPROM binary file OR press ENTER to use default {BIN_FILE}: \n')
    if not bin_file_path:
        bin_file_path = bin_file_path_found
    if not os.path.exists(bin_file_path):
        print(f'File {bin_file_path} does not exist. Exiting ...')
        time.sleep(3)
        sys.exit(1)
    try:
        print(f'Using EEPROM binary file: {bin_file_path}')
        input(f'Press Enter to start reading EEPROM data from {bin_file_path} ...')
        eeprom_bin_file = read_eeprom_bin_file(bin_file_path)
        master = setup_ethercat()
        if master:
            slave = master.slaves[0]
            print(f'Comparing EEPROM data with {BIN_FILE}')
            if not isinstance(eeprom_bin_file,bytearray):
                print(f'Error reading EEPROM binary file {bin_file_path}. Exiting ...')
                sys.exit(1)
            elif not verify_eeprom_data(eeprom_bin_file,slave):
                print('Writing EEPROM data')
                write_eeprom_data(eeprom_bin_file,slave)
                res = verify_eeprom_data(eeprom_bin_file,slave)
                print(f'EEPROM data written. Verify: {res}')
            else: 
                print(f'EEPROM data is up to date with {BIN_FILE}')
        else: 
            print('EtherCAT connection failed')
    except KeyboardInterrupt:
        print('KeyboardInterrupt: Exiting...')
    except Exception as e:
        print(f'Exception: {e}')
    finally:
        input(f'Press Enter to exit ...')
    