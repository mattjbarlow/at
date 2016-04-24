import logging
import boto3
import utils
from datetime import datetime
from dateutil.parser import parse
from utils import HTTPError
from boto3.dynamodb.conditions import Key, Attr


LOG = logging.getLogger()
logging.basicConfig()
LOG.setLevel(logging.INFO)

def get_operation_handler(operation):
    operation_handler_map = {
        'list_jobs': AtJob,
        'create_job': AtJob,
        'describe_job': AtJob,
        'delete_job': AtJob
    }
    return operation_handler_map[operation]

def lambda_handler(event, context):
    LOG.info(event)
    operation = event['parameters']['gateway']['operationId']
    handler = get_operation_handler(operation)(
        event=event,
        context=context
    )
    LOG.info("Received operation {}".format(operation))
    return getattr(handler, operation)()

class AtJob:
        def __init__(self, event=None, context=None):
            self.db_table = event['parameters']['gateway']['stage-variables'].get('DBTable')
            self.dynamo_connector = boto3.resource('dynamodb')

            self.event = event
            self.context = context
            self.query_params = event['parameters']['request']['query-params']
            self.path_params = event['parameters']['request']['path-params']
            self.body = event['parameters']['request']['body']

        def list_jobs(self):
            table = self.dynamo_connector.Table(self.db_table)
            items = table.scan()['Items']

            response = {
                'collection_count': len(items),
                'data': {
                    'items': [self.at_job(item) for item in items],
                }
            }
            return response

        def create_job(self):
            try:
                lambdaArn = self.body['lambdaArn']
                time = self.body['time']
            except KeyError as exc:
                raise HTTPError(status=400,
                                message='Missing required body fields: %s' % exc)

            try:
                parse(time)
            except ValueError as exc:
                raise HTTPError(status=400,
                                message='Invalid date format: %s' % exc)

            jobid = utils.random_id()
            self._put_rule(jobid, time)
            self._put_target(jobid, lambdaArn)

            table = self.dynamo_connector.Table(self.db_table)

            db_item = {
                'jobid': jobid,
                'lambdaArn': lambdaArn,
                'time': time,
                'created_at': str(datetime.now()),
                'modified_at': str(datetime.now())
            }

            try:
                table.put_item(
                    Item=db_item
                )

            except Exception as exc:
                warning_string = "Error creating new environment DB entry {}"
                LOG.warning(warning_string.format(lambdaArn), exc_info=exc)
                raise

            return db_item

        def describe_job(self):
            jobid = self.path_params['id']
            item = self._check_exists(jobid)

            response = {
                'data': self.at_job(item)
            }
            return response

        def delete_job(self):
            jobid = self.path_params['id']
            LOG.info("jobid is {}".format(jobid))
            table = self.dynamo_connector.Table(self.db_table)
            self._check_exists(jobid)
            response = table.delete_item(
                Key={'jobid': jobid}
            )

            self._remove_target(jobid)
            self._delete_rule(jobid)
            return

        def at_job(self, item):
            return {
                'jobid': item.get('jobid', None),
                'lambdaArn': item.get('lambdaArn', None),
                'time': item.get('time', None),
                'created_at': item.get('created_at', None),
                'modified_at': item.get('modified_at', None)
            }

        def _put_rule(self, jobid, time):
            client = boto3.client('events')
            # se => schedule expression
            se = self._time_to_cron(time)
            response = client.put_rule(
                Name=jobid,
                ScheduleExpression=se
            )
            return response

        def _put_target(self, jobid, lambdaArn):
            client = boto3.client('events')
            response = client.put_targets(
                Rule=jobid,
                Targets=[
                    {
                        'Id': jobid,
                        'Arn': lambdaArn
                    }
                ]
            )

        def _delete_rule(self, jobid):
            client = boto3.client('events')
            response = client.delete_rule(
                Name=jobid
            )
            return response


        def _remove_target(self, jobid):
            client = boto3.client('events')
            response = client.remove_targets(
                Rule=jobid,
                Ids=[jobid]
            )

        def _time_to_cron(self, time):
            # => dto => datetime object
            dto = parse(time)
            return "cron({} {} {} {} ? {})".format(dto.minute,
                                                   dto.hour,
                                                   dto.day,
                                                   dto.month,
                                                   dto.year)

        def _check_exists(self, jobid):
            table = self.dynamo_connector.Table(self.db_table)
            item = table.get_item(
                Key={'jobid': jobid},
            ).get('Item')
            if not item:
                raise HTTPError(status=404,
                                message='Application %s does not exist' % jobid)
            return item
