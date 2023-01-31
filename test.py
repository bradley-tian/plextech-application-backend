import requests
import json

print(requests.get('https://plextech-application-backend-production.up.railway.app/evaluate_results').json())