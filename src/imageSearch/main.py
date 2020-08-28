
import boto3
import botocore
import os
import logging
import sys
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

aws_config = botocore.config.Config(
    region_name = os.getenv('REGION'),
    signature_version = 'v4',
    retries = {
        'max_attempts': 5,
        'mode': 'standard'
    }
)

script_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "{}/assets".format(script_path))

dynamodb_resource = boto3.resource('dynamodb', config=aws_config)
dynamodb_table = dynamodb_resource.Table(os.getenv('TABLE_NAME'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region =  os.getenv('REGION')

def handler(event, context):
    params = {}
    
    for param in event['body'].split('&'):
        key, value = param.split('=')
        params[key] = value
        
    if 'language' in params and params['language'] != 'en':
        translated_label = translate(params['language'], params['label'])
        logger.info("Translated label {} ({}) to {} (en).".format(params['label'], params['language'], translated_label))
        params['label'] = translated_label

    dynamodb_response = dynamodb_table.query(
        IndexName='VAQUITA_TABLE_LABEL_INDEX', # tbc get this from env
        KeyConditionExpression=Key('label').eq(params['label'].lower())
    )

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps(dynamodb_response["Items"])
    }

def translate(language, word):
    translate = boto3.client(service_name='translate', config=aws_config)
    result = translate.translate_text(Text=word, SourceLanguageCode=language, TargetLanguageCode="en")

    return result.get('TranslatedText')