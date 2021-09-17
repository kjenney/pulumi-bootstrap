import logging
import sys
sys.path.append("../..//shared")
from encrypt_decrypt_file import retrieve_cmk, encrypt_file

encrypted_file = 'secrets.json.encrypted'
decrypted_file = 'secrets.json'
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
cmk_id, cmk_arn = retrieve_cmk('Pulumi State Encrypt Key')
if encrypt_file(decrypted_file, cmk_arn):
    logging.info(f'{decrypted_file} encrypted to '
             f'{encrypted_file}')