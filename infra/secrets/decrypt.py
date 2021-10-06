import logging
import os
import sys
sys.path.append("../..//shared")
from encrypt_decrypt_file import decrypt_file

DECRYPTED_FILE = 'secrets.json'
ENCRYPTED_FILE = 'secrets.json.encrypted'

logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
#cmk_id, cmk_arn = retrieve_cmk('Pulumi State Encrypt Key')
if decrypt_file(DECRYPTED_FILE):
    logging.info("%d decrypted to %d", ENCRYPTED_FILE, DECRYPTED_FILE)
os.rename(f"{DECRYPTED_FILE}.decrypted",DECRYPTED_FILE)
