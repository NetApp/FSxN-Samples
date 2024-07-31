#!/usr/bin/python3
#
# This script is used to add CloudWatch alarms for all the FSx for NetApp
# ONTAP volumes, that don't already have one, that will trigger when the
# utilization of the volume gets above the threshold defined below. It will
# also create an alarm that will trigger when the file system reach
# an average CPU utilization greater than what is specified below.
#
# It can either be run as a standalone script, or uploaded as a Lambda
# function with the thought being that you will create a EventBridge schedule
# to invoke it periodically.
#
# It will scan all regions looking for FSxN volumes, and since CloudWatch
# can't send SNS messages across regions, it assumes that the specified
# SNS topic exist in each region for the specified account ID.
#
# Finally, a default volume threshold is defined below. It sets the volume
# utilization threshold that will cause CloudWatch to send the alarm event
# to the SNS topic. It can be overridden on a per volume basis by having a
# tag with the name of "alarm_threshold" set to the desired threshold.
# If the tag is set to 100, then no alarm will be created. You can also
# set an override to the filesystem CPU utilization alarm, but setting
# a tag with the name of 'CPU_Alarm_Threshold' on the file system resouce.
# Lastly, you can create an override for the SSD alarm, by creating a tag
# with the name "SSD_Alarm_Threshold" on the file system resource.
#
################################################################################
#
# Define which SNS topic you want "volume full" message to be sent to.
SNStopic=''
#
# Provide the account id the SNS topic resides under:
# MUST be a string.
accountId=''
#
# Set the customer ID associated with the AWS account. This is used to
# as part of the alarm name prefix so a customer ID can be associated
# with the alarm. If it is left as an empty string, no extra prefix
# will be added.
customerId=''
#
# Define the default CPU utilization threshold before sending the alarm.
# Setting it to 100 will disable the creation of the alarm.
defaultCPUThreshold=80
#
# Define the default SSD utilization threshold before sending the alarm.
# Setting it to 100 will disable the creation of the alarm.
defaultSSDThreshold=90
#
# Define the default volume utilization threshold before sending the alarm.
# Setting it to 100 will disable the creation of the alarm.
defaultVolumeThreshold=80
#
# Define the prefix for the volume utilization alarm name for the CloudWatch alarms.
alarmPrefixVolume="Volume_Utilization_for_volume_"
#
# Define the prefix for the CPU utilization alarm name for the CloudWatch alarms.
alarmPrefixCPU="CPU_Utilization_for_fs_"
#
# Define the prefix for the SSD utilization alarm name for the CloudWatch alarms.
alarmPrefixSSD="SSD_Utilization_for_fs_"

################################################################################
# You shouldn't have to modify anything below here.
################################################################################

import boto3
import os
import getopt
import sys

################################################################################
# This function adds the SSD Utilization CloudWatch alarm.
################################################################################
def add_ssd_alarm(cw, fsId, alarmName, alarmDescription, threshold, region):
    action = 'arn:aws:sns:' + region + ':' + accountId + ':' + SNStopic
    if not dryRun:
        cw.put_metric_alarm(
            AlarmName=alarmName,
            ActionsEnabled=True,
            AlarmActions=[action],
            AlarmDescription=alarmDescription,
            EvaluationPeriods=1,
            DatapointsToAlarm=1,
            Threshold=threshold,
            ComparisonOperator='GreaterThanThreshold',
            MetricName="StorageCapacityUtilization",
            Period=300,
            Statistic="Average",
            Namespace="AWS/FSx",
            Dimensions=[{'Name': 'FileSystemId', 'Value': fsId}, {'Name': 'StorageTier', 'Value': 'SSD'}, {'Name': 'DataType', 'Value': 'All'}]
        )
    else:
        print(f'Would have added SSD alarm for {fsId} with name {alarmName} with thresold of {threshold} in {region} with action {action}')

################################################################################
# This function adds the CPU Utilization CloudWatch alarm.
################################################################################
def add_cpu_alarm(cw, fsId, alarmName, alarmDescription, threshold, region):
    action = 'arn:aws:sns:' + region + ':' + accountId + ':' + SNStopic
    if not dryRun:
        cw.put_metric_alarm(
            AlarmName=alarmName,
            ActionsEnabled=True,
            AlarmActions=[action],
            AlarmDescription=alarmDescription,
            EvaluationPeriods=1,
            DatapointsToAlarm=1,
            Threshold=threshold,
            ComparisonOperator='GreaterThanThreshold',
            MetricName="CPUUtilization",
            Period=300,
            Statistic="Average",
            Namespace="AWS/FSx",
            Dimensions=[{'Name': 'FileSystemId', 'Value': fsId}]
        )
    else:
        print(f'Would have added CPU alarm for {fsId} with name {alarmName} with thresold of {threshold} in {region} with action {action}.')

################################################################################
# This function adds the Volume utilization CloudWatch alarm.
################################################################################
def add_volume_alarm(cw, volumeId, alarmName, alarmDescription, fsId, threshold, region):
    action = 'arn:aws:sns:' + region + ':' + accountId + ':' + SNStopic
    if not dryRun:
        cw.put_metric_alarm(
            ActionsEnabled=True,
            AlarmName=alarmName,
            AlarmActions=[action],
            AlarmDescription=alarmDescription,
            EvaluationPeriods=1,
            DatapointsToAlarm=1,
            Threshold=threshold,
            ComparisonOperator='GreaterThanThreshold',
            Metrics=[{"Id":"e1","Label":"Utilization","ReturnData":True,"Expression":"m2/m1*100"},\
                     {"Id":"m2","ReturnData":False,"MetricStat":{"Metric":{"Namespace":"AWS/FSx","MetricName":"StorageUsed","Dimensions":[{"Name":"VolumeId","Value": volumeId},{"Name":"FileSystemId","Value":fsId}]},"Period":300,"Stat":"Average"}},\
                     {"Id":"m1","ReturnData":False,"MetricStat":{"Metric":{"Namespace":"AWS/FSx","MetricName":"StorageCapacity","Dimensions":[{"Name":"VolumeId","Value": volumeId},{"Name":"FileSystemId","Value":fsId}]},"Period":300,"Stat":"Average"}}]
        )
    else:
        print(f'Would have added volume alarm for {volumeId} {fsId} with name {alarmName} with thresold of {threshold} in {region} with action {action}.')


################################################################################
# This function deletes a CloudWatch alarm.
################################################################################
def delete_alarm(cw, alarmName):
    if not dryRun:
        cw.delete_alarms(AlarmNames=[alarmName])
    else:
        print(f'Would have deleted alarm {alarmName}.')
    return

################################################################################
# This function checks to see if the alarm already exists.
################################################################################
def contains_alarm(alarmName, alarms):
    for alarm in alarms:
        if(alarm['AlarmName'] == alarmName):
            return True
    return False

################################################################################
# This function checks to see if a volume exists.
################################################################################
def contains_volume(volumeId, volumes):
    for volume in volumes:
        if(volume['VolumeId'] == volumeId):
            return True
    return False

################################################################################
# This function checks to see if a file system exists.
################################################################################
def contains_fs(fsId, fss):
    for fs in fss:
        if(fs['FileSystemId'] == fsId):
            return True
    return False

################################################################################
# This function returns the value assigned to the "alarm_threshold" tag
# associated with the arn passed in. If none is found, it returns the default
# threshold set above.
################################################################################
def getAlarmThresholdTagValue(fsx, arn):
    #
    # This is put into a try block because it is possible that the volume
    # is deleted between the time we get the list of volumes and the time
    # we try to get the tags for the volume.
    try:
        tags = fsx.list_tags_for_resource(ResourceARN=arn)
        for tag in tags['Tags']:
            if(tag['Key'].lower() == "alarm_threshold"):
                return(tag['Value'])
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFound':
            return(100) # Return 100 so we don't try to create an alarm.
        else:
            raise e

    return(defaultVolumeThreshold)

################################################################################
# This function returns the value assigned to the "CPU_alarm_threshold" tag
# that is in the array of tags passed in. if it doesn't find that tag it
# returns the default threshold set above.
################################################################################
def getCPUAlarmThresholdTagValue(tags):
    for tag in tags:
        if(tag['Key'].lower() == "cpu_alarm_threshold"):
            return(tag['Value'])
    return(defaultCPUThreshold)

################################################################################
# This function returns the value assigned to the "CPU_alarm_threshold" tag
# that is in the array of tags passed in. if it doesn't find that tag it
# returns the default threshold set above.
################################################################################
def getSSDAlarmThresholdTagValue(tags):
    for tag in tags:
        if(tag['Key'].lower() == "ssd_alarm_threshold"):
            return(tag['Value'])
    return(defaultSSDThreshold)

################################################################################
# This is the main logic of the program. It loops on all the regions then all
# the fsx volumes within the region, checking to see if any of them already
# have a CloudWatch alarm, and if not, add one.
################################################################################
def lambda_handler(event, context):
    global customerId, regions
    #
    # If the customer ID is set, reformat to be used in the alarm description.
    if customerId != '':
        customerId = f", CustomerID: {customerId}"

    if len(SNStopic) == 0:
        raise Exception("You must specify a SNS topic to send the alarm messages to.")
        return

    if len(accountId) == 0:
        raise Exception("You must specify an accountId to run this program.")
        return

    if len(regions) == 0:
        ec2Client = boto3.client('ec2')
        ec2Regions = ec2Client.describe_regions()['Regions']
        for region in ec2Regions:
            regions += [region['RegionName']]

    fsxRegions = boto3.Session().get_available_regions('fsx')
    for region in regions:
        if region in fsxRegions:
            print(f'Scanning {region}')
            fsx = boto3.client('fsx', region_name=region)
            cw = boto3.client('cloudwatch', region_name=region)
            #
            # Get all the file systems, volumes and alarm in the region.
            response = fsx.describe_file_systems()
            fss = response['FileSystems']
            while response.get('NextToken'):
                response = fsx.describe_file_systems(NextToken=response['NextToken'])
                fss += response['FileSystems']

            response = fsx.describe_volumes()
            volumes = response['Volumes']
            while response.get('NextToken'):
                response = fsx.describe_volumes(NextToken=response['NextToken'])
                volumes += response['Volumes']

            response = cw.describe_alarms()
            alarms = response['MetricAlarms']
            while response.get('NextToken'):
                response = cw.describe_alarms(NextToken=response['NextToken'])
                alarms += response['MetricAlarms']
            #
            # Scan for filesystems without CPU Utilization Alarm.
            for fs in fss:
                if(fs['FileSystemType'] == "ONTAP"):
                    threshold = int(getCPUAlarmThresholdTagValue(fs['Tags']))
                    if(threshold != 100):
                        fsId = fs['FileSystemId']
                        fsName = fsId.replace('fs-', 'FsxId')
                        alarmName = alarmPrefixCPU + fsId
                        alarmDescription = f"CPU utilization alarm for file system {fsName}{customerId} in region {region}."

                        if(not contains_alarm(alarmName, alarms)):
                            print(f'Adding CPU Alarm for {fs["FileSystemId"]}')
                            add_cpu_alarm(cw, fsId, alarmName, alarmDescription, threshold, region)
            #
            # Scan for CPU alarms without a FSxN filesystem.
            for alarm in alarms:
                alarmName = alarm['AlarmName']
                if(alarmName[:len(alarmPrefixCPU)] == alarmPrefixCPU):
                    fsId = alarmName[len(alarmPrefixCPU):]
                    if(not contains_fs(fsId, fss)):
                        print("Deleteing alarm: " + alarmName + " in region " + region)
                        delete_alarm(cw, alarmName)
            #
            # Scan for filesystems without SSD Utilization Alarm.
            for fs in fss:
                if(fs['FileSystemType'] == "ONTAP"):
                    threshold = int(getSSDAlarmThresholdTagValue(fs['Tags']))
                    if(threshold != 100):
                        fsId = fs['FileSystemId']
                        fsName = fsId.replace('fs-', 'FsxId')
                        alarmName = alarmPrefixSSD + fsId
                        alarmDescription = f"SSD utilization alarm for file system {fsName}{customerId} in region {region}."

                        if(not contains_alarm(alarmName, alarms)):
                            print(f'Adding SSD Alarm for {fsId}')
                            add_ssd_alarm(cw, fs['FileSystemId'], alarmName, alarmDescription, threshold, region)
            #
            # Scan for SSD alarms without a FSxN filesystem.
            for alarm in alarms:
                alarmName = alarm['AlarmName']
                if(alarmName[:len(alarmPrefixSSD)] == alarmPrefixSSD):
                    fsId = alarmName[len(alarmPrefixSSD):]
                    if(not contains_fs(fsId, fss)):
                        print("Deleteing alarm: " + alarmName + " in region " + region)
                        delete_alarm(cw, alarmName)
            #
            # Scan for volumes without alarms.
            for volume in volumes:
                if(volume['VolumeType'] == "ONTAP"):
                    volumeId = volume['VolumeId']
                    volumeName = volume['Name']
                    volumeARN = volume['ResourceARN']
                    fsId = volume['FileSystemId']

                    threshold = int(getAlarmThresholdTagValue(fsx, volumeARN))

                    if(threshold != 100):   # No alarm if the value is set to 100.
                        alarmName = alarmPrefixVolume + volumeId
                        fsName = fsId.replace('fs-', 'FsxId')
                        alarmDescription = f"Volume utilization alarm for volumeId {volumeId}{customerId}, File System Name: {fsName}, Volume Name: {volumeName} in region {region}."
                        if(not contains_alarm(alarmName, alarms)):
                            print(f'Adding volume utilization alarm for {volumeName} in region {region}.')
                            add_volume_alarm(cw, volumeId, alarmName, alarmDescription, fsId, threshold, region)
            #
            # Scan for volume alarms without volumes.
            for alarm in alarms:
                alarmName = alarm['AlarmName']
                if(alarmName[:len(alarmPrefixVolume)] == alarmPrefixVolume):
                    volumeId = alarmName[len(alarmPrefixVolume):]
                    if(not contains_volume(volumeId, volumes)):
                        print("Deleteing alarm: " + alarmName + " in region " + region)
                        delete_alarm(cw, alarmName)

    return

################################################################################
# This function is used to print out the usage of the script.
################################################################################
def usage():
    print('Usage: add_cw_alarm [-h|--help] [-d|--dryRun] [[-c|--customerID] customerID] [[-a|--accountID] aws_account_id] [[-s|--SNSTopic] SNS_Topic_Name] [[-r|--region] region] [[-C|--CPUThreshold] threshold] [[-S|--SSDThreshold] threshold] [[-V|--VolumeThreshold] threshold]')

################################################################################
# Main logic starts here.
################################################################################
#
# Set some default values.
regions = []
dryRun = False
#
# Check to see if we are bring run from a command line or a Lmabda function.
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') == None:
    argumentList = sys.argv[1:]
    options = "hc:a:s:dr:C:S:V:"

    longOptions = ["help", "customerID=", "accountID=", "SNSTopic=", "dryRun", "region=", "CPUThreshold=", "SSDThreshold=", "VolumeThreshold="]
    skip = False
    try:
        arguments, values = getopt.getopt(argumentList, options, longOptions)

        for currentArgument, currentValue in arguments:
            if currentArgument in ("-h", "--help"):
                usage()
                skip = True
            elif currentArgument in ("-c", "--customerID"):
                customerId = currentValue
            elif currentArgument in ("-a", "--accountID"):
                accountId = currentValue
            elif currentArgument in ("-s", "--SNSTopic"):
                snsTopic = currentValue
            elif currentArgument in ("-C", "--CPUThreshold"):
                defaultCPUThreshold = int(currentValue)
            elif currentArgument in ("-S", "--SSDThreshold"):
                defaultSSDThreshold = int(currentValue)
            elif currentArgument in ("-V", "--VolumeThreshold"):
                defaultVolumeThreshold = int(currentValue)
            elif currentArgument in ("-d", "--dryRun"):
                dryRun = True
            elif currentArgument in ("-r", "--region"):
                regions += [currentValue]

    except getopt.error as err:
        print(str(err))
        usage()
        skip = True

    if not skip:
        lambda_handler(None, None)
