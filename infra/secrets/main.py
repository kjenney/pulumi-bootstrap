import argparse
import boto3
import json
import logging
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os

sys.path.append("../..//shared")
from bootstrap import *
from encrypt_decrypt_file import retrieve_cmk, decrypt_file

# Decrypting Secrets

decrypted_file = 'secrets.json'
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(message)s')
#cmk_id, cmk_arn = retrieve_cmk('Pulumi State Encrypt Key')
if decrypt_file(decrypted_file):
    logging.info(f'{decrypted_file}.encrypted decrypted to '
             f'{decrypted_file}')
os.rename(f"{decrypted_file}.decrypted",decrypted_file) 

# Deploy Secrets to Pulumi State

def pulumi_program():
    f = open('secrets.json')
    secrets_dict = json.load(f)
    for k,v in secrets_dict.items():
        #pulumi.export(k, pulumi.secret(v))
        pulumi.export(k,v)

stack = manage(args(), 'secrets', pulumi_program)
os.remove(decrypted_file)

