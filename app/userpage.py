from flask import request, render_template, redirect, url_for, flash, g, session

from app import webapp
from app.userforms import login_required, logout

# from werkzeug.utils import secure_filename

import os
import shutil
import time, datetime
from random import choice

import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))


def check_date_name(date):
    pass


def check_project_name(project):
    pass

def random_num():
    millis = int(round(time.time() * 1000000))
    return millis


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



@webapp.route('/userpage/<username>', methods=['GET'])
@login_required
def profile(username):
    if session['username'] != username:
        logout()
        flash("You are not allowed to log into different accounts without logging out fist!", 'warning')
        return redirect(url_for('login'))

    #search all the projects and dates
    project_whole_list = get_project_list(username)
    date_whole_list = get_date_list(username)

    #diaplay a random project's latest work
    if project_whole_list != []:
        project_chosen = choice(project_whole_list)
        # textareaOns3 = ""
        date_list = get_date_list_accord_project(username, project_chosen)
        if date_list != []:
            date_chosen = choice(date_list)
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
                textareaOns3 = obj.get()['Body'].read().decode('utf-8').rstrip()
                lines = [line for line in textareaOns3.split('\r\n')]
                textareaOns3 = "\\n".join(lines)
                return render_template("/user_profile.html", OLDtextarea=textareaOns3, username=username,
                                       project_list=project_whole_list, date_list = date_whole_list,
                                       project_chosen = project_chosen, date_chosen = date_chosen)
            else:
                return render_template("/user_profile.html", username=username,
                                       date_list=date_whole_list, project_list = project_whole_list, project_chosen = project_chosen)
        else:
            return render_template("/user_profile.html", username=username,
                                   date_list=date_whole_list, project_list = project_whole_list, project_chosen = project_chosen)
    else:
        return render_template("/user_profile.html", username=username,
                               date_list=date_whole_list, project_list = project_whole_list)


# @webapp.route('/edit', methods=['GET', 'POST'])
# @login_required
# def edit():
#     username = session['username']
#     project_list = get_project_list(username)
#     return render_template("/editMdFile.html", project_list = project_list)


# @webapp.route('/choose_before_editing', methods=['GET', 'POST'])
# @login_required
# def choose_before_editing():
#     username = session['username']
#     project_list = get_project_list(username)
#     if project_list == []:
#         flash("You don't have any project yet, create one first!", "warning")
#         return redirect(url_for('profile', username=username))
#     return render_template("/editMdFile_choose.html", project_list = project_list)


@webapp.route('/editFile', methods=['GET', 'POST'])
@login_required
def checkExist():
    username = session['username']
    project_list = get_project_list(username)
    if project_list == []:
        flash("You don't have any project yet, create one first!", "warning")
        return redirect(url_for('profile', username=username))

    #get user input
    date_chosen = request.args.get('dateChosen')
    project_chosen = request.args.get('projectChosen')
    #TODO: check these two names with functions

    #refresh the page if no data sent
    if date_chosen == "" or project_chosen == "":
        flash("Please choose the date and name first", "warning")
        return redirect(url_for('profile', username=username))

    #check if user typed the wrong project intentionally
    #todo
    if project_chosen not in project_list:
        return render_template("404_error.html")

    #check if file already exists by reading data from DB
    table = dynamodb.Table(username + "_files")
    response = table.query(
        KeyConditionExpression=Key('user_date').eq(date_chosen) & Key('user_project').eq(project_chosen)
    )
    records = []
    for i in response['Items']:
        records.append(i)
    if records:
        #retrive the textarea since file do exist
        s3 = boto3.resource('s3')
        obj = s3.Object('mybucket4test', username+"/"+project_chosen+"/"+records[0]['project_filename'])
        textareaOns3 = obj.get()['Body'].read().decode('utf-8').rstrip()
        lines = [line for line in textareaOns3.split('\r\n')]
        textareaOns3 = "\\n".join(lines)
        # date_chosen.replace('_','/')
        flash("Your history content has been retrieved.", "success")
        return render_template("/editMdFile.html", OLDtextarea = textareaOns3, project_name = project_chosen, project_date = date_chosen)
    else:
        #file do not exist, check textarea is not null
        # textarea = request.args.get('textarea')
        # if textarea == "":
        # date_chosen.replace('_', '\/')
        # print(date_chosen)
        flash("No record. Start editing!", "success")
        return render_template("/editMdFile.html", project_name=project_chosen,  project_date = date_chosen)


@webapp.route('/savework', methods=['GET', 'POST'])
@login_required
def savework():
    date_chosen = request.args.get('dateChosen')
    project_chosen = request.args.get('projectChosen')
    # TODO: check these two names with functions

    username = session['username']
    #textarea is not null, which means this is a new file which should be put in DB and S3.
    temp_1st_path = 'static/tmp_userfile/' + username
    temp_2nd_path_toDel = os.path.join(ROOT_PATH, temp_1st_path)
    try:
        # create file path
        if not os.path.isdir(os.path.join(ROOT_PATH, 'static/tmp_userfile/')):
            os.mkdir(os.path.join(ROOT_PATH, 'static/tmp_userfile/'))
        if not os.path.isdir(temp_2nd_path_toDel):
            os.mkdir(temp_2nd_path_toDel)

        #get file name
        table = dynamodb.Table(username + "_files")
        response = table.query(
            KeyConditionExpression=Key('user_date').eq(date_chosen) & Key('user_project').eq(project_chosen)
        )
        records = []
        for i in response['Items']:
            records.append(i)
        if records:
            filename = records[0]['project_filename']
        else:
            filename = username + str(random_num()) + '.md'

        #set local temp path
        temp_file_with_path = "/".join([temp_2nd_path_toDel, filename])

        # save file in local
        with open(temp_file_with_path, 'w') as outfile:
            package = request.args.get('textarea')
            outfile.write(package)
            outfile.close()

        # save file to s3
        s3_client = boto3.client('s3')
        s3_client.upload_file(temp_file_with_path, 'mybucket4test', username+"/"+project_chosen+"/"+filename)

        # save database
        table = dynamodb.Table(username + "_files")
        response = table.put_item(
            Item={
                'user_date': date_chosen,
                'user_project' : project_chosen,
                'project_filename' : filename
            }
        )

        # delete tmp file
        shutil.rmtree(temp_2nd_path_toDel)

        flash("Your MarkDown file has been saved successfully", "success")
        return redirect(url_for('profile', username=username))

    except Exception as e:
        if os.path.isdir(temp_2nd_path_toDel):
            shutil.rmtree(temp_2nd_path_toDel)
        return str(e)



@webapp.route('/viewdate', methods=['GET', 'POST'])
@login_required
def viewdate():
    date_chosen = request.args.get('dateChosen')
    username = session['username']

    if date_chosen == "":
        return redirect(url_for('profile', username=session['username']))

    if date_chosen not in get_date_list(username):
        return redirect(url_for('profile', username=session['username']))

    project_list = get_project_list_accord_date(username, date_chosen)
    if project_list == []:
        flash("You have not written anything on " + date_chosen, "warning")
        return redirect(url_for('profile', username=session['username']))

    content_list = []
    for project_chosen in project_list:
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


    return render_template("/list_date.html", date = date_chosen, project_list = project_list, content_list = content_list)


@webapp.route('/viewproject', methods=['GET', 'POST'])
@login_required
def viewproject():
    project_chosen = request.args.get('projectChosen')
    username = session['username']

    if project_chosen == "":
        return redirect(url_for('profile', username=session['username']))

    if project_chosen not in get_project_list(username):
        return redirect(url_for('profile', username=session['username']))

    date_list = get_date_list_accord_project(username, project_chosen)
    # if date_list == []:
    #     flash("You have not written anything related to " + project_chosen +" project","warning")
    #     return redirect(url_for('profile', username=session['username']))
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

    return render_template("/list_project.html", project = project_chosen, date_list = date_list, content_list = content_list)


# @webapp.route('/updatework', methods=['GET', 'POST'])
# @login_required
# def updatework():
#
#     flash("Your MarkDown file has been saved successfully", "success")
#     return redirect(url_for('profile', username=session['username']))


@webapp.route('/addproject', methods=['GET', 'POST'])
@login_required
def addproject():
    project_chosen = request.args.get('newProjectName')
    username = session['username']
    if project_chosen == "":
        flash("Please enter a valid new project name!", "warning")
        return redirect(url_for('profile', username=username))

    #check if projectname exists
    table = dynamodb.Table('users')
    response = table.get_item(
        Key={
            'username': username
        }
    )
    data = {}
    item = response['Item']
    data.update(item)

    if "project_list" not in data.keys():
        response = table.update_item(
            Key={
                'username': username
            },
            UpdateExpression="set project_list = :r",
            ExpressionAttributeValues={
                ':r': [project_chosen]
            }

        )
        flash("You have created the \"" + project_chosen + "\" project", "success")
        return redirect(url_for('profile', username=username))
    if project_chosen in data['project_list']:
       flash("You have used this project name \"" + project_chosen + "\", please choose another one.", "warning")
       return redirect(url_for('profile', username=username))
    else:
        response = table.update_item(
            Key={
                'username' : username
            },
            UpdateExpression="SET project_list = list_append(project_list, :r)",
            ExpressionAttributeValues={
                ':r': [project_chosen]
            }
        )
        flash("You have created the \"" + project_chosen + "\" project", "success")
        return redirect(url_for('profile', username=username))


@webapp.route('/deleteproject', methods=['GET', 'POST'])
@login_required
def deleteproject():
    project_chosen = request.args.get('projectToDel')
    username = session['username']

    if project_chosen == "":
        flash("Please select one first before delete project", "warning")
        return redirect(url_for('profile', username=username))

    #remvoe db project record
    date_list = get_date_list_accord_project(username, project_chosen)
    if date_list !=[]:
        dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
        for i in range(len(date_list)):
            response = dynamodb_client.delete_item(
                Key={
                    'user_project': {
                        'S': project_chosen,
                    },
                    'user_date': {
                        'S': date_list[i],
                    },
                },
                TableName= username + "_files",
            )

    #remove s3 files
    s3 = boto3.resource('s3')
    objects_to_delete = s3.meta.client.list_objects(Bucket="mybucket4test", Prefix=username + "/" + project_chosen +"/")
    delete_keys = {'Objects': []}
    delete_keys['Objects'] = [{'Key': k} for k in [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]
    if delete_keys['Objects'] != [] :
        s3.meta.client.delete_objects(Bucket="mybucket4test", Delete=delete_keys)

    # get original list
    project_list = get_project_list(username)
    #remove the item
    project_list.remove(project_chosen)
    #update the list
    table = dynamodb.Table('users')
    response = table.update_item(
        Key={
            'username': username
        },
        UpdateExpression="SET project_list = :r",
        ExpressionAttributeValues={
            ':r': project_list
        }
    )

    flash("You have removed the \"" + project_chosen + "\" project", "success")
    return redirect(url_for('profile', username=username))