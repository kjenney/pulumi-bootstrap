import logging
import os
import sys
sys.path.append("../..//shared")
from encrypt_decrypt_file import retrieve_cmk, decrypt_file

decrypted_file = 'secrets.json'
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
#cmk_id, cmk_arn = retrieve_cmk('Pulumi State Encrypt Key')
if decrypt_file(decrypted_file):
    logging.info(f'{decrypted_file}.encrypted decrypted to '
             f'{decrypted_file}')
os.rename(f"{decrypted_file}.decrypted",decrypted_file) 