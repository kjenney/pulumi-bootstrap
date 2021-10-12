import argparse
from common import dynamic_import, get_config

def deploy(project):
    """Deploy project"""
    module = dynamic_import(f"infra.{project}.main")
    module.stacked(environment)

parser = argparse.ArgumentParser(description='Deploy all infrastructure in a stack.')
parser.add_argument('-a', '--aws-region', required=False, default='us-east-1')
parser.add_argument('-e', '--environment', help='the environment of the stack', required=True, default='dev')
parser.add_argument('-p', '--project', help='an individual project to deploy', required=False)
args = parser.parse_args()

environment = args.environment
if args.project:
    deploy(args.project)
else:
    data = get_config(environment, "environments")
    if data:
        infra_projects = data['infra']
        for project in infra_projects:
            deploy(args.project)
    else:
        print(f"ERROR: Invalid environment {environment}")
        exit(1)
