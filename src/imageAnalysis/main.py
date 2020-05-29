import boto3
import os
import logging
import json

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# logger = logging.getLogger('Main_Logger')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# from elasticsearch import Elasticsearch, RequestsHttpConnection
# from aws_requests_auth.aws_auth import AWSRequestsAuth

es_host = os.getenv('ELASTICSEARCH_URL')
es_index = 'images'

## Establish connection to ElasticSearch
# auth = AWSRequestsAuth(aws_access_key=access_key,
#                        aws_secret_access_key=secret_access_key,
#                        aws_token=session_token,
#                        aws_host=es_host,
#                        aws_region=region,
#                        aws_service='es')

# es = Elasticsearch(host=es_host,
#                    port=443,
#                    use_ssl=True,
#                    connection_class=RequestsHttpConnection,
#                    http_auth=auth)

# logger.info("{}".format(es.info()))


def handler(event, context):
    rekognition = boto3.client('rekognition', os.environ['REGION'])

    for record in event['Records']:
        receiptHandle = record['receiptHandle']
        body = record['body']
        message = json.loads(body)

        bucket = os.environ['VAQUITA_IMAGES_BUCKET']
        key = message['image']
        last_modified = message['last_modified']
        etag = message['etag']

        logger.info('Processing {}.'.format(key))

        rekognition_response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10,
            MinConfidence=80)
            
        labels = []
        for l in rekognition_response['Labels']:
            labels.append(l['Name'])
        
        logger.info('Detected labels: {}'.format(labels))
        # res = es.index(index=es_index, doc_type='event',
        #                id=key, body={'labels': labels})

        # logger.debug(res)
        # logger.info("Message {} has been sent.".format(response.get('MessageId')))
        logger.info('Image is indexed')

    return True