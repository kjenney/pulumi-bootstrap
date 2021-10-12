from pulumi import ComponentResource, ResourceOptions, Output, export
import pulumi_aws as aws
from s3 import Bucket, BucketArgs

class CodePipelineArgs:
    """CodePipeline Arguments"""
    def __init__(self,
                environment=None,
                project_name=None,
                acl='private',
                versioning=False,
                principal='codebuild'
                ):
        self.environment = environment
        self.project_name = project_name
        self.acl = acl
        self.versioning = versioning
        self.principal = principal

class CodePipeline(ComponentResource):
    """
    Create a CodePipeline with permissions granted to an AWS Principal
    """
    def __init__(self, name, args=CodePipelineArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:codepipeline', name, None, opts)
        name = f"{name}-{args.project_name}-{args.environment}"

        
        codepipeline = aws.codepipeline.Pipeline("codepipeline",
            name=f"pipeline-{args.environment}",
            artifact_store=aws.codepipeline.PipelineArtifactStoreArgs(
                location=codepipeline_bucket,
                type="S3",
            ),
            role_arn=roles['codepipeline_role_arn'],
            stages=codepipeline_stages
        )
        export("codepipeline_arn", codepipeline.arn)
        export("codepipeline_id", codepipeline.id)

        assume_role = aws.iam.Role(f"assumeRole-{name}", assume_role_policy=f"""{{
            "Version": "2012-10-17",
            "Statement": [
            {{
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {{
                    "Service": "{args.principal}.amazonaws.com"
                }}
            }}
            ]
            }}""",
            tags=tags)
        aws.iam.RolePolicy(f"bucketPolicy-{name}",
            role=assume_role.name,
            policy=Output.all(bucket=bucket.id).apply(lambda args: f"""{{
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
            }}"""
        ))
        self.bucket_id = bucket.id
        self.assume_role = assume_role.arn
        self.register_outputs({})
