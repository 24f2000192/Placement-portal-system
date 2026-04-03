from flask import Blueprint, render_template, redirect, url_for, session
from jinja2 import Template
from models import CompanyProfile

# Create a Blueprint named 'admin'
# All route names will be 'admin.dashboard', 'admin.students', etc.
admin_bp = Blueprint('admin', __name__)

# A ROUTE in this blueprint
