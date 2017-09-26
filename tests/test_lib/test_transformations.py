from __future__ import absolute_import
import json
import os
import unittest

from lib.transformations import JSONTransformer, TransformationPipeline, \
    TransformerBase, KeyValuePairFormatTransformer, URLParserTransformer, \
    S3KeyFieldExtractorTransformer


ELB_LOG_JSON_SAMPLE = {
    "sent_bytes": "473",
    "ssl_protocol": "TLSv1.2",
    "target_processing_time": "4.675",
    "request_processing_time": "0.001",
    "target_ip": "10.2.6.153",
    "target_group_arn": "arn:aws:elasticloadbalancing:eu-west-1:1234567890:"
                        "targetgroup/aaaaffffbbbbeee3333444467890/"
                        "99990000aabbccdd",
    "elb_status_code": "200",
    "http_version": "HTTP/1.1",
    "ssl_cipher": "ECDHE-RSA-AES128-GCM-SHA256",
    "received_bytes": "395",
    "type": "https",
    "method": "GET",
    "response_processing_time": "0.000",
    "client_ip": "192.168.1.237",
    "timestamp": "2017-09-12T09:24:10.041931Z",
    "target_status_code": "200",
    "target_port": "45407",
    "client_port": "42830",
    "elb_id": "app/aaaaffffbbbbeee3333444467890/aaaabbbbddddffff",
    "url": "https://a.hostname.domain.net:443/"
           "get/details?test=1&timestamp=1505209399",
    "trace_id": "Root=1-55bbaaff-445577883322aabbccddeeee",
    "user_agent": "Ruby"
}


class TestAddFieldTransformer(TransformerBase):
    def __call__(self, event, parsed):
        parsed['A'] = 2
        return parsed


class TestMultiplicationTransformer(TransformerBase):
    def __call__(self, event, parsed):
        parsed['A'] *= 3
        return parsed


class TestToStringTransformer(TransformerBase):
    def __call__(self, event, parsed):
        parsed['A'] = str(parsed['A'])
        return parsed


class TestJSONTransformer(unittest.TestCase):
    def test_callable(self):
        transformer = JSONTransformer()
        self.assertEqual(
            transformer(event=None, parsed={'a': 1}),
            '{"a": 1}'
        )


class TestKeyValuePairFormatTransformer(unittest.TestCase):
    def test_callable(self):
        transformer = KeyValuePairFormatTransformer()
        result = transformer(
            event=None,
            parsed={
                "a": 1,
                "b": 'A"C',
                "c": "GET",
                "Z": 'hello world'
            }
        )
        self.assertEqual(
            result,
            r'Z="hello world" a="1" b="A\"C" c="GET"'
        )


class TestURLParserTransformer(unittest.TestCase):
    def test_callable(self):
        transformer = URLParserTransformer()
        result = transformer(event=None, parsed=ELB_LOG_JSON_SAMPLE)
        self.assertNotIn('url', result)
        self.assertDictContainsSubset(
            {
                "path": "/get/details",
                "port": "443",
                "host": "a.hostname.domain.net",
                "query_string": "test=1&timestamp=1505209399"
            },
            result
        )


class TestS3KeyFieldExtractorTransformer(unittest.TestCase):
    def setUp(self):
        if 'TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING' in os.environ:
            del os.environ['TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING']

    def test_callable(self):
        os.environ['TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING'] = \
            json.dumps([
                {
                    "field": "myfield",
                    "value": "key[1]"
                },
                {
                    "field": "myfield2",
                    "value": "key[3]"
                }
            ])
        event = {
            "Records": [
                {
                    "s3": {
                        "object": {
                            "key": "/a/b/c/d"
                        }
                    }
                }
            ]
        }
        transformer = S3KeyFieldExtractorTransformer()
        parsed_result = transformer(event=event, parsed={})
        expected_result = {"myfield": "b", "myfield2": "d"}
        self.assertDictEqual(
            expected_result,
            parsed_result
        )


class TestTransformationPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = TransformationPipeline(
            TestAddFieldTransformer(),
            TestMultiplicationTransformer(),
            TestToStringTransformer()
        )
        self.parsed_sample = {'B': 'hello world'}

    def _standard_apply_assertions(self, result):
        self.assertEqual(result['B'], self.parsed_sample['B'])
        self.assertIn('A', result)
        self.assertEqual(result['A'], '6')

    def test_apply(self):
        result = self.pipeline.apply(event=None, parsed=self.parsed_sample)
        self._standard_apply_assertions(result)

    def test_build_from_names(self):
        pipeline = TransformationPipeline.build_from_names(
            [
                'TestAddFieldTransformer',
                'TestMultiplicationTransformer',
                'TestToStringTransformer'
            ]
        )
        result = pipeline.apply(event=None, parsed=self.parsed_sample)
        self._standard_apply_assertions(result)
