# le_lambda
Follow the instructions below to send logs stored on AWS S3 to Logentries.

All source code and dependencies can be found on the [le_lambda Github page](https://github.com/logentries/le_lambda).

## Installation

Before deploying as a ZIP file, the additional top level requirements must be included:

```
pip install -r top-level-requirements.txt -t .
```

## Development


For development purposes, create a virtual environment with the development dependencies:

```
pip install -r dev-requirements.txt
py.test -sv tests/
```

###### Example use cases:
* Forwarding AWS ELB and CloudFront logs
  * (make sure to set ELB/CloudFront to write logs every 5 minutes)
  * When forwarding these logs, the script will format the log lines according to Logentries KVP or JSON spec to make them easier to analyze
* Forwarding OpenDNS logs

## Obtain log token
1. Log in to your Logentries account

2. Add a new [token based log](https://logentries.com/doc/input-token/)

## Deploy the script to AWS Lambda using AWS Console
1. Create a new Lambda function

2. Choose the Python blueprint for S3 objects

   ![Choose Blueprint](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step2.png)

3. Configure triggers:
   * Choose the bucket log files are being stored in
   * Set event type "Object Created (All)"
   * Tick "Enable Trigger" checkbox

4. Configure function:
   * Give your function a name
   * Set runtime to Python 2.7

5. Upload function code:
   * Create a .ZIP file, containing ```le_lambda.py``` and the folder ```certifi```
     * Make sure the files and ```certifi``` folder are in the **root** of the ZIP archive
   * Choose "Upload a .ZIP file" in "Code entry type" dropdown and upload the archive created in previous step

6. Set Environment Variables:
   * Token value should match UUID provided by Logentries UI or API
   * Region should be that of your LE account - currently only ```eu```

   | Key       | Value      |
   |-----------|------------|
   | region    | eu         |
   | token     | token uuid |

7. Additional Environment Variables (log record transformations)
  * You can perform transformation operations for each log record, such as:
    - Enrich the log record with the URL components or S3 path components (usually the `prefix`).
    - Serialize to KVP format, instead of JSON which is the default.
  * Transformations are applied sequentially and the entire pipeline can be defined via environment variable.


  | Key | Value|
  |------|------|
  | `TRANSFORMER_CLASS_LIST` | Comma-separated list of transformer classes. |
  | `TRANSFORMER_S3_KEY_FIELD_EXTRACTOR_MAPPING` | JSON-encoded field value mapping for the S3 path components enrichment: `[{"field": "my_field_1", "value": "key[0]"]`|

  Example:
  - By defining `TRANSFORMER_CLASS_LIST=URLParserTransformer,KeyValuePairFormatTransformer`, the `url` field of Application Load Balancer log will be expanded to its components:
    `host`, `port`, `path`, `query_string` and finally removed. The record will then be serialized as string in KVP format.

  ### `URLParserTransformer`

  Enrich the log record by expanding the `url` field to its components `host`, `port`, `path`, `query_string`.

  ### `KeyValuePairFormatTransformer`

  Serialize the log as string using the KVP format.

  ### `JSONTransformer`

  Encode the log record in JSON format. This is the default serialization.

  ### `S3KeyFieldExtractorTransformer`

  Extract path components from the S3 key path that triggered the event.
  The field-value mapping is specified using an array of objects:

  ```
  [{
    "field": "<NAME_OF_ADDED_FIELD>",
    "value": "key<SUBPATH_INDEX>"
  }]
  ```

  For example, defining `{"field": "my_field", "value": "key[1]"'}` and the S3 key is: `/prefix1/prefix2/AWSLogs/`
  will result in adding the field: `my_field="prefix2"` in the log record.



8. Lambda function handler and role
   * Change the "Handler" value to ```le_lambda.lambda_handler```
   * Choose "Create a new role from template" from dropdown and give it a name below.
   * Leave "Policy templates" to pre-populated value

9. Advanced settings:
   * Set memory limit to a high enough value to facilitate log parsing and sending - adjust to your needs
   * Set timeout to a high enough value to facilitate log parsing and sending - adjust to your needs
   * Leave VPC value to "No VPC" as the script only needs S3 access
     * If you choose to use VPC, please consult [Amazon Documentation](http://docs.aws.amazon.com/lambda/latest/dg/vpc.html)

10. Enable function:
   * Click "Create function"

## Gotchas:
   * The "Test" button execution in AWS Lambda will **ALWAYS** fail as the trigger is not provided by the built in test function. In order to verify, upload a sample file to source bucket
