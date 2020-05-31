import boto3
import os
import logging
import sys
import json

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
    rekognition = boto3.client('rekognition', es_region)

    for record in event['Records']:
        # receiptHandle = record['receiptHandle']
        body = record['body']
        message = json.loads(body)

        bucket = os.environ['VAQUITA_IMAGES_BUCKET']
        key = message['image']
        # original_key = message['original_key']
        # original_last_modified = message['original_last_modified']
        # etag = message['etag']

        logger.info('Processing {}.'.format(key))

        detected_labels = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10,
            MinConfidence=80)
            
        detected_unsafe_contents = rekognition.detect_moderation_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}})
               
        object_labels = []

        for l in detected_labels['Labels']:
            object_labels.append(l['Name']) # add objects in image

        for l in detected_unsafe_contents['ModerationLabels']:
            object_labels.append(l['Name'])
            object_labels.append("offensive") #label image as offensive

        es_body = {
                'labels': object_labels,
                'offensive': True if "offensive" in object_labels else False
            }

        try:
            es.index(index=es_index, doc_type='post', id=key.split("/")[-1], body=es_body)
        except Exception as e:
            print('Unable to load data into es:', e)
            print("Data: ", es_body)

        logger.info("Image is indexed: {}".format(es_body))

    return True