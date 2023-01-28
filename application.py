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
errors = pymongo.collection.Collection(db, 'errors')


@application.route('/add_applicant', methods=['POST'])
def addApplicant():
    application = json.loads(request.get_data(as_text=True))
    db.applicants.insert_one(application)
    return jsonify(message='SUCCESS')


@application.route('/get_applicant/<grader>', methods=['GET'])
def getApplicants(grader):
    documents = list(db.applicants.find(
        {"$and": [{'assigned_to': grader}, {'graded_by': {'$ne': grader}}]}))
    return json.dumps(documents, default=str)


@application.route('/add_review', methods=['POST'])
def addReview():
    review = json.loads(request.get_data(as_text=True))
    applicant = list(db.applicants.find(
        {"time_created": review['applicantID']}))[0]
    applicant['graded_by'].append(review['grader'])
    db.applicants.replace_one(
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
    applicants = list(db.applicants.find())
    count = len(applicants)
    freshmen, sophomore, junior, senior = 0, 0, 0, 0
    male, female, other = 0, 0, 0
    american_indian, asian, black, white, middle_eastern, pacific_islander = 0, 0, 0, 0, 0, 0

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

        if 'race' in app:
            race = app['race']
            if race == 'American Indian or Alaska Native':
                american_indian += 1
            elif race == "Asian (including Indian subcontinent and Philippines origin)":
                asian += 1
            elif race == 'Black or African American':
                black += 1
            elif race == 'White':
                white += 1
            elif race == 'Middle Eastern':
                middle_eastern += 1
            elif race == "Native American or Other Pacific Islander":
                pacific_islander += 1

    result = {
        'count': count,
        'freshmen': freshmen,
        'sophomore': sophomore,
        'junior': junior,
        'senior': senior,
        'male': male,
        'female': female,
        'other': other,
        'American_Indian': american_indian,
        "Asian": asian,
        "Black": black,
        "White": white,
        "Middle_Eastern": middle_eastern,
        "Pacific_Islander": pacific_islander,
    }

    return json.dumps(result, default=str)


@application.route('/assign_graders', methods=['GET'])
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
        app['assigned_to'].append(graders[(current + 2) % scope]['email'])
        db.applicants.replace_one({"time_created": app['time_created']}, app)
        current = (current + 1) % scope

    db.trackers.replace_one({'name': 'index'}, {'current': current})

    applicants = list(db.applicants.find())

    assignments = defaultdict(list)

    for app in applicants:
        profile = str(app['first_name']) + " " + \
            str(app['last_name']) + ", ID: " + str(app['time_created'])
        for grader in app['assigned_to']:
            assignments[grader].append(profile)

    applicants = list(db.applicants.find())
    leadership = [
        'bradley_tian@berkeley.edu',
        'sathvika@berkeley.edu',
        'winstoncai@berkeley.edu',
        'dyhuynh@berkeley.edu',
        'akhilsukh@berkeley.edu',
        'somup27@berkeley.edu',
        'shamith09@berkeley.edu',
        'tiajain@berkeley.edu',
        'jennabustami@berkeley.edu',
        'denvernguyen00@berkeley.edu',
        'epchao@berkeley.edu',
        'howardm12138@berkeley.edu',
        'preethi.m@berkeley.edu',
        'rohanrk2003@berkeley.edu',
        'samarth.ghai@berkeley.edu',
    ]

    currentLead = 0

    for app in applicants:
        included = False
        for lead in leadership:
            if lead in app['assigned_to']:
                included = True
        if not included: 
            app['assigned_to'].append(leadership[currentLead])
            db.applicants.replace_one({"time_created": app['time_created']}, app)
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

    applications = list(db.applicants.find())
    for app in applications:
        app['resume'] = 'See Database'
    data = []

    if len(applications) == 0:
        return json.dumps([])

    with open("applications.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=applications[11].keys())
        writer.writeheader()
        for app in applications:
            writer.writerow(app)

    with open("applications.csv", "r", newline="") as f:
        reader = csv.DictReader(f, fieldnames=applications[11].keys())
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

    applicants = list(db.applicants.find())
    for applicant in applicants:
        applicant['graded_by'] = []
        applicant['assigned_to'] = []
        db.applicants.replace_one(
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
        judgments[review['grader']]['resCommit'].append(
            (int(review['resCommit']), review['applicantID']))
        judgments[review['grader']]['resLead'].append(
            (int(review['resLead']), review['applicantID']))
        judgments[review['grader']]['resTech'].append(
            (int(review['resTech']), review['applicantID']))
        judgments[review['grader']]['initiative'].append(
            (int(review['initiative']), review['applicantID']))
        judgments[review['grader']]['problem'].append(
            (int(review['problem']), review['applicantID']))
        judgments[review['grader']]['ansCommit'].append(
            (int(review['ansCommit']), review['applicantID']))
        judgments[review['grader']]['impact'].append(
            (int(review['impact']), review['applicantID']))
        judgments[review['grader']]['passion'].append(
            (int(review['passion']), review['applicantID']))
        judgments[review['grader']]['excellence'].append(
            (int(review['excellence']), review['applicantID']))
        judgments[review['grader']]['commitment'].append(
            (int(review['commitment']), review['applicantID']))

    for grader in judgments:
        z_0 = stats.zscore([x[0] for x in judgments[grader]['resCommit']])
        z_1 = stats.zscore([x[0] for x in judgments[grader]['resLead']])
        z_2 = stats.zscore([x[0] for x in judgments[grader]['resTech']])
        z_3 = stats.zscore([x[0] for x in judgments[grader]['initiative']])
        z_4 = stats.zscore([x[0] for x in judgments[grader]['problem']])
        z_5 = stats.zscore([x[0] for x in judgments[grader]['ansCommit']])
        z_6 = stats.zscore([x[0] for x in judgments[grader]['impact']])
        z_7 = stats.zscore([x[0] for x in judgments[grader]['passion']])
        z_8 = stats.zscore([x[0] for x in judgments[grader]['excellence']])
        z_9 = stats.zscore([x[0] for x in judgments[grader]['commitment']])

        for i in range(len(z_0)):
            judgments[grader]['resCommit'][i] = (
                z_0[i], judgments[grader]['resCommit'][i][1])
            judgments[grader]['resLead'][i] = (
                z_1[i], judgments[grader]['resLead'][i][1])
            judgments[grader]['resTech'][i] = (
                z_2[i], judgments[grader]['resTech'][i][1])
            judgments[grader]['initiative'][i] = (
                z_3[i], judgments[grader]['initiative'][i][1])
            judgments[grader]['problem'][i] = (
                z_4[i], judgments[grader]['problem'][i][1])
            judgments[grader]['ansCommit'][i] = (
                z_5[i], judgments[grader]['ansCommit'][i][1])
            judgments[grader]['impact'][i] = (
                z_6[i], judgments[grader]['impact'][i][1])
            judgments[grader]['passion'][i] = (
                z_7[i], judgments[grader]['passion'][i][1])
            judgments[grader]['excellence'][i] = (
                z_8[i], judgments[grader]['excellence'][i][1])
            judgments[grader]['commitment'][i] = (
                z_9[i], judgments[grader]['commitment'][i][1])
            

    evaluations = defaultdict(lambda: defaultdict(list))

    for grader in judgments:
        for i in range(len(judgments[grader]['resCommit'])):
            evaluations[judgments[grader]['resCommit'][i][1]]['resCommit'].append(
                judgments[grader]['resCommit'][i][0])
            evaluations[judgments[grader]['resLead'][i][1]]['resLead'].append(
                judgments[grader]['resLead'][i][0])
            evaluations[judgments[grader]['resTech'][i][1]]['resTech'].append(
                judgments[grader]['resTech'][i][0])
            evaluations[judgments[grader]['initiative'][i][1]]['initiative'].append(
                judgments[grader]['initiative'][i][0])
            evaluations[judgments[grader]['problem'][i][1]]['problem'].append(
                judgments[grader]['problem'][i][0])
            evaluations[judgments[grader]['ansCommit'][i][1]]['ansCommit'].append(
                judgments[grader]['ansCommit'][i][0])
            evaluations[judgments[grader]['impact'][i][1]]['impact'].append(
                judgments[grader]['impact'][i][0])
            evaluations[judgments[grader]['passion'][i][1]]['passion'].append(
                judgments[grader]['passion'][i][0])
            evaluations[judgments[grader]['excellence'][i][1]]['excellence'].append(
                judgments[grader]['excellence'][i][0])     
            evaluations[judgments[grader]['commitment'][i][1]]['commitment'].append(
                judgments[grader]['commitment'][i][0])             

    for eval in evaluations:
        evaluations[eval]['resCommit'] = np.mean(evaluations[eval]['resCommit'])
        evaluations[eval]['resLead'] = np.mean(evaluations[eval]['resLead'])
        evaluations[eval]['resTech'] = np.mean(evaluations[eval]['resTech'])
        evaluations[eval]['initiative'] = np.mean(evaluations[eval]['initiative'])
        evaluations[eval]['problem'] = np.mean(evaluations[eval]['problem'])
        evaluations[eval]['ansCommit'] = np.mean(evaluations[eval]['ansCommit'])
        evaluations[eval]['impact'] = np.mean(evaluations[eval]['impact'])
        evaluations[eval]['passion'] = np.mean(evaluations[eval]['passion'])
        evaluations[eval]['excellence'] = np.mean(evaluations[eval]['excellence'])
        evaluations[eval]['commitment'] = np.mean(evaluations[eval]['commitment'])

    data = []
    applicants = list(db.applicants.find())

    for applicant in evaluations.keys():
        eval = {}

        # Edit weighings here
        w0, w1, w2, w3, w4, w5, w6, w7, w8, w9 = 0.1176, 0.08824, 0.08824, 0.1176, 0.1176, 0.1176, 0.1176, 0.08824, 0.08824, 0.0588

        eval['applicantID'] = applicant
        eval.update(evaluations[applicant])
        eval['total'] = (eval['resCommit'] * w0 +
                                eval['resLead'] * w1 +
                                eval['resTech'] * w2 +
                                eval['initiative'] * w3 +
                                eval['problem'] * w4 +
                                eval['ansCommit'] * w5 +
                                eval['impact'] * w6 +
                                eval['passion'] * w7 +
                                eval['excellence'] * w8 +
                                0 * w9)

        applicant = list(db.applicants.find({'time_created': applicant}))[0]

        if applicant['year'] == '2023':
            eval['total'] += 0.01
        elif applicant['year'] == '2024':
            eval['total'] += 0.02
        elif applicant['year'] == '2025':
            eval['total'] += 0.03
        elif applicant['year'] == '2026':
            eval['total'] += 0.04

        try:
            if applicant['race'] != 'Asian (including Indian subcontinent and Philippines origin)':
                eval['total'] += 0.05
        except: 
            pass
        
        if applicant['gender'] != 'Male':
            eval['total'] += 0.05

        eval['total'] = round((eval['total'] * 100), 2)
        data.append(eval)

    export = []

    if len(data) == 0:
        return json.dumps([])

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

    return json.dumps(export)

@application.route('/check_progress', methods=['GET'])
def checkProgress():
    applicants = list(db.applicants.find({}))
    incomplete = set()
    for app in applicants:
            if len(app['graded_by']) < 2:
                incomplete.add((app['first_name'], app['last_name'], app['time_created']))
    incomplete = list(incomplete)
    return json.dumps(incomplete)

if __name__ == '__main__':
    application.run(debug=True)

# Rebooting Server Test 5
