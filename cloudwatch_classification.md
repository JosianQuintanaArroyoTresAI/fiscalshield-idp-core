timestamp,message
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function remove_bucket_from_url_paths_from_model at 0xffff83cb8b80>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <bound method S3RegionRedirectorv2.annotate_request_context of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <bound method ClientCreator._inject_s3_input_parameters of <botocore.client.ClientCreator object at 0xffff81b09f40>>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function generate_idempotent_uuid at 0xffff83e12700>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function _handle_request_validation_mode_member at 0xffff83cb9260>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <function customize_endpoint_resolver_builtins at 0xffff83cb8d60>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <bound method S3RegionRedirectorv2.redirect_from_cache of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Calling endpoint provider with parameters: {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Region': 'eu-central-1', 'UseFIPS': False, 'UseDualStack': False, 'ForcePathStyle': False, 'Accelerate': False, 'UseGlobalEndpoint': False, 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json', 'DisableMultiRegionAccessPoints': False, 'UseArnRegion': True}
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Endpoint provider result: https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Selecting from endpoint provider's list of auth schemes: ""sigv4"". User selected auth scheme is: ""None""
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Selected auth type ""v4"" as ""v4"" with signing context params: {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function add_expect_header at 0xffff83e12ca0>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <bound method S3ExpressIdentityResolver.apply_signing_cache_key of <botocore.utils.S3ExpressIdentityResolver object at 0xffff703f3d10>>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function add_recursion_detection_header at 0xffff83e10fe0>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function inject_api_version_header_if_needed at 0xffff83cb8220>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Making request for OperationModel(name=GetObject) with params: {'url_path': '/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json', 'query_string': {}, 'method': 'GET', 'headers': {'x-amz-checksum-mode': 'ENABLED', 'User-Agent': 'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'X-Amzn-Trace-Id': 'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0'}, 'body': b'', 'auth_path': '/fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json', 'url': 'https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json', 'context': {'client_region': 'eu-central-1', 'client_config': <botocore.config.Config object at 0xffff703b55e0>, 'has_streaming_input': False, 'auth_type': 'v4', 'unsigned_payload': None, 'auth_options': ['aws.auth#sigv4'], 's3_redirect': {'redirected': False, 'bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'params': {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json', 'ChecksumMode': 'ENABLED'}}, 'input_params': {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json'}, 'signing': {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}, 'endpoint_properties': {'authSchemes': [{'disableDoubleEncoding': True, 'name': 'sigv4', 'signingName': 's3', 'signingRegion': 'eu-central-1'}]}, 'checksum': {'response_algorithms': ['crc32', 'sha1', 'sha256']}}}
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <bound method RequestSigner.handler of <botocore.signers.RequestSigner object at 0xffff703b56a0>>
"
1764520984727,"[DEBUG]	2025-11-30T16:43:04.727Z	72e452af-9de0-4b81-94d4-203b311e345d	Event choose-signer.s3.GetObject: calling handler <function set_operation_specific_signer at 0xffff83e12480>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <function remove_arn_from_signing_path at 0xffff83cb8cc0>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <function _set_extra_headers_for_unsigned_request at 0xffff83cb9300>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <bound method S3ExpressIdentityResolver.resolve_s3express_identity of <botocore.utils.S3ExpressIdentityResolver object at 0xffff703f3d10>>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Calculating signature using v4 auth.
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	CanonicalRequest:
"
1764520984728,"GET
"
1764520984728,"/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json
"
1764520984728,"host:fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com
"
1764520984728,"x-amz-checksum-mode:ENABLED
"
1764520984728,"x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
"
1764520984728,"x-amz-date:20251130T164304Z
"
1764520984728,"x-amz-security-token:IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E
"
1764520984728,"host;x-amz-checksum-mode;x-amz-content-sha256;x-amz-date;x-amz-security-token
"
1764520984728,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	StringToSign:
"
1764520984728,"AWS4-HMAC-SHA256
"
1764520984728,"20251130T164304Z
"
1764520984728,"20251130/eu-central-1/s3/aws4_request
"
1764520984728,"3780613aa318076abdab5da2809430a401b47cfc5944f48f48e3d7ad0875d236
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Signature:
"
1764520984728,"f76dcf101a96d429654c7cca0311d3093f69129ea7bef1df25fe7b719966e00c
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <bound method UserAgentString.rebuild_and_replace_user_agent_handler of <botocore.useragent.UserAgentString object at 0xffff703f3590>>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <function add_retry_headers at 0xffff83cb8ae0>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Sending http request: <AWSPreparedRequest stream_output=True, method=GET, url=https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json, headers={'x-amz-checksum-mode': b'ENABLED', 'User-Agent': b'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'X-Amzn-Trace-Id': b'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0', 'X-Amz-Date': b'20251130T164304Z', 'X-Amz-Security-Token': b'IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E', 'X-Amz-Content-SHA256': b'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'Authorization': b'AWS4-HMAC-SHA256 Credential=ASIA4SYAMK57AP6636FK/20251130/eu-central-1/s3/aws4_request, SignedHeaders=host;x-amz-checksum-mode;x-amz-content-sha256;x-amz-date;x-amz-security-token, Signature=f76dcf101a96d429654c7cca0311d3093f69129ea7bef1df25fe7b719966e00c', 'amz-sdk-invocation-id': b'b28fe7ea-80e2-4610-b85a-50c8ad448bd3', 'amz-sdk-request': b'attempt=1'}>
"
1764520984728,"[DEBUG]	2025-11-30T16:43:04.728Z	72e452af-9de0-4b81-94d4-203b311e345d	Certificate path: /opt/python/certifi/cacert.pem
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.754Z	72e452af-9de0-4b81-94d4-203b311e345d	https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com:443 ""GET /users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/27/result.json HTTP/1.1"" 200 420
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.GetObject: calling handler <function _handle_200_error at 0xffff83cb9080>
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.GetObject: calling handler <function handle_expires_header at 0xffff83cb8ea0>
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Response headers: {'x-amz-id-2': 'Jw2suibPxveNTlxlXEfcGAAOTETIups/q9/AydV5zfunNuD/igrr/dXq9ggLaeEMpVpS4vuK9Lu8R0JIsvM8OXNL/51g6ZBK9iz6Fa1Rg90=', 'x-amz-request-id': 'ZFZ0DB5WHDX6HJV8', 'Date': 'Sun, 30 Nov 2025 16:43:05 GMT', 'Last-Modified': 'Sun, 30 Nov 2025 16:42:51 GMT', 'x-amz-expiration': 'expiry-date=""Tue, 01 Dec 2026 00:00:00 GMT"", rule-id=""DeleteAfterNDays""', 'ETag': '""9a04511d0224abb233fdfa5959ecfb4c""', 'x-amz-checksum-crc32': 'KQm83Q==', 'x-amz-checksum-type': 'FULL_OBJECT', 'x-amz-server-side-encryption': 'aws:kms', 'x-amz-server-side-encryption-aws-kms-key-id': 'arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb', 'x-amz-version-id': 'M4V1ehXOJTEeEHQTjFanPqO1e9Dtk5l1', 'Accept-Ranges': 'bytes', 'Content-Type': 'application/json', 'Content-Length': '420', 'Server': 'AmazonS3'}
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Response body:
"
1764520984755,"<botocore.httpchecksum.StreamingChecksumBody object at 0xffff705405e0>
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <function _update_status_code at 0xffff83cb91c0>
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <botocore.retryhandler.RetryHandler object at 0xffff703f3ce0>
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	No retry needed.
"
1764520984755,"[DEBUG]	2025-11-30T16:43:04.755Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <bound method S3RegionRedirectorv2.redirect_from_error of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984756,"[INFO]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	📄 Section text length: 420 chars
"
1764520984756,"[ERROR]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	❌ Error in LLM boundary detection: '
    ""id""'
"
1764520984756,"[WARNING]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	⚠️ Boundary detection/validation failed for section 26
"
1764520984756,"[INFO]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	🔍 Detecting boundaries for invoice section 27
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function sse_md5 at 0xffff83e12980>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function validate_bucket_name at 0xffff83e128e0>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function remove_bucket_from_url_paths_from_model at 0xffff83cb8b80>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <bound method S3RegionRedirectorv2.annotate_request_context of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <bound method ClientCreator._inject_s3_input_parameters of <botocore.client.ClientCreator object at 0xffff81b09f40>>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function generate_idempotent_uuid at 0xffff83e12700>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.GetObject: calling handler <function _handle_request_validation_mode_member at 0xffff83cb9260>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <function customize_endpoint_resolver_builtins at 0xffff83cb8d60>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <bound method S3RegionRedirectorv2.redirect_from_cache of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984756,"[DEBUG]	2025-11-30T16:43:04.756Z	72e452af-9de0-4b81-94d4-203b311e345d	Calling endpoint provider with parameters: {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Region': 'eu-central-1', 'UseFIPS': False, 'UseDualStack': False, 'ForcePathStyle': False, 'Accelerate': False, 'UseGlobalEndpoint': False, 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json', 'DisableMultiRegionAccessPoints': False, 'UseArnRegion': True}
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Endpoint provider result: https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Selecting from endpoint provider's list of auth schemes: ""sigv4"". User selected auth scheme is: ""None""
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Selected auth type ""v4"" as ""v4"" with signing context params: {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function add_expect_header at 0xffff83e12ca0>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <bound method S3ExpressIdentityResolver.apply_signing_cache_key of <botocore.utils.S3ExpressIdentityResolver object at 0xffff703f3d10>>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function add_recursion_detection_header at 0xffff83e10fe0>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.GetObject: calling handler <function inject_api_version_header_if_needed at 0xffff83cb8220>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Making request for OperationModel(name=GetObject) with params: {'url_path': '/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json', 'query_string': {}, 'method': 'GET', 'headers': {'x-amz-checksum-mode': 'ENABLED', 'User-Agent': 'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'X-Amzn-Trace-Id': 'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0'}, 'body': b'', 'auth_path': '/fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json', 'url': 'https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json', 'context': {'client_region': 'eu-central-1', 'client_config': <botocore.config.Config object at 0xffff703b55e0>, 'has_streaming_input': False, 'auth_type': 'v4', 'unsigned_payload': None, 'auth_options': ['aws.auth#sigv4'], 's3_redirect': {'redirected': False, 'bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'params': {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json', 'ChecksumMode': 'ENABLED'}}, 'input_params': {'Bucket': 'fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen', 'Key': 'users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json'}, 'signing': {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}, 'endpoint_properties': {'authSchemes': [{'disableDoubleEncoding': True, 'name': 'sigv4', 'signingName': 's3', 'signingRegion': 'eu-central-1'}]}, 'checksum': {'response_algorithms': ['crc32', 'sha1', 'sha256']}}}
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <bound method RequestSigner.handler of <botocore.signers.RequestSigner object at 0xffff703b56a0>>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event choose-signer.s3.GetObject: calling handler <function set_operation_specific_signer at 0xffff83e12480>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <function remove_arn_from_signing_path at 0xffff83cb8cc0>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <function _set_extra_headers_for_unsigned_request at 0xffff83cb9300>
"
1764520984757,"[DEBUG]	2025-11-30T16:43:04.757Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.GetObject: calling handler <bound method S3ExpressIdentityResolver.resolve_s3express_identity of <botocore.utils.S3ExpressIdentityResolver object at 0xffff703f3d10>>
"
1764520984758,"[DEBUG]	2025-11-30T16:43:04.758Z	72e452af-9de0-4b81-94d4-203b311e345d	Calculating signature using v4 auth.
"
1764520984758,"[DEBUG]	2025-11-30T16:43:04.758Z	72e452af-9de0-4b81-94d4-203b311e345d	CanonicalRequest:
"
1764520984758,"GET
"
1764520984758,"/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json
"
1764520984758,"host:fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com
"
1764520984758,"x-amz-checksum-mode:ENABLED
"
1764520984758,"x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
"
1764520984758,"x-amz-date:20251130T164304Z
"
1764520984758,"x-amz-security-token:IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E
"
1764520984758,"host;x-amz-checksum-mode;x-amz-content-sha256;x-amz-date;x-amz-security-token
"
1764520984758,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
"
1764520984758,"[DEBUG]	2025-11-30T16:43:04.758Z	72e452af-9de0-4b81-94d4-203b311e345d	StringToSign:
"
1764520984758,"AWS4-HMAC-SHA256
"
1764520984758,"20251130T164304Z
"
1764520984758,"20251130/eu-central-1/s3/aws4_request
"
1764520984758,"6307706b720e815700bc3b4fa2aa40d4eb4affff2ec6884c1ff6ff8f13e594f5
"
1764520984758,"[DEBUG]	2025-11-30T16:43:04.758Z	72e452af-9de0-4b81-94d4-203b311e345d	Signature:
"
1764520984758,"4953e34680bd0b6e8416a5508ff52cc196589d2dd217872056a2ab7666fb45e2
"
1764520984758,"[DEBUG]	2025-11-30T16:43:04.758Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <bound method UserAgentString.rebuild_and_replace_user_agent_handler of <botocore.useragent.UserAgentString object at 0xffff703f3590>>
"
1764520984759,"[DEBUG]	2025-11-30T16:43:04.759Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.GetObject: calling handler <function add_retry_headers at 0xffff83cb8ae0>
"
1764520984759,"[DEBUG]	2025-11-30T16:43:04.759Z	72e452af-9de0-4b81-94d4-203b311e345d	Sending http request: <AWSPreparedRequest stream_output=True, method=GET, url=https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json, headers={'x-amz-checksum-mode': b'ENABLED', 'User-Agent': b'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'X-Amzn-Trace-Id': b'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0', 'X-Amz-Date': b'20251130T164304Z', 'X-Amz-Security-Token': b'IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E', 'X-Amz-Content-SHA256': b'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'Authorization': b'AWS4-HMAC-SHA256 Credential=ASIA4SYAMK57AP6636FK/20251130/eu-central-1/s3/aws4_request, SignedHeaders=host;x-amz-checksum-mode;x-amz-content-sha256;x-amz-date;x-amz-security-token, Signature=4953e34680bd0b6e8416a5508ff52cc196589d2dd217872056a2ab7666fb45e2', 'amz-sdk-invocation-id': b'f74583d7-0f37-4e51-98a5-772c88d41966', 'amz-sdk-request': b'attempt=1'}>
"
1764520984759,"[DEBUG]	2025-11-30T16:43:04.759Z	72e452af-9de0-4b81-94d4-203b311e345d	Certificate path: /opt/python/certifi/cacert.pem
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	https://fiscalshield-idp-dev-outputbucket-1b6w2y9hfuen.s3.eu-central-1.amazonaws.com:443 ""GET /users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/pages/17/result.json HTTP/1.1"" 200 446
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.GetObject: calling handler <function _handle_200_error at 0xffff83cb9080>
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.GetObject: calling handler <function handle_expires_header at 0xffff83cb8ea0>
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Response headers: {'x-amz-id-2': 'D/nWkG7NFXGEJ8Pm6Ldoyyp5eflaGe0JmucLc24q992kFILG7wbIaQUPR/qc5WyfAqYvizgv09jd491wMZHuVbP2s2cWPc9f6P/bPqI0AAc=', 'x-amz-request-id': 'ZFZ8HS8MV6QQFMQW', 'Date': 'Sun, 30 Nov 2025 16:43:05 GMT', 'Last-Modified': 'Sun, 30 Nov 2025 16:42:49 GMT', 'x-amz-expiration': 'expiry-date=""Tue, 01 Dec 2026 00:00:00 GMT"", rule-id=""DeleteAfterNDays""', 'ETag': '""ac1c82a486db4533ae06c760e0d879fe""', 'x-amz-checksum-crc32': 'ZfaJbw==', 'x-amz-checksum-type': 'FULL_OBJECT', 'x-amz-server-side-encryption': 'aws:kms', 'x-amz-server-side-encryption-aws-kms-key-id': 'arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb', 'x-amz-version-id': 'hkWeJJNtrdDE.LwXCCVE_cGJN8PBML_N', 'Accept-Ranges': 'bytes', 'Content-Type': 'application/json', 'Content-Length': '446', 'Server': 'AmazonS3'}
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Response body:
"
1764520984801,"<botocore.httpchecksum.StreamingChecksumBody object at 0xffff705420b0>
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <function _update_status_code at 0xffff83cb91c0>
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <botocore.retryhandler.RetryHandler object at 0xffff703f3ce0>
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	No retry needed.
"
1764520984801,"[DEBUG]	2025-11-30T16:43:04.801Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.GetObject: calling handler <bound method S3RegionRedirectorv2.redirect_from_error of <botocore.utils.S3RegionRedirectorv2 object at 0xffff703f35f0>>
"
1764520984802,"[INFO]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	📄 Section text length: 446 chars
"
1764520984802,"[ERROR]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	❌ Error in LLM boundary detection: '
    ""id""'
"
1764520984802,"[WARNING]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	⚠️ Boundary detection/validation failed for section 27
"
1764520984802,"[INFO]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	Lambda metering for Classification: duration=8.845s, memory=4096.0MB, gb_seconds=35.4
"
1764520984802,"[INFO]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	Document size after classification: 29715 bytes
"
1764520984802,"[INFO]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	Document size (29715 bytes) exceeds 0KB threshold, compressing to S3
"
1764520984802,"[DEBUG]	2025-11-30T16:43:04.802Z	72e452af-9de0-4b81-94d4-203b311e345d	Event choose-service-name: calling handler <function handle_service_name_alias at 0xffff83e10cc0>
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Event creating-client-class.s3: calling handler <function add_generate_presigned_post at 0xffff83dbc860>
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Event creating-client-class.s3: calling handler <function lazy_call.<locals>._handler at 0xffff838d54e0>
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Event creating-client-class.s3: calling handler <function add_generate_presigned_url at 0xffff83dbc5e0>
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Looking for endpoint for s3 via: environment_service
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Looking for endpoint for s3 via: environment_global
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Looking for endpoint for s3 via: config_service
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	Looking for endpoint for s3 via: config_global
"
1764520984805,"[DEBUG]	2025-11-30T16:43:04.805Z	72e452af-9de0-4b81-94d4-203b311e345d	No configured endpoint found.
"
1764520984806,"[DEBUG]	2025-11-30T16:43:04.806Z	72e452af-9de0-4b81-94d4-203b311e345d	Setting s3 timeout as (60, 60)
"
1764520984808,"[DEBUG]	2025-11-30T16:43:04.808Z	72e452af-9de0-4b81-94d4-203b311e345d	Registering retry handlers for service: s3
"
1764520984809,"[DEBUG]	2025-11-30T16:43:04.808Z	72e452af-9de0-4b81-94d4-203b311e345d	Registering S3 region redirector handler
"
1764520984809,"[DEBUG]	2025-11-30T16:43:04.809Z	72e452af-9de0-4b81-94d4-203b311e345d	Registering S3Express Identity Resolver
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function validate_ascii_metadata at 0xffff83e136a0>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function sse_md5 at 0xffff83e12980>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function convert_body_to_file_like_object at 0xffff83cb80e0>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function validate_bucket_name at 0xffff83e128e0>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function remove_bucket_from_url_paths_from_model at 0xffff83cb8b80>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <bound method S3RegionRedirectorv2.annotate_request_context of <botocore.utils.S3RegionRedirectorv2 object at 0xffff83f698b0>>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <bound method ClientCreator._inject_s3_input_parameters of <botocore.client.ClientCreator object at 0xffff7063a360>>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function generate_idempotent_uuid at 0xffff83e12700>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parameter-build.s3.PutObject: calling handler <function _handle_request_validation_mode_member at 0xffff83cb9260>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <function customize_endpoint_resolver_builtins at 0xffff83cb8d60>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-endpoint-resolution.s3: calling handler <bound method S3RegionRedirectorv2.redirect_from_cache of <botocore.utils.S3RegionRedirectorv2 object at 0xffff83f698b0>>
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Calling endpoint provider with parameters: {'Bucket': 'fiscalshield-idp-dev-workingbucket-c1mept6rt9di', 'Region': 'eu-central-1', 'UseFIPS': False, 'UseDualStack': False, 'ForcePathStyle': False, 'Accelerate': False, 'UseGlobalEndpoint': False, 'Key': 'compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json', 'DisableMultiRegionAccessPoints': False, 'UseArnRegion': True}
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Endpoint provider result: https://fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Selecting from endpoint provider's list of auth schemes: ""sigv4"". User selected auth scheme is: ""None""
"
1764520984810,"[DEBUG]	2025-11-30T16:43:04.810Z	72e452af-9de0-4b81-94d4-203b311e345d	Selected auth type ""v4"" as ""v4"" with signing context params: {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.PutObject: calling handler <function add_expect_header at 0xffff83e12ca0>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Adding expect 100 continue header to request.
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.PutObject: calling handler <bound method S3ExpressIdentityResolver.apply_signing_cache_key of <botocore.utils.S3ExpressIdentityResolver object at 0xffff705d75f0>>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.PutObject: calling handler <function add_recursion_detection_header at 0xffff83e10fe0>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-call.s3.PutObject: calling handler <function inject_api_version_header_if_needed at 0xffff83cb8220>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Making request for OperationModel(name=PutObject) with params: {'url_path': '/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json', 'query_string': {}, 'method': 'PUT', 'headers': {'Content-Type': 'application/json', 'User-Agent': 'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'Expect': '100-continue', 'X-Amzn-Trace-Id': 'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0', 'Transfer-Encoding': 'chunked', 'Content-Encoding': 'aws-chunked', 'X-Amz-Trailer': 'x-amz-checksum-crc32', 'X-Amz-Decoded-Content-Length': '29715', 'x-amz-sdk-checksum-algorithm': 'CRC32'}, 'body': <botocore.httpchecksum.AwsChunkedWrapper object at 0xffff70530bf0>, 'auth_path': '/fiscalshield-idp-dev-workingbucket-c1mept6rt9di/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json', 'url': 'https://fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json', 'context': {'client_region': 'eu-central-1', 'client_config': <botocore.config.Config object at 0xffff703b48c0>, 'has_streaming_input': True, 'auth_type': 'v4', 'unsigned_payload': None, 'auth_options': ['aws.auth#sigv4'], 's3_redirect': {'redirected': False, 'bucket': 'fiscalshield-idp-dev-workingbucket-c1mept6rt9di', 'params': {'Bucket': 'fiscalshield-idp-dev-workingbucket-c1mept6rt9di', 'Key': 'compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json', 'Body': <_io.BytesIO object at 0xffff706f1a80>, 'ContentType': 'application/json'}}, 'input_params': {'Bucket': 'fiscalshield-idp-dev-workingbucket-c1mept6rt9di', 'Key': 'compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json'}, 'signing': {'region': 'eu-central-1', 'signing_name': 's3', 'disableDoubleEncoding': True}, 'endpoint_properties': {'authSchemes': [{'disableDoubleEncoding': True, 'name': 'sigv4', 'signingName': 's3', 'signingRegion': 'eu-central-1'}]}, 'checksum': {'request_algorithm_header': {'name': 'x-amz-sdk-checksum-algorithm', 'value': 'CRC32'}, 'request_algorithm': {'algorithm': 'crc32', 'in': 'trailer', 'name': 'x-amz-checksum-crc32'}}}}
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.PutObject: calling handler <bound method RequestSigner.handler of <botocore.signers.RequestSigner object at 0xffff703b7800>>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event choose-signer.s3.PutObject: calling handler <function set_operation_specific_signer at 0xffff83e12480>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.PutObject: calling handler <function remove_arn_from_signing_path at 0xffff83cb8cc0>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.PutObject: calling handler <function _set_extra_headers_for_unsigned_request at 0xffff83cb9300>
"
1764520984811,"[DEBUG]	2025-11-30T16:43:04.811Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-sign.s3.PutObject: calling handler <bound method S3ExpressIdentityResolver.resolve_s3express_identity of <botocore.utils.S3ExpressIdentityResolver object at 0xffff705d75f0>>
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Calculating signature using v4 auth.
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	CanonicalRequest:
"
1764520984812,"PUT
"
1764520984812,"/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json
"
1764520984812,"content-encoding:aws-chunked
"
1764520984812,"content-type:application/json
"
1764520984812,"host:fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com
"
1764520984812,"x-amz-content-sha256:STREAMING-UNSIGNED-PAYLOAD-TRAILER
"
1764520984812,"x-amz-date:20251130T164304Z
"
1764520984812,"x-amz-decoded-content-length:29715
"
1764520984812,"x-amz-sdk-checksum-algorithm:CRC32
"
1764520984812,"x-amz-security-token:IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E
"
1764520984812,"x-amz-trailer:x-amz-checksum-crc32
"
1764520984812,"content-encoding;content-type;host;x-amz-content-sha256;x-amz-date;x-amz-decoded-content-length;x-amz-sdk-checksum-algorithm;x-amz-security-token;x-amz-trailer
"
1764520984812,"STREAMING-UNSIGNED-PAYLOAD-TRAILER
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	StringToSign:
"
1764520984812,"AWS4-HMAC-SHA256
"
1764520984812,"20251130T164304Z
"
1764520984812,"20251130/eu-central-1/s3/aws4_request
"
1764520984812,"e7ba8c2daf983a49df9b3d9b822e99b26162b4a95eb242a5b325c0872121740c
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Signature:
"
1764520984812,"840c613ec0488c09b7181525ecc76e4423975d1f3a950a98a264f509516e8a01
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.PutObject: calling handler <bound method UserAgentString.rebuild_and_replace_user_agent_handler of <botocore.useragent.UserAgentString object at 0xffff705d7530>>
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Event request-created.s3.PutObject: calling handler <function add_retry_headers at 0xffff83cb8ae0>
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Sending http request: <AWSPreparedRequest stream_output=False, method=PUT, url=https://fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json, headers={'Content-Type': b'application/json', 'User-Agent': b'Boto3/1.39.7 md/Botocore#1.39.17 ua/2.1 os/linux#5.10.245-269.978.amzn2.aarch64 md/arch#aarch64 lang/python#3.12.12 md/pyimpl#CPython exec-env/AWS_Lambda_python3.12 m/U,b,D,Z cfg/retry-mode#legacy Botocore/1.39.17', 'Expect': b'100-continue', 'X-Amzn-Trace-Id': b'Root=1-692c73f4-1ed9ccacf77f74d4f28a975e;Parent=39cbf63ae2e997a9;Sampled=0;Lineage=3:a9bb9278:0', 'Transfer-Encoding': b'chunked', 'Content-Encoding': b'aws-chunked', 'X-Amz-Trailer': b'x-amz-checksum-crc32', 'X-Amz-Decoded-Content-Length': b'29715', 'x-amz-sdk-checksum-algorithm': b'CRC32', 'X-Amz-Date': b'20251130T164304Z', 'X-Amz-Security-Token': b'IQoJb3JpZ2luX2VjECEaDGV1LWNlbnRyYWwtMSJGMEQCIDlOB+3kIPy7r0bZAqILETYKgKZRqyYlwacGFGc5koKnAiB07tCzno16ubuq6dyx8sj4Z/29AyyHrLriYWkT3C8idyrfAwjq//////////8BEAAaDDg2NDg5OTg0ODA2MiIMtEiFLF6HvtxD2yIoKrMD2vu09KQieiigbe7A5Msoyr7C7MlS2fvxG1ftV1F5nMf/5l00AEG3/p4H1nU2GSwvv8Skzo4GTBrI9XFiu/8u9OPXHSl0UXJWDB+kBW2W17gbSnXR2i5ITiJqhX/ftIzy4DPdHCD0r5CjkaW+WcFqXzmw2hwkgEzmZ2syKDtaWikW9BCvmkUD21m75kBgrRgFvcOhd7laHX0+HpLIXUXP9DWKRdqZ8Dp986ya44X41owUU6v9urjkGMDSucOxFszM0cTHnO6jjpo3sfZZWgWMimVpcrge9YQyrYiT2Yo0ywJXpbQJMcTKFTLPuvXx7onzCVobicLx1ZcxY8xEPArYrL2GvyIpV5YOf/EfaAbkMf05Mo69Hx8lLohQhHweLubg8eeLFEicQ7CUZhafxMu3mJms/CXB0oU+cOGEhy3/LgG+ZKPw4PgwPrts8lSHcgJRT0zzGLXNn0+0BhvoHUt5iVT72/pBaAdZBQsUlk8FdGt0ama+XFhow9Su0+bKPUgLRexma6l85LWvm6ESdRMqbfVjz0CToPEQjIO+EVTbnbJrEomCuzcwO6GfVZZ93jJaT9jLMI7osckGOp8BHZOQtXY4E+beFr2tLeucvAVi96pkcZF9iS+gSJwdBwAt2VcFdJgpCT6dnygsPdVJhouJPVKNyt7J/0rHgxsyyk7QxQR+30Vik5nBciPnkvohGlv8MPsB7iUa3fSlaelG4B3UysqgEkhTvAAzAMz+XJpEmpGlcAWEiD7+DB00tPfBzzBBCEBQzjh4RejzrDy9nAgnARqiJ8pTDwlui34E', 'X-Amz-Content-SHA256': b'STREAMING-UNSIGNED-PAYLOAD-TRAILER', 'Authorization': b'AWS4-HMAC-SHA256 Credential=ASIA4SYAMK57AP6636FK/20251130/eu-central-1/s3/aws4_request, SignedHeaders=content-encoding;content-type;host;x-amz-content-sha256;x-amz-date;x-amz-decoded-content-length;x-amz-sdk-checksum-algorithm;x-amz-security-token;x-amz-trailer, Signature=840c613ec0488c09b7181525ecc76e4423975d1f3a950a98a264f509516e8a01', 'amz-sdk-invocation-id': b'734b5926-d6ff-4685-abc2-ea0c070504b6', 'amz-sdk-request': b'attempt=1'}>
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Certificate path: /opt/python/certifi/cacert.pem
"
1764520984812,"[DEBUG]	2025-11-30T16:43:04.812Z	72e452af-9de0-4b81-94d4-203b311e345d	Starting new HTTPS connection (1): fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com:443
"
1764520984827,"[DEBUG]	2025-11-30T16:43:04.827Z	72e452af-9de0-4b81-94d4-203b311e345d	Waiting for 100 Continue response.
"
1764520984880,"[DEBUG]	2025-11-30T16:43:04.880Z	72e452af-9de0-4b81-94d4-203b311e345d	100 Continue response seen, now sending request body.
"
1764520984909,"[DEBUG]	2025-11-30T16:43:04.909Z	72e452af-9de0-4b81-94d4-203b311e345d	https://fiscalshield-idp-dev-workingbucket-c1mept6rt9di.s3.eu-central-1.amazonaws.com:443 ""PUT /compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json HTTP/1.1"" 200 0
"
1764520984909,"[DEBUG]	2025-11-30T16:43:04.909Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.PutObject: calling handler <function _handle_200_error at 0xffff83cb9080>
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.909Z	72e452af-9de0-4b81-94d4-203b311e345d	Event before-parse.s3.PutObject: calling handler <function handle_expires_header at 0xffff83cb8ea0>
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Response headers: {'x-amz-id-2': '3yYyV/HAv0of3Sp4EmbemmBaACfFrTYbYlY69bGGX5ziW+2wZomV9qeVHqXj+oFUR5dxe91tE5/xFS1XqDyDe9SGuOA7DskGypz5sUEFJDE=', 'x-amz-request-id': 'ZFZ4TVE6VBNJ773Y', 'Date': 'Sun, 30 Nov 2025 16:43:05 GMT', 'x-amz-version-id': 'Gow86pYVclugGy4ay2pPq_kajTuZRCmS', 'x-amz-expiration': 'expiry-date=""Wed, 31 Dec 2025 00:00:00 GMT"", rule-id=""DeleteAfterNDays""', 'x-amz-server-side-encryption': 'aws:kms', 'x-amz-server-side-encryption-aws-kms-key-id': 'arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb', 'ETag': '""06e875a502fcab85fe98eec137090518""', 'x-amz-checksum-crc32': 'zzGn+Q==', 'x-amz-checksum-type': 'FULL_OBJECT', 'Content-Length': '0', 'Server': 'AmazonS3'}
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Response body:
"
1764520984910,"b''
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.PutObject: calling handler <function _update_status_code at 0xffff83cb91c0>
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.PutObject: calling handler <botocore.retryhandler.RetryHandler object at 0xffff705d78f0>
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	No retry needed.
"
1764520984910,"[DEBUG]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Event needs-retry.s3.PutObject: calling handler <bound method S3RegionRedirectorv2.redirect_from_error of <botocore.utils.S3RegionRedirectorv2 object at 0xffff83f698b0>>
"
1764520984910,"[INFO]	2025-11-30T16:43:04.910Z	72e452af-9de0-4b81-94d4-203b311e345d	Compressed document users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf to s3://fiscalshield-idp-dev-workingbucket-c1mept6rt9di/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json
"
1764520984912,"[INFO]	2025-11-30T16:43:04.911Z	72e452af-9de0-4b81-94d4-203b311e345d	Response: {""document"": {""id"": ""users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf"", ""document_id"": ""users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf"", ""s3_uri"": ""s3://fiscalshield-idp-dev-workingbucket-c1mept6rt9di/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764520984809_classification_state.json"", ""timestamp"": ""1764520984809"", ""status"": ""CLASSIFYING"", ""num_pages"": 28, ""sections"": [{""section_id"": ""1"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""2"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""3"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""4"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""5"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""6"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""7"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""8"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""9"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""10"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""11"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""12"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""13"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""14"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""15"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""16"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""17"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""18"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""19"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""20"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""21"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""22"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""23"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""24"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""25"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""26"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""27"", ""classification"": ""invoice"", ""confidence"": 1.0}], ""compressed"": true, ""user_id"": ""23b4b872-20a1-709e-ffef-d20a604f60b5"", ""client_id"": ""15944206"", ""company_number"": ""15944206"", ""company_name"": ""TRESAI LIMITED""}}
"
1764520984917,"END RequestId: 72e452af-9de0-4b81-94d4-203b311e345d
"
1764520984917,"REPORT RequestId: 72e452af-9de0-4b81-94d4-203b311e345d	Duration: 8959.28 ms	Billed Duration: 10163 ms	Memory Size: 4096 MB	Max Memory Used: 159 MB	Init Duration: 1202.75 ms	
"