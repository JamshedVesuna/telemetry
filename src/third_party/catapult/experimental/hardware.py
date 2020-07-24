#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Query build subordinate hardware info, and print it to stdout as csv."""

import csv
import json
import sys
import urllib2


_MASTERS = [
    'chromium.perf',
    'tryserver.chromium.perf',
]


_KEYS = [
    'main', 'builder', 'hostname',

    'os family', 'os version',

    'product name', 'architecture', 'processor count', 'processor type',
    'memory total',

    'facter version', 'git version', 'puppet version', 'python version',
    'ruby version',

    'android device 1', 'android device 2', 'android device 3',
    'android device 4', 'android device 5', 'android device 6',
    'android device 7',
]
_EXCLUDED_KEYS = frozenset([
    'b directory',
    'last puppet run',
    'uptime',
    'windows version',
])


def main():
  writer = csv.DictWriter(sys.stdout, _KEYS)
  writer.writeheader()

  for main_name in _MASTERS:
    main_data = json.load(urllib2.urlopen(
      'http://build.chromium.org/p/%s/json/subordinates' % main_name))

    subordinates = sorted(main_data.iteritems(), key=lambda x: x[1]['builders'])
    for subordinate_name, subordinate_data in subordinates:
      for builder_name in subordinate_data['builders']:
        row = {
            'main': main_name,
            'builder': builder_name,
            'hostname': subordinate_name,
        }

        host_data = subordinate_data['host']
        if host_data:
          host_data = host_data.splitlines()
          if len(host_data) > 1:
            for line in host_data:
              if not line:
                continue
              key, value = line.split(': ')
              if key == 'osfamily':
                key = 'os family'
              if key in _EXCLUDED_KEYS:
                continue
              row[key] = value

        if 'product name' not in row and subordinate_name.startswith('subordinate'):
          row['product name'] = 'Google Compute Engine'

        writer.writerow(row)


if __name__ == '__main__':
  main()
