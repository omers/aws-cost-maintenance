from chalice import Chalice, Cron, Rate
import boto3


# REGIONS = ["us-east-1", "us-east-2", "eu-west-1"]
REGIONS = ["eu-central-1"]

app = Chalice(app_name="instance_schedueler")
app.debug = True


@app.schedule(Cron(0, 6, "*", "*", "?", "*"))
# @app.schedule(Rate(5, unit=Rate.MINUTES))
def start_instances(event):
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
        print(StoppedInstances)
        if len(StoppedInstances) > 0:
            # perform the shutdown
            app.log.info("Starting Instances")
            startingUp = ec2.start_instances(InstanceIds=ids)
        else:
            app.log.error("No instances to start up")


@app.schedule(Cron(00, 20, "*", "*", "?", "*"))
# @app.schedule(Rate(10, unit=Rate.MINUTES))
def stop_instances(event):
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
        print(RunningInstances)

        # make sure there are actually instances to shut down.
        if len(RunningInstances) > 0:
            # perform the shutdown
            shuttingDown = ec2.stop_instances(InstanceIds=ids)
            # print shuttingDown
        else:
            app.log.error("No instances to shut down")
