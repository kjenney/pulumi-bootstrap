import argparse
import json
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os

sys.path.append("../../shared")
from bootstrap import *

# Deploy CodePipeline with CodeBuild projects for each piece of infra

def pulumi_program():
    config = pulumi.Config()
    infra_projects = config.require('infra_projects')
    infra_projects = json.loads(infra_projects)
    environment = config.require('environment')
    create_pipeline(infra_projects, environment)
    #create_webhook()

stack = manage(args(), 'pipeline', pulumi_program, json.dumps(['secrets','vpc','pipeline']))


