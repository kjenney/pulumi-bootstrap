import sys
import os
import pulumi
import pulumi_aws as aws

sys.path.append("../../shared")
from bootstrap import manage, args, get_config

# Deploy S3 buckets to support pieces of infra

def pulumi_program():
    """Pulumi Program"""
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
    pulumi.export("codepipeline_bucket_id", codepipeline_bucket.id)

    # Create the S3 Buckets that will be used by the Lambda and CodeBuild
    codebuild_functional_bucket = aws.s3.Bucket(f"codebuild-functional-{environment}",
        acl="private",
        tags=ptags
    )

    codebuild_main_bucket = aws.s3.Bucket(f"codebuild-main-{environment}",
        acl="private",
        tags=ptags
    )

    codepipeline_source_bucket = aws.s3.Bucket(f"codepipeline-source-{environment}",
        acl="private",
        versioning=aws.s3.BucketVersioningArgs(
            enabled=True,
        ),
        tags=ptags
    )

    pipeline_s3_trail_bucket = aws.s3.Bucket(f"s3trail-{environment}",
        acl="private",
        tags=ptags
    )

    pulumi.export('codebuild_functional_bucket',codebuild_functional_bucket.id)
    pulumi.export('codebuild_main_bucket',codebuild_main_bucket.id)
    pulumi.export('codepipeline_source_bucket',codepipeline_source_bucket.id)
    pulumi.export('pipeline_s3_trail_bucket',pipeline_s3_trail_bucket.id)

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)
