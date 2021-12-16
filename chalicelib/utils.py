import boto3


def get_regions():
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.describe_regions()
    REGIONS = [region["RegionName"] for region in resp["Regions"]]
    return REGIONS
