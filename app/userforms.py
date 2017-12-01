import time
from flask import Flask, request, render_template, redirect, url_for, flash, g, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo

from app import webapp
from werkzeug.security import generate_password_hash, check_password_hash

from functools import wraps

# import pymysql
# from config import db_config

import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

#create two forms object
class RegisterForm(FlaskForm):
    username = StringField('Username',
                validators=[DataRequired(message= 'Username can not be empty.'), Length(4, 16)])
    password = PasswordField('Enter Your Password',
                validators=[DataRequired(message= 'Password can not be empty.'),
                EqualTo('confirm', message='Passwords does not match')])
    confirm = PasswordField('Repeat the Password')
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
               DataRequired(message='Username can not be empty.'), Length(4, 16)])
    password = PasswordField('Password',
                validators=[DataRequired(message='Password can not be empty.')])
    submit = SubmitField('Login')


def login_required(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return func(*args, **kwargs)
        else:
            flash("You need to log in first!",'danger')
            return redirect(url_for('login'))
    return wrap

#  Helper Function: Verify Identity
def verify(username, password):
    table = dynamodb.Table('users')
    response = table.get_item(
        Key={
            'username': username
        }
    )

    # if cursor.fetchone() is None:
    if 'Item' not in response:
        return -1 #User does not exist
    else:
        data = {}
        item = response['Item']
        data.update(item)
        if not check_password_hash(data['password'], password):
            return 1 # Password doesn't match
        else:
            return 0


@webapp.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You are logged out!",'warning')
    return render_template("/main.html")


@webapp.route('/login', methods=['GET', 'POST'])
def login():
    # if(session['logged_in'] == True):
    #     return redirect(url_for('profile', username=session['username']))
    form = LoginForm()
    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        result = verify(username, password)
        if result == -1: #User does not exist
            flash("The username does not exist", 'warning')
            return render_template("/login_form.html", form=form)
        if result == 1: # password does not match
            flash("The password is wrong!", 'warning')
            return render_template("/login_form.html", form=form)

        if result == 0:
            flash("Login Success!", 'success')
            session['logged_in']= True
            session['username']= username
            return redirect(url_for('profile', username=username))
    return render_template("/login_form.html", form=form)


@webapp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        table = dynamodb.Table('users')
        response = table.get_item(
            Key={
                'username': username
            }
        )
        if 'Item' in response:
            flash("The username has been used already", 'warning')
            return render_template("/register_form.html", form=form)
        else:
            password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            response = table.put_item(
                Item={
                    'username': username,
                    'password' : password
                }
            )

            response = table.update_item(
                Key={
                    'username': username
                },
                UpdateExpression="set project_list = :r, project_share = :p",
                ExpressionAttributeValues={
                    ':r': [],
                    ':p': []
                }

            )

            createdtable = dynamodb.create_table(
                TableName=username+'_files',
                KeySchema=[
                    {
                        'AttributeName': 'user_project',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'user_date',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'user_date',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_project',
                        'AttributeType': 'S'
                    },

                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )

            createdtable = dynamodb.create_table(
                TableName=username + '_comments',
                KeySchema=[
                    {
                        'AttributeName': 'comment_project',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'comment_time',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'comment_project',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'comment_time',
                        'AttributeType': 'S'
                    },

                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )



            flash("Register Success!", 'success')
            session['logged_in'] = True
            session['username'] = username

            return render_template("/user_profile.html", username=username)
    return render_template("/register_form.html", form=form)

@webapp.errorhandler(404)
def page_not_found(e):
    return render_template("404_error.html")