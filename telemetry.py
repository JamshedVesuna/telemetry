"""Writes a page set story, records a wpr file, and runs telemetry benchmarks

Usage: sudo python telemetry.py
"""
from os import geteuid

from telemetry_utils import *

def __main__():
    # Must run as root
    if geteuid() != 0:
        print "Must run as root"
        exit(1)

    # Clean up old sessions.
    reset_old_files()

    # Get url set.
    target_url_path = 'target_urls'
    urls = get_urls(target_url_path)

    # Write page_set and generate individual user stories.
    write_page_sets(urls)

    # Record WPR
    working_url_indices = []
    bad_urls = []
    for i in range(len(urls)):
        print 'Recording url {0}'.format(i)
        test_name = 'url{0}'.format(i)
        success = record_page_set('{0}_page_set'.format(test_name), urls[i])
        if success:
            working_url_indices.append(i)
        else:
            bad_urls.append(urls[i])

    for url in bad_urls:
        failed_url(url, 'Recording error')

    # Write a benchmark for each url.
    write_benchmarks(len(urls))

    # Run benchmark
    run_benchmarks(working_url_indices)

    # Write cold page load times, in milliseconds.
    plt_dict = {}
    for url_index in working_url_indices:
        plt_dict[url_index] = get_cold_plts(url_index)

    write_plts_to_file(plt_dict)


if __name__ == '__main__':
    __main__()
