import argparse
import json

from yaml.events import CollectionEndEvent
import pulumi
import pulumi_aws as aws
import pulumi_github as github
from pulumi import automation as auto
import sys
import yaml
import zipfile
import os

sys.path.append("../../shared")
from bootstrap import *

project_name = os.path.basename(os.getcwd())

# Deploy Lambda with CodeBuild projects for each piece of infra

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']

    # Export GitHub Token to provision the Webhook
    secrets = pulumi.StackReference(f"secrets-{environment}")
    github_token_secret = secrets.get_output("github_token")
    github_provider = github.Provider(resource_name='github_provider', token=github_token_secret)
    
    label_tags = {
        "Project" : project_name,
        "ManagedBy"  : 'Pulumi',
        "Environment": environment,
    }

    id = "-".join(label_tags.values())

    # Create the role for the Lambda to assume
    lambda_role = aws.iam.Role(f"{id}-lambda-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "lambda.amazonaws.com",
                    },
                    "Effect": "Allow",
                    "Sid": "",
                }]
        }),
        tags = label_tags,
    )

    # Attach the fullaccess policy to the Lambda role created above
    role_policy_attachment = aws.iam.RolePolicyAttachment("lambdaRoleAttachment",
        role=lambda_role,
        policy_arn=aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE)

    zipfile.ZipFile('/tmp/source.zip', mode='w').write('lambda/webhook.py','webhook.py')

    # Create the lambda to execute
    lambda_function = aws.lambda_.Function(f"{id}-lambda-function",
        code=pulumi.FileArchive('/tmp/source.zip'),
        runtime="python3.8",
        role=lambda_role.arn,
        handler="webhook.handler",
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "projects": ','.join(infra_projects),
            },
        ))

    # Give API Gateway permissions to invoke the Lambda
    lambda_permission = aws.lambda_.Permission("lambdaPermission",
        action="lambda:InvokeFunction",
        principal="apigateway.amazonaws.com",
        function=lambda_function)

    # Set up the API Gateway
    apigw = aws.apigatewayv2.Api(f"httpApiGateway-{environment}",
        protocol_type="HTTP",
        route_key="POST /",
        target=lambda_function.invoke_arn)

    pulumi.export('api_base_url', apigw.api_endpoint)
    pulumi.export(f"lambda_function_arn", lambda_function.arn)

    # Register webhook
    webhook = github.RepositoryWebhook(f"bootstrap-webhook-{environment}",
        repository='pulumi-bootstrap',
        configuration=github.RepositoryWebhookConfigurationArgs(
            url=apigw.api_endpoint,
            content_type="json",
            insecure_ssl=False,
        ),
        active=True,
        events=["pull_request"],
        opts=pulumi.ResourceOptions(provider=github_provider))

stack = manage(args(), project_name, pulumi_program)