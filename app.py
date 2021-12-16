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


@app.schedule(Cron(00, 20, "*", "*", "?", "*"))
def delete_old_amis(event):
    present = datetime.datetime.now().replace(tzinfo=utc) - datetime.timedelta(
        AMY_OLDER_THAN
    )
    REGIONS = get_regions()
    for region in REGIONS:
        client = boto3.client("ec2", region_name=region)
        amis = client.describe_images(Owners=["self"])
        for ami in amis["Images"]:
            create_date = datetime.datetime.strptime(
                ami["CreationDate"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=utc)
            if create_date < present:
                ami_id = ami["ImageId"]
                print(ami_id, create_date)


@app.schedule(Cron(00, 20, "*", "*", "?", "*"))
def delete_old_snapshots(event):
    REGIONS = get_regions()
    utc = pytz.UTC
    for region in REGIONS:
        present = datetime.datetime.now().replace(tzinfo=utc) - datetime.timedelta(512)
        client = boto3.client("ec2", region_name=region)
        snapshots = client.describe_snapshots(OwnerIds=["self"])
        ids = [
            snapshot["SnapshotId"]
            for snapshot in snapshots["Snapshots"]
            if snapshot["StartTime"].replace(tzinfo=utc) < present
        ]
        print(ids)
        # sys.exit(0)
        for snapshotid in ids:
            try:
                delete = client.delete_snapshot(SnapshotId=snapshotid)
                print("deleting this snapshot {}".format(snapshotid))

            except Exception as e:
                if "is currently in use by" in str(e):
                    print("skipping this snapshot {}".format(snapshotid))
                    continue


@app.route("/list_instances")
def spots_vs_on_demand():
    REGIONS = get_regions()
    resp = {}
    for region in REGIONS:
        ec2 = boto3.client("ec2", region_name=region)
        filters = [
            {"Name": "instance-state-name", "Values": ["running"]},
            {"Name": "instance-type", "Values": GPU_TYPES},
        ]
        instances = ec2.describe_instances(Filters=filters).get("Reservations")
        spots = ec2.describe_spot_instance_requests()
        if not instances:
            continue
        else:
            for reservation in instances:
                for instance in reservation["Instances"]:
                    continue
            resp[region] = len(instances)
        running_spots = [
            spot
            for spot in spots["SpotInstanceRequests"]
            if spot["State"] == "active"
            and spot["LaunchSpecification"]["InstanceType"] in GPU_TYPES
        ]
    return resp
