

from collections import defaultdict

test = defaultdict(list)

test['rating0'].append('1')

test['rating0'] = 5

print(test['rating0'])