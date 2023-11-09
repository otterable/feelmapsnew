from flask_caching import Cache
from flask_cors import CORS
from flask import Flask, Flask, render_template, request, jsonify, Response, session, redirect, url_for, send_from_directory, make_response, g, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from collections import Counter
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from datetime import datetime

import io
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///s.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'ZDlGoz5V4/CWj+OGx8h2vQ=='  # You should use a secure, random secret key.
CORS(app)  # This is to allow cross-origin requests, if needed.

db = SQLAlchemy(app)

class Shape(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shape_data = db.Column(db.JSON, nullable=False)
    shape_note = db.Column(db.String, nullable=True)
    shape_type = db.Column(db.String, nullable=False)
    shape_color = db.Column(db.String, nullable=True)  # Add a new column for color
    molen_id = db.Column(db.String, nullable=True, default="null")
    score = db.Column(db.String, nullable=True, default="null")
    highlight_id = db.Column(db.String, nullable=True, default="null")
    radius = db.Column(db.Float, nullable=True) 

@app.before_request
def before_request():
    if not hasattr(g, 'db_initialized'):
        db.create_all()
        print("Database and tables created")
        g.db_initialized = True

@app.route('/')
def index():
    total_objects, category_counts, color_counts = count_objects()  # Assuming count_objects is already defined as per your previous messages.
    return render_template('index.html', category_counts=category_counts, color_counts=color_counts)

@app.route('/categories')
def categories():
    return render_template('categories.html')
    


@app.route('/api/shapes', methods=['POST'])
def add_shape():
    data = request.json
    shape_data_json = json.dumps(data['shape_data'])  # Ensuring JSON serialization
    new_shape = Shape(
        shape_data=shape_data_json,
        shape_note=data.get('shape_note', ''),
        shape_type=data['shape_type'],
        shape_color=data.get('shape_color', 'yellow'),  # Save the color
        radius=data.get('radius'),  # Save the radius if provided
        molen_id=data.get('molen_id', 'null'),
        score=data.get('score', 'null'),
        highlight_id=data.get('highlight_id', 'null')
    )
    db.session.add(new_shape)
    db.session.commit()
    print('New shape added with ID:', new_shape.id)
    return jsonify(success=True, id=new_shape.id)

@app.route('/api/shapes', methods=['GET'])
def get_shapes():
    shapes = Shape.query.all()
    shapes_data = [
        {
            'id': shape.id,
            'shape_data': json.loads(shape.shape_data),  # Ensuring JSON deserialization
            'shape_type': shape.shape_type,
            'shape_color': shape.shape_color,
            'radius': shape.radius,  # Include the radius in the response if it exists
            'shape_note': shape.shape_note  # Include the note in the response
        } for shape in shapes
    ]
    print('Shapes fetched:', len(shapes_data))
    return jsonify(shapes=shapes_data)
    
@app.route('/api/shapes/<int:shape_id>', methods=['DELETE'])
def delete_shape(shape_id):
    shape = Shape.query.get(shape_id)
    if shape:
        db.session.delete(shape)
        db.session.commit()
        print('Shape deleted with ID:', shape_id)
        return jsonify(success=True), 200
    else:
        print('Shape not found with ID:', shape_id)
        return jsonify(success=False), 404


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


@app.route('/get-categories')
def get_categories():
    try:
        with open('templates/categories.html') as file:
            soup = BeautifulSoup(file, 'html.parser')  # Use BeautifulSoup directly
            categories = [{'color': button['style'].split(': ')[1].replace(';', '').strip(), 'text': button.h3.text}
                          for button in soup.find_all('button', {'class': 'categorybutton'})]
        # Include "null" category in the response
        categories.append({'color': 'null', 'text': 'Null Category'})
        return jsonify(categories)
    except Exception as e:
        # Log the error for debugging
        print(f"Error occurred: {e}")
        # Return a 500 error to the client with the error message
        return jsonify(error=str(e)), 500


@app.route('/update-category', methods=['POST'])
def update_category():
    color_to_update = request.json.get('oldColor')
    new_color = request.json.get('newColor')
    
    with open('templates/categories.html', 'r+') as file:
        content = file.read()
        soup = BeautifulSoup(content, 'html.parser')
        for button in soup.find_all('button', {'class': 'categorybutton'}):
            if color_to_update in button['style']:
                button['style'] = f"background-color: {new_color};"
                button['onclick'] = f"parent.setCategory('{new_color}')"
        file.seek(0)
        file.write(str(soup))
        file.truncate()
    
    return jsonify(success=True)
    
@app.route('/update-shape-colors', methods=['POST'])
def update_shape_colors():
    data = request.json
    old_color = data.get('oldColor')
    new_color = data.get('newColor')

    try:
        # Update the shapes with the old color to the new color
        Shape.query.filter_by(shape_color=old_color).update({'shape_color': new_color})
        db.session.commit()
        return jsonify(success=True), 200
    except Exception as e:
        print(f"Error updating shape colors: {e}")
        return jsonify(success=False, error=str(e)), 500
        
@app.route('/rename-category', methods=['POST'])
def rename_category():
    color = request.json.get('color')
    new_name = request.json.get('newName')
    
    try:
        with open('templates/categories.html', 'r+') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            buttons = soup.find_all('button', {'class': 'categorybutton'})
            for button in buttons:
                if color in button['style']:
                    button.h3.string = new_name  # Update the text within the <h3> tag
            file.seek(0)
            file.write(str(soup))
            file.truncate()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while renaming category: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/create-category', methods=['POST'])
def create_category():
    name = request.json.get('name')
    color = request.json.get('color')
    
    try:
        with open('templates/categories.html', 'r+') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            # Create a new button element for the category
            new_button = soup.new_tag('button', **{
                'class': 'categorybutton',
                'onclick': f"parent.setCategory('{color}')",
                'style': f"background-color: {color};"
            })
            new_button_h3 = soup.new_tag('h3')
            new_button_h3.string = name
            new_button.append(new_button_h3)
            soup.body.append(new_button)
            file.seek(0)
            file.write(str(soup))
            file.truncate()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while creating new category: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/delete-category', methods=['POST'])
def delete_category():
    color_to_delete = request.json.get('color')
    
    try:
        # Delete categories from the HTML file
        with open('templates/categories.html', 'r+') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            for button in soup.find_all('button', {'class': 'categorybutton'}):
                if color_to_delete in button['style']:
                    button.decompose()
            file.seek(0)
            file.write(str(soup))
            file.truncate()
        
        # Delete shapes with the corresponding color from the database
        shapes_to_delete = Shape.query.filter_by(shape_color=color_to_delete).all()
        for shape in shapes_to_delete:
            db.session.delete(shape)
        db.session.commit()
        
        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting category: {e}")
        db.session.rollback()  # Roll back the session in case of an error
        return jsonify(success=False, error=str(e)), 500
 
@app.route('/export-geojson', methods=['GET'])
def export_geojson():
    # Query all shapes from the database
    shapes = Shape.query.all()
    
    # Construct GeoJSON features list
    features = []
    for shape in shapes:
        # Parse shape data and create GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": json.loads(shape.shape_data),
            "properties": {
                "id": shape.id,
                "note": shape.shape_note,
                "type": shape.shape_type,
                "color": shape.shape_color,
                "molen_id": shape.molen_id,
                "score": shape.score,
                "highlight_id": shape.highlight_id,
                "radius": shape.radius
            }
        }
        features.append(feature)
    
    # Construct the full GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Convert the GeoJSON to a string and then to a BytesIO object for file download
    geojson_str = json.dumps(geojson, indent=2)
    geojson_bytes = io.BytesIO(geojson_str.encode('utf-8'))
    
    # Send the GeoJSON file to the client
    return send_file(geojson_bytes, mimetype='application/json',
    as_attachment=True, download_name='shapes_export.geojson')

@app.route('/import-geojson', methods=['POST'])
def import_geojson():
    try:
        uploaded_file = request.files['file']
        if uploaded_file:
            geojson_data = json.load(uploaded_file)
            for feature in geojson_data['features']:
                shape_data = json.dumps(feature['geometry'])
                shape_note = feature['properties']['note']
                shape_type = feature['properties']['type']
                shape_color = feature['properties']['color']
                molen_id = feature['properties']['molen_id']
                score = feature['properties']['score']
                highlight_id = feature['properties']['highlight_id']
                radius = feature['properties']['radius']
                shape = Shape(
                    shape_data=shape_data,
                    shape_note=shape_note,
                    shape_type=shape_type,
                    shape_color=shape_color,
                    molen_id=molen_id,
                    score=score,
                    highlight_id=highlight_id,
                    radius=radius
                )
                db.session.add(shape)
            db.session.commit()
            return '''
                <script>
                    alert('GeoJSON data imported successfully');
                    window.location.href = '/';
                </script>
            '''
        else:
            return '''
                <script>
                    alert('No file uploaded');
                    window.location.href = '/';
                </script>
            '''
    except Exception as e:
        return '''
            <script>
                alert('Error: {}');
                window.location.href = '/';
            </script>
        '''.format(str(e))

# Function to count all objects, category objects, and colors
def count_objects():
    total_objects = Shape.query.count()
    categories = Shape.query.with_entities(Shape.shape_type).distinct()
    category_counts = {}
    color_counts = {}

    for category in categories:
        category_counts[category[0]] = Shape.query.filter_by(shape_type=category[0]).count()

    # Count objects by color
    colors = Shape.query.with_entities(Shape.shape_color).distinct()
    for color in colors:
        color_counts[color[0]] = Shape.query.filter_by(shape_color=color[0]).count()

    return total_objects, category_counts, color_counts

# Route to display counts
# Change the return value to jsonify the counts
@app.route('/count-objects')
def display_counts():
    total_objects, category_counts, color_counts = count_objects()
    return jsonify({
        'total_objects': total_objects, 
        'category_counts': category_counts, 
        'color_counts': color_counts
    })  
    
# Route to delete objects by category
@app.route('/delete-objects-by-category', methods=['POST'])
def delete_objects_by_category():
    data = request.json
    color_to_delete = data.get('color')

    try:
        # Delete objects with the corresponding category color from the database
        objects_to_delete = Shape.query.filter_by(shape_color=color_to_delete).all()
        for obj in objects_to_delete:
            db.session.delete(obj)
        db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting objects by category: {e}")
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

# Route to delete objects by object type
@app.route('/delete-objects-by-object-type', methods=['POST'])
def delete_objects_by_object_type():
    data = request.json
    object_type_to_delete = data.get('objectType')

    try:
        # Delete objects with the corresponding object type from the database
        objects_to_delete = Shape.query.filter_by(shape_type=object_type_to_delete).all()
        for obj in objects_to_delete:
            db.session.delete(obj)
        db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting objects by object type: {e}")
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


if __name__ == '__main__':
    app.run(debug=True)
