import sys
import os
import json
import logging
import pulumi

sys.path.append("../..//shared")
from bootstrap import manage, args
from encrypt_decrypt_file import decrypt_file

# Decrypting Secrets Infra Deployment

DECRYPTED_FILE = 'secrets.json'
ENCRYPTED_FILE = 'secrets.json.encrypted'

logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
if decrypt_file(DECRYPTED_FILE):
    logging.info("%s decrypted to %s", ENCRYPTED_FILE, DECRYPTED_FILE)
os.rename(f"{DECRYPTED_FILE}.decrypted",DECRYPTED_FILE)

# Deploy Secrets to Pulumi State

def pulumi_program():
    """Pulumi Program"""
    #file = open('secrets.json')
    try:
        with open(DECRYPTED_FILE, 'rb') as file:
            secrets_dict = json.load(file)
    except IOError as error:
        logging.error(error)
        return False
    for key,value in secrets_dict.items():
        pulumi.export(key, pulumi.Output.secret(value))
    return True

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)
os.remove(DECRYPTED_FILE)
