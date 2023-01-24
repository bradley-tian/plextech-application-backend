import requests
import json

print((requests.get('http://127.0.0.1:5000/evaluate_results').json()))