import json
import os
import pytest
from moto import mock_aws
import boto3

@pytest.fixture
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='customer-alerts',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        os.environ['ALERTS_TABLE'] = 'customer-alerts'
        
        from handler import create_alert, list_alerts, update_alert
        yield table, create_alert, list_alerts, update_alert

def test_create_alert_success(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {
        'body': json.dumps({
            'userId': 'user123',
            'type': 'INFO',
            'message': 'Test alert'
        })
    }
    
    response = create_alert(event, None)
    
    assert response['statusCode'] == 201
    body = json.loads(response['body'])
    assert body['userId'] == 'user123'
    assert body['type'] == 'INFO'
    assert body['message'] == 'Test alert'
    assert 'id' in body
    assert body['read'] is False

def test_create_alert_missing_fields(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {'body': json.dumps({'userId': 'user123'})}
    
    response = create_alert(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_create_alert_invalid_type(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {
        'body': json.dumps({
            'userId': 'user123',
            'type': 'INVALID',
            'message': 'Test'
        })
    }
    
    response = create_alert(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'type must be' in body['error']

def test_list_alerts_success(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    # Create alerts
    for i in range(3):
        create_alert({
            'body': json.dumps({
                'userId': 'user123',
                'type': 'INFO',
                'message': f'Alert {i}'
            })
        }, None)
    
    event = {'queryStringParameters': {'userId': 'user123'}}
    
    response = list_alerts(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) == 3

def test_list_alerts_missing_userid(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {'queryStringParameters': None}
    
    response = list_alerts(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_update_alert_success(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    # Create alert
    create_response = create_alert({
        'body': json.dumps({
            'userId': 'user123',
            'type': 'WARNING',
            'message': 'Test alert'
        })
    }, None)
    alert_id = json.loads(create_response['body'])['id']
    
    # Update alert
    event = {
        'pathParameters': {'id': alert_id},
        'body': json.dumps({'read': True})
    }
    
    response = update_alert(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['read'] is True

def test_update_alert_not_found(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {
        'pathParameters': {'id': 'nonexistent'},
        'body': json.dumps({'read': True})
    }
    
    response = update_alert(event, None)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert 'not found' in body['error'].lower()

def test_update_alert_missing_read_field(dynamodb_table):
    table, create_alert, list_alerts, update_alert = dynamodb_table
    
    event = {
        'pathParameters': {'id': 'some-id'},
        'body': json.dumps({})
    }
    
    response = update_alert(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'read field is required' in body['error']
