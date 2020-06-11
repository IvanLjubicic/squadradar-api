
import os
import boto3
import constants
import time
import onesignal as onesignal_sdk

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


def onTtlPushNot():
    response = client.scan(TableName=PLAYERS_TABLE)
    currentTimestamp = int(round(time.time() * 1000))
    timestampForOneHour = currentTimestamp + 60 * 60 * 1000

    for i in response['Items']:
        if (i['ttl'].get('N') > timestampForOneHour):
            new_notification = onesignal_sdk.Notification(post_body={
                "contents": {"en": constants.TTL_NOTIFICATION_MESSAGE},
                "include_player_ids": i['playerId'].get('S'),
            })
            # send notification, it will return a response
            onesignal_response = onesignal_client.send_notification(
                new_notification)
