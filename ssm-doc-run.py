#!/usr/bin/python3

import asyncio
import aioboto3
import json
import argparse

# Function to read AWS profiles from inventory.ini
def read_aws_profiles(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# Function to read instance information from instances.json
def read_instances(file_path):
    if file_path:
        with open(file_path, 'r') as file:
            return json.load(file)
    return None

# Function to execute SSM document on an instance
async def execute_document_on_instance(profile, instance_id, document_name, semaphore):
    session = aioboto3.Session(profile_name=profile)
    async with session.client('ssm') as ssm_client:
        try:
            response = await ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Comment=f"Executing {document_name} on {instance_id}"
            )
            print(f"Command sent to {instance_id} in {profile}: {response['Command']['CommandId']}")
        except Exception as e:
            print(f"Error executing document on {instance_id} in {profile}: {e}")

# Function to execute SSM document on all instances based on OS type
async def execute_document_on_all_instances(profile, document_name, os_type, semaphore):
    async with semaphore:
        session = aioboto3.Session(profile_name=profile)
        async with session.client('ec2') as ec2_client:
            # List all EC2 instances
            reservations = await ec2_client.describe_instances()
            instances = [instance for reservation in reservations['Reservations'] for instance in reservation['Instances']]
            
            # Filter instances by OS type if specified
            if os_type:
                if os_type == 'win':
                    instances = [instance for instance in instances if 'windows' in instance.get('Platform', '').lower()]
                elif os_type == 'lin':
                    instances = [instance for instance in instances if instance.get('Platform', '').lower() != 'windows']

            # Execute the SSM document on each instance
            for instance in instances:
                instance_id = instance['InstanceId']
                async with session.client('ssm') as ssm_client:
                    try:
                        response = await ssm_client.send_command(
                            InstanceIds=[instance_id],
                            DocumentName=document_name,
                            Comment=f"Executing {document_name} on {instance_id}"
                        )
                        print(f"Command sent to {instance_id} in {profile}: {response['Command']['CommandId']}")
                    except Exception as e:
                        print(f"Error executing document on {instance_id} in {profile}: {e}")

# Main async function
async def main(args):
    semaphore = asyncio.Semaphore(10)  # Concurrency limit
    profiles = read_aws_profiles(args.profiles)
    instances_info = read_instances(args.instances_json) if args.instances_json else None
    document_name = args.document_name
    os_type = args.os  # Can be 'win', 'lin', or None

    tasks = []
    for profile in profiles:
        if instances_info and profile in instances_info:
            for instance_id in instances_info[profile]:
                task = asyncio.create_task(execute_document_on_instance(profile, instance_id, document_name, semaphore))
                tasks.append(task)
        else:
            # Execute on all instances if no specific instances are provided
            task = asyncio.create_task(execute_document_on_all_instances(profile, document_name, os_type, semaphore))
            tasks.append(task)

    await asyncio.gather(*tasks)
    print("AWS SSM Document Execution completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute AWS SSM Document on instances across AWS accounts.")
    parser.add_argument("-p", "--profiles", required=True, help="Path to the inventory.ini file")
    parser.add_argument("-d", "--document_name", required=True, help="Name of the SSM document to execute")
    parser.add_argument("-i", "--instances_json", help="Path to the JSON file containing instances information (optional)")
    parser.add_argument("-o", "--os", choices=['win', 'lin'], help="Operating System type for executing the SSM document (optional)", default=None)

    args = parser.parse_args()
    asyncio.run(main(args))

# usage:
# ssm-doc-run.py path/to/inventory.ini path/to/instances.json MySSMDocument