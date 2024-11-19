#!/bin/python3
#
################################################################################
# This script is used to ingest all the NAS audit logs from all the FSx for
# ONTAP File Systems from the specified volume into a specified CloudWatch log
# group. It will create a log stream for each FSxN audit logfile it finds.
# It will attempt to process every FSxN within the region. It leverage AWS
# secrets manager to get the credentials for the fsxadmin user on each FSxNs.
# It will store the last read file for each FSxN in the specified S3 bucket so
# that it will not process the same file twice. It will skip any FSxN file
# system that it doesn't have credentials for. It will also skip any FSxN file
# system that doesn't have the specified volume.
#
# It assumes:
#  - That there is only one data vserver per FSxN file system and that it
#    is named 'fsx'.
#  - That the administrator username is 'fsxadmin'.
#  - That the audit log files will be named in the following format:
#      audit_fsx_D2024-09-24-T13-00-03_0000000000.xml
#    Where 'fsx' is the vserver name.
#
################################################################################
#
from requests_toolbelt.multipart import decoder
import urllib3
import datetime
import xmltodict
import os
import json
from urllib3.util import Retry
import boto3
import botocore

################################################################################
# You can configure this script by either setting the following variables, or
# by setting environment variables with the same name.
################################################################################
#
# Specify the secret region and ARN for the fsxadmin passwords.
#   Format of the secret should be:
#   {"fsId": "fsxadmin-password", "fsId": "fsxadmin-password", ...}
#secretRegion = "us-west-2"
#secretArn = "arn:aws:secretsmanager:us-west-2:759995470648:secret:FSXN_passwords-MJixz9"
#
# Where to store last read stats.
#s3BucketRegion = "us-west-2"
#s3BucketName = "keith-test-mon-ems-events"
#statsName = "lastFileRead"
#
# The region to process the FSxNs in.
#fsxRegion = "us-west-2"
#
# The name of the volume that holds the audit logs. Assumed to be the same on
# all FSxNs.
#volumeName = "audit_logs"
#
# The name of the vserver that holds the audit logs. Assumed to be the same on 
# all FSxNs.
#vserverName = "fsx"
#
# The CloudWatch log group to store the audit logs in.
#logGroupName = "/fsx/audit_logs"

################################################################################
# This function returns the epoch time from the filename. It assumes the
# filename is in the format of:
#   audit_fsx_D2024-09-24-T13-00-03_0000000000.xml
################################################################################
def getEpoch(filename):
    dateStr = filename.split('_')[2][1:]
    year = int(dateStr.split('-')[0])
    month = int(dateStr.split('-')[1])
    day = int(dateStr.split('-')[2])

    hour = int(dateStr.split('-')[3][1:])
    minute = int(dateStr.split('-')[4])
    second = int(dateStr.split('-')[5])

    return datetime.datetime(year, month, day, hour, minute, second).timestamp()

################################################################################
# This function copies a file from the FSxN file system, using the ONTAP
# APIs, and then calls the ingestAuditFile function to upload the audit
# log entires to the CloudWatch log group.
################################################################################
def processFile(ontapAdminServer, headers, volumeUUID, filePath):
    global http
    #
    # Create the tempoary file to hold the contents from the ONTAP/FSxN file.
    tmpFileName = "/tmp/testout"
    f = open(tmpFileName, "wb")
    #
    # Number of bytes to read for each API call.
    blockSize=1024*1024

    bytesRead = 0
    requestSize = 1   # Set to > 0 to start the loop.
    while requestSize > 0:
        endpoint = f'https://{ontapAdminServer}/api/storage/volumes/{volumeUUID}/files/{filePath}?length={blockSize}&byte_offset={bytesRead}'
        response = http.request('GET', endpoint, headers=headers, timeout=5.0)
        if response.status == 200:
            bytesRead += blockSize
            data = response.data
            #
            # Get the multipart boundary separator from the first part of the file.
            boundary = data[4:20].decode('utf-8')
            #
            # Get MultipartDecoder to decode the data.
            contentType = f"multipart/form-data; boundary={boundary}"
            multipart_data = decoder.MultipartDecoder(data, contentType)
            #
            # The first part returned from ONTAP contains the amount of data in the response. When it is 0, we have read the entire file.
            firstPart = True
            for part in multipart_data.parts:
                if(firstPart):
                    requestSize = int(part.text)
                    firstPart = False
                else:
                    f.write(part.content)
        else:
            print(f'API call to {endpoint} failed. HTTP status code: {response.status}.')
            break

    f.close()
    #
    # Upload the audit events to CloudWatch.
    ingestAuditFile(tmpFileName, filePath)

################################################################################
# This function returns a CloudWatch event from the XML audit log event.
################################################################################
def createCWEvent(event):
    # ObjectServer: Always just seems to be: 'Security'.
    # HandleID: Is some odd string of numbers.
    # InformationRequested: A verbose string of information.
    # AccessList: A string of numbers that I'm not sure what they represent.
    # AccessMask: A number that represent the access mask.
    # DesiredAccess: A verbose list of strings represent the desired access.
    # Attributes: A verbose list of strings representing the attributes.
    # DirHandleID: A string of numbers that I'm not sure what they represent.
    # SearchFilter: Always seems to be null.
    # SearchPattern: Always seems to be set to "Not Present".
    # SubjectPort: Just the TCP port that the user came in on.
    # OldDirHandle and NewDirHandle: Are the UUIDs of the directory. The OldPath and NewPath are human readable.
    ignoredDataFields = ["ObjectServer", "HandleID", "InformationRequested", "AccessList", "AccessMask", "DesiredAccess", "Attributes", "DirHandleID", "SearchFilter", "SearchPattern", "SubjectPort", "OldDirHandle", "NewDirHandle"]
    #
    # Convert the timestamp from the XML file to a timestamp in milliseconds.
    # An example format of the time is: 2024-09-22T21:05:27.263864000Z
    year = int(event['System']['TimeCreated']['@SystemTime'].split('-')[0])
    month = int( event['System']['TimeCreated']['@SystemTime'].split('-')[1])
    day =  int(event['System']['TimeCreated']['@SystemTime'].split('-')[2].split('T')[0])
    hour =  int(event['System']['TimeCreated']['@SystemTime'].split('T')[1].split(':')[0])
    minute =  int(event['System']['TimeCreated']['@SystemTime'].split('T')[1].split(':')[1])
    second =  int(event['System']['TimeCreated']['@SystemTime'].split('T')[1].split(':')[2].split('.')[0])
    msecond = event['System']['TimeCreated']['@SystemTime'].split('T')[1].split(':')[2].split('.')[1].split('Z')[0]
    t = datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc).timestamp()
    #
    # Convert the timestep from a float in seconds to an integer in milliseconds.
    msecond = int(msecond)/(10 ** (len(msecond) - 3))
    t = int(t * 1000 + msecond)
    #
    # Build the message to send to CloudWatch.
    cwData  = f"Date={event['System']['TimeCreated']['@SystemTime']}, "
    cwData += f"Event={event['System']['EventName'].replace(' ', '-')}, " # Replace spaces with dashes.
    cwData += f"fs={event['System']['Computer'].split('/')[0]}, "
    cwData += f"svm={event['System']['Computer'].split('/')[1]}, "
    cwData += f"Result={event['System']['Result'].replace(' ', '-')}"     # Replace spaces with dashes.
    #
    # Add the data fields to the message. Some fields are ignored. Some required special handling.
    for data in event['EventData']['Data']:
        if data['@Name'] not in ignoredDataFields:
            if data['@Name'] == 'SubjectIP':
                cwData += f", IP={data['#text']}"
            elif data['@Name'] == 'SubjectUnix':
                cwData += f", UnixID={data['@Uid']}, GroupID={data['@Gid']}"
            elif data['@Name'] == 'SubjectUserSid':
                cwData += f", UserSid={data['#text']}"
            elif data['@Name'] == 'SubjectUserName':
                cwData += f", UserName={data['#text']}"
            elif data['@Name'] == 'SubjectDomainName':
                cwData += f", Domain={data['#text']}"
            elif data['@Name'] == 'ObjectName' or data['@Name'] == 'FileName':
                cwData += f", volume={data['#text'].split(';')[0].replace('(', '').replace(')', '')}, name={data['#text'].split(';')[1]}"
            elif data['@Name'] == 'InformationSet':
                if data.get('#text') == None:
                    cwData += ", InformationSet=Null"
                else:
                    cwData += f", InformationSet={data['#text']}"
            else: # Assume the rest of the fields don't need special handling.
                cwData += f", {data['@Name']}={data['#text']}"

    return {'timestamp': t, 'message': cwData}

################################################################################
# This function uploads the audit log events stored in XML format to a
# CloudWatch log stream.
################################################################################
def ingestAuditFile(auditLogPath, auditLogName):
    global cwLogsClient, config
    #
    # Convert the XML audit log file into a dictionary.
    f = open(auditLogPath, 'r')
    data = f.read()
    dictData = xmltodict.parse(data)

    if dictData.get('Events') == None or dictData['Events'].get('Event') == None:
        print(f"No events found in {auditLogName}")
        return
    #
    # Ensure the logstream exists.
    try:
        cwLogsClient.create_log_stream(logGroupName=config['logGroupName'], logStreamName=auditLogName)
    except cwLogsClient.exceptions.ResourceAlreadyExistsException:
        #
        # This really shouldn't happen, since we should only be processing
        # each file once, but during testing it happens all the time.
        print(f"Log stream {auditLogName} already exists")
    #
    # If there is only one event, then the dict['Events']['Event'] will be a
    # dictionary, otherwise it will be a list of dictionaries.
    if isinstance(dictData['Events']['Event'], list):
        cwEvents = []
        for event in dictData['Events']['Event']:
            cwEvents.append(createCWEvent(event))
            if len(cwEvents) == 5000:  # The real maximum is 10000 events, but there is also a size limit, so we will use 5000.
                print("Putting 5000 events")
                response = cwLogsClient.put_log_events(logGroupName=config['logGroupName'], logStreamName=auditLogName, logEvents=cwEvents)
                if response.get('rejectedLogEventsInfo') != None:
                    if response['rejectedLogEventsInfo'].get('tooNewLogEventStartIndex') > 0:
                        print(f"Warning: Too new log event start index: {response['rejectedLogEventsInfo']['tooNewLogEventStartIndex']}")
                    if response['rejectedLogEventsInfo'].get('tooOldLogEventStartIndex') > 0:
                        print(f"Warning: Too old log event start index: {response['rejectedLogEventsInfo']['tooOldLogEventStartIndex']}")
                cwEvents = []
    else:
        cwEvents = [createCWEvent(dictData['Events']['Event'])]

    if len(cwEvents) > 0:
        print(f"Putting {len(cwEvents)} events")
        response = cwLogsClient.put_log_events(logGroupName=config['logGroupName'], logStreamName=auditLogName, logEvents=cwEvents)
        if response.get('rejectedLogEventsInfo') != None:
            if response['rejectedLogEventsInfo'].get('tooNewLogEventStartIndex') > 0:   
                print(f"Warning: Too new log event start index: {response['rejectedLogEventsInfo']['tooNewLogEventStartIndex']}")
            if response['rejectedLogEventsInfo'].get('tooOldLogEventStartIndex') > 0:   
                print(f"Warning: Too old log event start index: {response['rejectedLogEventsInfo']['tooOldLogEventStartIndex']}")

################################################################################
# This function checks that all the required configuration variables are set.
################################################################################
def checkConfig():
    global config

    config = {
        'volumeName': volumeName if 'volumeName' in globals() else None,               # pylint: disable=E0602
        'logGroupName': logGroupName if 'logGroupName' in globals() else None,         # pylint: disable=E0602
        'fsxRegion': fsxRegion if 'fsxRegion' in globals() else None,                  # pylint: disable=E0602
        'secretRegion': secretRegion if 'secretRegion' in globals() else None,         # pylint: disable=E0602
        'secretArn': secretArn if 'secretArn' in globals() else None,                  # pylint: disable=E0602
        's3BucketRegion': s3BucketRegion if 's3BucketRegion' in globals() else None,   # pylint: disable=E0602
        's3BucketName': s3BucketName if 's3BucketName' in globals() else None,         # pylint: disable=E0602
        'statsName': statsName if 'statsName' in globals() else None,                  # pylint: disable=E0602
        'vserverName': vserverName if 'vserverName' in globals() else None             # pylint: disable=E0602
    }

    for item in config:
        if config[item] == None:
            config[item] = os.environ.get(item)
        if config[item] == None:
            raise Exception(f"{item} is not set.")

################################################################################
# This is the main function that checks that everything is configured correctly
# and then processes all the FSxNs.
################################################################################
def lambda_handler(event, context):     # pylint: disable=W0613
    global http, cwLogsClient, config
    #
    # Check that we have all the configuration variables we need.
    checkConfig()
    #
    # Create a Secrets Manager client.
    session = boto3.session.Session()
    secretsClient = session.client(service_name='secretsmanager', region_name=config['secretRegion'])
    #
    # Get the fsxadmin passwords for all the file systems.
    secretsInfo = secretsClient.get_secret_value(SecretId=config['secretArn'])
    secrets = json.loads(secretsInfo['SecretString'])
    username = "fsxadmin"
    #
    # Create a S3 client.
    s3Client = boto3.client('s3', config['s3BucketRegion'])
    #
    # Create a FSx client.
    fsxClient = boto3.client('fsx', config['fsxRegion'])
    #
    # Create a CloudWatch client.
    cwLogsClient = boto3.client('logs', config['fsxRegion'])
    #
    # Disable warning about connecting to servers with self-signed SSL certificates.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    retries = Retry(total=None, connect=1, read=1, redirect=10, status=0, other=0)  # pylint: disable=E1123
    http = urllib3.PoolManager(cert_reqs='CERT_NONE', retries=retries)
    #
    # Get a list of FSxNs in the region.
    fsxNs = []   # Holds the FQDN of the FSxNs management ports.
    fsxResponse = fsxClient.describe_file_systems()
    for fsx in fsxResponse['FileSystems']:
        fsxNs.append(fsx['OntapConfiguration']['Endpoints']['Management']['DNSName'])
    #
    # Make sure to get them all since the response is paginated.
    while fsxResponse.get('NextToken') != None:
        fsxResponse = fsxClient.describe_file_systems(NextToken=fsxResponse['NextToken'])
        for fsx in fsxResponse['FileSystems']:
            fsxNs.append(fsx['OntapConfiguration']['Endpoints']['Management']['DNSName'])
    #
    # Get the last read stats file.
    try:
        response = s3Client.get_object(Bucket=config['s3BucketName'], Key=config['statsName'])
    except botocore.exceptions.ClientError as err:
        #
        # If the error is that the object doesn't exist, then this must be the
        # first time this script has run so create an empty lastFileRead.
        if err.response['Error']['Code'] == "NoSuchKey":
            lastFileRead = {}
        else:
            raise err
    else:
        lastFileRead = json.loads(response['Body'].read().decode('utf-8'))
    #
    # Only update the lastFileRead if we actually copied a new file.
    lastFileReadChanged = False
    #
    # Process each FSxN.
    for fsxn in fsxNs:
        fsId = fsxn.split('.')[1]
        #
        # Get the password
        password = secrets.get(fsId)
        if password == None:
            print(f'Warning: No password found for {fsId}.')
            continue
        #
        # Create a header with the basic authentication.
        auth = urllib3.make_headers(basic_auth=f'{username}:{password}')
        headersDownload = { **auth, 'Accept': 'multipart/form-data' }
        headersQuery = { **auth }
        #
        # Get the volume UUID for the audit_logs volume.
        volumeUUID = None
        endpoint = f"https://{fsxn}/api/storage/volumes?name={config['volumeName']}&svm={config['vserverName']}"
        response = http.request('GET', endpoint, headers=headersQuery, timeout=5.0)
        if response.status == 200:
            data = json.loads(response.data.decode('utf-8'))
            if data['num_records'] > 0:
                volumeUUID = data['records'][0]['uuid']  # Since we specified the volume, and vserver name, there should only be one record.

        if volumeUUID == None:
            print(f"Warning: Volume {config['volumeName']} not found for {fsId} under SVM: {config['vserverName']}.")
            continue
        #
        # Get all the files in the volume that match the audit file pattern.
        endpoint = f"https://{fsxn}/api/storage/volumes/{volumeUUID}/files?name=audit_{config['vserverName']}_D*.xml&order_by=name%20asc&fields=name"
        response = http.request('GET', endpoint, headers=headersQuery, timeout=5.0)
        data = json.loads(response.data.decode('utf-8'))
        if data.get('num_records') == 0:
            print(f"Warning: No XML audit log files found on FsID: {fsId}; SvmID: {config['vserverName']}; Volume: {config['volumeName']}.")
            continue

        for file in data['records']:
            filePath = file['name']
            if lastFileRead.get(fsxn) == None or getEpoch(filePath) > lastFileRead[fsxn]:
                #
                # Process the file.
                processFile(fsxn, headersDownload, volumeUUID, filePath)
                lastFileRead[fsxn] = getEpoch(filePath)
                lastFileReadChanged = True
    #
    # Save the last read stats file.
    if lastFileReadChanged:
        s3Client.put_object(Key=config['statsName'], Bucket=config['s3BucketName'], Body=json.dumps(lastFileRead).encode('UTF-8'))
#
# If this script is not running as a Lambda function, then call the lambda_handler function.
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') == None:
    lambdaFunction = False
    lambda_handler(None, None)
else:
    lambdaFunction = True
