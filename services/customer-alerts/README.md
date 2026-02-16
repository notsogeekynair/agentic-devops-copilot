# Customer Alerts Service

Implementation of the Customer Alerts API based on the OpenAPI specification in `docs/specs/TKT-DEMO-openapi.yaml`.

## Features

### Endpoints Implemented

1. **POST /api/alerts** - Create a new alert
   - Returns 201 with alertId
   - Validates required fields: userId, type, message
   - Validates type enum: INFO, WARNING, CRITICAL

2. **GET /api/alerts?userId=...** - List alerts by user
   - Returns 200 with array of alerts
   - Requires userId query parameter

3. **PATCH /api/alerts/{id}** - Mark alert as read
   - Returns 200 with updated alert
   - Updates the read status

### DynamoDB Schema

Single-table design:
- **PK**: `USER#{userId}` (Partition Key)
- **SK**: `ALERT#{alertId}` (Sort Key)
- **Attributes**: id, userId, type, message, createdAt, read

This design enables efficient queries by userId using the primary key.

### Error Handling

- Input validation for all endpoints
- Proper HTTP status codes (400, 404, 500)
- Descriptive error messages

## Files Modified/Created

1. **handler.py** - Lambda function handlers
2. **serverless.yml** - DynamoDB table provisioning and function configuration
3. **requirements.txt** - Dependencies (boto3, pytest, moto)
4. **tests/test_handler.py** - Comprehensive unit tests

## Testing

Run tests with:
```bash
cd services/customer-alerts
pytest tests/test_handler.py -v
```

All 8 tests pass:
- ✓ Create alert success
- ✓ Create alert with missing fields
- ✓ Create alert with invalid type
- ✓ List alerts success
- ✓ List alerts with missing userId
- ✓ Update alert success
- ✓ Update alert not found
- ✓ Update alert with missing read field

## Deployment

Deploy with Serverless Framework:
```bash
cd services/customer-alerts
serverless deploy
```

This will:
- Create the DynamoDB table
- Deploy Lambda functions
- Set up API Gateway endpoints
- Configure IAM permissions
