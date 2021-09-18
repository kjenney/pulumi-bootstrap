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

def create_codebuild_project(environment, pipeline_bucket, project_name, github_connection):
    codebuild_bucket = aws.s3.Bucket(f"codeBuildBucket-{project_name}-{environment}", acl="private")
    codebuild_role = aws.iam.Role(f"codeBuildRole-{project_name}-{environment}", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "Service": "codebuild.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
          }
        ]
    }
    """)
    codebuild_role_policy = aws.iam.RolePolicy(f"codeBuildRolePolicy-{project_name}-{environment}",
        role=codebuild_role.name,
        policy=pulumi.Output.all(codebuild_bucket.arn, pipeline_bucket.arn, github_connection.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
              {{
                "Effect": "Allow",
                "Resource": ["*"],
                "Action": [
                  "logs:CreateLogGroup",
                  "logs:CreateLogStream",
                  "logs:PutLogEvents"
                ]
              }},
              {{
                "Effect": "Allow",
                "Resource": "*",
                "Action": [
                  "ec2:CreateNetworkInterface",
                  "ec2:CreateNetworkInterfacePermission",
                  "ec2:DescribeDhcpOptions",
                  "ec2:DescribeNetworkInterfaces",
                  "ec2:DeleteNetworkInterface",
                  "ec2:DescribeSubnets",
                  "ec2:DescribeSecurityGroups",
                  "ec2:DescribeVpcs"
                ]
              }},
              {{
                 "Effect": "Allow",
                 "Action": ["s3:*"],
                 "Resource": [
                   "{args[0]}",
                   "{args[0]}/*",
                   "{args[1]}",
                   "{args[1]}/*",
                   "arn:aws:s3:::my-pulumi-state",
                   "arn:aws:s3:::my-pulumi-state/*",
                   "arn:aws:s3:::codeBuildBucket-vpc-dev*",
                   "arn:aws:s3:::codeBuildBucket-vpc-dev*/*",
                   "arn:aws:s3:::codeBuildBucket-secrets-dev*",
                   "arn:aws:s3:::codeBuildBucket-secrets-dev*/*"
                 ]
              }},
              {{
                 "Effect": "Allow",
                 "Action": [
                   "codestar-connections:GetConnection",
                   "codestar-connections:UseConnection",
                   "codestar-connections:ListTagsForResource"
                 ],
                 "Resource": "{args[2]}"
              }},
              {{
                 "Effect": "Allow",
                 "Action": ["kms:*"],
                 "Resource": [
                   "arn:aws:kms:us-east-1:161101091064:key/4ed7e926-9130-4259-a8b4-d2e033d31b5f"                
                 ]
              }},
              {{
                  "Effect": "Allow",
                  "Action": [
                      "iam:ListRolePolicies",
                      "iam:GetRole",
                      "iam:GetRolePolicy",
                      "iam:ListAttachedRolePolicies"
                  ],
                  "Resource": "*"
              }},
              {{
                  "Effect": "Allow",
                  "Action": [
                      "ec2:*"
                  ],
                  "Resource": "*"                
              }},
              {{
                  "Effect": "Allow",
                  "Action": [
                      "codebuild:BatchGetProjects"
                  ],
                  "Resource": "*"
              }},
              {{
                  "Effect": "Allow",
                  "Action": [
                      "codepipeline:GetPipeline"
                  ],
                  "Resource": "*"
              }}
            ]
        }}
    """))
    codebuild_project = aws.codebuild.Project(f"{project_name}-{environment}",
        name=f"{project_name}-{environment}",
        description=f"codebuild project for {project_name} in {environment}",
        build_timeout=5,
        service_role=codebuild_role.arn,
        artifacts=aws.codebuild.ProjectArtifactsArgs(
            type="CODEPIPELINE",
        ),
        cache=aws.codebuild.ProjectCacheArgs(
            type="S3",
            location=codebuild_bucket.bucket,
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
                location=codebuild_bucket.id.apply(lambda id: f"{id}/build-log"),
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
        })

def create_pipeline(infra_projects, environment):
    # Get GitHub Connection
    github_connection = aws.codestarconnections.Connection("pipeline", provider_type="GitHub")
    # Create an S3 bucket for the artifacts - which we won't use 
    codepipeline_bucket = aws.s3.Bucket("codepipelineBucket", acl="private")
    # Create the IAM Assume Role
    codepipeline_role = aws.iam.Role("codepipelineRole", assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
        {
        "Effect": "Allow",
        "Principal": {
            "Service": "codepipeline.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
        }
    ]
    }
    """)
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
            location=codepipeline_bucket.bucket,
            type="S3",
        ),
        role_arn=codepipeline_role.arn,
        tags={
            "Name": 'pipeline',
            "Environment": environment,
            "Managed By": "Pulumi",
        },
        stages=codepipeline_stages
    )
    codepipeline_policy = aws.iam.RolePolicy("codepipelinePolicy",
        role=codepipeline_role.id,
        policy=pulumi.Output.all(codepipeline_bucket.arn, github_connection.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                "Effect":"Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetBucketVersioning",
                    "s3:PutObjectAcl",
                    "s3:PutObject"
                ],
                "Resource": [
                    "{args[0]}",
                    "{args[0]}/*",
                    "arn:aws:s3:::my-pulumi-state",
                    "arn:aws:s3:::my-pulumi-state/*"
                ]
                }},
                {{
                "Effect": "Allow",
                "Action": [
                    "codestar-connections:UseConnection"
                ],
                "Resource": "{args[1]}"
                }},
                {{
                "Effect": "Allow",
                "Action": [
                    "codebuild:BatchGetBuilds",
                    "codebuild:BatchGetProjects",
                    "codebuild:StartBuild"
                ],
                "Resource": "*"
                }},
                {{
                    "Effect": "Allow",
                    "Action": ["kms:*"],
                    "Resource": [
                    "arn:aws:kms:us-east-1:161101091064:key/4ed7e926-9130-4259-a8b4-d2e033d31b5f"                
                    ]
                }}
            ]
            }}
            """))
    pulumi.export(f"codepipeline_arn", codepipeline.arn)
    pulumi.export(f"codepipeline_id", codepipeline.id)
    for p in infra_projects:
        create_codebuild_project(environment, codepipeline_bucket, p, github_connection)

def create_webhook():
    webhook_secret = "super-secret"
    bar_webhook = aws.codepipeline.Webhook("barWebhook",
        authentication="GITHUB_HMAC",
        authentication_configuration={
            "secretToken": webhook_secret,
        },
        filters=[{
            "jsonPath": "$.ref",
            "matchEquals": "refs/heads/{Branch}",
        }],
        target_action="Source",
        target_pipeline=bar_pipeline.name)
    # Wire the CodePipeline webhook into a GitHub repository.
    bar_repository_webhook = github.RepositoryWebhook("barRepositoryWebhook",
        configuration={
            "contentType": "json",
            "insecureSsl": True,
            "secret": webhook_secret,
            "url": bar_webhook.url,
        },
        events=["push"],
        repository=github_repository["repo"]["name"])

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

def manage(args, project_name, pulumi_program, infra_projects=None):
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
    if infra_projects:
        stack.set_config('infra_projects', auto.ConfigValue(value=infra_projects))
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
    if os.path.exists(f"environments/{environment}.yaml"):
        with open(f"environments/{environment}.yaml", "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)



