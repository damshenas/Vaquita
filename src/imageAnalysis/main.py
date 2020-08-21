import boto3
import botocore.config
import os
import logging
import json

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

        # with dynamodb_table.batch_writer() as batch:
        #     for label in object_labels:
        #         dynamodb_record = {'id':image_id, 'label': label.lower()}
        #         batch.put_item(Item=dynamodb_record)

        logger.info("Image is indexed: {}: {}".format(image_id, object_labels))

    return True