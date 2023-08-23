from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_pymongo import pymongo
import json
import ssl
import csv
import os
from collections import defaultdict
import numpy as np
from scipy import stats
from os import environ

application = Flask(__name__)
cors = CORS(application)

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Enter administrator username and password here to access database
CONNECTION_STRING = "mongodb+srv://admin:plextechadmin@cluster0.wds89j7.mongodb.net/?retryWrites=true&w=majority"

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('application_pipeline')
user_collection = pymongo.collection.Collection(db, 'user_collection')

applicants = pymongo.collection.Collection(db, 'applicants_fa2023')
graders = pymongo.collection.Collection(db, 'graders')
reviews = pymongo.collection.Collection(db, 'reviews')
admins = pymongo.collection.Collection(db, 'admins')
trackers = pymongo.collection.Collection(db, 'trackers')
errors = pymongo.collection.Collection(db, 'errors')

# Assigning leadership guarantees to each applicant
# Replace the email addresses below per each semester
leadership = [
    'bradley_tian@berkeley.edu',
    'sathvika@berkeley.edu',
    'shamith09@berkeley.edu',
    'tiajain@berkeley.edu',
    'howardm12138@berkeley.edu',
    'samarth.ghai@berkeley.edu',
    'aakashpathak@berkeley.edu',
    'epchao@berkeley.edu',
    'jessica.young@berkeley.edu',
    'malam2003@berkeley.edu',
    'somup27@berkeley.edu',
    'tylerauton-smith@berkeley.edu',
    'vishal.bansal@berkeley.edu',
    'v_perisic@berkeley.edu',
]

# Change this every semester
yearTranslations = {
    '2024': 'senior',
    '2025': 'junior',
    '2026': 'sophomore',
    '2027': 'freshman',
}

ethnicTranslations = {
    'American Indian or Alaska Native': 'American_Indian',
    'Asian (including Indian subcontinent and Philippines origin)': 'Asian',
    'Black or African American': 'Black',
    'White': 'White',
    'Middle Eastern': 'Middle_Eastern',
    'Native American or Other Pacific Islander': 'Pacific_Islander',
    'Hispanic or Latino': 'Hispanic',
}

# Qualities graders will evaluate on the grading interface
qualities = [
    'resCommit',
    'resLead',
    'resTech',
    'initiative',
    'problem',
    'ansCommit',
    'impact',
    'passion',
    'excellence',
    'commitment',
]

# Edit weightings here
# Ensure that weighting order corresponds the ordering of qualities
weightings = [
    0.1176,
    0.08824,
    0.08824,
    0.1176,
    0.1176,
    0.1176,
    0.1176,
    0.8824,
    0.8824,
    0.0588,
]

# Graduation year bonus; edit this every semester
year_bonus = {
    '2023': 0,
    '2024': 0.01,
    '2025': 0.02,
    '2026': 0.03,
}

# No more DEI bonuses
URM_GENDER_BONUS = 0.0

@application.route('/add_applicant', methods=['POST'])
def addApplicant():
    application = json.loads(request.get_data(as_text=True))
    applicants.insert_one(application)
    return jsonify(message='SUCCESS')


@application.route('/get_applicant/<grader>', methods=['GET'])
def getApplicants(grader):
    documents = list(applicants.find(
        {"$and": [{'assigned_to': grader}, {'graded_by': {'$ne': grader}}]}))
    return json.dumps(documents, default=str)

@application.route('/add_review', methods=['POST'])
def addReview():
    review = json.loads(request.get_data(as_text=True))
    applicant = list(applicants.find(
        {"time_created": review['applicantID']}))[0]
    applicant['graded_by'].append(review['grader'])
    applicants.replace_one(
        {"time_created": applicant['time_created']}, applicant)
    db.reviews.insert_one(review)
    return jsonify(message='SUCCESS')


@application.route('/check_grader', methods=['POST'])
def checkGrader():
    grader = json.loads(request.get_data(as_text=True))
    target = grader['email']
    check = list(db.graders.find({'email': target}))
    result = False
    if len(check) > 0:
        result = True
    return json.dumps({"found": result}, default=str)


@application.route('/add_admin', methods=['POST'])
def addAdmin():
    admin = json.loads(request.get_data(as_text=True))
    db.admins.insert_one(admin)
    return jsonify(message='SUCCESS')


@application.route('/check_admin', methods=['POST'])
def checkAdmin():
    admin = json.loads(request.get_data(as_text=True))
    target = admin['email']
    check = list(db.admins.find({'email': target}))
    result = False
    if len(check) > 0:
        result = True
    return json.dumps({"found": result}, default=str)


@application.route('/get_graders', methods=['GET'])
def getGraders():
    graders = list(db.graders.find())
    return json.dumps(graders, default=str)


@application.route('/add_grader', methods=['POST'])
def addGrader():
    grader = json.loads(request.get_data(as_text=True))
    db.graders.insert_one(grader)
    return jsonify(message='SUCCESS')


@application.route('/remove_grader', methods=['POST'])
def removeGrader():
    grader = json.loads(request.get_data(as_text=True))
    target = grader['email']
    db.graders.delete_one({'email': target})
    return jsonify(message='SUCCESS')


@application.route('/analytics', methods=['GET'])
def getAnalytics():
    apps = list(applicants.find({}, {"year": 1, "gender": 1, "race": 1,}))
    count = len(apps)

    # Edit demographic information as needed
    analytics = {
        'count': count,
        'freshman': 0,
        'sophomore': 0,
        'junior': 0,
        'senior': 0,
        'Male': 0,
        'Female': 0,
        'Other': 0,
        'American_Indian': 0,
        'Asian': 0,
        'Black': 0,
        'White': 0,
        'Middle_Eastern': 0,
        'Pacific_Islander': 0,
        'Hispanic': 0, 
    }

    for app in apps:

        analytics[yearTranslations[app['year']]] += 1

        if not app['gender'] in analytics:
            analytics['other'] += 1
        else:
            analytics[app['gender'].lower()] += 1

        if 'race' in app and app['race'] != "Prefer not to answer":
            analytics[ethnicTranslations[app['race']]] += 1

    return json.dumps(analytics, default=str)


@application.route('/assign_graders', methods=['GET'])
def assignGraders():
    graders = list(db.graders.find())
    apps = list(applicants.find({'assigned_to': []}))

    tracker = list(db.trackers.find())[0]
    current = int(tracker['current'])
    scope = len(graders)

    if current >= scope:
        current = current % scope

    # How many graders are we assigning to the same applicant?
    redundancy = 3

    for app in apps:
        for i in range(redundancy):
            app['assigned_to'].append(graders[(current + i) % scope]['email'])
        applicants.replace_one({"time_created": app['time_created']}, app)
        current = (current + 1) % scope

    db.trackers.replace_one({'name': 'index'}, {'current': current})

    apps = list(applicants.find())

    assignments = defaultdict(list)

    for app in apps:
        profile = str(app['first_name']) + " " + \
            str(app['last_name']) + ", ID: " + str(app['time_created'])
        for grader in app['assigned_to']:
            assignments[grader].append(profile)

    apps = list(applicants.find())

    currentLead = 0

    for app in apps:
        included = False
        for lead in leadership:
            if lead in app['assigned_to']:
                included = True
        if not included:
            app['assigned_to'].append(leadership[currentLead])
            applicants.replace_one(
                {"time_created": app['time_created']}, app)
            profile = str(app['first_name']) + " " + \
                str(app['last_name']) + ", ID: " + str(app['time_created'])
            assignments[leadership[currentLead]].append(profile)
            currentLead = (currentLead + 1) % len(leadership)

    return json.dumps(assignments)


@application.route('/export_results', methods=['GET'])
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


@application.route('/export_applications', methods=['GET'])
def exportApplications():

    applications = list(applicants.find())
    for app in applications:
        app['resume'] = 'See Database'
    data = []

    if len(applications) == 0:
        return json.dumps([])

    with open("applications.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=applications[0].keys())
        writer.writeheader()
        for app in applications:
            writer.writerow(app)

    with open("applications.csv", "r", newline="") as f:
        reader = csv.DictReader(f, fieldnames=applications[0].keys())
        data = list(reader)
        f.close()

    try:
        os.remove('applications.csv')
    except:
        print("ERROR: CSV FILE NOT FOUND")

    return json.dumps(data)


@application.route('/flush_database', methods=['GET'])
def flushDatabase():
    db.reviews.delete_many({})

    apps = list(applicants.find())
    for applicant in apps:
        applicant['graded_by'] = []
        applicant['assigned_to'] = []
        applicants.replace_one(
            {"time_created": applicant['time_created']}, applicant)
    return jsonify(message='SUCCESS')


@application.route('/report_error', methods=['POST'])
def reportError():
    report = json.loads(request.get_data(as_text=True))
    db.errors.insert_one(report)
    return jsonify(message='SUCCESS')


@application.route('/evaluate_results', methods=['GET'])
def evaluateResults():
    reviews = list(db.reviews.find())
    judgments = defaultdict(lambda: defaultdict(list))

    for review in reviews:
        for quality in qualities:
            judgments[review['grader']][quality].append(
                (int(review[quality]), review['applicantID']))

    z_scores = []
        
    for grader in judgments:
        for quality in qualities:
            if quality == 'commitment':
                z = [x[0] / 10 for x in judgments[grader][quality]]
            else:
                z = stats.zscore([x[0] for x in judgments[grader][quality]])
            z_scores.append(z)

        for i in range(len(z_scores)):
            for j in range(len(z_scores[i])):
                judgments[grader][qualities[i]][j] = (
                    z_scores[i][j], judgments[grader][qualities[i]][j][1])
        
        z_scores = []

    evaluations = defaultdict(lambda: defaultdict(list))

    for grader in judgments:
        for i in range(len(judgments[grader][qualities[0]])):
            for quality in qualities:
                evaluations[judgments[grader][quality][i][1]][quality].append(
                    judgments[grader][quality][i][0])

    for eval in evaluations:
        for quality in qualities:
            evaluations[eval][quality] = np.mean(evaluations[eval][quality])

    data = []
    apps = list(applicants.find({}, {
        "time_created": 1,
        "year": 1,
        "race": 1,
        "gender": 1,
        "first_name": 1,
        "last_name": 1,
    }))

    for applicantID in evaluations.keys():
        eval = {}
        applicant = {}
        for app in apps:
            if app['time_created'] == applicantID:
                applicant = app

        eval['applicantID'] = applicantID
        eval['first_name'] = applicant['first_name']
        eval['last_name'] = applicant['last_name']
        eval.update(evaluations[applicantID])
        eval['total'] = 0

        for i in range(len(qualities)):
            eval['total'] += (eval[qualities[i]] * weightings[i])

        eval['total'] += year_bonus[applicant['year']]

        # URM diversity bonus
        if ('race' in applicant and
                applicant['race'] != 'Asian (including Indian subcontinent and Philippines origin)'):
            eval['total'] += URM_GENDER_BONUS

        # Gender bonus
        if applicant['gender'] != 'Male':
            eval['total'] += URM_GENDER_BONUS

        eval['total'] = round((eval['total'] * 100), 2)
        data.append(eval)

    export = []

    if len(data) == 0:
        return json.dumps([], default=str)

    with open("evaluations.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        for applicant in data:
            writer.writerow(applicant)

    with open("evaluations.csv", "r", newline="") as f:
        reader = csv.DictReader(f, fieldnames=data[0].keys())
        export = list(reader)
        f.close()

    try:
        os.remove('evaluations.csv')
    except:
        print("ERROR: CSV FILE NOT FOUND")

    return json.dumps(export, default=str)


@application.route('/check_progress', methods=['GET'])
def checkProgress():
    apps = list(applicants.find({}))
    incomplete = set()
    for app in apps:
        if len(app['graded_by']) < 2:
            missing = [grader for grader in app['assigned_to'] if grader not in app['graded_by']]
            incomplete.add(
                (app['first_name'], app['last_name'], app['time_created'], f'Missing reviews from: \n {missing}'))
    incomplete = list(incomplete)
    return json.dumps(incomplete)


if __name__ == '__main__':
    application.run(debug=True)

# Rebooting Server Test Post Op
