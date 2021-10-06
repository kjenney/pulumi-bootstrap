import sys
import os
import pulumi

sys.path.append("../../shared")
from bootstrap import manage, args, get_config, create_pipeline

# Deploy CodePipeline with CodeBuild projects for each piece of infra

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    # Get S3 buckets
    s3_reference = pulumi.StackReference(f"pipeline-s3-{environment}")
    iam_reference = pulumi.StackReference(f"pipeline-iam-{environment}")
    buckets = {}
    roles = {}
    # Set the CodeBuild Project roles and buckets here
    for project in infra_projects:
        buckets[f"codebuild_{project}_bucket_id"] = s3_reference.get_output(f"codebuild_{project}_bucket_id")
        roles[f"codebuild_role_{project}_arn"] = iam_reference.get_output(f"codebuild_role_{project}_arn")
        roles[f"codebuild_role_{project}_id"] = iam_reference.get_output(f"codebuild_role_{project}_id")
    buckets["codepipeline_bucket_id"] = s3_reference.get_output("codepipeline_bucket_id")
    # Set the CodePipeline role
    roles['codepipeline_role_arn'] = iam_reference.get_output("codepipeline_role_arn")
    roles['codepipeline_role_id'] = iam_reference.get_output("codepipeline_role_id")
    create_pipeline(infra_projects, buckets, roles, environment)

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)
