from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws

class BucketArgs:
    """S3 Bucket Arguments"""
    def __init__(self,
                environment=None,
                project_name=None,
                acl='private',
                versioning=False,
                assumed_role=None
                ):
        self.environment = environment
        self.project_name = project_name
        self.acl = acl
        self.versioning = versioning
        self.assumed_role = assumed_role

class Bucket(ComponentResource):
    """
    Create an S3 Bucket with permissions granted to an AWS Principal
    """
    def __init__(self, name, args=BucketArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:S3', name, None, opts)
        name = f"{name}-{args.project_name}-{args.environment}"
        bucket = aws.s3.Bucket(name,
            acl=args.acl,
            versioning=aws.s3.BucketVersioningArgs(
                enabled=args.versioning,
            ))
        assumed_policy = aws.iam.RolePolicy(f"bucketPolicy-{name}",
            role=args.assumed_role,
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
        self.assume_policy_id = assumed_policy.id
        self.register_outputs({})
