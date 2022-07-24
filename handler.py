import json
import os
from urllib import response
import requests

def add_task_to_notion(event, context):
    print(f':::EVENT_BODY_TYPE===> {type(event["body"])}')
    event_body = json.loads(event['body'])
    user_email = event_body["user"]["email"]
    contact_name = event_body["full_name"]
    task_body = event_body["task"].get("body","")
    contact_id = event_body["contact_id"]
    task_due_date = event_body["task"]["dueDate"]
    task_database_id = "e4ea055373df4cd79bfb190cd036d177"
    task_title = event_body["task"]["title"]
    
    notion_user_id = get_notion_user_id(user_email)

    children = create_notion_body_children(task_body, contact_name=contact_name, contact_id=contact_id)    

    response = create_notion_task(task_database_id, task_title, task_due_date, notion_user_id, children, notion_user_id)

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """

def get_notion_user_id(user_email):
    NOTION_SECRET = os.getenv("NOTION_SECRET")

    # Get All Users In Notion
    # Find Account Manager From Email Set In Webhook Call For User Email

    url = "https://api.notion.com/v1/users"

    headers = {
        "Authorization": f'Bearer {NOTION_SECRET}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-02-22'
    }

    response = requests.get(url, headers=headers)

    body = json.loads(response.text)

    results = body['results']

    notion_user = next((i for i in results if i['person']['email'] == user_email), None)

    # Return data for use in future steps
    return notion_user["id"]

def create_notion_body_children(task_body, contact_name, contact_id):
    contact_link = f'https://app.lasso.homes/v2/location/NHKutFUXViCWedCP4QIC/contacts/detail/{contact_id}'

    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": task_body
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": contact_name,
                            "link": {"url": contact_link}
                        }
                    }
                ]
            }
        }
    ]

    return children

def create_notion_task(task_database_id, event_title, event_start_date, assigner_id, children, assignee_id):
    NOTION_SECRET = os.getenv("NOTION_SECRET")
    task_url = "https://api.notion.com/v1/pages"

    task_headers = {
        "Authorization": f'Bearer {NOTION_SECRET}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-02-22'
    }
    
    task_body = {
      "parent": { "database_id": task_database_id},
      "icon": {
      	"emoji": "👥"
      },
    	"properties": {
    		"Name": {
    			"title": [
    				{
    					"text": {
    						"content": event_title
    					}
    				}
    			]
    		},
            "Status":
            {
                "select": {
                    "name": "Not Yet Started"
                }
            },
            "Start Date": { 
                "date": {
                    "start": event_start_date
                } 
            },
            "Assignee": {
                "people": [
                    {
                        "object": "user",
                        "id": assignee_id
                    }
                ]
            },
            "Reviewer": {
                "people": [
                    {
                        "object": "user",
                        "id": assigner_id
                    }
                ]
            }
    	},
        "children": children
    }
    
    task_body = json.dumps(task_body)
    
    task_response = requests.post(task_url, data=task_body, headers=task_headers)
    
    response_body = json.loads(task_response.text)
    response = {
        "statusCode": 200,
        "body": json.dumps(response_body)
    }

    return response