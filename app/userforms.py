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


#database related functions
# def setup_DB():
#     return pymysql.connect(host=db_config['host'],
#                port=3306,
#                user=db_config['user'],
#                password=db_config['password'],
#                db=db_config['database'])
#
# def connect_DB():
#     db = getattr(g, '_database', None)
#     if db is None:
#         db = g._database = setup_DB()
#     return db
#
#
# #close the database when the website is closed
# @webapp.teardown_appcontext
# def close_DB(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         if db.open:
#             db.close()


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
    # cnx = connect_DB()
    # cursor = cnx.cursor()
    # query = '''SELECT * FROM user WHERE username = %s'''
    # cursor.execute(query, (username,))
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
        #
        # query = '''SELECT password FROM user WHERE username = %s'''
        # cursor.execute(query, (username,))
        # myenPassWord = cursor.fetchone()
        data = {}
        item = response['Item']
        data.update(item)
        # print(type(data['Password']))
        # if not data['Password']==password:
        if not check_password_hash(data['password'], password):
            # query = '''SELECT * FROM user WHERE username = %s AND password = %s'''
            # cursor.execute(query, (username, password))
            # if cursor.fetchone() is None:
            
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
                UpdateExpression="set project_list = :r",
                ExpressionAttributeValues={
                    ':r': []
                }

            )

            createdtable = dynamodb.create_table(
                TableName=username+'_files',
                KeySchema=[
                    {
                        'AttributeName': 'user_date',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'user_project',
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



            flash("Register Success!", 'success')
            session['logged_in'] = True
            session['username'] = username
            time.sleep(10)
            return redirect(url_for('profile', username=username))
    return render_template("/register_form.html", form=form)

@webapp.errorhandler(404)
def page_not_found(e):
    return render_template("404_error.html")