# Trino

Access control trino using uc.

## Setup
```shell
$ docker compose up -d
$ docker exec -it trino-minio-1 trino --catalog bash
bash-5.1# cd /data && mc mb my-bucket
Bucket created successfully `my-bucket`.
$ docker exec -it trino-trino-1 trino --catalog minio
trino> create schema my_schema with ( location = 's3://my-bucket/' );
CREATE SCHEMA
trino> create table my_schema.my_table ( a int ) with ( external_location = 's3://my-bucket/my-path' );
CREATE TABLE
```

## Usage
```shell
$ curl -X POST http://localhost:8080/v1/statement \
    -H 'X-Trino-Extra-Credential: internal$s3_aws_access_key=curlkey, internal$s3_aws_secret_key=mysecret, internal$s3_aws_session_token=somsession' \
    -H 'X-Trino-User: a' \
    -d "create or replace table minio.my_schema.from_curl ( a int ) with ( external_location = 's3://my-bucket/from-curl' )"
# This results in a http request to the s3 api similar to:
# GET http://localhost:9000/my-bucket?list-type=2&prefix=from-curl%2F
# Host: host.docker.internal:9002
# amz-sdk-invocation-id: ea96d995-a791-1651-205b-18712007fb48
# amz-sdk-request:        attempt=1; max=10
# Authorization:          AWS4-HMAC-SHA256 Credential=curlkey/20240621/us-east-1/s3/aws4_request, SignedHeaders=amz-sdk-invocation-id;amz-sdk-request;host;x-amz-content-sha256;x-amz-date;x-amz-security-token, Signature=b7d6a5be64658ef14cd0f6c84ab60f8d8b1ce017ae74a0c1d4134468d47e38b9
# User-Agent:             aws-sdk-java/2.26.1 Linux/5.15.146.1-microsoft-standard-WSL2 OpenJDK_64-Bit_Server_VM/22.0.1+8 Java/22.0.1 kotlin/2.0.0-release-341 vendor/Eclipse_Adoptium io/sync http/Apache cfg/retry-mode/legacy cfg/auth-source#stat PAGINATED/2.26.1
# x-amz-content-sha256:   UNSIGNED-PAYLOAD
# X-Amz-Date:             20240621T011027Z
# X-Amz-Security-Token:   somsession
# Connection:             Keep-Alive
```