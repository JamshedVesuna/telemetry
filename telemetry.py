"""Writes a page set story, records a wpr file, and runs telemetry benchmarks

Usage: sudo python telemetry.py
"""
from base64 import urlsafe_b64encode, urlsafe_b64decode
from glob import glob
from subprocess import Popen, PIPE, STDOUT
from os import geteuid

def prescreenUrl(url):
    """Returns bool if url is online and available

    :param url: str url
    """
    if url == '':
        return False

    cmd = 'wget --spider -t 1 -T 10 {0} -O /dev/null'.format(url)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    out, err = p.communicate()

    if p.returncode != 0:
        return False

    failed = ['404 Not Found', 'Giving up', 'failed', 'FAILED',
            'Connection timed out']
    if any(x in out for x in failed):
        return False
    return True


def record_page_set(page_set, url, options='--browser=system'):
    """Runs wpr with telemetry to record an initial target page set

    :param page_set: str filename of the page set
    :param url: str url used if url fails
    :param options: chromium browser options
    """
    record_path = './record_wpr'
    cmd = ' '.join([record_path, options, page_set])
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    output, err = p.communicate()

    # Silently fail, push output to failed_urls
    if p.returncode == 1 or 'FAILED' in output or 'PASSED' not in output:
        print 'Url failed: ' + url
        return False
    return True


def get_urls(path):
    """Returns a list of urls from path

    :param path: str relative (to PLT_SRC/telemetry) or absolute path to target
    urls
    """
    urls = []
    with open(path, 'rb') as f:
        urls = [x.strip() for x in f.readlines()]

    # Prune urls that are not working
    goodUrls = []
    for url in urls:
        if prescreenUrl(url):
            print "PASS prescreen: " + str(url)
            goodUrls.append(url)
        else:
            print "FAIL prescreen: " + str(url)
            failed_url(url)

    with open(path, 'wb') as f:
        f.write('\n'.join(goodUrls))
        f.close()

    return goodUrls


def write_page_sets(urls):
    """Writes a page set file for each url (and its modified version) in urls

    Writes to src/tools/perf/page_sets/
    :param urls: A list of url strings
    """
    template = ''
    page_set_path = 'src/tools/perf/page_sets/'

    with open('wpr_template.py', 'rb') as f:
        template = ''.join(f.readlines())
        assert template, 'Failed to read from page set template'

    for i in range(len(urls)):
        with open('{0}/url{1}.py'.format(page_set_path, i), 'wb') as f:
            f.write(template.format(i, urls[i]))


def failed_url(url, output):
    """Url failed to record, place it in failed_urls

    :param url: str url
    :param output: str output of the failure
    """
    with open('failed_urls', 'a') as f:
        f.write('{0}: {1}\n'.format(url, output))


def write_benchmarks(num_urls):
    """Writes url{0}.py, the benchmark for Chromium to run

    Writes benchmarks to src/tools/perf/benchmarks/

    :param num_urls: int of the number of urls to create benchmarks for
    """
    template = ''
    benchmark_path = 'src/tools/perf/benchmarks'

    with open('benchmark_template.py', 'rb') as f:
        template = ''.join(f.readlines())
        assert template, 'Failed to read from benchmark template'

    for i in range(num_urls):
        with open('{0}/url{1}.py'.format(benchmark_path, i), 'wb') as f:
            f.write(template.format(i))


def run_benchmarks(urlIndices):
    """Runs the telemetryBenchmarks benchmark for each url

    Dumps data results/
    :param urlIndices: a list of int indices from the original list
    """
    benchmark_path = './run_benchmark'

    for index in urlIndices:
        page_set = 'page_cycler.url{0}'.format(index)
        cmd = ' '.join(['sudo', benchmark_path, page_set,
            '> results/url{0}.out'.format(index)])

        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output, err = p.communicate()

        if p.returncode != 0:
            raise Exception('Return code for url {0} was {1}'.format(
                index, p.returncode))


def reset_old_files():
    """Deletes old files to make way for a new run

    Removes:
    src/tools/perf/page_sets/url*
    src/tools/perf/page_sets/data/url*
    src/tools/perf/benchmarks/*
    src/tools/perf/results.html
    results/url*
    """
    commands = [
        'rm -f src/tools/perf/page_sets/url*',
        'rm -f src/tools/perf/page_sets/data/url*',
        'rm -f src/tools/perf/benchmarks/url*',
        'rm -f src/tools/perf/results.html',
        'rm -f results/*',
            ]

    for cmd in commands:
        p = Popen(cmd, shell=True)
        p.wait()


def generate_hars():
    """Merge plts and wprs into a har file

    Stores 2 .har files per url (regular and modified) in data/replay/
    """
    results_path = 'data/results.db'
    results_data = {}
    try:
        results_data = pickle.load(open(results_path, 'rb'))
    except IOError:
        raise IOError('Could not read from {0}'.format(results_path))

    wpr_path = 'data/wpr_source'
    wpr_files = filter(lambda x: '.wpr' in x, os.listdir(wpr_path))
    for wpr_file in wpr_files:
        curr_wpr = cPickle.load(open(os.path.join(wpr_path, wpr_file), 'rb'))
        curr_har_dict = {'log':
                            {'pages':
                                [{'id': '',
                                 'title': '',
                                 'pageTimings': {
                                        'onContentLoad': None,
                                        'onLoad': None
                                        }
                                 }],
                             'entries': []
                            }
                        }
        wpr_host = None
        print wpr_file
        for key, value_lst in zip(curr_wpr.keys(), curr_wpr.values()):
            matches = [full_url for full_url in results_data.keys() if \
                    key.host in full_url]
            if matches:
                if len(matches) != 1:
                    print "Found 2 urls with the same name!"
                    print matches
                    continue
                assert len(matches) == 1, ('Found more than 1 match for'
                        ' {0}'.format(matches))
                agg_key = matches[0]
                # Found a match!
                curr_har_dict['log']['pages'][0]['id'] = key.host
                curr_har_dict['log']['pages'][0]['title'] = key.host
                if '_pc' in wpr_file:
                    wpr_host = urlsafe_b64encode(agg_key) + '.pc'
                    # It's a modified wpr file
                    curr_har_dict['log']['pages'][0]['pageTimings']['onLoad'] \
                            = results_data[agg_key]['modified_cold_time']
                else:
                    wpr_host = urlsafe_b64encode(agg_key)
                    # It's an original wpr file
                    curr_har_dict['log']['pages'][0]['pageTimings']['onLoad'] \
                            = results_data[agg_key]['cold_time']
            else:
                # This website is loading a third party object
                # Still include this in the har file
                pass
            # Add to each element to entries
            # Request data
            method = key.command
            element_url = key.host + key.full_path
            # Response data
            status = value_lst.status
            # TODO: Correct way to calculate headersSize and bodySize?
            headerSize = 0  # Need to find this in value_lst
            bodySize = 0  # Need to find this in value_lst
            # Create each element's header list
            tmp_header_lst = []
            for name, value in value_lst.headers:
                if 'content-length' in name:
                    bodySize = int(value)
                headerSize += len(name) + len(value)  # This should be verified
                tmp_header_lst.append({'name': name, 'value': value})

            tmp_entry = {
                        'request': {
                            'method': None,
                            'url': None
                            },
                        'response': {
                                'status': None,
                                'headers': [],
                                'headersSize': None,
                                'bodySize': None
                            }
                    }
            curr_entry = tmp_entry.copy()
            curr_entry['request']['method'] = method
            curr_entry['request']['url'] = element_url
            curr_entry['response']['status'] = status
            curr_entry['response']['headers'] = tmp_header_lst
            curr_entry['response']['headersSize'] = headerSize
            curr_entry['response']['bodySize'] = bodySize

            curr_har_dict['log']['entries'].append(curr_entry)

        # Write to har file
        if wpr_host is None:
            print 'Could not create host from url: {0}'.format(wpr_file)
            continue

        har_path = '../data/replay/'
        file_name = har_path + wpr_host + '.har'  # Modified for har processing
        with open(file_name, 'wb') as f:
            try:
                json.dump(curr_har_dict, f)
            except:
                # Silently fail
                print "Unable to write har file: " + str(file_name)


def __main__():
    # Must run as root
    if geteuid() != 0:
        print "Must run as root"
        exit(1)

    # Clean up old sessions
    reset_old_files()

    # Get url set
    target_url_path = 'target_urls'
    urls = get_urls(target_url_path)

    # Write page_set and generate individual user stories
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

    # Write a benchmark for each url
    write_benchmarks(len(urls))

    # Run benchmark
    run_benchmarks(working_url_indices)

if __name__ == '__main__':
    __main__()
