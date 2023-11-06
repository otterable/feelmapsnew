from flask_caching import Cache
from flask_cors import CORS
from flask import Flask, Flask, render_template, request, jsonify, Response, session, redirect, url_for, send_from_directory, make_response, before_first_request
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from collections import Counter
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from datetime import datetime

import json
import os
import re
import time
import sqlite3
import pyotp  # Importing pyotp for 2FA
import random
import string
from datetime import timedelta
app = Flask(__name__)
app.secret_key = 'ZDlGoz5V4/CWj+OGx8h2vQ=='  # You should use a secure, random secret key.
CORS(app)  # This is to allow cross-origin requests, if needed.

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mapobjects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class MapObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    geocoordinates = db.Column(db.String(100))
    time_of_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    written_note = db.Column(db.Text, nullable=False)
    categoryid = db.Column(db.Integer, nullable=False)
    hexColor = db.Column(db.String(6), nullable=False)
    molenId = db.Column(db.String(20), nullable=False, unique=True)
    objectId = db.Column(db.Integer, nullable=False)
    highlightId = db.Column(db.Integer, nullable=False)

    def to_json(self):
        return {
            'id': self.id,
            'geocoordinates': self.geocoordinates,
            'time_of_creation': self.time_of_creation.isoformat(),
            'written_note': self.written_note,
            'categoryid': self.categoryid,
            'hexColor': self.hexColor,
            'molenId': self.molenId,
            'objectId': self.objectId,
            'highlightId': self.highlightId
        }

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/save_object', methods=['POST'])
def save_object():
    data = request.json
    map_object = MapObject(
        geocoordinates=data['geocoordinates'],
        written_note=data['written_note'],
        categoryid=data['categoryid'],
        hexColor=data['hexColor'],
        molenId=data['molenId'],
        objectId=data['objectId'],
        highlightId=data['highlightId']
    )
    db.session.add(map_object)
    db.session.commit()
    return jsonify({'message': 'Object saved successfully', 'id': map_object.id}), 201

@app.route('/get_objects', methods=['GET'])
def get_objects():
    objects = MapObject.query.all()
    return jsonify([obj.to_json() for obj in objects])
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/categories')
def categories():
    return send_from_directory('.', 'static/categories.html')


# Hardcoded user credentials and OTP secret
USER_CREDENTIALS = {
    'username': 'stimmungskarte',
    'password': 'techdemo',
}
OTP_SECRET = 'MangoOttersLove'

@app.route('/login', methods=['POST'])
def login():
    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    otp_token = request.form.get('otp')
    
    # Validate username and password
    if username == USER_CREDENTIALS['username'] and password == USER_CREDENTIALS['password']:
        # Validate OTP token
        totp = pyotp.TOTP(OTP_SECRET)
        if totp.verify(otp_token):
            session['logged_in'] = True  # Set the session as logged in
            app.logger.info('User logged in successfully.')
            return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
        else:
            return jsonify({'status': 'failed', 'message': 'Incorrect OTP. Please contact your administrator.'}), 401
    else:
        return jsonify({'status': 'failed', 'message': 'Invalid credentials'}), 401


@app.route('/is-authenticated', methods=['GET'])
def is_authenticated():
    # Check if 'logged_in' key is in the session and if it's True
    if 'logged_in' in session and session['logged_in']:
        return jsonify({'isAuthenticated': True}), 200
    else:
        return jsonify({'isAuthenticated': False}), 401


@app.route('/admintools')
def admintools():
    app.logger.info(f'Logged in: {session.get("logged_in")}')
    if session.get('logged_in'):
        # If the user is logged in, serve the admintools.html content
        return send_from_directory('.', 'admintools.html')
    else:
        # If the user is not logged in, return an error or redirect to login
        return jsonify({'status': 'failed', 'message': 'Unauthorized access'}), 401
 


# OVERLAY IMAGE REPLACEMENT (TITELBILD) START
@app.route('/upload_overlay', methods=['GET'])
def upload_overlay():
    return render_template('upload.html')

@app.route('/upload_overlay_image', methods=['POST'])
def upload_overlay_image():
    file = request.files['file']
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, 'static', 'overlay.jpg'))
        return redirect(url_for('index'))  # Redirect to home page after successful upload
    return "File upload failed!", 400
# OVERLAY IMAGE REPLACEMENT (TITELBILD) END



# RENAMING LOGIC BACKEND START
@app.route('/get-categories-renaming', methods=['GET'])
def get_categories_renaming():
    # Read the static/categories.html file
    with open('static/categories.html', 'r', encoding='utf-8') as file:
        categories_html_content = file.read()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(categories_html_content, 'html.parser')

    # Extract category names from all <h3> tags within .categorybutton divs
    category_names = [h3.get_text().strip() for h3 in soup.select('.categorybutton h3')]

    # Return the list of category names as a JSON response
    return jsonify(category_names)

@app.route('/rename-category', methods=['POST'])
def rename_category():
    data = request.get_json()
    old_name = data['oldName']
    new_name = data['newName']

    # Read the static/categories.html file
    with open('static/categories.html', 'r+', encoding='utf-8') as file:
        categories_html_content = file.read()
        soup = BeautifulSoup(categories_html_content, 'html.parser')

        # Find the category to rename
        category_to_rename = soup.find('h3', text=old_name)
        if category_to_rename:
            category_to_rename.string = new_name
            # Write the changes back to the file
            file.seek(0)
            file.write(str(soup))
            file.truncate()

            return 'Category renamed successfully', 200
        else:
            return 'Category not found', 404
# RENAMING LOGIC BACKEND END



# RECOLORING LOGIC BACKEND START
@app.route('/recolor-category', methods=['POST'])
def recolor_category():
    data = request.get_json()
    category_name = data['categoryName']
    new_color = data['newColor']

    # Ensure the new color has the '#' symbol for valid CSS hex color
    css_color = f"#{new_color}"

    # Update categories.html
    with open('static/categories.html', 'r+', encoding='utf-8') as file:
        categories_html_content = file.read()
        soup = BeautifulSoup(categories_html_content, 'html.parser')

        category_to_recolor = soup.find('h3', text=category_name).find_parent('div', class_='categorybutton')
        if category_to_recolor:
            category_to_recolor['data-color'] = new_color
            # Update the style attribute with the '#' symbol included for CSS
            category_to_recolor['style'] = f'background-color: {css_color};'
            file.seek(0)
            file.write(str(soup))
            file.truncate()

    # Update database
    map_objects_to_recolor = MapObject.query.filter_by(categoryid=category_name).all()
    for map_object in map_objects_to_recolor:
        map_object.hexColor = new_color
    db.session.commit()

    return jsonify({'message': 'Category recolored successfully'}), 200
    
@app.route('/get-current-color', methods=['POST'])
def get_current_color():
    data = request.get_json()
    category_name = data['categoryName']

    # Assuming the category name is unique and used as the ID in the category buttons
    with open('static/categories.html', 'r', encoding='utf-8') as file:
        categories_html_content = file.read()
        soup = BeautifulSoup(categories_html_content, 'html.parser')

    category_button = soup.find('h3', text=category_name).find_parent('div', class_='categorybutton')
    current_color = category_button['data-color'] if category_button else '#FFFFFF'

    return jsonify(currentColor=current_color)
# RECOLORING LOGIC BACKEND END



# NEW CATEGORY CREATION LOGIC BACKEND START
@app.route('/add-category', methods=['POST'])
def add_category():
    data = request.get_json()
    category_title = data.get('title')
    category_color = data.get('color')

    if category_title and category_color:
        with open('static/categories.html', 'a', encoding='utf-8') as file:
            file.write(f'<div class="categorybutton" data-color="{category_color}" style="background-color: #{category_color};">\n')
            file.write(f'    <h3>{category_title}</h3>\n')
            file.write('</div>\n')
        return jsonify({'message': 'New category added successfully'}), 200
    else:
        return jsonify({'error': 'Invalid category title or color'}), 400
# NEW CATEGORY CREATION LOGIC BACKEND END

# DELETE CATEGORY CREATION LOGIC BACKEND START
@app.route('/delete-category', methods=['POST'])
def delete_category():
    data = request.get_json()
    category_name = data['categoryName']

    with open('static/categories.html', 'r+', encoding='utf-8') as file:
        categories_html_content = file.read()
        soup = BeautifulSoup(categories_html_content, 'html.parser')

        category_to_delete = soup.find('h3', text=category_name).find_parent('div', class_='categorybutton')
        if category_to_delete:
            category_to_delete.decompose()  # Remove the category div
            file.seek(0)
            file.write(str(soup))
            file.truncate()
            return jsonify({'message': 'Category deleted successfully'}), 200
        else:
            return jsonify({'error': 'Category not found'}), 404

# DELETE CATEGORY CREATION LOGIC BACKEND END


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
