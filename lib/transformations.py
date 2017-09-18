import json
import logging
import os

from collections import Sequence
from urlparse import urlparse
import urllib

import jmespath


logger = logging.getLogger(__name__)


class TransformerBase(object):
    def __call__(self, event, parsed):
        """
        Perform the transformation on log record field-value pairs.
        Note: only the parsed argument value is retained, if modified.

        :param dict[str] event: the S3 event information for the Lambda
        function invocation.
        :param dict[str] parsed: key-value pairs of log record fields and
        their corresponding values after CSV parsing.
        :return:
        """
        raise NotImplemented()


class JSONTransformer(TransformerBase):
    """
    Serialize in JSON format.
    """
    def __call__(self, event, parsed):
        """
        :rtype: str
        """
        return json.dumps(parsed)


class KeyValuePairFormatTransformer(TransformerBase):
    """
    Convert to KVP format.
    """

    @staticmethod
    def _escape(value):
        return '"{}"'.format(value.replace('"', r'\"'))

    def __call__(self, event, parsed):
        """
        :rtype: str
        """
        formatted_key_value_pairs = []
        for key in sorted(parsed.keys()):
            value = self._escape(str(parsed[key]))
            formatted_key_value_pairs.append(
                '{key}={value}'.format(key=key, value=value)
            )
        return ' '.join(formatted_key_value_pairs)


class URLParserTransformer(TransformerBase):
    """
    Parse the `url` field to all its components:
    - host
    - port
    - path
    - query_string
    """
    def __call__(self, event, parsed):
        """
        :rtype: dict[str]
        """
        full_url = parsed.get('url', '')
        parsed_url = urlparse(full_url)
        host, port = parsed_url.netloc.rsplit(':', 1)
        url_components = {
            'path': parsed_url.path,
            'host': host,
            'port': port,
            'query_string': parsed_url.query
        }

        parsed.update(url_components)

        if 'url' in parsed:
            del parsed['url']

        return parsed


class S3KeyFieldExtractorTransformer(TransformerBase):
    """
    Extract information from the S3 key and enrich the log record.
    - Configurable by: TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING

      JSON-encoded field-value mapping that contains the assignment of
      new field names and their values, as taken from components of the S3 key.
      Assignments are defined using the following structure:

      [
        {
          "field": "custom_1", # the name of the new log field
          "value": "key[0]"    # JMESPATH expression specifying the index
        }
      ]
    """
    def __call__(self, event, parsed):
        field_mappings = json.loads(
            os.environ.get(
                'TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING',
                'null'
            )
        )

        if field_mappings is None:
            return parsed

        key = urllib.unquote_plus(
            jmespath.search('Records[0].s3.object.key', event)
        )
        key_components = key.strip('/').split('/')

        for assignment in field_mappings:
            field_name = assignment['field']
            field_value = jmespath.search(
                assignment['value'],
                {'key': key_components}
            )
            parsed[field_name] = field_value

        return parsed


class TransformationPipeline(Sequence):
    def __init__(self, *callables):
        self.__callables = callables

    def __getitem__(self, item):
        return self.__callables.__getitem__(item)

    def __len__(self):
        return len(self.__callables)

    def apply(self, event, parsed):
        """
        Apply all transformations.
        :param dict[str] event: the S3 event information for the Lambda
        function invocation.
        :param dict[str] parsed: the parsed log record in the form of
        dictionary mapping.
        :return:
        """
        # For the initial iteration we set the identity function
        result = parsed

        for transformer in self.__callables:
            result = transformer(event, result)

        return result

    @staticmethod
    def get_available_transformers_by_name():
        """
        Mapping of transformer classes by name.
        :rtype: dict[str]
        """
        return {
            subclass.__name__: subclass
            for subclass in TransformerBase.__subclasses__()
        }

    @classmethod
    def build_from_names(cls, transformer_class_names):
        """
        Build a pipeline from the given list of transformer class names.
        :param list[str] transformer_class_names: the list of
        transformation class names that will be applied sequentially.
        :rtype: TransformationPipeline
        """
        transformers_by_name = cls.get_available_transformers_by_name()

        callables = []

        for name in transformer_class_names:
            try:
                callables.append(transformers_by_name[name]())
            except KeyError:
                logger.error('Invalid transformer class: {}'.format(name))
                raise

        return cls(*callables)
