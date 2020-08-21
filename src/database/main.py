import boto3
import botocore.config
import logging
import json
import os

aws_config = botocore.config.Config(
    region_name = os.getenv('REGION'),
    signature_version = 'v4',
    retries = {
        'max_attempts': 5,
        'mode': 'standard'
    }
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

data_client = boto3.client('rds-data', config=aws_config)
cluster_arn = os.getenv('CLUSTER_ARN')
credentials_arn = os.getenv('CREDENTIALS_ARN')
db_name = os.getenv('DB_NAME')

create_table_and_index = "CREATE TABLE IF NOT EXISTS tags (image_id VARCHAR(40) PRIMARY KEY, label VARCHAR(255) NOT NULL, INDEX (image_id, label))"
data_client.execute_statement(resourceArn = cluster_arn, secretArn = credentials_arn, database = db_name, sql = create_table_and_index)

def handler(event, context):
    query = 'SHOW TABLES'
    response = data_client.execute_statement(resourceArn = cluster_arn, secretArn = credentials_arn, database = db_name, sql = query)

    print (response["records"])
    print (response["numberOfRecordsUpdated"])

    return True