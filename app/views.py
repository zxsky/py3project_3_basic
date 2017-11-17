from app import webapp
from flask import render_template

@webapp.route('/')
@webapp.route('/main')
@webapp.route('/index')
def main():
    return render_template("main.html")