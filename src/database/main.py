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

def handler(event, context):

    response = data_client.execute_statement(
        resourceArn = cluster_arn, 
        secretArn = credentials_arn, 
        database = 'mydb', 
        sql = 'SHOW DATABASES')


    return response