from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3_notifications as _s3notification,
    aws_s3 as _s3,
    core
)

class VaquitaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # create lambda function
        getSignedUrlFunction = _lambda.Function(self, "VAQUITA_GET_SIGNED_URL",
                                    runtime=_lambda.Runtime.PYTHON_3_7,
                                    handler="main.handler",
                                    code=_lambda.Code.asset("./src/getSignedUrl"))
        # create s3 bucket
        imagesS3Bucket = _s3.Bucket(self, "VAQUITA_IMAGES")

        # create s3 notification for lambda function
        newImageAddedNotification = _s3notification.LambdaDestination(getSignedUrlFunction)

        # assign notification for the s3 event type (ex: OBJECT_CREATED)
        imagesS3Bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, newImageAddedNotification)
