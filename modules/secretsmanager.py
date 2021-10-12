from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws

class SecretArgs:
    """SecretsManager Secret Arguments"""
    def __init__(self,
                environment=None,
                project_name=None,
                description=None,
                assumed_role=None
                ):
        self.environment = environment
        self.project_name = project_name
        self.description = description
        self.assumed_role = assumed_role

class Secret(ComponentResource):
    """
    Create a Secrets Manager Secret with permissions granted to an AWS Principal
    """
    def __init__(self, name, args=SecretArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:Secret', name, None, opts)
        name = f"{name}-{args.project_name}-{args.environment}"
        secret = aws.secretsmanager.Secret(name,
            name=name,
            description=args.description,
        )
        assumed_policy = aws.iam.RolePolicy(f"secretPolicy-{name}",
            role=args.assumed_role,
            policy=Output.all(secret=secret.arn).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["secretsmanager:*"],
                    "Resource": ["{args[0]}"]
                }}
                ]
            }}"""
        ))
        self.secret_arn = secret.arn
        self.assume_policy_id = assumed_policy.id
        self.register_outputs({})
