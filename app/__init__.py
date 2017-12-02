from flask import Flask

webapp = Flask(__name__)

webapp.config['SECRET_KEY'] = 'this is a secret string hard to guess'
webapp.config['S3ID'] = 'tests3yong'

from app import views
from app import userforms
from app import userpage
from app import utils
from app import usershare