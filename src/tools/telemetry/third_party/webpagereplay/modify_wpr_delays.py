#!/usr/bin/env python
"""Sets header delays to 0ms for every cacheable object in each .wpr file in
the given directory and writes the output to <filename>.pc.wpr

Usage: python modify_wpr_delays.py <directory containing wpr files>

Note: Does not overwrite existing *.pc.wpr files
See httparchive.py.ArchivedHttpResponse.fix_delays() for delay setting
"""

# TODO(cs): make cache hit ratio tunable.
# TODO(cs): two analyses: perfect cachability at proxy, and perfect
# cachability in browser. Use CC: private vs. CC: public to make distinction.
# TODO(cs): don't assume that cache is co-located with browser, i.e. insert
# delays between browser and perfect cache.
# TODO(cs): account for performance cost of conditional GETs
# TODO(cs): show a CDF of fraction of response bytes that are cacheable per
# site.
# TODO(cs): show a PDF of cache expiration date weighted by number of bytes
# per resource. Intuition: nearly impossible to have perfect cache for objects
# with very short expirations.

from httparchive import HttpArchive
from random import shuffle
import glob
import os
import re
import optparse

def get_random_indices(indices, percentage):
    """Returns a subset list of random indicies"""
    shuffle(indices)
    return indices[:int(len(indices)*percentage)]

# Modified archive.
def assume_perfect_cache(archive, percentage, item_dict):
  cacheable_indices = []
  i = 0
  for request in archive:
    response = archive[request]
    if is_cacheable(response):
        cacheable_indices.append(i)
    i += 1
  rand = get_random_indices(range(i), percentage)

  i = 0
  cached = []
  for request in archive:
    response = archive[request]
    if item_dict == []:
        if is_cacheable(response) and i in rand:
          print "Caching an object!"
          response.delays = None
          response.fix_delays()
          cached.append(response)
    elif response in item_dict:
      print "Caching an object!"
      response.delays = None
      response.fix_delays()

    i += 1

  return cached

def is_cacheable(response):
  # We use an array to handle the case where there are redundant headers. The
  # most restrictive caching header wins.
  cc_headers = []
  expires_headers = []
  for (name, value) in response.headers:
    if re.match("cache-control", name, re.IGNORECASE):
      cc_headers.append(value)
    if re.match("expires", name, re.IGNORECASE):
      expires_headers.append(value)

  # N.B. we consider undefined as cacheable.
  # WHEN LENGTH(resp_cache_control) = 0
  #   AND LENGTH(resp_expires) = 0
  #   THEN "undefined"
  if cc_headers == [] and expires_headers == []:
    return True

  # WHEN resp_cache_control CONTAINS "no-store"
  #   OR resp_cache_control CONTAINS "no-cache"
  #   OR resp_cache_control CONTAINS "max-age=0"
  #   OR resp_expires = "-1"
  #   THEN "non-cacheable"
  for cc_header in cc_headers:
    if (re.match("no-store", cc_header, re.IGNORECASE) or
        re.match("no-cache", cc_header, re.IGNORECASE) or
        re.match("max-age=0", cc_header, re.IGNORECASE)):
      return False

  for expires_header in expires_headers:
    if re.match("-1", expires_header, re.IGNORECASE):
      return False

  # ELSE "cacheable"
  return True

if __name__ == '__main__':
  option_parser = optparse.OptionParser(
      usage='%prog <directory containing wpr files>')

  options, args = option_parser.parse_args()

  if len(args) < 1:
    print 'args: %s' % args
    option_parser.error('Must specify a directory containing wpr files')

  for wpr in glob.iglob(args[0] + "/*.wpr"):
    archive = HttpArchive.Load(wpr)
    output_file = re.sub('.wpr$', '.pc.wpr', wpr)
    output_file2 = re.sub('.wpr$', '.p2c.wpr', wpr)
    if not os.path.exists(output_file):
      print "Caching"
      cached_responses = assume_perfect_cache(archive, 0.3, [])
      archive.Persist(output_file)

      # 60% of 30% is 20%
      print "next"
      cached_responses = assume_perfect_cache(HttpArchive.Load(wpr), 0.2, cached_responses[:int((2/3)*len(cached_responses))])
      archive.Persist(output_file2)
