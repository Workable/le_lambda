from __future__ import absolute_import
import gzip
import os
import unittest
from StringIO import StringIO

import mock

import le_lambda

os.environ.update({
    'region': 'unknown-region',
    'token': 'fake-token',
    'AWS_ACCESS_KEY_ID': '-',
    'AWS_SECRET_ACCESS_KEY': '-',
    'AWS_SESSION_TOKEN': '-'
})

# Patch global module-level variables
le_lambda.TOKEN = os.environ['token']
le_lambda.REGION = os.environ['region']


class TestLambdaHandler(unittest.TestCase):
    def setUp(self):
        self.s3_key = \
            'some-prefix/AWSLogs/1234567890/' \
            'elasticloadbalancing/eu-west-1/2017/09/12/' \
            '1234567890_elasticloadbalancing_eu-west-1_' \
            'app.22ff55229966cc00aa9911eeaa226677/' \
            '9999cceedd225588.9999cceedd225588_' \
            '20170912T1850Z_254.254.254.110_' \
            'aabbkkgg.log.gz'

    @mock.patch('le_lambda.s3')
    @mock.patch('le_lambda.create_socket', return_value=mock.MagicMock())
    @mock.patch('le_lambda.validate_uuid', return_value=True)
    def _run_test_case(self, validate_uuid, create_socket, s3, **kwargs):
        _ = validate_uuid
        mock_socket = create_socket.return_value
        mock_socket.sendall = mock.MagicMock()

        s3_file_contents = kwargs['s3_file_contents']
        s3_contents = StringIO()
        with gzip.GzipFile(fileobj=s3_contents, mode="w") as f:
            f.write(s3_file_contents)
        s3_contents.seek(0)
        s3.get_object.return_value = {'Body': s3_contents}

        s3_key = kwargs['s3_key']
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'hello-world-ZZabcdefg'},
                        'object': {
                            'key': s3_key
                        }
                    }
                }
            ]
        }
        event_record = event['Records'][0]
        le_lambda.lambda_handler(event, None)
        s3.get_object.assert_called_once_with(
            Bucket=event_record['s3']['bucket']['name'],
            Key=event_record['s3']['object']['key']
        )

        logentries_forwarded_line = kwargs['logentries_forwarded_line']
        mock_socket.sendall.assert_called_once_with(logentries_forwarded_line)

    def test_invocation(self):
        s3_file_contents = \
            'https 2017-09-12T18:49:38.910213Z app/' \
            '22ff55229966cc00aa9911eeaa226677/9999cceedd225588 ' \
            '254.254.254.5:8750 10.0.3.100:32831 0.001 0.002 0.000 ' \
            '200 200 40 1166 ' \
            '"GET https://254.254.254.211:443/ HTTP/1.1" "-" ' \
            'ECDHE-RSA-AES128-GCM-SHA256 TLSv1.2 ' \
            'arn:aws:elasticloadbalancing:eu-west-1:1234567890:' \
            'targetgroup/bb2299006677ffccaabb22bb33221100/' \
            'dd441133ccdd7744 ' \
            '"Root=1-aabbccdd-33330000444422334444ffff"'

        logentries_forwarded_line = \
            'fake-token {"sent_bytes": "1166", "ssl_protocol": "TLSv1.2", ' \
            '"target_processing_time": "0.002", ' \
            '"request_processing_time": "0.001", ' \
            '"target_ip": "10.0.3.100", ' \
            '"target_group_arn": "arn:aws:elasticloadbalancing:' \
            'eu-west-1:1234567890:targetgroup/' \
            'bb2299006677ffccaabb22bb33221100/dd441133ccdd7744", ' \
            '"elb_status_code": "200", "http_version": "HTTP/1.1", ' \
            '"ssl_cipher": "ECDHE-RSA-AES128-GCM-SHA256", ' \
            '"received_bytes": "40", "type": "https", "method": "GET", ' \
            '"response_processing_time": "0.000", ' \
            '"client_ip": "254.254.254.5", ' \
            '"timestamp": "2017-09-12T18:49:38.910213Z", ' \
            '"target_status_code": "200", "target_port": "32831", ' \
            '"client_port": "8750", "elb_id": "app/22ff55229966cc00aa' \
            '9911eeaa226677/9999cceedd225588", ' \
            '"url": "https://254.254.254.211:443/", ' \
            '"trace_id": "Root=1-aabbccdd-33330000444422334444ffff", ' \
            '"user_agent": "-"}\n'

        self._run_test_case(**{
            'logentries_forwarded_line': logentries_forwarded_line,
            's3_key': self.s3_key,
            's3_file_contents': s3_file_contents
        })

    def test_unknown_target_ip(self):
        s3_file_contents = \
            'https 2017-09-12T18:49:38.910213Z app/' \
            '22ff55229966cc00aa9911eeaa226677/9999cceedd225588 ' \
            '254.254.254.5:8750 - 0.001 0.002 0.000 ' \
            '200 200 40 1166 ' \
            '"GET https://254.254.254.211:443/ HTTP/1.1" "-" ' \
            'ECDHE-RSA-AES128-GCM-SHA256 TLSv1.2 ' \
            'arn:aws:elasticloadbalancing:eu-west-1:1234567890:' \
            'targetgroup/bb2299006677ffccaabb22bb33221100/' \
            'dd441133ccdd7744 ' \
            '"Root=1-aabbccdd-33330000444422334444ffff"'

        logentries_forwarded_line = \
            'fake-token {"sent_bytes": "1166", "ssl_protocol": "TLSv1.2", ' \
            '"target_processing_time": "0.002", ' \
            '"request_processing_time": "0.001", ' \
            '"target_ip": "-", ' \
            '"target_group_arn": "arn:aws:elasticloadbalancing:' \
            'eu-west-1:1234567890:targetgroup/' \
            'bb2299006677ffccaabb22bb33221100/dd441133ccdd7744", ' \
            '"elb_status_code": "200", "http_version": "HTTP/1.1", ' \
            '"ssl_cipher": "ECDHE-RSA-AES128-GCM-SHA256", ' \
            '"received_bytes": "40", "type": "https", "method": "GET", ' \
            '"response_processing_time": "0.000", ' \
            '"client_ip": "254.254.254.5", ' \
            '"timestamp": "2017-09-12T18:49:38.910213Z", ' \
            '"target_status_code": "200", "target_port": "-", ' \
            '"client_port": "8750", "elb_id": "app/22ff55229966cc00aa' \
            '9911eeaa226677/9999cceedd225588", ' \
            '"url": "https://254.254.254.211:443/", ' \
            '"trace_id": "Root=1-aabbccdd-33330000444422334444ffff", ' \
            '"user_agent": "-"}\n'

        self._run_test_case(**{
            'logentries_forwarded_line': logentries_forwarded_line,
            's3_key': self.s3_key,
            's3_file_contents': s3_file_contents
        })

