import json
import random
import logging
import os
import http.client

from botocore.exceptions import ClientError

def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': file_get_contents("upload.html")
    }


def file_get_contents(filename):
    with open(filename) as f:
        return f.read()