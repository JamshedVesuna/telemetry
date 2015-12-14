"""Records each url x times and finds the intersection of all resources

Usage: sudo python telemetry.py -t 5
"""
from optparse import OptionParser

from telemetry_utils import *

def __main__():
    # Must run as root
    # if geteuid() != 0:
        # print "Must run as root"
        # exit(1)

    # Get the number of trials to run for each url
    parser = OptionParser()
    parser.add_option('-t', '--trials', action='store', dest='trials',
        help='number of trials to run each url and modified url')
    options, args = parser.parse_args()
    if options.trials is None:
        parser.error('Must specify number of trials with -t')
    NUMBER_OF_TRIALS = int(options.trials)
    if NUMBER_OF_TRIALS > 9:
        raise ValueError('Number of trials must be less than 10')

    # Clean up old sessions.
    reset_old_files()

    # Get url set.
    target_url_path = 'target_urls'
    urls = get_urls(target_url_path)

    # Write page_set and generate individual user stories.
    write_page_sets(urls)

    # Record WPR
    working_url_indices = set()
    bad_urls = []
    for i in range(len(urls)):
        print 'Recording url {0}'.format(i)
        test_name = 'url{0}'.format(i)
        for i in range(NUMBER_OF_TRIALS):
            success = record_page_set('{0}_page_set'.format(test_name), urls[i])
            if success:
                working_url_indices.add(i)
            else:
                bad_urls.append(urls[i])
                break

    working_url_indices = list(working_url_indices)

    for index in working_url_indices:
        wpr_resource_intersection = get_wpr_intersection(index, NUMBER_OF_TRIALS)

    return

    for url in bad_urls:
        failed_url(url, 'Recording error')

    # Write a benchmark for each url.
    write_benchmarks(len(urls))

    # Run benchmark
    run_benchmarks(working_url_indices)

    # Write cold page load times, in milliseconds.
    plt_dict = {}
    for url_index in working_url_indices:
        plt_dict[url_index] = get_cold_plts(0)

    write_plts_to_file(plt_dict)


if __name__ == '__main__':
    __main__()
