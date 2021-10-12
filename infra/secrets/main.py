import sys
import os
import json
import logging
import pulumi
from codebuild import CodeBuildProject, CodeBuildProjectArgs
from common import AutoTag, manage
from encrypt_decrypt_file import decrypt_file

# Deploy Secrets to Pulumi State
# Decrypting Secrets Infra Deployment

CURRENT_DIR = os.path.dirname(__file__)
DECRYPTED_FILE = f"{CURRENT_DIR}/secrets.json"
ENCRYPTED_FILE = f"{CURRENT_DIR}/secrets.json.encrypted"

def decrypt_secrets():
    """Decrypting secrets for laoding into stack"""
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(asctime)s: %(message)s')
    if decrypt_file(DECRYPTED_FILE):
        logging.info("%s decrypted to %s", ENCRYPTED_FILE, DECRYPTED_FILE)
    os.rename(f"{DECRYPTED_FILE}.decrypted",DECRYPTED_FILE)

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    project_name = pulumi.get_project()
    AutoTag(environment)
    codebuild_project = CodeBuildProject('test',
        CodeBuildProjectArgs(
            environment=environment,
            project_name=project_name,
            codebuild_image=codebuild_image,
        ))
    decrypt_secrets()
    pulumi.export("codebuild_project_id", codebuild_project.bucket_id)
    try:
        with open(DECRYPTED_FILE, 'rb') as file:
            secrets_dict = json.load(file)
    except IOError as error:
        logging.error(error)
        return False
    for key,value in secrets_dict.items():
        pulumi.export(key, pulumi.Output.secret(value))
    os.remove(DECRYPTED_FILE)
    return True

def stacked(environment, action='deploy'):
    """Manage the stack"""
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)

def test():
    """Test the stack"""
    print("Run something useful here")