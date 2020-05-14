from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3_notifications as _s3notification,
    aws_s3 as _s3,
    aws_cognito as _cognito,
    aws_cloudfront as _cloudFront,
    aws_apigateway as _apigw,
    core
)

class VaquitaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### cognito
        usersPool = _cognito.UserPool(self, "VAQUITA_USERS")

        ### lambda function
        getSignedUrlFunction = _lambda.Function(self, "VAQUITA_GET_SIGNED_URL",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/getSignedUrl"))

        imageAnalyzerFunction = _lambda.Function(self, "VAQUITA_IMAGE_ANALYSIS",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageAnalysis"))

        imageSearchFunction = _lambda.Function(self, "VAQUITA_IMAGE_SEARCH",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageSearch"))

        ### api gateway
        apiGateway = _apigw.RestApi(self, 'VAQUITA_API_GATEWAY',
            rest_api_name='VaquitaApiGateway')

        apiGatewayResource = apiGateway.root.add_resource('vaquita')

        geySignedUrlIntegration = _apigw.LambdaIntegration(
            getSignedUrlFunction, 
            proxy=False, 
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }]
        )
        
        apiGatewayResource.add_method('GET', geySignedUrlIntegration, 
            # authorization_type=AuthorizationType.COGNITO,
            # authorization_scopes=["Scope1", "Scope2"],
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        self.add_cors_options(apiGatewayResource)

        ### cloud front
        # _cloudFront.CloudFrontWebDistribution(self, "VAQUITA_CLOUDFRONT",
        #                         price_class=_cloudFront.PriceClass.PRICE_CLASS_100,
        #                         origin_configs=[
        #                             _cloudFront.SourceConfiguration(
        #                                 behaviors=[
        #                                     _cloudFront.Behavior(
        #                                         is_default_behavior=True)
        #                                 ],
        #                                 s3_origin_source=_cloudFront.S3OriginConfig(
        #                                     s3_bucket_source=bucket
        #                                 )
        #                             )
        #                         ]
        #                         )

        ### S3
        imagesS3Bucket = _s3.Bucket(self, "VAQUITA_IMAGES")

        newImageAddedNotification = _s3notification.LambdaDestination(getSignedUrlFunction)

        imagesS3Bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, newImageAddedNotification)

    def add_cors_options(self, apigw_resource):
        apigw_resource.add_method('OPTIONS', _apigw.MockIntegration(
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
                }
            }
            ],
            passthrough_behavior=_apigw.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={"application/json":"{\"statusCode\":200}"}
        ),
        method_responses=[{
            'statusCode': '200',
            'responseParameters': {
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True,
                }
            }
        ],
    )
