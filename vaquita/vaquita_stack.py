from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3_notifications as _s3notification,
    aws_lambda_event_sources as _lambda_event_source,
    aws_s3 as _s3,
    aws_cognito as _cognito,
    aws_sqs as _sqs,
    aws_dynamodb as _dydb,
    aws_apigateway as _apigw,
    aws_iam as _iam,
    core
)

# read config file

# create first user of the cognito user pool?

class VaquitaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### S3 core
        imagesS3Bucket = _s3.Bucket(self, "VAQUITA_IMAGES")

        imagesS3Bucket.add_cors_rule(
            allowed_methods=[_s3.HttpMethods.POST],
            allowed_origins=["*"] # add API gateway web resource URL
        )

        ### SQS core
        imageDeadletterQueue = _sqs.Queue(self, "VAQUITA_IMAGES_DEADLETTER_QUEUE")
        imageQueue = _sqs.Queue(self, "VAQUITA_IMAGES_QUEUE",
            dead_letter_queue={
                "max_receive_count": 3,
                "queue": imageDeadletterQueue
            })

        ### api gateway core
        apiGateway = _apigw.RestApi(self, 'VAQUITA_API_GATEWAY', rest_api_name='VaquitaApiGateway')
        apiGatewayResource = apiGateway.root.add_resource('vaquita')
        apiGatewayLandingPageResource = apiGatewayResource.add_resource('web')
        apiGatewayGetSignedUrlResource = apiGatewayResource.add_resource('signedUrl')
        apiGatewayImageSearchResource = apiGatewayResource.add_resource('search')

        ### create dynamo table
        dynamodb_table = _dydb.Table(
            self, "VAQUITA_TABLE",
            partition_key=_dydb.Attribute(
                name="id",
                type=_dydb.AttributeType.STRING
            ),
            sort_key=_dydb.Attribute(
                name="label",
                type=_dydb.AttributeType.STRING
            ),
            billing_mode=_dydb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY # NOT recommended for production code
        )

        dynamodb_table.add_global_secondary_index(
            index_name='VAQUITA_TABLE_LABEL_INDEX',
            partition_key=_dydb.Attribute(
                name="label",
                type=_dydb.AttributeType.STRING
            ),
            projection_type=_dydb.ProjectionType.KEYS_ONLY
        )

        ### landing page function
        getLandingPageFunction = _lambda.Function(self, "VAQUITA_GET_LANDING_PAGE",
            function_name="VAQUITA_GET_LANDING_PAGE",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/landingPage"))

        getLandingPageIntegration = _apigw.LambdaIntegration(
            getLandingPageFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        apiGatewayLandingPageResource.add_method('GET', getLandingPageIntegration,
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

        userPoolAppClient = _cognito.CfnUserPoolClient(self, "VAQUITA_USERS_POOL_APP_CLIENT", 
            supported_identity_providers=["COGNITO"],
            allowed_o_auth_flows=["implicit"],
            allowed_o_auth_scopes=["phone", "email", "openid", "profile"],
            user_pool_id=usersPool.user_pool_id,
            callback_ur_ls=[apiGatewayLandingPageResource.url],
            allowed_o_auth_flows_user_pool_client=True,
            explicit_auth_flows=["ALLOW_REFRESH_TOKEN_AUTH"])

        userPoolDomain = _cognito.UserPoolDomain(self, "VAQUITA_USERS_POOL_DOMAIN", 
            user_pool=usersPool, 
            cognito_domain=_cognito.CognitoDomainOptions(domain_prefix="vaquita"))

        ### get signed URL function
        getSignedUrlFunction = _lambda.Function(self, "VAQUITA_GET_SIGNED_URL",
            function_name="VAQUITA_GET_SIGNED_URL",
            environment={"VAQUITA_IMAGES_BUCKET": imagesS3Bucket.bucket_name},
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="main.handler",
            code=_lambda.Code.asset("./src/getSignedUrl"))

        getSignedUrlIntegration = _apigw.LambdaIntegration(
            getSignedUrlFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        apiGatewayGetSignedUrlAuthorizer = _apigw.CfnAuthorizer(self, "VAQUITA_API_GATEWAY_GET_SIGNED_URL_AUTHORIZER",
            rest_api_id=apiGatewayGetSignedUrlResource.rest_api.rest_api_id,
            name="VAQUITA_API_GATEWAY_GET_SIGNED_URL_AUTHORIZER",
            type="COGNITO_USER_POOLS", #_apigw.AuthorizationType.COGNITO,
            identity_source="method.request.header.Authorization",
            provider_arns=[usersPool.user_pool_arn])

        apiGatewayGetSignedUrlResource.add_method('GET', getSignedUrlIntegration,
            authorization_type=_apigw.AuthorizationType.COGNITO,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
            ).node.find_child('Resource').add_property_override('AuthorizerId', apiGatewayGetSignedUrlAuthorizer.ref)

        imagesS3Bucket.grant_put(getSignedUrlFunction, objects_key_pattern="new/*")

        ### image massage function
        imageMassageFunction = _lambda.Function(self, "VAQUITA_IMAGE_MASSAGE",
            function_name="VAQUITA_IMAGE_MASSAGE",
            timeout=core.Duration.seconds(6),
            runtime=_lambda.Runtime.PYTHON_3_7,
            environment={"VAQUITA_IMAGE_MASSAGE": imageQueue.queue_name},
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageMassage"))

        imagesS3Bucket.grant_write(imageMassageFunction, "processed/*")
        imagesS3Bucket.grant_delete(imageMassageFunction, "new/*")
        imagesS3Bucket.grant_read(imageMassageFunction, "new/*")
        
        newImageAddedNotification = _s3notification.LambdaDestination(imageMassageFunction)

        imagesS3Bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, 
            newImageAddedNotification, 
            _s3.NotificationKeyFilter(prefix="new/")
            )

        imageQueue.grant_send_messages(imageMassageFunction)

        ### image analyzer function
        imageAnalyzerFunction = _lambda.Function(self, "VAQUITA_IMAGE_ANALYSIS",
            function_name="VAQUITA_IMAGE_ANALYSIS",
            runtime=_lambda.Runtime.PYTHON_3_7,
            timeout=core.Duration.seconds(10),
            environment={
                "VAQUITA_IMAGES_BUCKET": imagesS3Bucket.bucket_name,
                "REGION": core.Aws.REGION,
                "TABLE_NAME": dynamodb_table.table_name
                },
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageAnalysis")) 

        imageAnalyzerFunction.add_event_source(_lambda_event_source.SqsEventSource(queue=imageQueue, batch_size=10))
        imageQueue.grant_consume_messages(imageMassageFunction)

        lambda_rekognition_access = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW, 
            actions=["rekognition:DetectLabels", "rekognition:DetectModerationLabels"],
            resources=["*"]                    
        )

        imageAnalyzerFunction.add_to_role_policy(lambda_rekognition_access)
        imagesS3Bucket.grant_read(imageAnalyzerFunction, "processed/*")
        dynamodb_table.grant_write_data(imageAnalyzerFunction)
        
        ### image search function
        imageSearchFunction = _lambda.Function(self, "VAQUITA_IMAGE_SEARCH",
            function_name="VAQUITA_IMAGE_SEARCH",
            runtime=_lambda.Runtime.PYTHON_3_7,
            timeout=core.Duration.seconds(10),
            environment={
                "VAQUITA_IMAGES_BUCKET": imagesS3Bucket.bucket_name,
                "REGION": core.Aws.REGION,
                "TABLE_NAME": dynamodb_table.table_name
                },
            handler="main.handler",
            code=_lambda.Code.asset("./src/imageSearch"))

        imageSearchIntegration = _apigw.LambdaIntegration(
            imageSearchFunction, 
            proxy=True, 
            integration_responses=[{
                'statusCode': '200',
               'responseParameters': {
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        apiGatewayImageSearchAuthorizer = _apigw.CfnAuthorizer(self, "VAQUITA_API_GATEWAY_IMAGE_SEARCH_AUTHORIZER",
            rest_api_id=apiGatewayImageSearchResource.rest_api.rest_api_id,
            name="VAQUITA_API_GATEWAY_IMAGE_SEARCH_AUTHORIZER",
            type="COGNITO_USER_POOLS", #_apigw.AuthorizationType.COGNITO,
            identity_source="method.request.header.Authorization",
            provider_arns=[usersPool.user_pool_arn])

        apiGatewayImageSearchResource.add_method('POST', imageSearchIntegration,
            authorization_type=_apigw.AuthorizationType.COGNITO,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
            ).node.find_child('Resource').add_property_override('AuthorizerId', apiGatewayImageSearchAuthorizer.ref)


        lambda_access_search = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW, 
            actions=["dynamodb:Query", "translate:TranslateText"],
            resources=["*"] #tbc [elasticSearch.attr_arn]              
        ) 

        imageSearchFunction.add_to_role_policy(lambda_access_search)

        ### API gateway finalizing
        self.add_cors_options(apiGatewayGetSignedUrlResource)
        self.add_cors_options(apiGatewayLandingPageResource)
        self.add_cors_options(apiGatewayImageSearchResource)

        ### outputs
        core.CfnOutput(self, 'CognitoHostedUILogin',
            value='https://{}.auth.{}.amazoncognito.com/login?client_id={}&response_type=token&scope={}&redirect_uri={}'.format(userPoolDomain.domain_name, core.Aws.REGION, userPoolAppClient.ref, '+'.join(userPoolAppClient.allowed_o_auth_scopes), apiGatewayLandingPageResource.url),
            description='The Cognito Hosted UI Login Page'
        )

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
