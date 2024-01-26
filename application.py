from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_pymongo import pymongo
import json
import ssl
import csv
import os
import sys
from collections import defaultdict
import numpy as np
from scipy import stats
from os import environ
import logging

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

applicants = pymongo.collection.Collection(db, 'applicants_sp2024')
graders = pymongo.collection.Collection(db, 'graders')
reviews = pymongo.collection.Collection(db, 'reviews')
admins = pymongo.collection.Collection(db, 'admins')
trackers = pymongo.collection.Collection(db, 'trackers')
errors = pymongo.collection.Collection(db, 'errors')
prompts = pymongo.collection.Collection(db, 'prompts')

# Assigning leadership guarantees to each applicant
# Replace the email addresses below per each semester
leadership = [
    'bradley_tian@berkeley.edu',
    'shamith09@berkeley.edu',
    'danielsamony@berkeley.edu',
    'joon.yoo181@berkeley.edu',
    'terriannezhang@berkeley.edu',
    'eldenyap@berkeley.edu',
    'nkhanchu@berkeley.edu',
    'rakhichd@berkeley.edu',
    'taiga2002@berkeley.edu',
    'epchao@berkeley.edu',
    'malam2003@berkeley.edu',
    'tylerauton-smith@berkeley.edu',
    'jchuang77@berkeley.edu',
    'dylanhopkins@berkeley.edu',
    'satwik@berkeley.edu',
    'joying@berkeley.edu',
]

# How many people are we assigning to the same applicant?
member_redundancy, leadership_redundancy = 3, 2

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
    'r1',
    'r2',
    'r3',
    'r4',
    'r5',
    'r6',
    'r7',
    'r8',
    'r9',
    'r0',
]

# Edit weightings here
# Ensure that the weighting order corresponds element-wise to the ordering of qualities
curriculum_weightings = [
    0.025,
    0.025,
    0.1,
    0.15,
    0.1,
    0.1,
    0.15,
    0.1,
    0.1,
    0.05,
]

dev_weightings = [
    0.1,
    0.2,
    0.1,
    0.10588,
    0.070588,
    0.070588,
    0.10588,
    0.070588,
    0.070588,
    0.05,
]

# Graduation year bonus; edit this every semester
year_bonus = {
    '2024': 0,
    '2025': 0.01,
    '2026': 0.02,
    '2027': 0.03,
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
    newApp = applicant.copy()
    del newApp['_id']
    applicants.replace_one(
        {"time_created": applicant['time_created']}, newApp)
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
        'male': 0,
        'female': 0,
        'other': 0,
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

        if not app['gender'].lower() in analytics:
            analytics['other'] += 1
        else:
            analytics[app['gender'].lower()] += 1

        if 'race' in app and app['race'] != "Prefer not to answer":
            analytics[ethnicTranslations[app['race']]] += 1

    return json.dumps(analytics, default=str)


@application.route('/assign_graders', methods=['GET'])
def assignGraders():
    graders = list(db.graders.find())
    members = [m['email'] for m in graders if not m['email'] in leadership]
    apps = list(applicants.find({'assigned_to': []}))

    member_scope = len(members)
    leadership_scope = len(leadership)

    # How many people are we assigning to the same applicant?
    member_redundancy, leadership_redundancy = 2, 2
    
    member_pointer, leadership_pointer = 0, 0

    for app in apps:
        for _ in range(member_redundancy):
            member_pointer = (member_pointer + 1) % member_scope
            app['assigned_to'].append(members[member_pointer])
        for _ in range(leadership_redundancy):
            leadership_pointer = (leadership_pointer + 1) % leadership_scope
            app['assigned_to'].append(leadership[leadership_pointer])
        newApp = app.copy()
        del newApp['_id']
        applicants.replace_one({"time_created": app['time_created']}, newApp)

    apps = list(applicants.find())
    assignments = defaultdict(list)

    for app in apps:
        profile = str(app['first_name']) + " " + \
            str(app['last_name']) + ", ID: " + str(app['time_created'])
        for grader in app['assigned_to']:
            assignments[grader].append(profile)

    apps = list(applicants.find())
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
    csv.field_size_limit(sys.maxsize)
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
        newApp = applicant.copy()
        del newApp['_id']
        applicants.replace_one(
            {"time_created": applicant['time_created']}, newApp)
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
            # Populate the scores a grader has given for each question on the grading interface
            # <email> : {<rating name> : [(rating, applicant_ID)]}
            judgments[review['grader']][quality].append(
                (int(review[quality]), review['applicantID']))

    z_scores = []
        
    for grader in judgments:
        for quality in qualities:
            if quality == 'r0':
                z = [x[0] / 15 for x in judgments[grader][quality]]
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
        "desired_roles": 1,
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
        eval['desired_roles'] = applicant['desired_roles']
        eval.update(evaluations[applicantID])
        eval['total'] = 0

        for i in range(len(qualities)):
            if eval['desired_roles'] == "Industry Developer":
                dev_score = eval[qualities[i]] * dev_weightings[i]
                if np.isnan(dev_score):
                    dev_score = 0.02
                eval['total'] += dev_score
            else:
                curriculum_score = eval[qualities[i]] * curriculum_weightings[i]
                if np.isnan(curriculum_score):
                    curriculum_score = 0.02
                eval['total'] += curriculum_score

        eval['total'] += year_bonus[applicant['year']]

        # URM diversity bonus
        if ('race' in applicant and
                applicant['race'] != 'Asian (including Indian subcontinent and Philippines origin)'):
            eval['total'] += URM_GENDER_BONUS

        # Gender bonus
        if applicant['gender'] != 'Male':
            eval['total'] += URM_GENDER_BONUS

        eval['total'] = round((eval['total'] * 100), 2)
        logging.info("Total: ", eval['total'])
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

@application.route('/load_prompts', methods=['GET'])
def loadPrompts():
    prompt = list(prompts.find({}))
    if not prompt:
        return json.dumps({})
    result = {}
    for key, value in prompt[0].items():
        if key == "_id":
            result['id'] = str(value)
        else:
            result[key] = value
    return json.dumps(result)

@application.route('/change_prompts', methods=['POST'])
def changePrompts():
    change = json.loads(request.get_data(as_text=True))
    db.prompts.delete_many({})
    db.prompts.insert_one(change)
    print(list(db.prompts.find({})))
    return jsonify(message='SUCCESS')

if __name__ == '__main__':
    application.run(debug=True)

# Rebooting Server Test Post Op 2
