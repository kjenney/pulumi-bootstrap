import argparse
import json
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os
from pprint import pprint

def pulumi_program():
    config = pulumi.Config()
    db_user = config.require_secret('db_user')
    db_pass = config.require_secret('db_pass')

    pulumi.export("db_user", db_user)
    pulumi.export("db_pass", db_pass)

def args():
    parser = argparse.ArgumentParser(description='Manage a Pulumi automation stack.')
    parser.add_argument('-n', '--project-name', required=False, default='test')
    parser.add_argument('-a', '--aws-region', required=False, default='us-east-1')
    parser.add_argument('-b', '--backend-bucket', required=True)
    parser.add_argument('-s', '--stack-name', required=False, default='dev')
    parser.add_argument('-k', '--kms-alias-name', required=True)
    parser.add_argument('-d', '--destroy', help='destroy the stack',
                        action='store_true')
    return parser.parse_args()

def manage(args, project_name, pulumi_program):
    backend_bucket = args.backend_bucket
    aws_region = args.aws_region
    kms_alias_name = args.kms_alias_name
    stack_name = f"{project_name}-{args.stack_name}"
    secrets_provider = f"awskms://alias/{kms_alias_name}"
    backend_url = f"s3://{backend_bucket}"
    environment = args.stack_name
    print(f"Deploying infra: {project_name}")
    
    project_settings=auto.ProjectSettings(
        name=project_name,
        runtime="python",
        backend={"url": backend_url}
    )

    stack_settings=auto.StackSettings(
        secrets_provider=secrets_provider)

    stack = auto.create_or_select_stack(stack_name=stack_name,
                                        project_name=project_name,
                                        program=pulumi_program,
                                        opts=auto.LocalWorkspaceOptions(project_settings=project_settings,
                                                                        secrets_provider=secrets_provider,
                                                                        stack_settings={stack_name: stack_settings}))


    print("successfully initialized stack")

    # for inline programs, we must manage plugins ourselves
    print("installing plugins...")
    stack.workspace.install_plugin("aws", "v4.0.0")
    stack.workspace.install_plugin("github", "v4.0.0")
    print("plugins installed")

    # set stack configuration from argparse arguments, local environment config and/or secrets
    print("setting up config")
    stack.set_config("aws_region", auto.ConfigValue(value=aws_region))
    stack.set_config("environment", auto.ConfigValue(value=environment))
    print("config set")

    print("refreshing stack...")
    stack.refresh(on_output=print)
    print("refresh complete")

    if args.destroy:
        print("destroying stack...")
        stack.destroy(on_output=print)
        print("stack destroy complete")
        sys.exit()

    print("updating stack...")
    up_res = stack.up(on_output=print)
    print(f"update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}")
    return up_res

    if exists(f"environments/{environment}.yaml"):
        with open(f"environments/{environment}.yaml", "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

# Deploy CodePipeline which will in turn deploy the rest of the infrastructure
stack = manage(args(), 'secrets', pulumi_program)

