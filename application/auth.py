from flask import Blueprint, render_template, redirect, url_for
from flask import request, session, flash
from models import db, User, StudentProfile, CompanyProfile

auth_bp = Blueprint('auth', __name__)
