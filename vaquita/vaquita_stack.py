from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3_notifications as _s3notification,
    aws_s3 as _s3,
    aws_cognito as _cognito,
    aws_cloudfront as _cloudFront,
    aws_apigateway as _apigw,
    core
)

# read config file

# create first user of the cognito user pool?

class VaquitaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### cognito
        usersPool = _cognito.UserPool(self, "VAQUITA_USERS_POOL",
            auto_verify={"email": True},
            self_sign_up_enabled=True)

        userPoolAppClient = _cognito.CfnUserPoolClient(self, "VAQUITA_USERS_POOL_APP_CLIENT", 
            supported_identity_providers=["COGNITO"],
            allowed_o_auth_flows=["implicit"],
            allowed_o_auth_scopes=["phone", "email", "openid", "profile"],
            user_pool_id=usersPool.user_pool_id,
            callback_ur_ls=["https://www.amazon.com/"], #should read from config fileß
            allowed_o_auth_flows_user_pool_client=True,
            explicit_auth_flows=["ALLOW_REFRESH_TOKEN_AUTH"])

        userPoolDomain = _cognito.UserPoolDomain(self, "VAQUITA_USERS_POOL_DOMAIN", 
            user_pool=usersPool, 
            cognito_domain=_cognito.CognitoDomainOptions(domain_prefix="vaquita"))

        ### S3
        imagesS3Bucket = _s3.Bucket(self, "VAQUITA_IMAGES")

        ### lambda function
        getSignedUrlFunction = _lambda.Function(self, "VAQUITA_GET_SIGNED_URL",
            function_name="VAQUITA_GET_SIGNED_URL",
            environment={"image_bucket_name": imagesS3Bucket.bucket_name, "test": "true"},
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/getSignedUrl"))

        imageAnalyzerFunction = _lambda.Function(self, "VAQUITA_IMAGE_ANALYSIS",
            function_name="VAQUITA_IMAGE_ANALYSIS",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageAnalysis"))

        newImageAddedNotification = _s3notification.LambdaDestination(imageAnalyzerFunction)
        imagesS3Bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, newImageAddedNotification)

        imageSearchFunction = _lambda.Function(self, "VAQUITA_IMAGE_SEARCH",
            function_name="VAQUITA_IMAGE_SEARCH",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageSearch"))

        ### api gateway
        apiGateway = _apigw.RestApi(self, 'VAQUITA_API_GATEWAY',
            rest_api_name='VaquitaApiGateway')

        apiGatewayResource = apiGateway.root.add_resource('vaquita')

        apiGatewayAuthorizer = _apigw.CfnAuthorizer(self, "VAQUITA_API_GATEWAY_AUTHORIZER",
            rest_api_id=apiGatewayResource.rest_api.rest_api_id,
            name="VAQUITA_API_GATEWAY_AUTHORIZER",
            type="COGNITO_USER_POOLS", #_apigw.AuthorizationType.COGNITO,
            identity_source="method.request.header.Authorization",
            provider_arns=[usersPool.user_pool_arn])

        geySignedUrlIntegration = _apigw.LambdaIntegration(
            getSignedUrlFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        apiGatewayResource.add_method('GET', geySignedUrlIntegration,
            authorization_type=_apigw.AuthorizationType.COGNITO,
            # authorizer= {"authorizerId": apiGatewayAuthorizer.ref},
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
            ).node.find_child('Resource').add_property_override('AuthorizerId', apiGatewayAuthorizer.ref)

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
