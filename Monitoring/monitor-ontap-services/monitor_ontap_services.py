#!/bin/python3.11
################################################################################
# THIS SOFTWARE IS PROVIDED BY NETAPP "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL NETAPP BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR'
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################
#
################################################################################
# This program is used to monitor some of Data ONTAP services (EMS Message,
# Snapmirror relationships, quotas) running under AMS, and alert on any
# "matching conditions."  It is intended to be run as a Lambda function, but
# can be run as a standalone program.
#
# Version: %%VERSION%%
# Date: %%DATE%%
################################################################################

import json
import re
import os
import datetime
import logging
from logging.handlers import SysLogHandler
import urllib3
from urllib3.util import Retry
import botocore
import boto3

eventResilience = 4 # Times an event has to be missing before it is removed
                    # from the alert history.
                    # This was added since the Ontap API that returns EMS
                    # events would often drop some events and then including 
                    # them in the subsequent calls. If I don't "age" the
                    # alert history duplicate alerts will be sent.
initialVersion = "Initial Run"  # The version to store if this is the first
                                # time the program has been run against a
                                # FSxN.

################################################################################
# This function is used to extract the one-, two-, or three-digit number from
# the string passed in, starting at the 'start' character. Then, multiple it
# by the unit after the number:
# D = Day = 60*60*24
# H = Hour = 60*60
# M = Minutes = 60
#
# It returns a tuple that has the extracted number and the end position.
################################################################################
def getNumber(string, start):

    if len(string) <= start:
        return (0, start)
    #
    # Check to see if it is a 1, 2 or 3 digit number.
    startp1=start+1   # Single digit
    startp2=start+2   # Double digit
    startp3=start+3   # Triple digit
    if re.search('[0-9]', string[startp1:startp2]) and re.search('[0-9]', string[startp2:startp3]):
        end=startp3
    elif re.search('[0-9]', string[startp1:startp2]):
        end=startp2
    else:
        end=startp1

    num=int(string[start:end])

    endp1=end+1
    if string[end:endp1] == "D":
        num=num*60*60*24
    elif string[end:endp1] == "H":
        num=num*60*60
    elif string[end:endp1] == "M":
        num=num*60
    elif string[end:endp1] != "S":
        print(f'Unknown lag time specifier "{string[end:endp1]}".')

    return (num, endp1)

################################################################################
# This function is used to parse the lag time string returned by the
# ONTAP API and return the equivalent seconds it represents.
# The input string is assumed to follow this pattern "P#DT#H#M#S" where
# each of those "#" can be one to three digits long. Also, if the lag isn't
# more than 24 hours, then the "#D" isn't there and the string simply starts
# with "PT". Similarly, if the lag time isn't more than an hour then the "#H"
# string is missing.
################################################################################
def parseLagTime(string):
    #
    num=0
    #
    # First check to see if the Day field is there, by checking to see if the
    # second character is a digit. If not, it is assumed to be 'T'.
    includesDay=False
    if re.search('[0-9]', string[1:2]):
        includesDay=True
        start=1
    else:
        start=2
    data=getNumber(string, start)
    num += data[0]

    start=data[1]
    #
    # If there is a 'D', then there is a 'T' between the D and the # of hours
    # so skip pass it.
    if includesDay:
        start += 1
    data=getNumber(string, start)
    num += data[0]

    start=data[1]
    data=getNumber(string, start)
    num += data[0]

    start=data[1]
    data=getNumber(string, start)
    num += data[0]

    return(num)

################################################################################
# This function checks to see if an event is in the events array based on
# the unique Identifier passed in. It will also update the "refresh" field on
# any matches.
################################################################################
def eventExist (events, uniqueIdentifier):
    for event in events:
        if event["index"] == uniqueIdentifier:
            event["refresh"] = eventResilience
            return True

    return False

################################################################################
# This function makes an API call to the FSxN to ensure it is up. If the
# errors out, then it sends an alert, and returns 'False'. Otherwise it returns
# 'True'.
################################################################################
def checkSystem():
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger

    changedEvents = False
    #
    # Get the previous status.
    try:
        data = s3Client.get_object(Key=config["systemStatusFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then this must be the
        # first time this script has run against thie filesystem so create an
        # initial status structure.
        if err.response['Error']['Code'] == "NoSuchKey":
            fsxStatus = {
                "systemHealth": True,
                "version" : initialVersion,
                "numberNodes" : 2,
                "downInterfaces" : []
            }
            changedEvents = True
        else:
            raise err
    else:
        fsxStatus = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Get the cluster name and ONTAP version from the FSxN.
    # This is also a way to test that the FSxN cluster is accessible.
    badHTTPStatus = False
    try:
        endpoint = f'https://{config["OntapAdminServer"]}/api/cluster?fields=version,name'
        response = http.request('GET', endpoint, headers=headers, timeout=5.0)
        if response.status == 200:
            if not fsxStatus["systemHealth"]:
                fsxStatus["systemHealth"] = True
                changedEvents = True

            data = json.loads(response.data)
            if config["awsAccountId"] != None:
                clusterName = f'{data["name"]}({config["awsAccountId"]})'
            else:
                clusterName = data['name']
            #
            # The following assumes that the format of the "full" version
            # looks like: "NetApp Release 9.13.1P6: Tue Dec 05 16:06:25 UTC 2023".
            # The reason for looking at the "full" instead of the individual
            # keys (generation, major, minor) is because they don't provide
            # the patch level. :-(
            clusterVersion = data["version"]["full"].split()[2].replace(":", "")
            if fsxStatus["version"] == initialVersion:
                fsxStatus["version"] = clusterVersion
        else:
            print(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
            badHTTPStatus = True
            raise Exception(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
    except:
        if fsxStatus["systemHealth"]:
            if config["awsAccountId"] != None:
                clusterName = f'{config["OntapAdminServer"]}({config["awsAccountId"]})'
            else:
                clusterName = config["OntapAdminServer"]
            if badHTTPStatus:
                message = f'CRITICAL: Received a non 200 HTTP status code ({response.status}) when trying to access {clusterName}.'
            else:
                message = f'CRITICAL: Failed to issue API against {clusterName}. Cluster could be down.'
            logger.critical(message)
            snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
            fsxStatus["systemHealth"] = False
            changedEvents = True

    if changedEvents:
        s3Client.put_object(Key=config["systemStatusFilename"], Bucket=config["s3BucketName"], Body=json.dumps(fsxStatus).encode('UTF-8'))
    # 
    # If the cluster is done, return false so the program can exit cleanly.
    return(fsxStatus["systemHealth"])

################################################################################
# This function checks the following things:
#   o If the ONTAP version has changed.
#   o If one of the nodes are down.
#   o If a network interface is down.
#
# ASSUMPTIONS: That checkSystem() has been called before it.
################################################################################
def checkSystemHealth(service):
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger

    changedEvents = False
    #
    # Get the previous status.
    # Shouldn't have to check for status of the get_object() call, to see if the object exist or not,
    # since "checkSystem()" should already have been called and it creates the object if it doesn't
    # already exist. So, if there is a failure, it should be something else than "non-existent".
    data = s3Client.get_object(Key=config["systemStatusFilename"], Bucket=config["s3BucketName"])
    fsxStatus = json.loads(data["Body"].read().decode('UTF-8'))

    for rule in service["rules"]:
        for key in rule.keys():
            lkey = key.lower()
            if lkey == "versionchange":
                if rule[key] and clusterVersion != fsxStatus["version"]:
                    message = f'NOTICE: The ONTAP vesion changed on cluster {clusterName} from {fsxStatus["version"]} to {clusterVersion}.'
                    logger.info(message)
                    snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                    fsxStatus["version"] = clusterVersion
                    changedEvents = True
            elif lkey == "failover":
                #
                # Check that both nodes are available.
                # Using the CLI passthrough API because I couldn't find the equivalent API call.
                if rule[key]:
                    endpoint = f'https://{config["OntapAdminServer"]}/api/private/cli/system/node/virtual-machine/instance/show-settings'
                    response = http.request('GET', endpoint, headers=headers)
                    if response.status == 200:
                        data = json.loads(response.data)
                        if data["num_records"] != fsxStatus["numberNodes"]:
                            message = f'Alert: The number of nodes on cluster {clusterName} went from {fsxStatus["numberNodes"]} to {data["num_records"]}.'
                            logger.info(message)
                            snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                            fsxStatus["numberNodes"] = data["num_records"]
                            changedEvents = True
                    else:
                        print(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
            elif lkey == "networkinterfaces":
                if rule[key]:
                    endpoint = f'https://{config["OntapAdminServer"]}/api/network/ip/interfaces?fields=state'
                    response = http.request('GET', endpoint, headers=headers)
                    if response.status == 200:
                        #
                        # Decrement the refresh field to know if any events have really gone away.
                        for interface in fsxStatus["downInterfaces"]:
                            interface["refresh"] -= 1
               
                        data = json.loads(response.data)
                        for interface in data["records"]:
                            if interface.get("state") != None and interface["state"] != "up":
                                uniqueIdentifier = interface["name"]
                                if(not eventExist(fsxStatus["downInterfaces"], uniqueIdentifier)): # Resets the refresh key.
                                    message = f'Alert: Network interface {interface["name"]} on cluster {clusterName} is down.'
                                    logger.info(message)
                                    snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                    event = {
                                        "index": uniqueIdentifier,
                                        "refresh": eventResilience
                                    }
                                    fsxStatus["downInterfaces"].append(event)
                                    changedEvents = True
                        #
                        # After processing the records, see if any events need to be removed.
                        i = 0
                        while i < len(fsxStatus["downInterfaces"]):
                            if fsxStatus["downInterfaces"][i]["refresh"] <= 0:
                                print(f'Deleting downed interface: {fsxStatus["downInterfaces"][i]["index"]}')
                                del fsxStatus["downInterfaces"][i]
                                changedEvents = True
                            else:
                                if fsxStatus["downInterfaces"][i]["refresh"] != eventResilience:
                                    changedEvents = True
                                i += 1
                    else:
                        print(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
            else:
                print(f'Unknown System Health alert type: "{key}".')

    if changedEvents:
        s3Client.put_object(Key=config["systemStatusFilename"], Bucket=config["s3BucketName"], Body=json.dumps(fsxStatus).encode('UTF-8'))

################################################################################
# This function processes the EMS events.
################################################################################
def processEMSEvents(service):
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger

    changedEvents = False
    #
    # Get the saved events so we can ensure we are only reporting on new ones.
    try:
        data = s3Client.get_object(Key=config["emsEventsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then it will get created once an alert it sent.
        if err.response['Error']['Code'] == "NoSuchKey":
            events = []
        else:
            raise err
    else:
        events = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Decrement the refresh field to know if any records have really gone away.
    for event in events:
        event["refresh"] -= 1
    #
    # Run the API call to get the current list of EMS events.
    endpoint = f'https://{config["OntapAdminServer"]}/api/support/ems/events'
    response = http.request('GET', endpoint, headers=headers)
    if response.status == 200:
        data = json.loads(response.data)
        #
        # Process the events to see if there are any new ones.
        print(f'Received {len(data["records"])} EMS records.')
        logger.debug(f'Received {len(data["records"])} EMS records.')
        for record in data["records"]:
            for rule in service["rules"]:
                if (re.search(rule["name"], record["message"]["name"]) and
                    re.search(rule["severity"], record["message"]["severity"]) and
                    re.search(rule["message"], record["log_message"])):
                    if (not eventExist (events, record["index"])):  # This resets the "refresh" field if found.
                        message = f'{record["time"]} : {clusterName} {record["message"]["name"]}({record["message"]["severity"]}) - {record["log_message"]}'
                        useverity=record["message"]["severity"].upper()
                        if useverity == "EMERGENCY":
                            logger.critical(message)
                        elif useverity == "ALERT":
                            logger.error(message)
                        elif useverity == "ERROR": 
                            logger.warning(message)
                        elif useverity == "NOTICE" or useverity == "INFORMATIONAL":
                            logger.info(message)
                        elif useverity == "DEBUG":
                            logger.debug(message)
                        else:
                            print(f'Received unknown severity from ONTAP "{record["message"]["severity"]}". The message received is next.')
                            logger.info(f'Received unknown severity from ONTAP "{record["message"]["severity"]}". The message received is next.')
                            logger.info(message)
                        snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                        changedEvents = True
                        event = {
                                "index": record["index"],
                                "time": record["time"],
                                "messageName": record["message"]["name"],
                                "message": record["log_message"],
                                "refresh": eventResilience
                                }
                        print(message)
                        events.append(event)
        #
        # Now that we have processed all the events, check to see if any events should be deleted.
        i = 0
        while i < len(events):
            if events[i]["refresh"] <= 0:
                print(f'Deleting event: {events[i]["time"]} : {events[i]["message"]}')
                del events[i]
                changedEvents = True
            else:
                # If an event wasn't refreshed, then we need to save the new refresh count.
                if events[i]["refresh"] != eventResilience:
                    changedEvents = True
                i += 1
        #
        # If the events array changed, save it.
        if changedEvents:
            s3Client.put_object(Key=config["emsEventsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(events).encode('UTF-8'))
    else:
        print(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
        logger.debug(f'API call to {endpoint} failed. HTTP status code: {response.status}.')

################################################################################
# This function is used to find an existing SM relationship based on the source
# and destinatino path passed in. It returns None if one isn't found
################################################################################
def getPreviousSMRecord(relationShips, sourceCluster, sourcePath, destPath):
    for relationship in relationShips:
        if relationship['sourcePath'] == sourcePath and relationship['destPath'] == destPath and relationship['sourceCluster'] == sourceCluster:
            relationship['refresh'] = True
            return(relationship)

    return(None)

################################################################################
# This function is used to check SnapMirror relationships.
################################################################################
def processSnapMirrorRelationships(service):
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger
    #
    # Get the saved events so we can ensure we are only reporting on new ones.
    try:
        data = s3Client.get_object(Key=config["smEventsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then it will get created once an alert it sent.
        if err.response['Error']['Code'] == "NoSuchKey":
            events = []
        else:
            raise err
    else:
        events = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Decrement the refresh field to know if any records have really gone away.
    for event in events:
        event["refresh"] -= 1

    changedEvents=False
    #
    # Get the saved SM relationships.
    try:
        data = s3Client.get_object(Key=config["smRelationshipsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then it will get created once an alert it sent.
        if err.response['Error']['Code'] == "NoSuchKey":
            smRelationships = []
        else:
            raise err
    else:
        smRelationships = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Set the refresh to False to know if any of the relationships still exist.
    for relationship in smRelationships:
        relationship["refresh"] = False

    updateRelationships = False
    #
    # Get the current time in seconds since UNIX epoch 01/01/1970.
    curTime = int(datetime.datetime.now().timestamp())
    #
    # Run the API call to get the current state of all the snapmirror relationships.
    endpoint = f'https://{config["OntapAdminServer"]}/api/snapmirror/relationships?fields=*'
    response = http.request('GET', endpoint, headers=headers)
    if response.status == 200:
        data = json.loads(response.data)

        for record in data["records"]:
            for rule in service["rules"]:
                for key in rule.keys():
                    lkey = key.lower()
                    if lkey == "maxlagtime":
                        if record.get("lag_time") != None:
                            lagSeconds = parseLagTime(record["lag_time"])
                            if lagSeconds > rule["maxLagTime"]:
                                uniqueIdentifier = record["uuid"] + "_" + key
                                if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                    message = f'Snapmirror Lag Alert: {record["source"]["cluster"]["name"]}::{record["source"]["path"]} -> {clusterName}::{record["destination"]["path"]} has a lag time of {lagSeconds} seconds.'
                                    logger.warning(message)
                                    snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                    changedEvents=True
                                    event = {
                                        "index": uniqueIdentifier,
                                        "message": message,
                                        "refresh": eventResilience
                                    }
                                    print(message)
                                    events.append(event)
                    elif lkey == "healthy":
                        if not record["healthy"]:
                            uniqueIdentifier = record["uuid"] + "_" + key
                            if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                message = f'Snapmirror Health Alert: {record["source"]["cluster"]["name"]}::{record["source"]["path"]} {clusterName}::{record["destination"]["path"]} has a status of {record["healthy"]}'
                                logger.warning(message)  # Intentionally put this before adding the reasons, since I'm not sure how syslog will handle a multi-line message.
                                for reason in record["unhealthy_reason"]:
                                    message += "\n" + reason["message"]
                                snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                changedEvents=True
                                event = {
                                    "index": uniqueIdentifier,
                                    "message": message,
                                    "refresh": eventResilience
                                }
                                print(message)
                                events.append(event)
                    elif lkey == "stalledtransferseconds":
                        if record.get('transfer') and record['transfer']['state'].lower() == "transferring":
                            sourcePath = record['source']['path']
                            destPath = record['destination']['path']
                            sourceCluster = record['source']['cluster']['name']
                            bytesTransferred = record['transfer']['bytes_transferred']

                            prevRec =  getPreviousSMRecord(smRelationships, sourceCluster, sourcePath, destPath)

                            if prevRec != None:
                                timeDiff=curTime - prevRec["time"]
                                print(f'transfer bytes last time:{prevRec["bytesTransferred"]} this time:{bytesTransferred} and {timeDiff} > {rule[key]}')
                                if prevRec['bytesTransferred'] == bytesTransferred:
                                    if (curTime - prevRec['time']) > rule[key]:
                                        uniqueIdentifier = record['uuid'] + "_" + "transfer"
    
                                        if not eventExist(events, uniqueIdentifier):
                                            message = f'Snapmiorror transfer has stalled: {sourceCluster}::{sourcePath} -> {clusterName}::{destPath}.'
                                            logger.warning(message)
                                            snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject='Monitor ONTAP Services Alert for cluster {clusterName}')
                                            changedEvents=True
                                            event = {
                                                "index": uniqueIdentifier,
                                                "message": message,
                                                "refresh": eventResilience
                                            }
                                            print(message)
                                            events.append(event)
                                else:
                                    prevRec['time'] = curTime
                                    prevRec['refresh'] = True
                                    prevRec['bytesTransferred'] = bytesTransferred
                                    updateRelationships = True
                            else:
                                prevRec = {
                                    "time": curTime,
                                    "refresh": True,
                                    "bytesTransferred": bytesTransferred,
                                    "sourcePath": sourcePath,
                                    "destPath": destPath,
                                    "sourceCluster": sourceCluster
                                }
                                updateRelationships = True
                                smRelationships.append(prevRec)
                    else:
                        message = f'Unknown snapmirror alert type: "{key}".'
                        logger.warning(message)
                        print(message)
        #
        # After processing the records, see if any SM relationships need to be removed.
        i = 0
        while i < len(smRelationships):
            if not smRelationships[i]["refresh"]:
                del smRelationships[i]
                updateRelationships = True
            else:
                i += 1
        #
        # If any of the SM relationships changed, save it.
        if(updateRelationships):
            s3Client.put_object(Key=config["smRelationshipsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(smRelationships).encode('UTF-8'))
        #
        # After processing the records, see if any events need to be removed.
        i = 0
        while i < len(events):
            if events[i]["refresh"] <= 0:
                print(f'Deleting event: {events[i]["message"]}')
                del events[i]
                changedEvents = True
            else:
                # If an event wasn't refreshed, then we need to save the new refresh count.
                if events[i]["refresh"] != eventResilience:
                    changedEvents = True
                i += 1
        #
        # If the events array changed, save it.
        if(changedEvents):
            s3Client.put_object(Key=config["smEventsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(events).encode('UTF-8'))
    else:
        print(f'API call to {endpoint} failed. HTTP status code {response.status}.')

################################################################################
# This function is used to check all the volume and aggregate utlization.
################################################################################
def processStorageUtilization(service):
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger

    changedEvents=False
    #
    # Get the saved events so we can ensure we are only reporting on new ones.
    try:
        data = s3Client.get_object(Key=config["storageEventsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then it will get created once an alert it sent.
        if err.response['Error']['Code'] == "NoSuchKey":
            events = []
        else:
            raise err
    else:
        events = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Decrement the refresh field to know if any records have really gone away.
    for event in events:
        event["refresh"] -= 1

    for rule in service["rules"]:
        for key in rule.keys():
            lkey=key.lower()
            if lkey == "aggrwarnpercentused" or lkey == 'aggrcriticalpercentused':
                #
                # Run the API call to get the physical storage used.
                endpoint = f'https://{config["OntapAdminServer"]}/api/storage/aggregates?fields=space'
                response = http.request('GET', endpoint, headers=headers)
                if response.status == 200:
                    data = json.loads(response.data)
                    for aggr in data["records"]:
                        if aggr["space"]["block_storage"]["used_percent"] >= rule[key]:
                            uniqueIdentifier = aggr["uuid"] + "_" + key
                            if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                alertType = 'Warning' if lkey == "aggrwarnpercentused" else 'Critical'
                                message = f'Aggregate {alertType} Alert: Aggregate {aggr["name"]} on {clusterName} is {aggr["space"]["block_storage"]["used_precent"]}% full, which is more or equal to {rule[key]}% full.'
                                logger.warning(message)
                                snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                changedEvents = True
                                event = {
                                        "index": uniqueIdentifier,
                                        "message": message,
                                        "refresh": eventResilience
                                    }
                                print(event)
                                events.append(event)
                else:
                    print(f'API call to {endpoint} failed. HTTP status code {response.status}.')
            elif lkey == "volumewarnpercentused" or lkey == "volumecriticalpercentused":
                #
                # Run the API call to get the volume information.
                endpoint = f'https://{config["OntapAdminServer"]}/api/storage/volumes?fields=space,svm'
                response = http.request('GET', endpoint, headers=headers)
                if response.status == 200:
                    data = json.loads(response.data)
                    for record in data["records"]:
                        if record["space"].get("used_percent"):
                            if record["space"]["used_percent"] >= rule[key]:
                                uniqueIdentifier = record["uuid"] + "_" + key
                                if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                    alertType = 'Warning' if lkey == "volumewarnpercentused" else 'Critical'
                                    message = f'Volume Usage {alertType} Alert: volume {record["svm"]["name"]}:/{record["name"]} on {clusterName} is {record["space"]["used_percent"]}% full, which is more or equal to {rule[key]}% full.'
                                    logger.warning(message)
                                    snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                    changedEvents = True
                                    event = {
                                            "index": uniqueIdentifier,
                                            "message": message,
                                            "refresh": eventResilience
                                        }
                                    print(message)
                                    events.append(event)
                else:
                    print(f'API call to {endpoint} failed. HTTP status code {response.status}.')
            else:
                message = f'Unknown storage alert type: "{key}".'
                logger.warning(message)
                print(message)
    #
    # After processing the records, see if any events need to be removed.
    i = 0
    while i < len(events):
        if events[i]["refresh"] <= 0:
            print(f'Deleting event: {events[i]["message"]}')
            del events[i]
            changedEvents = True
        else:
            # If an event wasn't refreshed, then we need to save the new refresh count.
            if events[i]["refresh"] != eventResilience:
                changedEvents = True
            i += 1
    #
    # If the events array changed, save it.
    if(changedEvents):
        s3Client.put_object(Key=config["storageEventsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(events).encode('UTF-8'))

################################################################################
# This function is used to check utilization of quota limits.
################################################################################
def processQuotaUtilization(service):
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger

    changedEvents=False
    #
    # Get the saved events so we can ensure we are only reporting on new ones.
    try:
        data = s3Client.get_object(Key=config["quotaEventsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        # If the error is that the object doesn't exist, then it will get created once an alert it sent.
        if err.response['Error']['Code'] == "NoSuchKey":
            events = []
        else:
            raise err
    else:
        events = json.loads(data["Body"].read().decode('UTF-8'))
    #
    # Decrement the refresh field to know if any records have really gone away.
    for event in events:
        event["refresh"] -= 1
    #
    # Run the API call to get the quota report.
    endpoint = f'https://{config["OntapAdminServer"]}/api/storage/quota/reports?fields=*'
    response = http.request('GET', endpoint, headers=headers)
    if response.status == 200:
        data = json.loads(response.data)
        for record in data["records"]:
            for rule in service["rules"]:
                for key in rule.keys():
                    lkey = key.lower() # Convert to all lower case so the key can be case insensitive.
                    if lkey == "maxquotainodespercentused":
                        #
                        # Since the quota report might not have the files key, and even if it does, it might not have
                        # the hard_limit_percent" key, need to check for their existencae first.
                        if(record.get("files") != None and record["files"]["used"].get("hard_limit_percent") != None and
                                record["files"]["used"]["hard_limit_percent"] > rule[key]):
                            uniqueIdentifier = str(record["index"]) + "_" + key
                            if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                if record.get("qtree") != None:
                                    qtree=f' under qtree: {record["qtree"]["name"]} '
                                else:
                                    qtree=' '
                                if record.get("users") != None:
                                    users=None
                                    for user in record["users"]:
                                        if users == None:
                                            users = user["name"]
                                        else:
                                            users += ',{user["name"]}'
                                    user=f'associated with user(s) "{users}" '
                                else:
                                    user=''
                                message = f'Quota Inode Usage Alert: Quota of type "{record["type"]}" on {record["svm"]["name"]}:/{record["volume"]["name"]}{qtree}{user}on {clusterName} is using {record["files"]["used"]["hard_limit_percent"]}% which is more than {rule[key]}% of its inodes.'
                                logger.warning(message)
                                snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                changedEvents=True
                                event = {
                                        "index": uniqueIdentifier,
                                        "message": message,
                                        "refresh": eventResilience
                                        }
                                print(message)
                                events.append(event)
                    elif lkey == "maxhardquotaspacepercentused":
                        if(record.get("space") != None and record["space"]["used"].get("hard_limit_percent") and
                                record["space"]["used"]["hard_limit_percent"] >= rule[key]):
                            uniqueIdentifier = str(record["index"]) + "_" + key
                            if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                if record.get("qtree") != None:
                                    qtree=f' under qtree: {record["qtree"]["name"]} '
                                else:
                                    qtree=" "
                                if record.get("users") != None:
                                    users=None
                                    for user in record["users"]:
                                        if users == None:
                                            users = user["name"]
                                        else:
                                            users += ',{user["name"]}'
                                    user=f'associated with user(s) "{users}" '
                                else:
                                    user=''
                                message = f'Quota Space Usage Alert: Hard quota of type "{record["type"]}" on {record["svm"]["name"]}:/{record["volume"]["name"]}{qtree}{user}on {clusterName} is using {record["space"]["used"]["hard_limit_percent"]}% which is more than {rule[key]}% of its allocaed space.'
                                logger.warning(message)
                                snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                changedEvents=True
                                event = {
                                        "index": uniqueIdentifier,
                                        "message": message,
                                        "refresh": eventResilience
                                        }
                                print(message)
                                events.append(event)
                    elif lkey == "maxsoftquotaspacepercentused":
                        if(record.get("space") != None and record["space"]["used"].get("soft_limit_percent") and
                                record["space"]["used"]["soft_limit_percent"] >= rule[key]):
                            uniqueIdentifier = str(record["index"]) + "_" + key
                            if not eventExist(events, uniqueIdentifier):  # This resets the "refresh" field if found.
                                if record.get("qtree") != None:
                                    qtree=f' under qtree: {record["qtree"]["name"]} '
                                else:
                                    qtree=" "
                                if record.get("users") != None:
                                    users=None
                                    for user in record["users"]:
                                        if users == None:
                                            users = user["name"]
                                        else:
                                            users += ',{user["name"]}'
                                    user=f'associated with user(s) "{users}" '
                                else:
                                    user=''
                                message = f'Quota Space Usage Alert: Soft quota of type "{record["type"]}" on {record["svm"]["name"]}:/{record["volume"]["name"]}{qtree}{user}on {clusterName} is using {record["space"]["used"]["soft_limit_percent"]}% which is more than {rule[key]}% of its allocaed space.'
                                logger.info(message)
                                snsClient.publish(TopicArn=config["snsTopicArn"], Message=message, Subject=f'Monitor ONTAP Services Alert for cluster {clusterName}')
                                changedEvents=True
                                event = {
                                    "index": uniqueIdentifier,
                                    "message": message,
                                    "refresh": eventResilience
                                }
                                print(message)
                                events.append(event)
                    else:
                        message = f'Unknown quota matching condition type "{key}".'
                        logger.warning(message)
                        print(message)
        #
        # After processing the records, see if any events need to be removed.
        i=0
        while i < len(events):
            if events[i]["refresh"] <= 0:
                print(f'Deleting event: {events[i]["message"]}')
                del events[i]
                changedEvents = True
            else:
                # If an event wasn't refreshed, then we need to save the new refresh count.
                if events[i]["refresh"] != eventResilience:
                    changedEvents = True
                i += 1
        #
        # If the events array changed, save it.
        if(changedEvents):
            s3Client.put_object(Key=config["quotaEventsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(events).encode('UTF-8'))
    else:
        print(f'API call to {endpoint} failed. HTTP status code {response.status}.')

################################################################################
# This function returns the index of the service in the conditions dictionary.
################################################################################
def getServiceIndex(targetService, conditions):

    i = 0
    while i < len(conditions["services"]):
        if conditions["services"][i]["name"] == targetService:
            return i
        i += 1
    
    return None

################################################################################
# This function builds a default matching conditions dictionary based on the
# environment variables passed in.
################################################################################
def buildDefaultMatchingConditions():
    #
    # Define global variables so we don't have to pass them to all the functions.
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger
    #
    # Define an empty matching conditions dictionary.
    conditions = { "services": [
        {"name": "systemHealth", "rules": []},
        {"name": "ems", "rules": []},
        {"name": "snapmirror", "rules": []},
        {"name": "storage", "rules": []},
        {"name": "quota", "rules": []}
    ]}
    #
    # Now, add rules based on the environment variables.
    for name, value in os.environ.items():
        if name == "versionChangeAlert":
            if value == "true":
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"versionChange": True})
            else:
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"versionChange": False})
        elif name == "failoverAlert":
            if value == "true":
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"failover": True})
            else:
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"failover": False})
        elif name == "networkInterfacesAlert":
            if value == "true":
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"networkInterfaces": True})
            else:
                conditions["services"][getServiceIndex("systemHealth", conditions)]["rules"].append({"networkInterfaces": False})
        elif name == "emsEventsAlert":
            if value == "true":
                conditions["services"][getServiceIndex("ems", conditions)]["rules"].append({"name": "", "severity": "error|alert|emergency", "message": ""})
        elif name == "snapMirrorHealthAlert":
            if value == "true":
                conditions["services"][getServiceIndex("snapmirror", conditions)]["rules"].append({"Healthy": False})  # This is what it matches on, so it is interesting when the health is false.
            else:
                conditions["services"][getServiceIndex("snapmirror", conditions)]["rules"].append({"Healthy": True})
        elif name == "snapMirrorLagTimeAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("snapmirror", conditions)]["rules"].append({"maxLagTime": value})
        elif name == "snapMirrorStalledAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("snapmirror", conditions)]["rules"].append({"stalledTransferSeconds": value})
        elif name == "fileSystemUtilizationWarnAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("storage", conditions)]["rules"].append({"aggrWarnPercentUsed": value})
        elif name == "fileSystemUtilizationCriticalAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("storage", conditions)]["rules"].append({"aggrCriticalPercentUsed": value})
        elif name == "volumeUtilizationWarnAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("storage", conditions)]["rules"].append({"volumeWarnPercentUsed": value})
        elif name == "volumeUtilizationCriticalAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("storage", conditions)]["rules"].append({"volumeCriticalPercentUsed": value})
        elif name == "softQuotaUtilizationAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("quota", conditions)]["rules"].append({"maxSoftQuotaPercentUsed": value})
        elif name == "hardQuotaUtilizationAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("quota", conditions)]["rules"].append({"maxHardQuotaPercentUsed": value})
        elif name == "inodeQuotaUtilizationAlert":
            value = int(value)
            if value > 0:
                conditions["services"][getServiceIndex("quota", conditions)]["rules"].append({"maxInodeQuotaPercentUsed": value})

    return conditions

################################################################################
# This function is used to read in all the configuration parameters from the
# various places:
#   Environment Variables
#   Config File
#   Calculated
################################################################################
def readInConfig():
    #
    # Define global variables so we don't have to pass them to all the functions.
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger
    #
    # Define a dictionary with all the required variables so we can
    # easily add them and check for their existence.
    requiredEnvVariables = {
        "OntapAdminServer": None,
        "s3BucketName": None,
        "s3BucketRegion": None
        }

    optionalVariables = {
        "configFilename": None,
        "secretsManagerEndPointHostname": None,
        "snsEndPointHostname": None,
        "syslogIP": None,
        "awsAccountId": None
        }

    filenameVariables = {
        "emsEventsFilename": None,
        "smEventsFilename": None,
        "smRelationshipsFilename": None,
        "conditionsFilename": None,
        "storageEventsFilename": None,
        "quotaEventsFilename": None,
        "systemStatusFilename": None
        }

    config = {
        "snsTopicArn": None,
        "secretArn": None,
        "secretUsernameKey": None,
        "secretPasswordKey": None
        }
    config.update(filenameVariables)
    config.update(optionalVariables)
    config.update(requiredEnvVariables)
    #
    # Get the required, and any additional, paramaters from the environment.
    for var in config:
        config[var] = os.environ.get(var)
    #
    # Check to see if s3BacketArn was provided instead of s3BucketName.
    if config["s3BucketName"] == None and os.environ.get("s3BucketArn") != None:
        config["s3BucketName"] = os.environ.get("s3BucketArn").split(":")[-1]
    #
    # Check that required environmental variables are there.
    for var in requiredEnvVariables:
        if config[var] == None:
            raise Exception (f'\n\nMissing required environment variable "{var}".')
    #
    # Open a client to the s3 service.
    s3Client = boto3.client('s3', config["s3BucketRegion"])
    #
    # Calculate the config filename if it hasn't already been provided.
    defaultConfigFilename = config["OntapAdminServer"] + "-config"
    if config["configFilename"] == None:
        config["configFilename"] = defaultConfigFilename
    #
    # Calculate the conditions filename if it hasn't already been provided.
    defaultConditionsFilename = config["OntapAdminServer"] + "-conditions"
    if config["conditionsFilename"] == None:
        config["conditionsFilename"] = defaultConditionsFilename
    #
    # Process the config file if it exist.
    try:
        lines = s3Client.get_object(Key=config["configFilename"], Bucket=config["s3BucketName"])['Body'].iter_lines()
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] != "NoSuchKey":
            raise err
        else:
            if config["configFilename"] != defaultConfigFilename:
                print(f"Warning, did not find file '{config['configFilename']}' in s3 bucket '{config['s3BucketName']}' in region '{config['s3BucketRegion']}'.")
    else:
        #
        # While iterating through the file, get rid of any "export ", comments, blank lines, or anything else that isn't key=value.
        for line in lines:
            line = line.decode('utf-8')
            if line[0:7] == "export ":
                line = line[7:]
            comment = line.split("#")
            line=comment[0].strip().replace('"', '')
            x = line.split("=")
            if len(x) == 2:
                (key, value) = line.split("=")
            key = key.strip()
            value = value.strip()
            #
            # Preserve any environment variables settings.
            if key in config:
                if config[key] == None:
                    config[key] = value
            else:
                print(f"Warning, unknown config parameter '{key}'.")
    #
    # Now, fill in the filenames for any that aren't already defined.
    for filename in filenameVariables:
        if config[filename] == None:
            config[filename] = config["OntapAdminServer"] + "-" + filename.replace("Filename", "")
    #
    # Define the endpoints if alternates weren't provided.
    if config.get("secretArn") != None:
        secretRegion = config["secretArn"].split(":")[3]
    else:
        #
        # Give it a value so secretsManagerEndPointHostname can be set. The check for all variables will correctly error out because secretArn is missing.
        secretRegion = "No-secretArn-was-provided"
    if config["secretsManagerEndPointHostname"] == None or config["secretsManagerEndPointHostname"] == "":
        config["secretsManagerEndPointHostname"] = f'secretsmanager.{secretRegion}.amazonaws.com'

    if config.get("snsTopicArn") != None:
        snsRegion = config["snsTopicArn"].split(":")[3]
    else:
        #
        # Give it a value so snsEndPointHostname can be set. The check for all variables will correctly error out because snsTopicArn is missing.
        snsRegion = "No-snsTopicArn-was-provided"
    if config["snsEndPointHostname"] == None or config["snsEndPointHostname"] == "":
        config["snsEndPointHostname"] = f'sns.{snsRegion}.amazonaws.com'
    #
    # Now, check that all the configuration parameters have been set.
    for key in config:
        if config[key] == None and key not in optionalVariables:
            raise Exception(f'Missing configuration parameter "{key}".')

################################################################################
# Main logic
################################################################################
def lambda_handler(event, context):
    #
    # Define global variables so we don't have to pass them to all the functions.
    global config, s3Client, snsClient, http, headers, clusterName, clusterVersion, logger
    #
    # Read in the configuraiton.
    readInConfig()   # This defines the s3Client variable.
    #
    # Set up loging.
    logger = logging.getLogger("mon_fsxn_service")
    logger.setLevel(logging.DEBUG)       # Anything at this level and above this get logged.
    if config["syslogIP"] != None:
        #
        # Due to a bug with the SysLogHandler() of not sending proper framing with a message
        # when using TCP (it should end it with a LF and not a NUL like it does now) you must add 
        # an additional frame delimiter to the receiving syslog server. With rsyslog, you add
        # a AddtlFrameDelimiter="0" directive to the "input()" line where they have it listen
        # to a TCP port. For example:
        #
        #  # provides TCP syslog reception
        #  module(load="imtcp")
        #  input(type="imtcp" port="514" AddtlFrameDelimiter="0")
        # 
        # Because of this bug, I am going to stick with UDP, the default protocol used by
        # the syslog handler. If TCP is required, then the above changes will have to be made
        # to the syslog server. Or, the program will have to handle closing and opening the
        # connection for each message. The following will do that:
        #    handler.flush()
        #    handler.close()
        #    logger.removeHandler(handler)
        #    handler = logging.handlers.SysLogHandler(facility=SysLogHandler.LOG_LOCAL0, address=(syslogIP, 514), socktype=socket.SOCK_STREAM)
        #    handler.setFormatter(formatter)
        #    logger.addHandler(handler)
        #
        # You might get away with a simple handler.open() after the close(), without having to
        # remove and add the handler. I didn't test that.
        handler = logging.handlers.SysLogHandler(facility=SysLogHandler.LOG_LOCAL0, address=(config["syslogIP"], 514))
        formatter = logging.Formatter(
                fmt="%(name)s:%(funcName)s - Level:%(levelname)s - Message:%(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    #
    # Create a Secrets Manager client.
    session = boto3.session.Session()
    secretRegion = config["secretArn"].split(":")[3]
    client = session.client(service_name='secretsmanager', region_name=secretRegion, endpoint_url=f'https://{config["secretsManagerEndPointHostname"]}')
    #
    # Get the username and password of the ONTAP/FSxN system.
    secretsInfo = client.get_secret_value(SecretId=config["secretArn"])
    secrets = json.loads(secretsInfo['SecretString'])
    if secrets.get(config['secretUsernameKey']) == None:
        print(f'Error, "{config["secretUsernameKey"]}" not found in secret "{config["secretArn"]}".')
        return

    if secrets.get(config['secretPasswordKey']) == None:
        print(f'Error, "{config["secretPasswordKey"]}" not found in secret "{config["secretArn"]}".')
        return

    username = secrets[config['secretUsernameKey']]
    password = secrets[config['secretPasswordKey']]
    #
    # Create clients to the other AWS services we will be using.
    #s3Client = boto3.client('s3', config["s3BucketRegion"])  # Defined in readInConfig()
    snsRegion = config["snsTopicArn"].split(":")[3]
    snsClient = boto3.client('sns', region_name=snsRegion, endpoint_url=f'https://{config["snsEndPointHostname"]}')
    #
    # Create a http handle to make ONTAP/FSxN API calls with.
    auth = urllib3.make_headers(basic_auth=f'{username}:{password}')
    headers = { **auth }
    #
    # Disable warning about connecting to servers with self-signed SSL certificates.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    retries = Retry(total=None, connect=1, read=1, redirect=10, status=0, other=0)  # pylint: disable=E1123
    http = urllib3.PoolManager(cert_reqs='CERT_NONE', retries=retries)
    #
    # Get the conditions we know what to alert on.
    try:
        data = s3Client.get_object(Key=config["conditionsFilename"], Bucket=config["s3BucketName"])
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] != "NoSuchKey":
            print(f'\n\nError, could not retrieve configuration file {config["conditionsFilename"]} from: s3://{config["s3BucketName"]}.\nBelow is additional information:\n\n')
            raise err
        else:
            matchingConditions = buildDefaultMatchingConditions()
            s3Client.put_object(Key=config["conditionsFilename"], Bucket=config["s3BucketName"], Body=json.dumps(matchingConditions).encode('UTF-8'))
    else:
        matchingConditions = json.loads(data["Body"].read().decode('UTF-8'))

    if(checkSystem()):
        #
        # Loop on all the configured ONTAP services we want to check on.
        for service in matchingConditions["services"]:
            if service["name"].lower() == "systemhealth":
                checkSystemHealth(service)
            elif service["name"].lower() == "ems":
                processEMSEvents(service)
            elif (service["name"].lower() == "snapmirror"):
                processSnapMirrorRelationships(service)
            elif service["name"].lower() == "storage":
                processStorageUtilization(service)
            elif service["name"].lower() == "quota":
                processQuotaUtilization(service)
            else:
                print(f'Unknown service "{service["name"]}".')
    return

if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') == None:
    lambdaFunction = False
    lambda_handler(None, None)
else:
    lambdaFunction = True
