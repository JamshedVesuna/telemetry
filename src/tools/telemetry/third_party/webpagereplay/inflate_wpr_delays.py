#!/usr/bin/env python
"""Artificially inflate the delays of objects in a wpr file

Usage:
    python inflate_delays.py [--fixed=15] [--percentage=2] path_to_wprs/

Note: for compatibility with the "perfect cache" schema of telemetry.py and
telemetry_utils.py,  this file writes modified wpr files with the suffix '.pc'
"""
from httparchive import HttpArchive
import glob
import os
import re
from optparse import OptionParser

# Modified archive.
def inflate_delays(archive, fixed=0, percentage=1):
   for request in archive:
       response = archive[request]
       for key in response.delays:
           if type(response.delays[key]) == list:
               new_delays = []
               for item in response.delays[key]:
                   new_delays.append(item * percentage + fixed)
               response.delays[key] = new_delays
           else:
               response.delays[key] = response.delays[key] * percentage + fixed
       response.fix_delays()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
            '-f',
            '--fixed',
            dest='fixed',
            help='Fixed value, in ms, to add to each delay')
    parser.add_option(
            '-p',
            '--percentage',
            dest='percentage',
            help='Percentage to change delays by')

    options, args = parser.parse_args()

    if len(args) < 1:
        print 'args: %s' % args
        parser.error('Must specify a directory containing wpr files')

    # Default: add fixed delay of 0, and change percentage by a factor of 1
    # (which is nothing).
    fixed, percentage = 0, 1
    if options.fixed:
        fixed = int(options.fixed)
    if options.percentage:
        percentage = int(options.percentage)

    for wpr in glob.iglob(args[-1] + "/*.wpr"):
        archive = HttpArchive.Load(wpr)
        output_file = re.sub('.wpr$', '.pc.wpr', wpr)
        if not os.path.exists(output_file):
            inflate_delays(archive, fixed=fixed, percentage=percentage)
            archive.Persist(output_file)
