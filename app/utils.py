import boto3
from boto3.dynamodb.conditions import Key, Attr
import re
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def check_date_name(date):
    pass


def check_project_name(project):
    pass

def get_comments(projectname, username):
    fe = Key('comment_project').eq(projectname)
    pe = "#dt, comment_time, comment_content, comment_user"
    ean = {"#dt": "comment_project", }
    table = dynamodb.Table(username + "_comments")
    response = table.scan(
        FilterExpression=fe,
        ProjectionExpression=pe,
        ExpressionAttributeNames=ean
    )
    records = []
    for i in response['Items']:
        records.append(i)
    return records

def get_parameters_when_view_project_page(username, project_chosen):
    date_list = get_date_list_accord_project(username, project_chosen)
    content_list = []
    for date_chosen in date_list:
        table = dynamodb.Table(username + "_files")
        response = table.query(
            KeyConditionExpression=Key('user_date').eq(date_chosen) & Key('user_project').eq(project_chosen)
        )
        records = []
        for i in response['Items']:
            records.append(i)
        if records:
            # retrive the textarea since file do exist
            s3 = boto3.resource('s3')
            obj = s3.Object('mybucket4test', username + "/" + project_chosen + "/" + records[0]['project_filename'])
            textareaOns3 = obj.get()['Body'].read().decode('utf-8')
            content_list.append(textareaOns3)

    share_flag = check_if_share(username, project_chosen)
    return share_flag, date_list,content_list

def random_num():
    millis = int(round(time.time() * 1000000))
    return millis

def check_if_share(username, project_chosen):
    table = dynamodb.Table('users')
    response = table.get_item(
        Key={
            'username': username
        }
    )
    data = {}
    item = response['Item']
    data.update(item)
    project_share_list = data["project_share"]
    if project_chosen in project_share_list:
        return True
    else:
        return False

def get_project_list(username):
    table = dynamodb.Table('users')
    response = table.get_item(
        Key={
            'username': username
        }
    )
    data = {}
    item = response['Item']
    data.update(item)
    project_list = data["project_list"]
    return project_list

def get_shared_project_list(username):
    table = dynamodb.Table('users')
    response = table.get_item(
        Key={
            'username': username
        }
    )
    data = {}
    item = response['Item']
    data.update(item)
    project_list = data["project_share"]
    return project_list

def get_date_list(username):
    pe = "#dt, user_project, project_filename"
    ean = {"#dt": "user_date", }
    table = dynamodb.Table(username + "_files")
    response = table.scan(
        ProjectionExpression=pe,
        ExpressionAttributeNames=ean
    )
    records = []
    for i in response['Items']:
        records.append(i)
    date_list = []
    for i in range(len(records)):
        i_date = records[i]['user_date']
        if i_date not in date_list:
            date_list.append(i_date)
    return date_list

def get_date_list_accord_project(username, project_chosen):
    pe = "#dt, user_project, project_filename"
    ean = {"#dt": "user_date", }
    table = dynamodb.Table(username + "_files")
    response = table.scan(
        ProjectionExpression=pe,
        ExpressionAttributeNames=ean
    )
    records = []
    for i in response['Items']:
        records.append(i)
    date_list = []
    for i in range(len(records)):
        if records[i]['user_project'] == project_chosen:
            date_list.append(records[i]['user_date'])
    return date_list

def get_project_list_accord_date(username, date_chosen):
    pe = "user_date, #pj, project_filename"
    ean = {"#pj": "user_project", }
    table = dynamodb.Table(username + "_files")
    response = table.scan(
        ProjectionExpression=pe,
        ExpressionAttributeNames=ean
    )
    records = []
    for i in response['Items']:
        records.append(i)
    project_list = []
    for i in range(len(records)):
        if records[i]['user_date'] == date_chosen:
            project_list.append(records[i]['user_project'])
    return project_list


def fuzzyfinder(user_input, collection):
    suggestions = []
    pattern = '.*?'.join(user_input)  # Converts 'djm' to 'd.*?j.*?m'
    regex = re.compile(pattern)  # Compiles a regex.
    for item in collection:
        match = regex.search(item)  # Checks if the current item matches the regex.
        if match:
            suggestions.append((len(match.group()), match.start(), item))
    return [x for _, _, x in sorted(suggestions)]


def get_all_public_projects():
    table = dynamodb.Table('users')
    response = table.scan()
    item = response['Items']

    all_public_projects = {}
    for i in range(response['Count']):
        if 'project_share' in item[i]:
            if item[i]['project_share']!= []:
                all_public_projects.update({item[i]['username']:item[i]['project_share']})
    return all_public_projects

def get_all_users():
    table = dynamodb.Table('users')
    response = table.scan()
    item = response['Items']

    all_users = []
    for i in range(response['Count']):
        all_users.append(item[i]['username'])
    return all_users

def get_comments(projectname, username):
    fe = Key('comment_project').eq(projectname)
    pe = "#dt, comment_time, comment_content, comment_user"
    ean = {"#dt": "comment_project", }
    table = dynamodb.Table(username + "_comments")
    response = table.scan(
        FilterExpression=fe,
        ProjectionExpression=pe,
        ExpressionAttributeNames=ean
    )
    records = []
    for i in response['Items']:
        records.append(i)
    return records