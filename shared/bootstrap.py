import argparse
import json
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os
from pprint import pprint

# Repeatable process for creating/update Pulumi stacks
# Assumes:
#    * pulumi automation module as auto
#    * pulumi-aws module as aws
#    * json module as json
#    * pulumi cli is installed
#    * stack-name corresponds to an environment (i.e. prod, staging, dev)

def create_codebuild_pipeline_project(environment, buckets, roles, project_name, github_connection):
    """Create a CodeBuild Pipeline Project whose source is that takes the source code after a merge to main"""
    codebuild_role_arn = roles[f"codebuild_role_{project_name}_arn"]
    codebuild_role_id = roles[f"codebuild_role_{project_name}_id"]
    # Use the existing S3 bucket
    codebuild_bucket = buckets[f"codebuild_{project_name}_bucket_id"]
    #codepipeline_bucket = buckets["codepipeline_bucket_id"]
    # Create IAM policy to create github connections for CodeBuild Projects
    codebuild_policy = aws.iam.RolePolicy(f"codebuldPolicy_{project_name}_{environment}",
        role=codebuild_role_id,
        policy=pulumi.Output.all(github_connection=github_connection.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                "Effect": "Allow",
                "Action": [
                    "codestar-connections:GetConnection",
                    "codestar-connections:UseConnection",
                    "codestar-connections:ListTagsForResource"
                ],
                "Resource": "{args['github_connection']}"
                }}
            ]
        }}
    """))
    codebuild_project = aws.codebuild.Project(f"{project_name}-{environment}",
        name=f"{project_name}-{environment}",
        description=f"codebuild project for {project_name} in {environment}",
        build_timeout=5,
        service_role=codebuild_role_arn,
        artifacts=aws.codebuild.ProjectArtifactsArgs(
            type="CODEPIPELINE",
        ),
        cache=aws.codebuild.ProjectCacheArgs(
            type="S3",
            location=codebuild_bucket,
        ),
        environment=aws.codebuild.ProjectEnvironmentArgs(
            compute_type="BUILD_GENERAL1_SMALL",
            image="aws/codebuild/standard:1.0",
            type="LINUX_CONTAINER",
            image_pull_credentials_type="CODEBUILD",
        ),
        logs_config=aws.codebuild.ProjectLogsConfigArgs(
            cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
                group_name="log-group",
                stream_name="log-stream",
            ),
            s3_logs=aws.codebuild.ProjectLogsConfigS3LogsArgs(
                status="ENABLED",
                location=codebuild_bucket.apply(lambda id: f"{id}/build-log"),
            ),
        ),
        source=aws.codebuild.ProjectSourceArgs(
            type="CODEPIPELINE",
            buildspec=f"infra/{project_name}/buildspec.yml"
        ),
        tags={
            "Name": project_name,
            "Environment": environment,
            "Managed By": "Pulumi",
        }
    )

def create_codebuild_pullrequest_project(environment, buckets, roles, project_name):
    """Create a CodeBuild Project whose source is from a Webhook triggered when a Pull Request is
    created or updated
    """
    codebuild_role_arn = roles[f"codebuild_role_{project_name}_arn"]
    codebuild_role_id = roles[f"codebuild_role_{project_name}_id"]
    # Use the existing S3 bucket
    codebuild_bucket = buckets[f"codebuild_{project_name}_bucket_id"]
    codebuild_project = aws.codebuild.Project(f"{project_name}-{environment}-pullrequest",
        name=f"{project_name}-{environment}",
        description=f"codebuild project for {project_name} in {environment} - Pull Request",
        build_timeout=5,
        service_role=codebuild_role_arn,
        artifacts=aws.codebuild.ProjectArtifactsArgs(
            type="CODEPIPELINE",
        ),
        cache=aws.codebuild.ProjectCacheArgs(
            type="S3",
            location=codebuild_bucket,
        ),
        environment=aws.codebuild.ProjectEnvironmentArgs(
            compute_type="BUILD_GENERAL1_SMALL",
            image="aws/codebuild/standard:1.0",
            type="LINUX_CONTAINER",
            image_pull_credentials_type="CODEBUILD",
        ),
        logs_config=aws.codebuild.ProjectLogsConfigArgs(
            cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
                group_name="log-group",
                stream_name="log-stream",
            ),
            s3_logs=aws.codebuild.ProjectLogsConfigS3LogsArgs(
                status="ENABLED",
                location=codebuild_bucket.apply(lambda id: f"{id}/build-log"),
            ),
        ),
        source=aws.codebuild.ProjectSourceArgs(
            type="CODEPIPELINE",
            buildspec=f"infra/{project_name}/buildspec_pr.yml"
        ),
        tags={
            "Name": project_name,
            "Environment": environment,
            "Managed By": "Pulumi",
        }
    )

def create_codebuild_pullrequest_webhook(environment, project_name):
    """Create a Webhook for a CodeBuild Project"""
    webhook = aws.codebuild.Webhook(f"{project_name}-{environment}",
        project_name=f"{project_name}-{environment}-pullrequest",
        build_type="BUILD",
        filter_groups=[aws.codebuild.WebhookFilterGroupArgs(
            filters=[
                aws.codebuild.WebhookFilterGroupFilterArgs(
                    type="EVENT",
                    pattern="PULL_REQUEST_CREATED",
                ),
                aws.codebuild.WebhookFilterGroupFilterArgs(
                    type="EVENT",
                    pattern="PULL_REQUEST_UPDATED",
                ),
            ],
        )])

def create_pipeline(infra_projects, buckets, roles, environment):
    """Create a CodePipeline from a list of Infrastructure, 
    a list of S3 Bucket ID's,
    a list of IAM Role ARN's and ID's,
    and an environment name
    """
    # Get GitHub Connection
    github_connection = aws.codestarconnections.Connection("pipeline", provider_type="GitHub")
    # Use the existing S3 bucket
    codepipeline_bucket = buckets["codepipeline_bucket_id"]
    codepipeline_stages = [
        aws.codepipeline.PipelineStageArgs(
            name="Source",
            actions=[aws.codepipeline.PipelineStageActionArgs(
                name="Source",
                category="Source",
                owner="AWS",
                provider="CodeStarSourceConnection",
                version="1",
                output_artifacts=["source_output"],
                configuration={
                    "ConnectionArn": github_connection.arn,
                    "FullRepositoryId": "kjenney/pulumi-bootstrap",
                    "BranchName": "main",
                },
            )],
        )
    ]
    # Create the Build stages
    for p in infra_projects:
        codepipeline_stages.append(
            aws.codepipeline.PipelineStageArgs(
                name=f"Build-{p}",
                actions=[aws.codepipeline.PipelineStageActionArgs(
                    name=f"Build-{p}",
                    category="Build",
                    owner="AWS",
                    provider="CodeBuild",
                    input_artifacts=["source_output"],
                    output_artifacts=[f"build_output-{p}"],
                    version="1",
                    configuration={
                        "ProjectName": f"{p}-{environment}",
                    },
                )],
            )
        )

    # Create the CodePipeline
    codepipeline = aws.codepipeline.Pipeline("codepipeline",
        name=f"pipeline-{environment}",
        artifact_store=aws.codepipeline.PipelineArtifactStoreArgs(
            location=codepipeline_bucket,
            type="S3",
        ),
        role_arn=roles['codepipeline_role_arn'],
        tags={
            "Name": 'pipeline',
            "Environment": environment,
            "Managed By": "Pulumi",
        },
        stages=codepipeline_stages
    )
    codepipeline_policy = aws.iam.RolePolicy("codepipelinePolicy",
        role=roles['codepipeline_role_id'],
        policy=pulumi.Output.all(github_connection=github_connection.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                "Effect": "Allow",
                "Action": [
                    "codestar-connections:UseConnection"
                ],
                "Resource": "{args['github_connection']}"
                }}
            ]
            }}
            """))
    pulumi.export(f"codepipeline_arn", codepipeline.arn)
    pulumi.export(f"codepipeline_id", codepipeline.id)
    for project_name in infra_projects:
        create_codebuild_pipeline_project(environment, buckets, roles, project_name, github_connection)
        create_codebuild_pullrequest_project(environment, buckets, roles, project_name)
        create_codebuild_pullrequest_webhook(environment, project_name)

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

def get_config(environment):
    if os.path.exists(f"../../environments/{environment}.yaml"):
        with open(f"../../environments/{environment}.yaml", "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
