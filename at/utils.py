import json
import uuid
from BaseHTTPServer import BaseHTTPRequestHandler


def random_id():
        """Get a random UUID."""
        return str(uuid.uuid4())


class HTTPError(Exception):

    default_status = 500

    def __init__(self, status=None, message=None):
        """Initialize class."""
        responses = BaseHTTPRequestHandler.responses
        self.status_code = status or self.default_status
        error_message = "%d: %s" % (self.status_code,
                                    responses[self.status_code][0])
        if message:
            error_message = "%s - %s" % (error_message,
                                         message)

        super(HTTPError, self).__init__(error_message)
