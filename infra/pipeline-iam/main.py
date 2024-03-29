import sys
import os
import json
import pulumi
import pulumi_aws as aws

sys.path.append("../../shared")
from bootstrap import manage, args, get_config

# Deploy IAM roles and policies for CodePipeline and CodeBuild projects for each piece of infra

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    # Get S3 buckets
    s3_reference = pulumi.StackReference(f"pipeline-s3-{environment}")
    codepipeline_source_bucket = s3_reference.get_output("codepipeline_source_bucket")
    # Get KMS Key Arn
    secrets = pulumi.StackReference(f"secrets-{environment}")
    buckets = {}
    for project in infra_projects:
        buckets[f"codebuild_{project}_bucket_id"] = s3_reference.get_output(f"codebuild_{project}_bucket_id")
    buckets["codepipeline_bucket_id"] = s3_reference.get_output("codepipeline_bucket_id")
    buckets["codepipeline_source_bucket"] = s3_reference.get_output("codepipeline_source_bucket")
    buckets["codebuild_functional_bucket"] = s3_reference.get_output("codebuild_functional_bucket")
    buckets["codebuild_main_bucket"] = s3_reference.get_output("codebuild_main_bucket")
    buckets["pipeline_s3_trail_bucket"] = s3_reference.get_output("pipeline_s3_trail_bucket")

    # Create the IAM Assume Roles
    codepipeline_role = aws.iam.Role(f"codepipelineRole-{environment}", assume_role_policy="""{
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

    aws.iam.RolePolicy("codepipelinePolicy",
        role=codepipeline_role.id,
        policy=pulumi.Output.all(codepipeline_source_bucket=codepipeline_source_bucket,
                                 kms_key_arn=secrets.get_output("kms_arn"),
                                ).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
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
                    "Resource": "{args['kms_key_arn']}"
                }},
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        "arn:aws:s3:::{args['codepipeline_source_bucket']}",
                        "arn:aws:s3:::{args['codepipeline_source_bucket']}/*"
                    ]
                }}
            ]
        }}
    """))

    # Grant access to every bucket for CodePipeline
    for key, value in buckets.items():
        aws.iam.RolePolicy(f"codepipelinebucketpolicy-{key}",
            role=codepipeline_role.name,
            policy=pulumi.Output.all(bucket=value).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        "arn:aws:s3:::{args['bucket']}",
                        "arn:aws:s3:::{args['bucket']}/*"
                    ]
                }}
                ]
            }}
            """))
    # Grant access to codebuild projects
    for project_name in infra_projects:
        codebuild_role = aws.iam.Role(f"codebuildRole-{project_name}-{environment}", assume_role_policy="""{
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
        pulumi.export(f"codebuild_role_{project_name}_arn", codebuild_role.arn)
        pulumi.export(f"codebuild_role_{project_name}_id", codebuild_role.id)

        for key, value in buckets.items():
            aws.iam.RolePolicy(f"codeBuildBucketRolePolicy-{project_name}-{key}-{environment}",
                role=codebuild_role.name,
                policy=pulumi.Output.all(bucket=value).apply(lambda args: f"""{{
                    "Version": "2012-10-17",
                    "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": [
                            "arn:aws:s3:::{args['bucket']}",
                            "arn:aws:s3:::{args['bucket']}/*"
                        ]
                    }}
                    ]
                }}
                """))
        aws.iam.RolePolicy(f"codeBuildRolePolicy-{project_name}-{environment}",
            role=codebuild_role.name,
            policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Resource": ["*"],
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ]
                },
                {
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
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                    "arn:aws:s3:::my-pulumi-state",
                    "arn:aws:s3:::my-pulumi-state/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": ["kms:*"],
                    "Resource": [
                    "arn:aws:kms:us-east-1:161101091064:key/4ed7e926-9130-4259-a8b4-d2e033d31b5f"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:ListRolePolicies",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListAttachedRolePolicies",
                        "iam:CreateRole",
                        "iam:UpdateRole",
                        "iam:DeleteRole",
                        "iam:PutRolePolicy",
                        "iam:PassRole"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "codebuild:BatchGetProjects"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "events:*",
                        "secretsmanager:*",
                        "codepipeline:*",
                        "lambda:*",
                        "apigateway:*",
                        "ec2:*",
                        "cloudtrail:*"
                    ],
                    "Resource": "*"
                }
                ]
            }))

    pulumi.export("codepipeline_role_arn", codepipeline_role.arn)
    pulumi.export("codepipeline_role_id", codepipeline_role.id)

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)
