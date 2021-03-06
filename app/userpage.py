from flask import request, render_template, redirect, url_for, flash, g, session

from app import webapp
from app.userforms import login_required, logout
from app.utils import get_date_list, get_project_list, get_date_list_accord_project,\
    get_project_list_accord_date, random_num, get_comments, get_parameters_when_view_project_page,\
    get_shared_project_list

from random import choice

import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


@webapp.route('/userpage/<username>', methods=['GET'])
@login_required
def profile(username):
    if session['username'] != username:
        logout()
        flash("You are not allowed to log into different accounts without logging out fist!", 'warning')
        return redirect(url_for('login'))

    #search all the projects and dates
    project_whole_list = get_project_list(username)
    date_whole_list_bug = get_date_list(username)

    #a stupid bug caused by the datepicker itself
    date_whole_list = []
    for date in date_whole_list_bug:
        if date[3] == '0':
            date = date[0:3] + date[4:]
        if date[0] == '0':
            date = date[1:]
        date_whole_list.append(date)

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
    # temp_1st_path = 'static/tmp_userfile/' + username
    # temp_2nd_path_toDel = os.path.join(ROOT_PATH, temp_1st_path)
    try:
        # create file path
        # if not os.path.isdir(os.path.join(ROOT_PATH, 'static/tmp_userfile/')):
        #     os.mkdir(os.path.join(ROOT_PATH, 'static/tmp_userfile/'))
        # if not os.path.isdir(temp_2nd_path_toDel):
        #     os.mkdir(temp_2nd_path_toDel)

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

        # #set local temp path
        # temp_file_with_path = "/".join([temp_2nd_path_toDel, filename])
        #
        # # save file in local
        # with open(temp_file_with_path, 'w') as outfile:
        #     package = request.args.get('textarea')
        #     outfile.write(package)
        #     outfile.close()

        # save file to s3
        filepath = username+"/"+project_chosen+"/"+filename
        content_body = request.args.get('textarea')
        s3_resource = boto3.resource('s3')
        s3 = s3_resource.Bucket("mybucket4test")
        s3.put_object(Key=filepath, Body=content_body)
        # s3_client.upload_file(temp_file_with_path, 'mybucket4test', username+"/"+project_chosen+"/"+filename)

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
        # shutil.rmtree(temp_2nd_path_toDel)

        flash("Your MarkDown file has been saved successfully", "success")
        return redirect(url_for('profile', username=username))

    except Exception as e:
        # if os.path.isdir(temp_2nd_path_toDel):
        #     shutil.rmtree(temp_2nd_path_toDel)
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

    share_flag, date_list, content_list= get_parameters_when_view_project_page(username, project_chosen)

    comment_list = get_comments(project_chosen, username)

    return render_template("/list_project.html", project = project_chosen, date_list = date_list, content_list = content_list, share_flag = share_flag , comment_list = comment_list)


@webapp.route('/addproject', methods=['GET', 'POST'])
@login_required
def addproject():
    project_chosen = request.args.get('newProjectName')
    username = session['username']
    if project_chosen == "":
        flash("Please enter a valid new project name!", "warning")
        return redirect(url_for('profile', username=username))

    if " " in project_chosen:
        flash("Please do not use space when create the name!", "warning")
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

    #delete from shared list if it is shared
    shared_list = get_shared_project_list(username)
    if project_chosen in shared_list:
        sharedtable = dynamodb.Table('users')
        shared_list.remove(project_chosen)
        if shared_list is None:
            shared_list = []
        response = sharedtable.update_item(
            Key={
                'username': username
            },
            UpdateExpression="SET project_share = :r",
            ExpressionAttributeValues={
                ':r': shared_list
            }
        )

    #delete comments
    comment_list = get_comments(project_chosen, username)
    if comment_list != []:
        dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
        for i in range(len(comment_list)):
            response = dynamodb_client.delete_item(
                Key={
                    'comment_project': {
                        'S': project_chosen,
                    },
                    'comment_time': {
                        'S': comment_list[i]['comment_time'],
                    },
                },
                TableName=username + "_comments",
            )


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