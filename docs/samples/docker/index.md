# Using Presidio in Docker

## Description

Presidio can expose REST endpoints for each service using Flask and Docker. Follow the [installation guide](https://github.com/data-privacy-stack/presidio/blob/V2/docs/installation.md#using-docker) to learn how to install and run presidio-analyzer and presidio-anonymizer using docker.

## Postman collection

This repository contains a postman collection with sample REST API request for each service. Follow [this tutorial](https://learning.postman.com/docs/getting-started/importing-and-exporting-data/#importing-data-into-postman) to learn how to export the sample requests into postman

1. <a href="PresidioAnalyzer.postman_collection.json" download>Download Presidio Analyzer postman requests</a>
2. <a href="PresidioAnonymizer.postman_collection.json" download>Download Presidio Anonymizer postman requests</a>

## Sample API Calls

### Simple Text Analysis

```curl
curl -X POST http://localhost:5002/analyze -H "Content-type: application/json" --data "{ \"text\": \"John Smith drivers license is AC432223\", \"language\" : \"en\"}"
```

### Simple Text Anonymization

```curl
curl -X POST http://localhost:5001/anonymize -H "Content-type: application/json" --data "{\"text\": \"hello world, my name is Jane Doe. My number is: 034453334\", \"analyzer_results\": [{\"start\": 24, \"end\": 32, \"score\": 0.8, \"entity_type\": \"NAME\"}, { \"start\": 48, \"end\": 57,  \"score\": 0.95,\"entity_type\": \"PHONE_NUMBER\" }],  \"anonymizers\": {\"DEFAULT\": { \"type\": \"replace\", \"new_value\": \"ANONYMIZED\" },\"PHONE_NUMBER\": { \"type\": \"mask\", \"masking_char\": \"*\", \"chars_to_mask\": 4, \"from_end\": true }}}"
```
