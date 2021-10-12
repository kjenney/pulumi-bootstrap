import sys
import os
import pulumi
import pulumi_aws as aws
from s3 import Bucket, BucketArgs
from codebuild import CodeBuildProject, CodeBuildProjectArgs
from common import AutoTag, manage

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    project_name = pulumi.get_project()
    #ecr_reference = pulumi.StackReference(f"pipeline-ecr-{environment}")
    codebuild_image = 'test'
    AutoTag(environment)
    # CodeBuild Assume Role
    assumed_role = aws.iam.Role(f"assumeRole-{project_name}", assume_role_policy=f"""{{
        "Version": "2012-10-17",
        "Statement": [
        {{
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {{
                "Service": "codebuild.amazonaws.com"
            }}
        }}
        ]
        }}""")
    # CodeBuild bucket
    bucket = Bucket('test',
        BucketArgs(
            environment=environment,
            project_name=project_name,
            assumed_role=assumed_role.id
        ))
    pulumi.export("bucket_id", bucket.bucket_id)
    pulumi.export("bucket_builder_policy_id", bucket.assume_policy_id)
    # CodeBuild Project
    # Use the existing S3 bucket
    #codebuild_bucket = buckets[f"codebuild_{project_name}_bucket_id"]
    #codepipeline_bucket = buckets["codepipeline_bucket_id"]
    codebuild = CodeBuildProject('test',
        CodeBuildProjectArgs(
            environment=environment,
            project_name=project_name,
            assumed_role_id=assumed_role.id,
            assumed_role_arn=assumed_role.arn,
            codebuild_image=codebuild_image,
            bucket=bucket.bucket_id
        ))
    # aws.codebuild.Project(f"{project_name}-{environment}",
    #     name=f"{project_name}-{environment}",
    #     description=f"codebuild project for {project_name} in {environment}",
    #     build_timeout=5,
    #     service_role=assumed_role.arn,
    #     artifacts=aws.codebuild.ProjectArtifactsArgs(
    #         type="CODEPIPELINE",
    #     ),
    #     cache=aws.codebuild.ProjectCacheArgs(
    #         type="S3",
    #         location=bucket.bucket_id,
    #     ),
    #     environment=aws.codebuild.ProjectEnvironmentArgs(
    #         compute_type="BUILD_GENERAL1_SMALL",
    #         image=codebuild_image,
    #         type="LINUX_CONTAINER",
    #         image_pull_credentials_type="CODEBUILD",
    #         environment_variables=[
    #             aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
    #                 name="environment",
    #                 value=environment,
    #             ),
    #             aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
    #                 name="project_name",
    #                 value=project_name,
    #             ),
    #         ],
    #     ),
    #     logs_config=aws.codebuild.ProjectLogsConfigArgs(
    #         cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
    #             group_name="log-group",
    #             stream_name="log-stream",
    #         ),
    #         s3_logs=aws.codebuild.ProjectLogsConfigS3LogsArgs(
    #             status="ENABLED",
    #             location=bucket.bucket_id.apply(lambda id: f"{id}/build-log"),
    #         ),
    #     ),
    #     source=aws.codebuild.ProjectSourceArgs(
    #         type="CODEPIPELINE",
    #         buildspec="buildspec.yml"
    #     )
    # )

def stacked(environment, action='deploy'):
    """Manage the stack"""
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)

def test():
    """Test the stack"""
    print("Run something useful here")

