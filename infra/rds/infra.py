import managor
import json
import pulumi
import pulumi_aws as aws
from mysql.connector import connect

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    secrets = pulumi.StackReference(f"secrets-{environment}")
    vpc = pulumi.StackReference(f"vpc-{environment}")
    data = managor.get_config(environment)
    db_name = data['rds']['db_name']
    db_user = secrets.get_output("db_user")
    db_pass = secrets.get_output("db_pass")
    vpc_id = vpc.get_output("vpc_id")

    my_vpc = aws.ec2.get_vpc(id=vpc_id)
    public_subnet_tags = {"Type": "public"}
    public_subnet_ids = aws.ec2.get_subnet_ids(
        tags=public_subnet_tags,
        vpc_id=my_vpc.id
    )
    subnet_group = aws.rds.SubnetGroup("db_subnet", subnet_ids=public_subnet_ids.ids)

    # make a public security group for our cluster for the migration
    security_group = aws.ec2.SecurityGroup("public_group",
                                           vpc_id=vpc_id,
                                           ingress=[aws.ec2.SecurityGroupIngressArgs(
                                               protocol="-1",
                                               from_port=0,
                                               to_port=0,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )],
                                           egress=[aws.ec2.SecurityGroupEgressArgs(
                                              protocol="-1",
                                              from_port=0,
                                              to_port=0,
                                              cidr_blocks=["0.0.0.0/0"]
                                           )])

    # provision our db
    cluster = aws.rds.Cluster("db",
                              engine=aws.rds.EngineType.AURORA_MYSQL,
                              engine_version="5.7.mysql_aurora.2.03.2",
                              database_name=db_name,
                              master_username=db_user,
                              master_password=db_pass,
                              skip_final_snapshot=True,
                              db_subnet_group_name=subnet_group.name,
                              vpc_security_group_ids=[security_group.id],
                              opts=pulumi.resource.ResourceOptions(additional_secret_outputs=['master_username','master_password']))

    cluster_instance = aws.rds.ClusterInstance("db_instance",
                                               cluster_identifier=cluster.cluster_identifier,
                                               instance_class=aws.rds.InstanceType.T3_SMALL,
                                               engine=aws.rds.EngineType.AURORA_MYSQL,
                                               engine_version="5.7.mysql_aurora.2.03.2",
                                               publicly_accessible=True,
                                               db_subnet_group_name=subnet_group.name)

    pulumi.export("host", cluster.endpoint)
    pulumi.export("db_name", db_name)
    pulumi.export("db_user", db_user)
    pulumi.export("db_pass", db_pass)

args = managor.args()
stack = managor.manage(args, pulumi_program)
print(f"db host url: {stack.outputs['host'].value}")
print(f"db name: {stack.outputs['db_name'].value}")

print("configuring db...")
with connect(
        host=stack.outputs['host'].value,
        user=stack.outputs['db_user'].value,
        password=stack.outputs['db_pass'].value,
        database=stack.outputs['db_name'].value) as connection:
    print("db configured!")

    # make sure the table exists
    print("creating table...")
    create_table_query = """CREATE TABLE IF NOT EXISTS hello_pulumi(
        id int(9) NOT NULL PRIMARY KEY,
        color varchar(14) NOT NULL);
        """
    with connection.cursor() as cursor:
        cursor.execute(create_table_query)
        connection.commit()

    # seed the table with some data to start
    seed_table_query = """INSERT IGNORE INTO hello_pulumi (id, color)
    VALUES
        (1, 'Purple'),
        (2, 'Violet'),
        (3, 'Plum');
    """
    with connection.cursor() as cursor:
        cursor.execute(seed_table_query)
        connection.commit()

    print("rows inserted!")
    print("querying to verify data...")

    # read the data back
    read_table_query = """SELECT COUNT(*) FROM hello_pulumi;"""
    with connection.cursor() as cursor:
        cursor.execute(read_table_query)
        result = cursor.fetchone()
        print(f"Result: {json.dumps(result)}")

    print("database, table and rows successfully configured")

