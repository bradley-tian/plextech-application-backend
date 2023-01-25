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
        judgments[review['grader']]['rating0'].append(
            (int(review['rating0']), review['applicantID']))
        judgments[review['grader']]['rating1'].append(
            (int(review['rating1']), review['applicantID']))
        judgments[review['grader']]['rating2'].append(
            (int(review['rating2']), review['applicantID']))
        judgments[review['grader']]['rating3'].append(
            (int(review['rating3']), review['applicantID']))
        judgments[review['grader']]['rating4'].append(
            (int(review['rating4']), review['applicantID']))

    for grader in judgments:
        z_0 = stats.zscore([x[0] for x in judgments[grader]['rating0']])
        z_1 = stats.zscore([x[0] for x in judgments[grader]['rating1']])
        z_2 = stats.zscore([x[0] for x in judgments[grader]['rating2']])
        z_3 = stats.zscore([x[0] for x in judgments[grader]['rating3']])
        z_4 = stats.zscore([x[0] for x in judgments[grader]['rating4']])

        for i in range(len(z_0)):
            judgments[grader]['rating0'][i] = (
                z_0[i], judgments[grader]['rating0'][i][1])
            judgments[grader]['rating1'][i] = (
                z_1[i], judgments[grader]['rating1'][i][1])
            judgments[grader]['rating2'][i] = (
                z_2[i], judgments[grader]['rating2'][i][1])
            judgments[grader]['rating3'][i] = (
                z_3[i], judgments[grader]['rating3'][i][1])
            judgments[grader]['rating4'][i] = (
                z_4[i], judgments[grader]['rating4'][i][1])

    evaluations = defaultdict(lambda: defaultdict(list))

    for grader in judgments:
        for i in range(len(judgments[grader]['rating0'])):
            evaluations[judgments[grader]['rating0'][i][1]]['rating0'].append(
                judgments[grader]['rating0'][i][0])
            evaluations[judgments[grader]['rating1'][i][1]]['rating1'].append(
                judgments[grader]['rating1'][i][0])
            evaluations[judgments[grader]['rating2'][i][1]]['rating2'].append(
                judgments[grader]['rating2'][i][0])
            evaluations[judgments[grader]['rating3'][i][1]]['rating3'].append(
                judgments[grader]['rating3'][i][0])
            evaluations[judgments[grader]['rating4'][i][1]]['rating4'].append(
                judgments[grader]['rating4'][i][0])

    for eval in evaluations:
        evaluations[eval]['rating0'] = np.mean(evaluations[eval]['rating0'])
        evaluations[eval]['rating1'] = np.mean(evaluations[eval]['rating1'])
        evaluations[eval]['rating2'] = np.mean(evaluations[eval]['rating2'])
        evaluations[eval]['rating3'] = np.mean(evaluations[eval]['rating3'])
        evaluations[eval]['rating4'] = np.mean(evaluations[eval]['rating4'])

    data = []

    for applicant in evaluations.keys():
        eval = {}

        # Edit weighings here
        w0, w1, w2, w3, w4 = 0.2, 0.2, 0.2, 0.2, 0.2

        eval['applicantID'] = applicant
        eval.update(evaluations[applicant])
        eval['total'] = round(((eval['rating0'] * w0 +
                         eval['rating1'] * w1 +
                         eval['rating2'] * w2 +
                         eval['rating3'] * w3 +
                         eval['rating4'] * w4) * 100), 2)

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


if __name__ == '__main__':
    application.run(debug=True)

# Rebooting Server Test
