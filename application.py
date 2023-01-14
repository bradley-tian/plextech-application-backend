from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_pymongo import pymongo
import json
import ssl
import csv
import os
from collections import defaultdict

application = Flask(__name__)
cors = CORS(application)

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

CONNECTION_STRING = "mongodb+srv://admin:plextechAdmin@cluster0.wds89j7.mongodb.net/?retryWrites=true&w=majority"

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('application_pipeline')
user_collection = pymongo.collection.Collection(db, 'user_collection')

graders = pymongo.collection.Collection(db, 'applicants')
graders = pymongo.collection.Collection(db, 'graders')
reviews = pymongo.collection.Collection(db, 'reviews')
admins = pymongo.collection.Collection(db, 'admins')
trackers = pymongo.collection.Collection(db, 'trackers')

@application.route('/add_applicant', methods = ['POST'])
def addApplicant():
    application = json.loads(request.get_data(as_text = True))
    db.applicants.insert_one(application)
    return jsonify(message = 'SUCCESS')

@application.route('/get_applicant/<grader>', methods = ['GET'])
def getApplicants(grader):
    documents = list(db.applicants.find({"$and" : [{ 'assigned_to': grader }, { 'graded_by': {'$ne': grader}}]}))
    return json.dumps(documents, default=str)

@application.route('/add_review', methods = ['POST'])
def addReview():
    review = json.loads(request.get_data(as_text = True))
    applicant = list(db.applicants.find({ "time_created" : review['applicantID'] }))[0]
    applicant['graded_by'].append(review['grader'])
    db.applicants.replace_one({ "time_created" : applicant['time_created'] }, applicant)
    db.reviews.insert_one(review)
    return jsonify(message = 'SUCCESS')

@application.route('/check_grader', methods = ['POST'])
def checkGrader():
    grader = json.loads(request.get_data(as_text = True))
    target = grader['email']
    check = list(db.graders.find({'email': target}))
    result = False
    if len(check) > 0:
        result = True
    return json.dumps({"found": result}, default=str)

@application.route('/add_admin', methods = ['POST'])
def addAdmin():
    admin = json.loads(request.get_data(as_text = True))
    db.admins.insert_one(admin)
    return jsonify(message = 'SUCCESS')

@application.route('/check_admin', methods = ['POST'])
def checkAdmin():
    admin = json.loads(request.get_data(as_text = True))
    target = admin['email']
    check = list(db.admins.find({'email': target}))
    result = False
    if len(check) > 0:
        result = True
    return json.dumps({"found": result}, default=str)

@application.route('/get_graders', methods = ['GET'])
def getGraders():
    graders = list(db.graders.find())
    return json.dumps(graders, default=str)

@application.route('/add_grader', methods = ['POST'])
def addGrader():
    grader = json.loads(request.get_data(as_text = True))
    db.graders.insert_one(grader)
    return jsonify(message = 'SUCCESS')

@application.route('/remove_grader', methods = ['POST'])
def removeGrader():
    grader = json.loads(request.get_data(as_text = True))
    target = grader['email']
    db.graders.delete_one({'email': target})
    return jsonify(message = 'SUCCESS')

@application.route('/analytics', methods = ['GET'])
def getAnalytics():
    # Applicant count, Distribution by: year, major, gender
    applicants = list(db.applicants.find())
    count = len(applicants)
    freshmen, sophomore, junior, senior = 0, 0, 0, 0
    male, female, other = 0, 0, 0
    for app in applicants:
        year = app['year']
        if year == "2023":
            senior += 1
        elif year == "2024":
            junior += 1
        elif year == "2025":
            sophomore += 1
        elif year == "2026":
            freshmen += 1

        gender = app['gender']
        if gender == "Male":
            male += 1
        elif gender == "Female":
            female += 1
        else:
            other += 1

    result = {
        'count': count,
        'freshmen': freshmen,
        'sophomore': sophomore,
        'junior': junior,
        'senior': senior,
        'male': male,
        'female': female,
        'other': other,
    }

    return json.dumps(result, default=str)

@application.route('/assign_graders', methods = ['GET'])
def assignGraders():
    graders = list(db.graders.find())
    applicants = list(db.applicants.find({'assigned_to': []}))

    tracker = list(db.trackers.find())[0]
    current = int(tracker['current'])
    scope = len(graders)

    if current >= scope: 
        current = current % scope

    for app in applicants:
        app['assigned_to'].append(graders[current]['email'])
        app['assigned_to'].append(graders[(current + 1) % scope]['email'])
        db.applicants.replace_one({ "time_created": app['time_created'] }, app)
        current = (current + 1) % scope
    
    db.trackers.replace_one({'_id': tracker['_id'] }, {'current': current})

    applicants = list(db.applicants.find())

    assignments = defaultdict(list)

    for app in applicants:
        profile = str(app['first_name']) + " " + str(app['last_name']) + ", ID: " + str(app['time_created'])
        for grader in app['assigned_to']:
            assignments[grader].append(profile)

    return json.dumps(assignments)

@application.route('/export_results', methods = ['GET'])
def exportResults():
    reviews = list(db.reviews.find())
    data = []

    if len(reviews) == 0:
        return json.dumps([])

    with open("results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
        writer.writeheader()
        for review in reviews:
            writer.writerow(review)

    with open("results.csv", "r", newline="") as f:
        reader = csv.DictReader(f, fieldnames=reviews[0].keys())
        data = list(reader)
        f.close()
    
    try:
        os.remove('results.csv')
    except:
        print("ERROR: CSV FILE NOT FOUND")
        
    return json.dumps(data)

@application.route('/flush_database', methods = ['GET'])
def flushDatabase():
    db.applicants.remove({})
    return jsonify(message = 'SUCCESS')

if __name__ == '__main__':
    application.run(debug=True)

#Rebooting Test Command