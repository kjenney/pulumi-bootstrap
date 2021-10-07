import logging
import sys
sys.path.append("../..//shared")
from encrypt_decrypt_file import retrieve_cmk, encrypt_file

ENCRYPTED_FILE = 'secrets.json.encrypted'
DECRYPTED_FILE = 'secrets.json'

logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
cmk_id, cmk_arn = retrieve_cmk('Pulumi State Encrypt Key')
if encrypt_file(DECRYPTED_FILE, cmk_arn):
    logging.info("%s decrypted to %s", DECRYPTED_FILE, ENCRYPTED_FILE)
