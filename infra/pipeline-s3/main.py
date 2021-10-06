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

# Deploy S3 buckets to support pieces of infra

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    for project in infra_projects:
        codebuild_bucket = aws.s3.Bucket(
            f"codeBuildBucket-{project}-{environment}", 
            acl="private",
            tags={
                "Environment": environment,
                "Managed By": "Pulumi",
                "Name": f"codeBuildBucket-{project}-{environment}",
            }
        )
        pulumi.export(f"codebuild_{project}_bucket_id", codebuild_bucket.id)

    ptags={
        "Environment": environment,
        "Managed By": "Pulumi",
        "Name": f"codeBuildBucket-{environment}",
    }

    codepipeline_bucket = aws.s3.Bucket(
        f"codePipelineBucket-{environment}", 
        acl="private",
        tags=ptags
    )
    pulumi.export(f"codepipeline_bucket_id", codepipeline_bucket.id)

    # Create the S3 Buckets that will be used by the Lambda and CodeBuild
    codebuild_functional_bucket = aws.s3.Bucket(f"codebuild-functional-{environment}", 
        acl="private",
        tags=ptags
    )

    codebuild_main_bucket = aws.s3.Bucket(f"codebuild-main-{environment}",
        acl="private",
        tags=ptags
    )

    pulumi.export('codebuild_functional_bucket',codebuild_functional_bucket.id)
    pulumi.export('codebuild_main_bucket',codebuild_main_bucket.id)

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)


