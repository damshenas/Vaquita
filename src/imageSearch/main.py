
import boto3
import os
import logging
import sys
import json
from botocore.exceptions import ClientError

script_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "{}/assets".format(script_path))

from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

es_region =  os.getenv('REGION')
es_host = os.getenv('ES_HOST')
es_index = os.getenv('ES_INDEX')

service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, es_region, service, session_token=credentials.token)

es = Elasticsearch(
    hosts = [{'host': es_host, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

logger.info("Elasticsearch Connected: {}".format(es.info()))

def handler(event, context):
    params = {}
    
    for param in event['body'].split('&'):
        key, value = param.split('=')
        params[key] = value
        
    # do something for other languages

    if 'language' in params and params['language'] != 'en':
        translated_label = translate(params['language'], params['label'])
        logger.info("Translated label {} ({}) to {} (en).".format(params['label'], params['language'], translated_label))
        params['label'] = translated_label

    if 'offensive' in params:
        es_response = searchByLabel('offensive', True)
    elif 'label' in params:
        es_response = searchByLabel('labels', params['label'])
    
    count = es_response['hits']['total']
    results = es_response['hits']['hits']

    response = []

    for item in results:
        response.append({
            'id': item['_id'],
            'offensive': item['_source']['offensive'],
            'labels': item['_source']['labels']
        })

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps(response)
    }

def searchByLabel(label, value):
    result = es.search(index=es_index, body={
                'query': {
                    'match': {
                        label: value,
                    }
                }
            })
    logger.info('Found result for label {} and value {}: {}'.format(label, value, result))
    return result

def searchById(id):
    result = es.get(index=es_index, id=id)
    logger.info('Found result for id {}: {}'.format(id, result))
    return result

def translate(language, word):
    translate = boto3.client(service_name='translate', region_name=es_region, use_ssl=True)
    result = translate.translate_text(Text=word, SourceLanguageCode=language, TargetLanguageCode="en")

    return result.get('TranslatedText')