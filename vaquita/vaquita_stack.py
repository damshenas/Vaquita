from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3_notifications as _s3notification,
    aws_s3 as _s3,
    aws_cognito as _cognito,
    # aws_cloudfront as _cloudFront,
    aws_elasticsearch as _esearch,
    aws_apigateway as _apigw,
    aws_iam as _iam,
    # aws_ec2 as _ec2,
    core
)

# read config file

# create first user of the cognito user pool?

class VaquitaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### S3 core
        imagesS3Bucket = _s3.Bucket(self, "VAQUITA_IMAGES")

        ### api gateway core
        apiGateway = _apigw.RestApi(self, 'VAQUITA_API_GATEWAY', rest_api_name='VaquitaApiGateway')
        apiGatewayResource = apiGateway.root.add_resource('vaquita')
        apiGatewayLandingPageResource = apiGatewayResource.add_resource('web')
        apiGatewayGetSignedUrlResource = apiGatewayResource.add_resource('signedUrl')

        ### landing page function
        getLandingPageFunction = _lambda.Function(self, "VAQUITA_GET_LANDING_PAGE",
            function_name="VAQUITA_GET_LANDING_PAGE",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/landingPage"))

        geyLandingPageIntegration = _apigw.LambdaIntegration(
            getLandingPageFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        apiGatewayLandingPageResource.add_method('GET', geyLandingPageIntegration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }])

        ### cognito
        usersPool = _cognito.UserPool(self, "VAQUITA_USERS_POOL",
            auto_verify={"email": True},
            self_sign_up_enabled=True)

        self.userPoolAppClient = _cognito.CfnUserPoolClient(self, "VAQUITA_USERS_POOL_APP_CLIENT", 
            supported_identity_providers=["COGNITO"],
            allowed_o_auth_flows=["implicit"],
            allowed_o_auth_scopes=["phone", "email", "openid", "profile"],
            user_pool_id=usersPool.user_pool_id,
            callback_ur_ls=[apiGatewayLandingPageResource.url],
            allowed_o_auth_flows_user_pool_client=True,
            explicit_auth_flows=["ALLOW_REFRESH_TOKEN_AUTH"])

        self.userPoolDomain = _cognito.UserPoolDomain(self, "VAQUITA_USERS_POOL_DOMAIN", 
            user_pool=usersPool, 
            cognito_domain=_cognito.CognitoDomainOptions(domain_prefix="vaquita"))

        apiGatewayAuthorizer = _apigw.CfnAuthorizer(self, "VAQUITA_API_GATEWAY_AUTHORIZER",
            rest_api_id=apiGatewayGetSignedUrlResource.rest_api.rest_api_id,
            name="VAQUITA_API_GATEWAY_AUTHORIZER",
            type="COGNITO_USER_POOLS", #_apigw.AuthorizationType.COGNITO,
            identity_source="method.request.header.Authorization",
            provider_arns=[usersPool.user_pool_arn])

        ### get signed URL function
        getSignedUrlFunction = _lambda.Function(self, "VAQUITA_GET_SIGNED_URL",
            function_name="VAQUITA_GET_SIGNED_URL",
            environment={"image_bucket_name": imagesS3Bucket.bucket_name},
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/getSignedUrl"))

        geySignedUrlIntegration = _apigw.LambdaIntegration(
            getSignedUrlFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        imagesS3Bucket.grant_put(getSignedUrlFunction)

        ### image analyer function
        imageAnalyzerFunction = _lambda.Function(self, "VAQUITA_IMAGE_ANALYSIS",
            function_name="VAQUITA_IMAGE_ANALYSIS",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageAnalysis"))

        newImageAddedNotification = _s3notification.LambdaDestination(imageAnalyzerFunction)
        imagesS3Bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, newImageAddedNotification)

        apiGatewayGetSignedUrlResource.add_method('GET', geySignedUrlIntegration,
            authorization_type=_apigw.AuthorizationType.COGNITO,
            # authorizer= {"authorizerId": apiGatewayAuthorizer.ref},
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
            ).node.find_child('Resource').add_property_override('AuthorizerId', apiGatewayAuthorizer.ref)

        ### image search function
        self.imageSearchFunction = _lambda.Function(self, "VAQUITA_IMAGE_SEARCH",
            function_name="VAQUITA_IMAGE_SEARCH",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageSearch"))

        ### API gateway finializing
        self.add_cors_options(apiGatewayGetSignedUrlResource)
        self.add_cors_options(apiGatewayLandingPageResource)

        ### elastic search
        esearchDocument = _iam.PolicyDocument()
        esearchStatement = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW, 
            actions=["es:*",]
        )

        esearchStatement.add_aws_account_principal(core.Aws.ACCOUNT_ID)
        esearchStatement.add_resources("arn:aws:es:{}:{}:domain/VAQUITA_ELASTIC_SEARCH/*".format(core.Aws.REGION, core.Aws.ACCOUNT_ID))
        esearchDocument.add_statements(esearchStatement)

        self.elasticSearch = _esearch.CfnDomain(self, "VAQUITA_ELASTIC_SEARCH",
            domain_name="vaquita-elastic-search",
            elasticsearch_version="7.4",
            access_policies=esearchDocument,
            elasticsearch_cluster_config={
                "InstanceCount": "1",
                "InstanceType": "t2.small.elasticsearch",
                "DedicatedMasterEnabled": False,
                "zoneAwarenessEnabled": False,
                },
            ebs_options={
                "ebsEnabled": True, 
                "volumeSize": 10
                }
            )

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
