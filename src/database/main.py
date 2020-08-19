import boto3
import botocore.config
import os
import logging
import sys
import json

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_resource = boto3.resource('dynamodb', config=aws_config)
dynamodb_table = dynamodb_resource.Table(os.getenv('TABLE_NAME'))

rekognition_client = boto3.client('rekognition', config=aws_config)

def handler(event, context):

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

        detected_labels = rekognition_client.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=20,
            MinConfidence=85)
            
        detected_unsafe_contents = rekognition_client.detect_moderation_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}})
               
        object_labels = []

        for l in detected_labels['Labels']:
            object_labels.append(l['Name']) # add objects in image

        for l in detected_unsafe_contents['ModerationLabels']:
            object_labels.append(l['Name'])
            object_labels.append("offensive") #label image as offensive

        image_id = key.split("/")[-1]

        with dynamodb_table.batch_writer() as batch:
            for label in object_labels:
                dynamodb_record = {'id':image_id, 'label': label.lower()}
                batch.put_item(Item=dynamodb_record)

        logger.info("Image is indexed: {}: {}".format(image_id, object_labels))

    return True