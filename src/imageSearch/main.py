
import boto3
import botocore
import os
import logging
import json
from botocore.exceptions import ClientError
# from boto3.dynamodb.conditions import Key, Attr

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

region =  os.getenv('REGION')

data_client = boto3.client('rds-data', config=aws_config)
cluster_arn = os.getenv('CLUSTER_ARN')
credentials_arn = os.getenv('CREDENTIALS_ARN')
db_name = os.getenv('DB_NAME')

create_table_and_index = "CREATE TABLE IF NOT EXISTS tags (image_id VARCHAR(40) PRIMARY KEY, label VARCHAR(255) NOT NULL, INDEX (image_id, label))"
data_client.execute_statement(resourceArn = cluster_arn, secretArn = credentials_arn, database = db_name, sql = create_table_and_index)

def handler(event, context):
    params = {}
    
    for param in event['body'].split('&'):
        key, value = param.split('=')
        params[key] = value
        
    if 'language' in params and params['language'] != 'en':
        translated_label = translate(params['language'], params['label'])
        logger.info("Translated label {} ({}) to {} (en).".format(params['label'], params['language'], translated_label))
        params['label'] = translated_label

    # dynamodb_response = dynamodb_table.query(
    #     IndexName='VAQUITA_TABLE_LABEL_INDEX', # tbc get this from env
    #     KeyConditionExpression=Key('label').eq(params['label'].lower())
    # )

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        # 'body': json.dumps(dynamodb_response["Items"])
    }

def translate(language, word):
    translate = boto3.client(service_name='translate', config=aws_config)
    result = translate.translate_text(Text=word, SourceLanguageCode=language, TargetLanguageCode="en")

    return result.get('TranslatedText')