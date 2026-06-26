import boto3
import json

QUARANTINE_SG_ID = "sg-077438ebfe44979ad"

ec2 = boto3.client("ec2")

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    detail = event.get("detail", {})
    finding_type = detail.get("type", "")
    instance_id = detail.get("resource", {}).get("instanceDetails", {}).get("instanceId")

    if not instance_id:
        print("No instance ID found in finding — nothing to remediate.")
        return {"status": "skipped", "reason": "no instance id"}

    print(f"Finding type: {finding_type} | Instance: {instance_id}")

    try:
        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[QUARANTINE_SG_ID]
        )
        print(f"Instance {instance_id} quarantined — security group swapped to {QUARANTINE_SG_ID}")
        return {"status": "remediated", "instance_id": instance_id, "finding_type": finding_type}
    except Exception as e:
        print(f"Remediation failed: {str(e)}")
        raise
