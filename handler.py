import json
import os
from urllib import response
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def add_task_to_notion(event, context):
    logger.info(f"Incoming Event ==> {event}")
    event_body = json.loads(event['body'])
    user = event_body.get('user', "")
    if user:
        user_email = user["email"]
    contact_name = event_body["full_name"]
    task_body = event_body["task"].get("body","")
    contact_id = event_body["contact_id"]
    task_due_date = event_body["task"]["dueDate"]
    task_database_id = "e4ea055373df4cd79bfb190cd036d177"
    task_title = event_body["task"]["title"]
    location_id = event_body["location"]["id"]

    agency_api_key = os.getenv("GHL_AGENCY_API_KEY")
    
    logger.info("Getting Assignee Email")
    user_email_task = get_assignee_email(location_id, agency_api_key, contact_id, task_title)

    # set user email to assignee email if there is an assignee for the task, else use contact user email
    user_email = user_email_task if user_email_task else user_email
    
    logger.info(f"Called get_notion_user_id with user_email {user_email}")
    notion_user_id = get_notion_user_id(user_email)

    logger.info(f"Called create_notion_body_children")
    children = create_notion_body_children(task_body, contact_name=contact_name, contact_id=contact_id, location_id=location_id)

    logger.info(f"Called create_notion_task")
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

def get_assignee_email(location_id, agency_api_key, contact_id, task_title):
    # get go high level location api key
    location_api_key_url = f"https://rest.gohighlevel.com/v1/locations/{location_id}"
    headers = {
        "Authorization": f"Bearer {agency_api_key}",
    }

    location_response = requests.get(location_api_key_url, headers=headers)
    location_response = json.loads(location_response.text)

    location_api_key = location_response["apiKey"]
    # get all tasks for contact id
    get_tasks_api_url = f"https://rest.gohighlevel.com/v1/contacts/{contact_id}/tasks"

    headers = {
        "Authorization": f"Bearer {location_api_key}",
    }

    task_response = requests.get(get_tasks_api_url, headers=headers)
    task_response = json.loads(task_response.text)

    tasks = task_response.get("tasks", [])

    # match task title to current task title
    filtered_tasks = filter(lambda x: x["title"] == task_title, tasks)

    task = list(filtered_tasks)[0]

    user_id = task.get("assignedTo", "")

    # get ghl user info
    get_user_url = f"https://rest.gohighlevel.com/v1/users/{user_id}"

    headers = {
        "Authorization": f"Bearer {agency_api_key}",
    }

    user_response = requests.get(get_user_url, headers=headers)
    user_response = json.loads(user_response.text)

    email = user_response.get("email", "")

    # return email
    return email
    



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
    logger.info(f"Response Body ==> {body}")

    results = body['results']
    results_people = list((x for x in results if 'person' in x.keys()))

    notion_user = next((i for i in results_people if i['person']['email'] == user_email), None)
    if notion_user is None:
        notion_user = next((i for i in results_people if i['person']['email'] == 'george@volumeup.agency'), None)

    logger.info(f"NOTION USER :==> {notion_user}")
    # Return data for use in future steps
    return notion_user["id"]

def create_notion_body_children(task_body, contact_name, contact_id, location_id):
    contact_link = f'https://app.lasso.homes/v2/location/{location_id}/contacts/detail/{contact_id}'

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

    logger.info(f"NOTION BODY CHILDREN :==> {children}")
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

    logger.info(f"NOTION TASK RESPONSE :==> {response}")

    return response