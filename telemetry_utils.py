from base64 import urlsafe_b64encode, urlsafe_b64decode
from glob import glob
from shutil import move, copy
from subprocess import Popen, PIPE, STDOUT
from sys import path
import cPickle
import cPickle
import json
import os
import pickle
import re

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


def record_page_set(page_set, url, options='--browser=android-jb-system-chrome --chrome-root=/home/jamshed/src/'):
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
            failed_url(url, 'failed prescreen check')

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
        # TODO(jvesuna): pc page sets may not be necessary.
        with open('{0}/url{1}_pc.py'.format(page_set_path, i), 'wb') as f:
            f.write(template.format(str(i) + '_pc', urls[i]))


def failed_url(url, output):
    """Url failed to record, place it in failed_urls

    :param url: str url
    :param output: str output of the failure
    """
    with open('failed_urls', 'a') as f:
        f.write('{0}: {1}\n'.format(url, output))


def move_wpr_files(name_schema):
    """Moves wpr files from within src/ to local data directory

    :param name_schema: regex for the matching filename for wpr files
    """
    remote_data_path = os.path.join('src/tools/perf/page_sets/data/',
        name_schema)
    local_path = 'tmp_data/'
    # Uses shutil.move
    [move(f, local_path) for f in glob(remote_data_path)]


def modify_wpr():
    """Sets cacheable objects delay time to 0, creates pc.wpr files

    Note: *.pc.wpr files are converted to url{index}_pc.wpr, which lets
    them be treated like regular urls.
    """
    wpr_directory = 'tmp_data/'
    wpr_path = \
            'src/tools/telemetry/third_party/webpagereplay/modify_wpr_delays.py'
    p = Popen('python {0} {1}'.format(wpr_path, wpr_directory), shell=True)
    p.wait()
    pc_files = filter(lambda x: 'pc' in x, os.listdir(wpr_directory))
    for pc_file in pc_files:
        insert_index = pc_file.find('_page')
        new_file = pc_file[:insert_index] + '_pc' + pc_file[insert_index:]
        new_file = new_file.replace('.pc', '')
        # Uses shutil.move
        move(os.path.join(wpr_directory, pc_file), os.path.join(wpr_directory,
            new_file))


def copy_wpr_to_benchmark():
    """Copies wpr and _pc.wpr (all) files from local tmp_data/ to src/"""
    local_path = 'tmp_data/*'
    remote_data_path = 'src/tools/perf/page_sets/data/'
    # Uses shutil.copy
    [copy(f, remote_data_path) for f in glob(local_path)]


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
        with open('{0}/url{1}_pc.py'.format(benchmark_path, i), 'wb') as f:
            f.write(template.format(str(i) + '_pc'))


def run_benchmarks(urlIndices):
    """Runs the telemetryBenchmarks benchmark for each url

    Dumps data results/
    :param urlIndices: a list of int indices from the original list
    """
    benchmark_path = './run_benchmark'

    for index in urlIndices:
        for modified_index in [index, str(index) + '_pc']:
            print 'Running benchmark for url {0}'.format(modified_index)
            page_set = 'page_cycler.url{0}'.format(modified_index)
            options = '--browser=android-jb-system-chrome --chrome-root=/home/jamshed/src/'
            cmd = ' '.join(['sudo', benchmark_path, options, page_set,
                '> results/url{0}.out'.format(modified_index)])

            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            output, err = p.communicate()

            # Fail silently for now.
            if p.returncode != 0:
                failed_url('url{0}'.format(modified_index), str(p.returncode))
                print'Return code for url {0} was {1}'.format(modified_index, p.returncode)


def reset_old_files():
    """Deletes old files to make way for a new run

    Removes:
    results/*
    src/tools/perf/benchmarks/*
    src/tools/perf/page_sets/data/url*
    src/tools/perf/page_sets/url*
    src/tools/perf/results.html
    tmp_data/*
    """
    commands = [
        'rm -f results/*',
        'rm -f src/tools/perf/benchmarks/url*',
        'rm -f src/tools/perf/page_sets/data/url*',
        'rm -f src/tools/perf/page_sets/url*',
        'rm -f src/tools/perf/results.html',
        'rm -f tmp_data/*',
            ]

    for cmd in commands:
        p = Popen(cmd, shell=True)
        p.wait()


def get_cold_plts(url_index):
    """Returns a list of cold page load times as floats for a given url index

    :param url_index: int index of a url in results/
    """
    # TODO(jvesuna): This is ugly. Make it beautiful.
    cmd = \
        "sed -n 's/\*RESULT cold_times: page_load_time= //p' results/url{0}.out"
    output = Popen(cmd.format(url_index), shell=True, stdout=PIPE)
    string_vals = output.stdout.read().strip(' ms\n')[1:-1].split(',')
    plts = [float(x) for x in string_vals if x]

    return plts


def write_plts_to_file(plt_dict):
    """Writes a dict of plts to a results/plts.out in json human readable format

    :param plt_dict: dict of index to list of plts
    """
    with open('results/plts.out', 'w') as f:
        json.dump(plt_dict, f)


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
        har_path = 'hars/'
        file_name = os.path.join(har_path, wpr_host, '.har')
        with open(file_name, 'wb') as f:
            try:
                json.dump(curr_har_dict, f)
            except:
                # Silently fail
                print "Unable to write har file: " + str(file_name)


def get_wpr(index, trial=0):
    """Returns a wpr http archive dict for a given url

    :param index: int url number in src/tools/perf/page_sets/data
    :param trial: int url trial number in url0_page_00{0}.wpr
    """
    wpr_path = 'src/tools/perf/page_sets/data'
    wpr_file = 'url{0}_page_00{1}.wpr'

    # Access httparchive.py
    path.append("src/tools/telemetry/third_party/webpagereplay/")
    full_path = os.path.join(wpr_path, wpr_file.format(index, trial))
    curr_wpr = cPickle.load(open(full_path, 'rb'))

    return curr_wpr


def get_wpr_stats(index, trial=0):
    """Returns a dict of wpr stats for the given url index

    :param index: int url number in src/tools/perf/page_sets/data
    """
    wpr_str = get_wpr(index, trial)
    wpr = json.loads(wpr_str)

    return wpr


def get_wpr_intersection(index, trials):
    """Returns a har object of the intersection of all resources in the url

    :param index: int index of the url in src/tools/perf/page_sets/data/url
    """
    all_wprs = []
    request_set = set()
    response_set = set()
    for i in range(trials):
        curr_wpr = get_wpr(index, i)

        curr_requests = set(curr_wpr.get_requests())
        curr_responses = set()
        for host in curr_wpr.responses_by_host.keys():
            for response in curr_wpr.responses_by_host[host].keys():
                curr_responses.add(response)

        if i == 0:
            request_set = curr_requests
            response_set = curr_responses
        else:
            request_set = request_set.intersection(curr_requests)
            response_set = response_set.intersection(curr_responses)

    return request_set, response_set

def write_intersection(index, request, response):
    """Writes a dict to results/url{index}.inter

    :param index: int index of the url
    :param request: the set of requests in all loads of the url
    :param responses: the set of responses in all loads of the url
    """
    pickle.dump({index: [[x for x in request], [x for x in response]]},
            open('results/{0}.inter'.format(index), 'wb'))


def write_json(urls):
    """Writes a *_pc.json file for each url

    Located in src/tools/perf/page_sets/data/
    :param urls: list of urls
    """
    for index, url in enumerate(urls):
        write_pc_json(index, url)

def write_pc_json(url_index, url):
    """Creates *_pc.json files to point to the modified archive files

    Located in src/tools/perf/page_sets/data/
    TODO: add sha1 to remove runtime WARNING

    :param url_index: int for the number of target urls
    :param url: str the url
    """
    json_path = 'src/tools/perf/page_sets/data/'
    json_template = ('{{ '
    '"description": "Describes the Web Page Replay archives for a story set. Dont edit by hand! Use record_wpr for updating.", '
    '"archives": {{ "url{0}_pc_page_000.wpr": [ "{1}" ] }} }}\n')

    file_name = os.path.join(json_path, 'url{0}_pc_page.json'.format(url_index))

    with open(file_name, 'wb') as f:
        f.write(json_template.format(url_index, url))

def get_min_plts_from_results(modified_url_index):
    """Returns the minimum page load time from results/plts.out for url_index

    :param modified_url_index: str index of the url in the list of target urls.
        Example: "1", "1_pc"
    """
    all_plts = {}
    with open('results/plts.out', 'r') as f:
        all_plts = json.load(f)

    if all_plts != {}:
        if modified_url_index in all_plts.keys():
            return min(all_plts[modified_url_index])

def generate_hars(urls):
    """Generates a HAR file from a WPR file

    Merge plts and wprs into a har file
    Stores 2 .har files per url (regular and modified) in hars/
    :param urls: list of string urls, ordered by the indices of target_urls
    """

    # Enable usage of httparchive.py
    path.append("src/tools/telemetry/third_party/webpagereplay/")

    wpr_path = 'tmp_data/'
    wpr_files = filter(lambda x: '.wpr' in x, os.listdir(wpr_path))
    for wpr_file in wpr_files:
        try:
            url_index = re.match('url([0-9]+)_', wpr_file).group(1)
        except:
            raise Exception('Unable to parse index from wpr file: {0}'.format(
                wpr_file))

        url_name = urls[int(url_index)]

        is_pc = False
        if "pc" in wpr_file:
            is_pc = True
            url_index += '_pc'
            # It's a modified wpr file
            wpr_host = urlsafe_b64encode(url_name) + '.pc'
        else:
            # It's an original wpr file
            wpr_host = urlsafe_b64encode(url_name)

        min_plt = get_min_plts_from_results(url_index)
        if min_plt is None:
            # Can't find the Page Load Time for this url.
            continue

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
        for key, value_lst in zip(curr_wpr.keys(), curr_wpr.values()):
            curr_har_dict['log']['pages'][0]['id'] = key.host
            curr_har_dict['log']['pages'][0]['title'] = key.host
            curr_har_dict['log']['pages'][0]['pageTimings']['onLoad'] = min_plt

            # Add to each element to entries
            # Request data
            method = key.command
            element_url = key.host + key.full_path
            # Response data
            status = value_lst.status

            # TODO(jvesuna): Correct way to calculate headersSize and bodySize?
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

        har_path = 'hars/'
        file_name = har_path + wpr_host + '.har'  # Modified for har processing
        with open(file_name, 'wb') as f:
            try:
                json.dump(curr_har_dict, f)
            except:
                # Silently fail
                print "Unable to write har file: " + str(file_name)

def write_valids():
    """Writes valid urls to /home/jamshed/page_load_time/data/filtered_stats"""
    har_path = "/home/jamshed/scripts/telemetry/hars/*"
    valid_path = "/home/jamshed/page_load_time/data/filtered_stats/valids.txt"
    har_files = [f for f in glob(har_path)]
    urls = \
        [urlsafe_b64decode(f.split('/')[-1].split('.')[0]) for f in har_files]
    with open(valid_path, 'w') as f:
        for url, url_har_path in zip(urls, har_files):
            f.write('{0} {1}\n'.format(url, url_har_path))
