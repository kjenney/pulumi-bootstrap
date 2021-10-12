from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws
from s3 import Bucket, BucketArgs

class CodeBuildProjectArgs:
    """CodeBuild Project Arguments"""
    def __init__(self,
                environment=None,
                project_name=None,
                codebuild_image=None,
                bucket=None
                ):
        self.environment = environment
        self.project_name = project_name
        self.codebuild_image = codebuild_image
        self.bucket = bucket
    
class CodeBuildProject(ComponentResource):
    """
    Create a CodeBuild Project with permissions granted to an AWS Principal
    """
    def __init__(self, name, args=CodeBuildProjectArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:CodeBuild', name, None, opts)
        name = f"{name}-{args.project_name}-{args.environment}"
        assumed_role = aws.iam.Role(f"assumeRole-{args.project_name}", assume_role_policy=f"""{{
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
        bucket = Bucket('test',
            BucketArgs(
                environment=args.environment,
                project_name=args.project_name,
                assumed_role=assumed_role.id
            ))
        codebuild = aws.codebuild.Project(f"{args.project_name}-{args.environment}",
            name=f"{args.project_name}-{args.environment}",
            description=f"codebuild project for {args.project_name} in {args.environment}",
            build_timeout=5,
            service_role=assumed_role,
            artifacts=aws.codebuild.ProjectArtifactsArgs(
                type="CODEPIPELINE",
            ),
            cache=aws.codebuild.ProjectCacheArgs(
                type="S3",
                location=bucket.id,
            ),
            environment=aws.codebuild.ProjectEnvironmentArgs(
                compute_type="BUILD_GENERAL1_SMALL",
                image=args.codebuild_image,
                type="LINUX_CONTAINER",
                image_pull_credentials_type="CODEBUILD",
                environment_variables=[
                    aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
                        name="environment",
                        value=args.environment,
                    ),
                    aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
                        name="project_name",
                        value=args.project_name,
                    ),
                ],
            ),
            logs_config=aws.codebuild.ProjectLogsConfigArgs(
                cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
                    group_name="log-group",
                    stream_name="log-stream",
                ),
                s3_logs=aws.codebuild.ProjectLogsConfigS3LogsArgs(
                    status="ENABLED",
                    location=args.bucket.apply(lambda id: f"{id}/build-log"),
                ),
            ),
            source=aws.codebuild.ProjectSourceArgs(
                type="CODEPIPELINE",
                buildspec="buildspec.yml"
            )
        )
        assumed_policy = aws.iam.RolePolicy(f"codebuildPolicy-{name}",
            role=args.assumed_role_id,
            policy=Output.all(codebuild.arn).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["codebuild:*"],
                    "Resource": ["{args[0]}"]
                }}
                ]
            }}"""
        ))
        self.project_arn = codebuild.arn
        self.assume_policy_id = assumed_policy.id
        self.register_outputs({})