#!/usr/bin/env python3
"""Sanity-check generated sapling_overrides the way Treeplacer's parser sees them.

Usage: python3 .dev/validate_overrides.py <glob-root> [id-out-file]
"""

import json
import glob
import sys

root = sys.argv[1] if len(sys.argv) > 1 else 'data'
pattern = root.rstrip('/') + '/*/sapling_overrides/*/minecraft/*.json'

ids = set()
bad = []
for path in sorted(glob.glob(pattern)):
    tail = path.split('sapling_overrides/')[1].split('/')
    if len(tail) != 3:
        bad.append((path, 'unexpected path depth %r' % tail))
    data = json.load(open(path))
    if 'replace' not in data or 'values' not in data:
        bad.append((path, 'missing replace/values'))
        continue
    for key, value in data['values'].items():
        if ':' not in key:
            bad.append((path, 'unnamespaced key ' + key))
        if isinstance(value, str):
            ids.add(value)
        else:
            total = sum(entry['weight'] for entry in value)
            if total != 100:
                bad.append((path, '%s weights sum to %d' % (key, total)))
            for entry in value:
                ids.add(entry['feature'])

print('files: OK' if not bad else 'PROBLEMS:')
for path, why in bad:
    print('  %s: %s' % (path, why))
print('distinct features: %d' % len(ids))

if len(sys.argv) > 2:
    with open(sys.argv[2], 'w') as fh:
        fh.write('\n'.join(sorted(ids)) + '\n')

sys.exit(1 if bad else 0)
