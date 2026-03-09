import requests

r = requests.post('http://localhost:8000/api/study-plan/generate', json={
    'subject_code': 'OB',
    'units': [1, 2, 3, 4, 5],
    'hours_per_day': 2,
    'section': 'C',
    'custom_request': 'Create a study plan for units 1-3 in 2 hours'
})
data = r.json()
plan = data['plan']
md = plan['plan_markdown']
with open('test_out.md', 'w', encoding='utf-8') as f:
    f.write(md)
print('Length:', len(md))
print(md[:600])
