import asyncio
import aioboto3
import json
import configparser
import argparse

# Function to read AWS profiles from inventory.ini
def read_aws_profiles(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# Function to read instance information from instances.json
def read_instances(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to retrieve command results for an instance
async def get_command_results(profile, instance_id):
    session = aioboto3.Session(profile_name=profile)
    async with session.client('ssm') as ssm_client:
        try:
            response = await ssm_client.list_commands(
                InstanceId=instance_id,
                MaxResults=5  # Adjust as needed
            )
            for command in response.get('Commands', []):
                print(f"Results for {instance_id} in {profile}: CommandId {command['CommandId']}, Status {command['Status']}")
        except Exception as e:
            print(f"Error retrieving command results for {instance_id} in {profile}: {e}")

# Main async function
async def main(args, semaphore=10):
    semaphore = asyncio.Semaphore(args.semaphore)
    profiles = read_aws_profiles(args.inventory)
    instances_info = read_instances(args.instances)

    tasks = []
    for profile in profiles:
        for instance in instances_info.get(profile, []):
            task = asyncio.create_task(retrieve_command_results(profile, instance, semaphore))
            tasks.append(task)

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve results of AWS SSM commands executed on instances across AWS accounts.")
    parser.add_argument("-p", "--profiles", required=True, help="Path to the inventory.ini file")
    parser.add_argument("-i" "--instances", required=True, help="Path to the JSON file containing instances information")
    parser.add_argument("-S", "--semaphore", required=False, default=10, help="Set concurrency limit")


    args = parser.parse_args()
    asyncio.run(main(args))
