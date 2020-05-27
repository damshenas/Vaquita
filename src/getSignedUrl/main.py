import json
import boto3
import logging
import os
import time
import hashlib

from botocore.exceptions import ClientError

def handler(event, context):
    uniquehash = hashlib.sha1("{}".format(time.time_ns()).encode('utf-8')).hexdigest()
    result = create_presigned_post(os.environ['image_bucket_name'], uniquehash)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps(result)
    }

def create_presigned_post(bucket_name, object_name,
                          fields=None, conditions=None, expiration=3600):

    # Generate a presigned S3 POST URL
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(bucket_name,
                                                     object_name,
                                                     Fields=fields,
                                                     Conditions=conditions,
                                                     ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL and required fields
    return response