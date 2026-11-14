# Live Sewage Discharge

This project is to replace the old live sewage discharge updates for the app.

Since Southern Water changed from the old REST API to the now web based service, I need to obtain data and make it available every hour or 2.

This project uses Python Playwright to automate extracting the discharge data for the last 72 hours for displaying to folks living in the Folkestone to New Romney bay area.

Writes json to:
- https://stevshil.github.io/sewage-monitor/sewage.json

## AWS Lambda

The SAM template runs the scraper hourly in a Lambda container and uploads
`sewage.json` to an existing S3 bucket. The bucket name and object key are
configurable; the default key is `sewage.json`.
The GitHub Actions workflow remains available for manually publishing to
GitHub Pages; its hourly schedule is handled by Lambda instead.

Deploy with the AWS SAM CLI and Docker installed:

```sh
sam build
sam deploy --guided
```

When prompted, set `S3BucketName` to the destination bucket and optionally set
`S3ObjectKey` to a key such as `reports/sewage.json`. The Lambda execution role
is limited to writing that object. Keep the function out of a private VPC without
internet egress so it can reach the Southern Water site.

To invoke the handler outside the scheduled deployment, configure `S3_BUCKET`
and optionally `S3_KEY` (`sewage.json` by default). Collection or upload errors
are raised so failed runs do not overwrite the S3 object with an empty report.
