import json
import os
import boto3
import yaml

s3 = boto3.resource(
    's3',
    region_name='us-east-1'
)

environment = os.environ.get('environment')

def buildspec_functional(environment, branch):
    """Create the CodeBuild Job that will be used for Functional Testing"""
    return {'version': '0.2',
            'env': {
                'secrets-manager': {
                    'GITHUB_TOKEN': f"webhook-github-token-secret-{environment}"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'python': '3.x'
                    },
                    'commands': [
                        'curl -fsSL https://get.pulumi.com | sh',
                        'PATH=$PATH:/root/.pulumi/bin'
                    ]
                },
                'pre_build': {
                    'commands': [
                        f"git clone --branch {branch} https://$(GITHUB_TOKEN)@github.com/kjenney/pulumi-bootstrap.git"
                    ]
                },
                'build': {
                    'commands': [
                        'cd pulumi-bootstrap',
                        'pip install -r requirements.txt'
                    ]
                }
            }}

def buildspec_main(environment):
    """Create the CodeBuild Job that will be used to clone the main branch"""
    return {'version': '0.2',
            'env': {
                'secrets-manager': {
                    'GITHUB_TOKEN': f"webhook-github-token-secret-{environment}"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'python': '3.x'
                    },
                    'commands': [
                        'curl -fsSL https://get.pulumi.com | sh',
                        'PATH=$PATH:/root/.pulumi/bin'
                    ]
                },
                'pre_build': {
                    'commands': [
                        "git clone https://$(GITHUB_TOKEN)@github.com/kjenney/pulumi-bootstrap.git"
                    ]
                },
                'build': {
                    'commands': [
                        'cd pulumi-bootstrap',
                        'pip install -r requirements.txt'
                    ]
                }
            }}

def handler(event, context):
    """Gets PR events
    Check to see if the PR is open
    Write an object to S3 which triggers one of two jobs
    """
    body = event['body']
    body = json.loads(body)
    # If the Pull Request is not closed - let's do something
    if not body['pull_request']['closed_at']:
        # If the Pull Request is merged Zip up the source to S3 via CodeBuild else Lint the code
        print('Copy buildspec to S3 bucket to kick off CodeBuild')
        if body['pull_request']['merged_at']:
            s3_bucket_main = os.environ.get('s3_bucket_main')
            buildspec = buildspec_main(environment)
            content=yaml.dump(buildspec, indent=4, default_flow_style=False)
            s3.Object(s3_bucket_main, 'buildspec.yml').put(Body=content)
        else:
            s3_bucket_functional = os.environ.get('s3_bucket_functional')
            # Branch metadata includes origin and branch - splitting the string to only include the branch
            branch = body['pull_request']['head']['label'].split(':')[1]
            buildspec = buildspec_functional(environment, branch)
            content=yaml.dump(buildspec, indent=4, default_flow_style=False)
            s3.Object(s3_bucket_functional, 'buildspec.yml').put(Body=content)
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }