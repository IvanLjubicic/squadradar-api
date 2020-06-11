# app.py
import os
import boto3
from boto3 import dynamodb
from flask import Flask, jsonify, request
import json
import uuid
from datetime import datetime
import time
from haversine import haversine, Unit
import onesignal as onesignal_sdk
from flask_cors import CORS
from logging.config import fileConfig
from dynamodb_json import json_util as json
import constants
from errors import InternalServerError
from response import ResponseGeneric

app = Flask(__name__)
fileConfig('logging.cfg')
CORS(app)
app.response_class = ResponseGeneric

INCIDENTS_TABLE = os.environ['INCIDENTS_TABLE']
PLAYERS_TABLE = os.environ['PLAYERS_TABLE']
IS_OFFLINE = os.environ.get('IS_OFFLINE')
if IS_OFFLINE:
    client = boto3.client(
        'dynamodb',
        region_name='localhost',
        endpoint_url=constants.LOCALHOST_DYNAMODB_ENDPOINT_URL
    )
else:
    client = boto3.client('dynamodb')

onesignal_client = onesignal_sdk.Client(user_auth_key=constants.ONE_SIGNAL_USER_AUTH_KEY,
                                        app_auth_key=constants.ONE_SIGNAL_USER_AUTH_KEY,
                                        app_id=constants.ONE_SIGNAL_APP_ID)


@app.route("/")
def hello():
    app.logger.info('Processing default request')
    return "Hello World!"


@app.route('/api/incidents', methods=['GET'])
def getIncidents():
    try:
        response = client.scan(TableName=INCIDENTS_TABLE)
        return response
    except Exception as e:
        raise InternalServerError


@app.route('/api/incidents/getByLocation', methods=['GET'])
def getIncidentsByLocation():
    try:
        userLocation = (float(request.args.get('latitude')),
                        float(request.args.get('longitude')))
        response = client.scan(TableName=INCIDENTS_TABLE)

        for i in response['Items']:
            fetchedLocation = (float(i['latitude'].get(
                'S')), float(i['longitude'].get('S')))
            distance = haversine(userLocation, fetchedLocation, Unit.METERS)

            if (distance <= 200):
                return {'incidentHappened': 1}

        return {'incidentHappened': 0}
    except Exception as e:
        raise InternalServerError


@app.route("/api/incident", methods=["POST"])
def createIncident():
    try:
        response = client.scan(TableName=PLAYERS_TABLE)
        userLocation = (request.json.get('latitude'),
                        request.json.get('longitude'))

        for i in response['Items']:
            fetchedLocation = (float(i['latitude'].get(
                'N')), float(i['longitude'].get('N')))
            distance = haversine(userLocation, fetchedLocation, Unit.METERS)

            if distance <= 200:
                new_notification = onesignal_sdk.Notification(post_body={
                    "contents": {"en": constants.INCIDENT_NOTIFICATION_MESSAGE},
                    "include_player_ids": i['playerId'].get('S'),
                })
                # send notification, it will return a response
                onesignal_response = onesignal_client.send_notification(
                    new_notification)

        latitude = request.json.get('latitude')
        longitude = request.json.get('longitude')
        peopleNumberEstimate = request.json.get('peopleNumberEstimate')
        comment = request.json.get('comment')
        itemUuid = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%d.%m.%Y. %H:%M:%S")
        ttlTimestamp = int(round(time.time() * 1000))
        strTtlTimestamp = str(ttlTimestamp)
        print(strTtlTimestamp)

        resp = client.put_item(
            TableName=INCIDENTS_TABLE,
            Item={
                'latitude': {'N': str(latitude)},
                'longitude': {'N': str(longitude)},
                'peopleNumberEstimate': {'N': str(peopleNumberEstimate)},
                'comment': {'S': comment},
                'id': {'S': itemUuid},
                'tstamp': {'S': timestamp},
                'ttl': {'N': strTtlTimestamp}
            }
        )

        return {'uuid': itemUuid}

    except Exception as e:
        raise InternalServerError


@app.route("/api/player", methods=["POST"])
def createPlayer():
    try:
        playerId = request.json.get('playerId')
        latitude = request.json.get('latitude')
        longitude = request.json.get('longitude')
        # current time + add hours * minutes * seconds * milis
        ttlTimestamp = int(round(time.time() * 1000)) + (24 * 60 * 60 * 1000)
        strTtlTimestamp = str(ttlTimestamp)

        resp = client.get_item(
            TableName=PLAYERS_TABLE,
            Key={
                'playerId': {"S": playerId}
            }
        )
        item = resp.get('Item')
        if not item:
            resp = client.put_item(
                TableName=PLAYERS_TABLE,
                Item={
                    'latitude': {'N': str(latitude)},
                    'longitude': {'N': str(longitude)},
                    'playerId': {'S': playerId},
                    'ttl': {'N': strTtlTimestamp}
                }
            )
        else:
            client.update_item(
                TableName=PLAYERS_TABLE,
                Key={'playerId': {'S': playerId}},
                UpdateExpression="SET latitude = :latitude, longitude = :longitude",
                ExpressionAttributeValues={':latitude': {'N': str(latitude)}, ':longitude': {
                    'N': str(longitude)}}
            )
            client.update_time_to_live(
                TableName=PLAYERS_TABLE,
                TimeToLiveSpecification={
                    "Enabled": True, "AttributeName": "ttl"},
            )

        return {'STATUS': 'OK'}
    except Exception as e:
        raise InternalServerError


@app.route('/api/incidents/getRecent', methods=['GET'])
def getRecentIncidents():
    try:
        response = client.scan(TableName=INCIDENTS_TABLE, Limit=30)

        jsonified = json.loads(response.get('Items'))

        return jsonified
    except Exception as e:
        raise InternalServerError


@app.route('/api/incidents/getNear', methods=['GET'])
def getNearIncidentsByLocation():
    try:
        userLocation = (float(request.args.get('latitude')),
                        float(request.args.get('longitude')))
        response = client.scan(TableName=INCIDENTS_TABLE)
        prefDistance = int(request.args.get('prefDistance'))

        itemsToReturn = []
        maxNumOfItems = 30
        itemCounter = 0

        for i in response['Items']:
            fetchedLocation = (float(i['latitude'].get(
                'S')), float(i['longitude'].get('S')))
            distance = haversine(userLocation, fetchedLocation, Unit.METERS)

            if (distance <= prefDistance):
                itemsToReturn.append(i)
                itemCounter = itemCounter + 1
                if itemCounter >= maxNumOfItems:
                    break
            else:
                itemsToReturn.append(i)
                itemCounter = itemCounter + 1
                if itemCounter >= maxNumOfItems:
                    break

        return itemsToReturn
    except Exception as e:
        raise InternalServerError


@app.route('/api', methods=['DELETE'])
def truncateAll():
    try:
        scanIncidents = client.scan(TableName=INCIDENTS_TABLE)

        for each in scanIncidents['Items']:
            client.delete_item(TableName=INCIDENTS_TABLE, Key=each)

        scanPlayers = client.scan(TableName=PLAYERS_TABLE)

        for each in scanPlayers['Items']:
            client.delete_item(TableName=PLAYERS_TABLE, Key=each)

        return {'STATUS': 'OK'}
    except Exception as e:
        raise InternalServerError
