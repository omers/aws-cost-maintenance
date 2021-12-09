from chalice import Chalice, Cron, Rate
import boto3
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#REGIONS = ["us-east-1", "us-east-2", "eu-west-1"]
REGIONS = ["eu-central-1"]

app = Chalice(app_name='instance_schedueler')

#@app.schedule(Cron(0, 8, '*', '*', '?', '*'))
@app.schedule(Rate(5, unit=Rate.MINUTES))
def start_instances(event):
   for region in REGIONS:
       ec2 = boto3.client('ec2', region_name=region)
       filters = [
                 {
                'Name': 'tag:AutoStopEnabled',
                'Values': ['True']
            },
            {
                'Name': 'instance-state-name',
                'Values': ['stopped']
            }
        ]
     
     
       instances = ec2.describe_instances(Filters=filters)
       StoppedInstances = [instance for instance in instances['Reservations']]
       ids = [i['Instances'][0]['InstanceId'] for i in StoppedInstances]     
       print(StoppedInstances)
       if len(StoppedInstances) > 0:
            #perform the shutdown
            app.log.info("Starting Instances")
            startingup = ec2.start_instances(InstanceIds=ids)
       else:
        app.log.error("No instances to start up")

#@app.schedule(Cron(00, 22, '*', '*', '?', '*'))
@app.schedule(Rate(10, unit=Rate.MINUTES))
def stop_instances(event):
   for region in REGIONS:
       ec2 = boto3.client('ec2', region_name=region)
       filters = [
                 {
                'Name': 'tag:AutoStopEnabled',
                'Values': ['True']
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
     
     
       instances = ec2.describe_instances(Filters=filters)
       RunningInstances = [instance for instance in instances['Reservations']]
       ids = [i['Instances'][0]['InstanceId'] for i in RunningInstances]     
       print(RunningInstances)
     
        #make sure there are actually instances to shut down.
       if len(RunningInstances) > 0:
            #perform the shutdown
            shuttingDown = ec2.stop_instances(InstanceIds=ids)
            #print shuttingDown
       else:
            app.log.error("No instances to shut down")
