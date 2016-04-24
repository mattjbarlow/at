import json
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flex.core import load, validate_api_call


def test_post_request(request_path):
    schema = load('swagger.awsexport.json')

    URL = 'https://' + schema['host'] + schema['basePath'] + request_path
    lambdaArn = 'arn:aws:lambda:us-east-1:769482945897:function:' \
                'anon-service-Lambda-1CNEQSHUD7Z25'

    time = str(datetime.now() + relativedelta(months=1))
    postdata = json.dumps({"lambdaArn": lambdaArn, "time": time})
    headers = {'Content-Type': 'application/json'}

    # r => response
    r = requests.post(URL, data=postdata, headers=headers)
    validate_api_call(schema, raw_request=r.request, raw_response=r)

if __name__ == "__main__":
    test_post_request('/v1/atq')
