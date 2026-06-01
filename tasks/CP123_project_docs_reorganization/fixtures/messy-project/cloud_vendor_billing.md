# Cloud Vendor Billing Specification

## Overview

Each cloud vendor provides billing data in different formats. This document
describes the extraction and normalization process.

## AWS

- Source: Cost Explorer API or S3 CSV export
- Frequency: Daily (detailed) or Monthly (summary)
- Authentication: IAM role with billing read access

## GCP

- Source: BigQuery billing export
- Frequency: Near real-time
- Authentication: Service account with BigQuery read

## Azure

- Source: Cost Management REST API
- Frequency: Daily
- Authentication: Service principal with Cost Reader role

## Normalization

All vendor data is normalized into the unified `billing_record` schema before storage.
