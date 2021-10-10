import sys
import yaml
import argparse
import bootstrap
import pprint
import importlib

def dynamic_import(module):
    return importlib.import_module(module)

def destroy(project):
    """Destroy project"""
    module = dynamic_import(f"infra.{project}.main")
    module.stacked(environment,'destroy')

parser = argparse.ArgumentParser(description='Destroy all infrastructure in a stack.')
parser.add_argument('-a', '--aws-region', required=False, default='us-east-1')
parser.add_argument('-e', '--environment', help='the environment of the stack', required=True, default='dev')
parser.add_argument('-p', '--project', help='an individual project to deploy', required=False)
args = parser.parse_args()

environment = args.environment
if args.project:
    destroy(args.project)
else:
    data = bootstrap.get_config(environment, "environments")
    infra_projects = data['infra']
    for project in infra_projects:
        destroy(args.project)
