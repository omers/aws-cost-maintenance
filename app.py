from chalice import Chalice, Cron, Rate
import boto3
from chalicelib.utils import get_regions
import datetime
import pytz
import sys
import os

GPU_TYPES = ["p3.2xlarge", "g4dn.2xlarge"]
SNAPSHOT_OLDER_THAN = os.environ["SNAPSHOT_OLDER_THAN"]
AMI_OLDER_THAN = os.environ["AMI_OLDER_THAN"]

app = Chalice(app_name="cost_maintenance")
app.debug = True


@app.schedule(Cron(0, 6, "*", "*", "?", "*"))
def start_instances(event):
    """Scheduled lambda function to start tagged instances"""
    REGIONS = get_regions()
    for region in REGIONS:
        ec2 = boto3.client("ec2", region_name=region)
        filters = [
            {"Name": "tag:AutoStopEnabled", "Values": ["True"]},
            {"Name": "instance-state-name", "Values": ["stopped"]},
        ]

        instances = ec2.describe_instances(Filters=filters)
        StoppedInstances = [instance for instance in instances["Reservations"]]
        ids = [i["Instances"][0]["InstanceId"] for i in StoppedInstances]
        types = [i["Instances"][0]["InstanceType"] for i in StoppedInstances]
        gpus = [gpu for gpu in types if gpu.startswith("p") or gpu.startswith("g")]
        app.log.info(gpus)
        if len(StoppedInstances) > 0:
            app.log.info("Starting Instances")
            startingUp = ec2.start_instances(InstanceIds=ids)
        else:
            app.log.error("No instances to start up")


@app.schedule(Cron(00, 20, "*", "*", "?", "*"))
def stop_instances(event):
    REGIONS = get_regions()
    for region in REGIONS:
        ec2 = boto3.client("ec2", region_name=region)
        filters = [
            {"Name": "tag:AutoStopEnabled", "Values": ["True"]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]

        instances = ec2.describe_instances(Filters=filters)
        RunningInstances = [instance for instance in instances["Reservations"]]
        ids = [i["Instances"][0]["InstanceId"] for i in RunningInstances]
        types = [i["Instances"][0]["InstanceType"] for i in RunningInstances]
        gpus = [gpu for gpu in types if gpu.startswith("p") or gpu.startswith("g")]
        app.log.info(gpus)
        # make sure there are actually instances to shut down.
        if len(RunningInstances) > 0:
            shuttingDown = ec2.stop_instances(InstanceIds=ids)
        else:
            app.log.error("No instances to shut down")
