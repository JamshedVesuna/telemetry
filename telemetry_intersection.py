"""Records each url x times and finds the intersection of all resources

Usage: sudo python telemetry.py -t 5
"""
from glob import glob
from optparse import OptionParser
from shutil import move

from telemetry_utils import *

def __main__():
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

    local_path = 'src/tools/perf/page_sets/data/url*.wpr'
    remote_path = '/tmp/'

    # Record WPR
    working_url_indices = set()
    bad_urls = []
    for i in range(len(urls)):
        print 'Recording url {0}'.format(i)
        test_name = 'url{0}'.format(i)
        for trial in range(NUMBER_OF_TRIALS):
            success = record_page_set('{0}_page_set'.format(test_name), urls[i])
            if success:
                working_url_indices.add(i)
            else:
                bad_urls.append(urls[i])
                break

            # Finicky python and wpr interfacing.
            files = glob('src/tools/perf/page_sets/data/url*.wpr')
            if len(files) != 1:
                raise Exception(
                        'Requires 1 wpr file in src/tools/perf/page_sets/data')
            move(files[0], remote_path)


    remote_files = glob('/tmp/url*.wpr')
    [move(f, 'src/tools/perf/page_sets/data/') for f in remote_files]

    working_url_indices = list(working_url_indices)

    for index in working_url_indices:
        request_intersection, response_intersection = \
                get_wpr_intersection(index, NUMBER_OF_TRIALS)

        write_intersection(index, request_intersection, response_intersection)



    # for url in bad_urls:
        # failed_url(url, 'Recording error')

    # # Write a benchmark for each url.
    # write_benchmarks(len(urls))

    # # Run benchmark
    # run_benchmarks(working_url_indices)

    # # Write cold page load times, in milliseconds.
    # plt_dict = {}
    # for url_index in working_url_indices:
        # plt_dict[url_index] = get_cold_plts(0)

    # write_plts_to_file(plt_dict)


if __name__ == '__main__':
    __main__()
