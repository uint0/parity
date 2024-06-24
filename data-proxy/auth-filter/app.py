import logging
import re

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
import httpx
from quart import Quart, request, Response

UNITY_CATALOG_LOCATION = "http://localhost:8080/api/2.1/unity-catalog"
TARGET_S3_ENDPOINT_TMPL = "https://s3.{region}.amazonaws.com"

app = Quart(__name__)
log = logging.getLogger(__name__)

async def map_auth(catalog_token: str, table_id: str):
    request_body = {
        "table_id": table_id,
        "operation": "READ_WRITE"
    }

    response = httpx.post(
        f"{UNITY_CATALOG_LOCATION}/temporary-table-credentials",
        headers={"Authorization": f"Bearer {catalog_token}"},
        json=request_body
    )

    if response.status_code == 200:
        response_body = response.json()
        raw_creds = response_body["aws_temp_credentials"]
        return Credentials(
            access_key=raw_creds["access_key_id"],
            secret_key=raw_creds["secret_access_key"],
            token=raw_creds.get("session_token"),
        )
    else:
        print(response.text)
        return None


def parse_aws4_hmac_sha256(serialized_credentials: str | None):
    if matches := re.match(
        r"^AWS4-HMAC-SHA256 Credential=(?P<Credential>.+), SignedHeaders=(?P<SignedHeaders>.+), Signature=(?P<Signature>.+)$",
        serialized_credentials
    ):
        credential, signed_headers, _signature = matches.groups()
        c_kid, _c_date, c_region, c_service, _c_ver = credential.split('/')
        headers = set(x.lower() for x in signed_headers.split(';')) - set('x-amz-security-token')

        return (c_kid, c_region, c_service, headers)

    return None


@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
async def handle_request(path: str):
    req_headers = request.headers
    security_token = req_headers.get("x-amz-security-token")
    aws_credentials = req_headers.get("authorization")

    if not security_token: return None
    if not aws_credentials: return None

    c_kid, c_region, c_svc, c_headers = parse_aws4_hmac_sha256(aws_credentials)
    if c_kid != 'passthrough':
        return None

    temp_creds = await map_auth(security_token, "table_id")
    if not temp_creds:
        return Response(status=403)

    # todo: deal with x-amz-content-sha256 not being in the headers
    assert 'x-amz-content-sha256' in c_headers
    target = TARGET_S3_ENDPOINT_TMPL.format(region = c_region)

    signable_headers = {k: v for k, v in req_headers.items() if k.lower() in c_headers and k.lower() != 'host'}
    signable_headers['host'] = target.removeprefix('https://')
    url = f"{target}/{path.lstrip('/')}"
    signed_request = AWSRequest(
        method = request.method,
        url = url,
        headers = signable_headers,
    )
    SigV4Auth(temp_creds, c_svc, c_region).add_auth(signed_request)

    
    print(signed_request.headers)
    response = httpx.request(request.method, url, data=await request.get_data(), headers=dict(signed_request.headers))
    body = response.read()
    print(body)

    return Response(
        response = body,
        status = response.status_code,
        headers = dict(response.headers),
    )

    # TODO: consider running this as a auth filter in envoy instead of standalone
    # return Response(headers=dict(req_headers.copy()) | dict(signed_request.headers))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)