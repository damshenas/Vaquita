import boto3
import os
import logging
import hashlib
import json
import botocore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    s3 = boto3.resource('s3')

    for record in event['Records']:
        newKey = record['s3']['object']['key']
        bucket = record['s3']['bucket']['name']
        name = bucket.split("/")[-1]
        localfile = "/tmp/{}".format(name)

        # download the file
        newKeyObj = s3.Object(bucket, newKey)
        newKeyObj.download_file(localfile)

        # calc hash
        imageSHA1 = getSha1(localfile)

        # check if not exist
        processedKey = "processed/{}/{}".format(imageSHA1[:2], imageSHA1)
        keyIsProcessed = isS3ObjectExist(bucket, processedKey)
        if keyIsProcessed: continue

        # add to the queue
        message = json.dumps({
            "image": processedKey,
            "original_key": newKey,
            "original_last_modified": newKeyObj.last_modified,
            "etag": newKeyObj.e_tag
        }, default=str)

        queueName = os.environ["VAQUITA_IMAGE_MASSAGE"]
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queueName)
        response = queue.send_message(MessageBody=message)
        logger.info("Message {} has been sent.".format(response.get('MessageId')))

        #move the image
        s3.Object(bucket, processedKey).copy_from(CopySource="{}/{}".format(bucket,newKey))
        newKeyObj.delete()

        # delete local file
        os.remove(localfile)

    return True

def isS3ObjectExist(bucket, key):
    s3 = boto3.resource('s3')

    try:
        s3.Object(bucket,key)
        return False
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return True
        else:
            raise e

def getSha1(filepath):
    sha1 = hashlib.sha1()

    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536) # read in 64kb chunks
            if not data: break
            sha1.update(data)

    return sha1.hexdigest()