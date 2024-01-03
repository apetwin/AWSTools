#!/usr/bin/python3

import asyncio
import aioboto3
import json
import argparse

# Function to read AWS profiles from inventory.ini
def read_aws_profiles(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# Function to read SSM Document content from JSON file
def read_ssm_document(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to deploy Document to a single AWS profile with semaphore
async def deploy_document(profile, document_content, document_name, document_os, semaphore):
    async with semaphore:
        session = aioboto3.Session(profile_name=profile)
        async with session.client('ssm') as ssm_client:
        try:
            await ssm_client.describe_document(Name=document_name)
            # Update the existing document
            response = await ssm_client.update_document(
                Name=document_name,
                Content=json.dumps(document_content),
                DocumentVersion='$LATEST',
                DocumentFormat='JSON',
                # Removed Description parameter
            )
            print(f"Document {document_name} updated in {profile}.")
        except ssm_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidDocument':
                # Create the document if it does not exist
                response = await ssm_client.create_document(
                    Name=document_name,
                    Content=json.dumps(document_content),
                    DocumentType='Command',
                    DocumentFormat='JSON',
                    # Removed Description parameter
                )
                print(f"Document {document_name} created in {profile}.")
            else:
                raise

            except Exception as e:
                print(f"Error processing document in {profile}: {e}")


# Main async function with semaphore
async def main(args):
    semaphore = asyncio.Semaphore(10)  # Adjust the concurrency limit as needed
    profiles = read_aws_profiles(args.profiles)
    document_content = read_ssm_document(args.document)
    document_name = args.document_name
    document_os = args.os  # This can be 'win', 'lin', or None (if not provided)

    tasks = []
    for profile in profiles:
        task = asyncio.create_task(deploy_document(profile, document_content, document_name, document_os, semaphore))
        tasks.append(task)

    await asyncio.gather(*tasks)
    print("AWS SSM Document Deployment completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy AWS SSM Document to multiple AWS accounts.")
    parser.add_argument("-p", "--profiles", required=True, help="Path to the profiles list file (inventory.ini)")
    parser.add_argument("-d", "--document", required=True, help="Path to the JSON file containing the SSM document")
    parser.add_argument("-D", "--document_name", required=True, help="Name of the SSM document to deploy")
    parser.add_argument("-o", "--os", choices=['win', 'lin'], help="Operating System type for the SSM document (win or lin), optional", default=None)

    args = parser.parse_args()
    asyncio.run(main(args))

# usage example:
# python ssm-doc-crud.py path/to/inventory.ini path/to/ExampleSSMDocument.json MySSMDocumentName

