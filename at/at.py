import logging


LOG = logging.getLogger()
logging.basicConfig()
LOG.setLevel(logging.INFO)


def lambda_handler(event, context):
    LOG.info('received event{}'.format(event))
