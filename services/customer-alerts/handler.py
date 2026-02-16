import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Key

def get_table():
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table(os.environ.get('ALERTS_TABLE', 'customer-alerts'))

def health(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})
    }

def create_alert(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validation
        if not body.get('userId') or not body.get('type') or not body.get('message'):
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "userId, type, and message are required"})
            }
        
        if body['type'] not in ['INFO', 'WARNING', 'CRITICAL']:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "type must be INFO, WARNING, or CRITICAL"})
            }
        
        alert_id = str(uuid.uuid4())
        alert = {
            'PK': f"USER#{body['userId']}",
            'SK': f"ALERT#{alert_id}",
            'id': alert_id,
            'userId': body['userId'],
            'type': body['type'],
            'message': body['message'],
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'read': False
        }
        
        get_table().put_item(Item=alert)
        
        response_alert = {k: v for k, v in alert.items() if k not in ['PK', 'SK']}
        
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_alert)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }

def list_alerts(event, context):
    try:
        user_id = event.get('queryStringParameters', {}).get('userId') if event.get('queryStringParameters') else None
        
        if not user_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "userId query parameter is required"})
            }
        
        response = get_table().query(
            KeyConditionExpression=Key('PK').eq(f"USER#{user_id}") & Key('SK').begins_with('ALERT#')
        )
        
        alerts = [{k: v for k, v in item.items() if k not in ['PK', 'SK']} for item in response.get('Items', [])]
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(alerts)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }

def update_alert(event, context):
    try:
        alert_id = event.get('pathParameters', {}).get('id')
        body = json.loads(event.get('body', '{}'))
        
        if not alert_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "id path parameter is required"})
            }
        
        if 'read' not in body:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "read field is required"})
            }
        
        table = get_table()
        # Query to find the item (we need userId to construct PK)
        # Since we don't have userId in path, we need to scan or use GSI
        # For simplicity, we'll scan for the alert by SK
        response = table.scan(
            FilterExpression=Key('SK').eq(f"ALERT#{alert_id}")
        )
        
        if not response.get('Items'):
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Alert not found"})
            }
        
        item = response['Items'][0]
        
        # Update the item
        table.update_item(
            Key={'PK': item['PK'], 'SK': item['SK']},
            UpdateExpression='SET #read = :read',
            ExpressionAttributeNames={'#read': 'read'},
            ExpressionAttributeValues={':read': body['read']}
        )
        
        # Get updated item
        updated = table.get_item(Key={'PK': item['PK'], 'SK': item['SK']})['Item']
        response_alert = {k: v for k, v in updated.items() if k not in ['PK', 'SK']}
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_alert)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
