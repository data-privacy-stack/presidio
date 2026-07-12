# Presidio Revamp (aka V2)

As of March 2021, Presidio underwent a revamp to a new version referred to as **V2**.

The main changes introduced in **V2** are:

1. gRPC replaced with HTTP to allow more customizable APIs and easier debugging
2. Focus on the Analyzer and Anonymizer services.

    1. Presidio Anonymizer is now Python-based and pip-installable.
    2. Presidio Analyzer does not use templates and external recognizer store.
    3. Image Redactor (formerly presidio-image-anonymizer) is in early beta and is Python based and pip installable.
    4. Other services are deprecated and may be migrated over time to **V2** with the help of the community.

3. Improved documentation, sample code, and build workflows.

4. Format-Preserving Encryption replaced with Advanced Encryption Standard (AES) 

## V1 Availability

Version V1 (legacy) is still available for download. To continue using the previous version:
-	For docker containers, use tag=v1 
-	For python packages, download version < 2 (e.g. pip install presidio-analyzer==0.95)

!!! note "Note"
	The legacy V1 code base will continue to be available under branch [V1](https://github.com/data-privacy-stack/presidio/tree/V1) but will no longer be officially supported.


## API Changes

The move from gRPC to HTTP-based APIs included changes to the API requests.

1. Changed payload format – moving from structured objects to JSON.

2. Removed templates from the API, including flattening the JSON structure.
   
3. Using snake_case instead of camelCase .

Below is a detailed outline of all changes made to the Analyzer and Anonymizer.

### Analyzer API Changes

#### Legacy json request (gRPC)

```json
{
    "text": "My phone number is 212-555-5555",
    "AnalyzeTemplateId": "1234",
    "AnalyzeTemplate": {
        "Fields": [
            {
                "Name": "PHONE_NUMBER",
                "MinScore": "0.5"
            }
        ],
        "AllFields": true,
        "Description": "template description",
        "CreateTime": "template creation time",
        "ModifiedTime": "template modification time",
        "Language": "fr",
        "ResultsScoreThreshold": 0.5
    }
}
```

#### V2 json request (HTTP)

```json
{
    "text": "My phone number is 212-555-5555",
    "entities": ["PHONE_NUMBER"],
    "language": "en",
    "correlation_id": "213",
    "score_threshold": 0.5,
    "trace": true,
    "return_decision_process": true
}
```

### Anonymizer API Changes

#### Legacy json request (gRPC)

```json
{
  "text": "hello world, my name is Jane Doe. My number is: 034453334",
  "template": {
    "description": "DEPRECATED",
    "create_time": "DEPRECATED",
    "modified_time": "DEPRECATED",
    "default_transformation": {
      "replace_value": {...},
      "redact_value": {...},
      "hash_value": {...},
      "mask_value": {...},
      "fpe_value": {...}
    },
    "field_type_transformations": [
      {
        "fields": [
          {
            "name": "FIRST_NAME",
            "min_score": "0.2"
          }
        ],
        "transformation": {
          "replace_value": {...},
          "redact_value": {...},
          "hash_value": {...},
          "mask_value": {...},
          "fpe_value": {...}
        }
      }
    ],
    "analyze_results": [
      {
        "text": "Jane",
        "field": {
          "name": "FIRST_NAME",
          "min_score": "0.5"
        },
        "location": {
          "start": 24,
          "end": 32,
          "length": 6
        },
        "score": 0.8
      }
    ]
  }
}
```

#### V2 json request (HTTP)

```json
{
    "text": "hello world, my name is Jane Doe. My number is: 034453334",
    "anonymizers": {
        "DEFAULT": {
            "type": "replace",
            "new_value": "val"
        },
        "PHONE_NUMBER": {
            "type": "mask",
            "masking_char": "*",
            "chars_to_mask": 4,
            "from_end": true
        }
    },
    "analyzer_results": [
        {
            "start": 24,
            "end": 32,
            "score": 0.8,
            "entity_type": "NAME"
        },
        {
            "start": 24,
            "end": 28,
            "score": 0.8,
            "entity_type": "FIRST_NAME"
        },
        {
            "start": 29,
            "end": 32,
            "score": 0.6,
            "entity_type": "LAST_NAME"
        },
        {
            "start": 48,
            "end": 57,
            "score": 0.95,
            "entity_type": "PHONE_NUMBER"
        }
    ]
}
```

**Specific for each anonymization type:**

| Anonymization name | Legacy format (V1)                                                                      | New json format (V2)                                                                       |
| ------------------ | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Replace            | <pre>string newValue = 1;</pre>                                                         | <pre>{ "new_value": "VALUE" }</pre>                                                        |
| Redact             | NONE                                                                                    | NONE                                                                                       |
| Mask               | <pre>string maskingCharacter = 1;<br>int32 charsToMask = 2; <br>bool fromEnd = 3;</pre> | <pre>{<br> "chars_to_mask": 10,<br> "from_end": true,<br> "masking_char": "\*" <br>}</pre> |
| Hash               | NONE                                                                                    | <pre>{"hash_type": "VALUE"}</pre>                                                          |
| FPE (now Encrypt)  | <pre>string key = 3t6w9z$C&F)J@NcR;<br>int32 tweak = D8E7920AFA330A73</pre>             | <pre>{"key": "3t6w9z$C&F)J@NcR"}</pre>                                                          |

!!! note "Note"
	The V2 API is continuously evolving. please [follow the change log](https://github.com/data-privacy-stack/presidio/blob/main/CHANGELOG.md) for updates.
