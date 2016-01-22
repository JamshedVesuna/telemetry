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
import glob
import os
import re
import optparse

def get_random(percentage):
    """Returns a generator

    :param percentage: A decimal less than 1
    """
    i = 0
    while True:
        yield i % int((1/percentage))
        i += 1

# Modified archive.
def assume_perfect_cache(archive):
  rand = get_random(0.3)
  for request in archive:
    response = archive[request]
    if is_cacheable(response):
      if True:
          if rand.next() == 0:
              response.delays = None
              response.fix_delays()
      # Set all delays to zero:
      else:
          response.delays = None
          response.fix_delays()

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
    if not os.path.exists(output_file):
      assume_perfect_cache(archive)
      archive.Persist(output_file)
