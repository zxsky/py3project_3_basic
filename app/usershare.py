from flask import request, render_template, redirect, url_for, flash, session
from app import webapp
from app.userforms import login_required, logout
from app.userpage import get_date_list, get_project_list, \
    get_project_list_accord_date, get_date_list_accord_project, \
    check_if_share, get_parameters_when_view_project_page, get_shared_project_list

import boto3
from boto3.dynamodb.conditions import Key, Attr
import re
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


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


@webapp.route('/shareproject', methods=['GET', 'POST'])
@login_required
def shareproject():
    project_chosen = request.args.get('projectToShare')
    username = session['username']

    if project_chosen == "":
        return redirect(url_for('profile', username=session['username']))

    if project_chosen not in get_project_list(username):
        return redirect(url_for('profile', username=session['username']))

    #check if user has written anything. If no, refresh the page.
    date_list = get_date_list_accord_project(username, project_chosen)
    # if date_list == []:
    #     flash("You should at least write something first before sharing it!", 'warning')
    #     return redirect(url_for('profile', username=username))

    #check shared
    table = dynamodb.Table('users')

    shared_list = get_shared_project_list(username)

    if project_chosen in shared_list:
        render_template("/user_profile.html", username=username)
    else:
        response = table.update_item(
            Key={
                'username': username
            },
            UpdateExpression="SET project_share = list_append(project_share, :r)",
            ExpressionAttributeValues={
                ':r': [project_chosen]
            }
        )

        # same as viewproject function.
        share_flag, date_list, content_list = get_parameters_when_view_project_page(username, project_chosen)

        flash("You shared this project \"" + project_chosen +"\"", "success")
        return redirect(url_for('viewproject') + "?projectChosen=" + project_chosen)
        # return render_template("/list_project.html", project=project_chosen, date_list=date_list,
        #                        content_list=content_list,
        #                        share_flag= True)

@webapp.route('/donotshareproject', methods=['GET', 'POST'])
@login_required
def donotshareproject():
    project_chosen = request.args.get('projectToShare')
    username = session['username']

    if project_chosen == "":
        return redirect(url_for('profile', username=session['username']))

    if project_chosen not in get_project_list(username):
        return redirect(url_for('profile', username=session['username']))

    # check shared, delete it from the shared list
    table = dynamodb.Table('users')

    shared_list = get_shared_project_list(username)

    if project_chosen not in shared_list:
        render_template("/user_profile.html", username=username)
    else:

        shared_list.remove(project_chosen)

        if shared_list is None:
            shared_list = []

        response = table.update_item(
            Key={
                'username': username
            },
            UpdateExpression="SET project_share = :r",
            ExpressionAttributeValues={
                ':r': shared_list
            }
        )

        share_flag, date_list, content_list = get_parameters_when_view_project_page(username, project_chosen)

        flash("You make the project \"" + project_chosen +"\"private now", "success")
        # return render_template("/list_project.html", project=project_chosen, date_list=date_list,
        #                        content_list=content_list,
        #                        share_flag=False)
        return redirect(url_for('viewproject') + "?projectChosen=" + project_chosen)

@webapp.route('/searchProject', methods=['GET', 'POST'])
@login_required
def searchProject():
    project_chosen = request.args.get('projectToSearch')
    username = session['username']

    if project_chosen == "":
        return redirect(url_for('profile', username=username))

    if " " in project_chosen:
        flash("Please search one word for better results, since all project names are one word.", "warning")
        return redirect(url_for('profile', username=username))

    #get all public projects from all users
    all_users_public_projects = get_all_public_projects()

    #fuzzy find
    matched_projects = {}
    for key, value in all_users_public_projects.items():
        matched_per_user = fuzzyfinder(project_chosen, value)
        if matched_per_user != []:
            matched_projects.update({key : matched_per_user})

    return render_template("/search_result.html", outcome = matched_projects, project_chosen = project_chosen)



@webapp.route('/viewOthersProject', methods=['GET', 'POST'])
@login_required
def viewprojects_notowner():
    other_username = request.args.get('otheruser')
    other_project = request.args.get('otherproject')
    username = session['username']

    if other_username not in get_all_users():
        return redirect(url_for('profile', username=username))

    if other_project not in get_all_public_projects().get(other_username):
        return redirect(url_for('profile', username=username))

    share_flag, date_list, content_list = get_parameters_when_view_project_page(other_username, other_project)

    comment_list = get_comments(other_project, other_username)

    return render_template("/list_project_notowner.html", project=other_project, date_list=date_list,
                           content_list=content_list, otherusername = other_username, comment_list = comment_list)


@webapp.route('/addComment', methods=['GET', 'POST'])
@login_required
def addComment():
    comment_content = request.args.get('newComment')
    other_username = request.args.get('otheruser')
    other_project = request.args.get('otherproject')
    username = session['username']

    # comment_list = get_comments(other_project, other_username)
    # print(comment_list)
    # return

    # comment_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    comment_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

    table = dynamodb.Table(other_username + "_comments")
    response = table.put_item(
        Item={
            'comment_project': other_project,
            'comment_time': comment_time,
            'comment_content' : comment_content,
            'comment_user' : username
        }
    )

    # share_flag, date_list, content_list = get_parameters_when_view_project_page(other_username, other_project)
    #
    # comment_list = get_comments(other_project, other_username)

    return redirect( url_for('viewprojects_notowner') + "?otheruser=" + other_username + "&otherproject=" +other_project)
