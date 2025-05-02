"""
Example demonstrating how to use the Datasets v2 client.

To run this example, set your Autoblocks API key in the environment:
export AUTOBLOCKS_API_KEY=your_api_key_here
"""

import os
from autoblocks.datasets_v2 import (
    create_datasets_v2_client,
    CreateDatasetV2Request,
    StringProperty,
    ConversationProperty,
    Conversation,
    ConversationMessage,
    ConversationTurn,
    validate_conversation,
    CreateDatasetItemsV2Request
)

# Get the API key from environment variable
api_key = os.environ.get("AUTOBLOCKS_API_KEY")
if not api_key:
    print("Please set the AUTOBLOCKS_API_KEY environment variable")
    exit(1)

# Create the datasets v2 client
client = create_datasets_v2_client({
    "api_key": api_key,
    "app_slug": "your-app-slug"  # Replace with your app slug
})

def create_dataset_example():
    """Example of creating a dataset with schema"""
    dataset_request = CreateDatasetV2Request(
        name="Customer Support Conversations",
        description="Dataset containing customer support conversations with metadata",
        schema=[
            ConversationProperty(
                id="conversation",
                name="Conversation",
                required=True,
                roles=["customer", "agent"]
            ),
            StringProperty(
                id="customer_id",
                name="Customer ID",
                required=True
            ),
            StringProperty(
                id="category",
                name="Support Category",
                required=False
            )
        ]
    )
    
    # Create the dataset
    dataset = client.create(dataset_request)
    print(f"Created dataset: {dataset.name}")
    print(f"  ID: {dataset.id}")
    print(f"  External ID: {dataset.external_id}")
    
    return dataset.external_id


def add_items_example(dataset_external_id):
    """Example of adding items to a dataset"""
    # Create a conversation to add
    conversation_data = {
        "roles": ["customer", "agent"],
        "turns": [
            {
                "turn": 1,
                "messages": [
                    {
                        "role": "customer",
                        "content": "I'm having trouble logging into my account. Can you help?"
                    },
                    {
                        "role": "agent",
                        "content": "I'd be happy to help you with the login issue. Could you please provide your email address?"
                    }
                ]
            },
            {
                "turn": 2,
                "messages": [
                    {
                        "role": "customer",
                        "content": "My email is customer@example.com"
                    },
                    {
                        "role": "agent",
                        "content": "Thank you. I've sent a password reset link to your email. Please check your inbox."
                    }
                ]
            }
        ]
    }
    
    # Validate the conversation
    validation_result = validate_conversation(conversation_data)
    if not validation_result["valid"]:
        print(f"Conversation validation failed: {validation_result['message']}")
        return
    
    # Create item data
    items_request = CreateDatasetItemsV2Request(
        items=[
            {
                "conversation": conversation_data,
                "customer_id": "CUST-12345",
                "category": "login_issues"
            },
            {
                "conversation": {
                    "roles": ["customer", "agent"],
                    "turns": [
                        {
                            "turn": 1,
                            "messages": [
                                {
                                    "role": "customer",
                                    "content": "How do I update my billing information?"
                                },
                                {
                                    "role": "agent",
                                    "content": "You can update your billing information in the account settings page."
                                }
                            ]
                        }
                    ]
                },
                "customer_id": "CUST-67890",
                "category": "billing"
            }
        ],
        split_names=["training"]
    )
    
    # Add items to the dataset
    result = client.create_items(dataset_external_id, items_request)
    print(f"Added items to dataset: {result}")


def list_datasets_example():
    """Example of listing all datasets"""
    datasets = client.list()
    print(f"Found {len(datasets)} datasets:")
    
    for dataset in datasets:
        print(f"  {dataset.name} (ID: {dataset.id}, External ID: {dataset.external_id})")


def get_dataset_items_example(dataset_external_id):
    """Example of getting items from a dataset"""
    items_response = client.get_items(dataset_external_id)
    print(f"Dataset: {items_response.external_id}")
    print(f"Revision ID: {items_response.revision_id}")
    print(f"Schema Version: {items_response.schema_version}")
    print(f"Items count: {len(items_response.items)}")
    
    # Print details of the first item
    if items_response.items:
        first_item = items_response.items[0]
        print(f"\nFirst item:")
        print(f"  ID: {first_item.id}")
        print(f"  Splits: {', '.join(first_item.splits)}")
        print(f"  Data keys: {', '.join(first_item.data.keys())}")


if __name__ == "__main__":
    # Uncomment to run the examples
    
    # Create a new dataset
    # dataset_id = create_dataset_example()
    
    # Add items to the dataset
    # add_items_example(dataset_id)
    
    # List all datasets
    list_datasets_example()
    
    # Get items from a specific dataset (replace with your dataset ID)
    # get_dataset_items_example("your-dataset-external-id") 