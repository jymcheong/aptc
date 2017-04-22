#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-

from pymisp import PyMISP
from key import *
import json
import time
import os
from urllib.parse import urljoin
import sys
import traceback
from shutil import copyfile
import logging.handlers
from urllib.parse import quote
import argparse


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log')
formatter = logging.Formatter('APTC: [%(levelname)s][%(filename)s:%(funcName)s():line %(lineno)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# ensure prefix ends with /
conf_target_path_prefix = '/opt/aptc/targets/'  # in case of changing path
conf_script_path_prefix = os.path.dirname(os.path.realpath(__file__)) + '/'  # change to /opt/pec later
conf_vm_wait_sec = 60 * 5
conf_poll_sleep_interval_sec = 2
conf_graylog_poll_timeout_sec = 60 * 1
conf_tag_prefix = 'aptc:'

target_query_strings = {}  # hostname:query_string


def init(url, key):
    return PyMISP(url, key, False, 'json', False)


def get_all_target_host_names(test_case):
    host_names = []
    share_paths = get_all_target_share_paths(test_case)
    for t in share_paths:
        hn = t.split('/')
        host_names.append(hn[len(hn)-1])
    return host_names


def get_all_target_share_paths(test_case):
    share_paths = []
    targets = get_related_targets(test_case)
    for t in targets:
        share_paths.append(t['Event']['info'])
    return share_paths


def get_related_targets(test_case):
    targets = []
    if 'RelatedEvent' not in str(test_case):
        return targets
    for re in test_case['Event']['RelatedEvent']:
        if re['Event']['info'].startswith(conf_target_path_prefix):
            targets.append(re)
    return targets


def get_all_query_strings(m, testcase_id=0):
    found = False
    r = m.search(eventid=testcase_id)
    if 'Tag' not in str(r):
        logger.error(str(r))
        return found
    for e in r['response']:
        for t in e['Event']['Tag']:
            if t['name'] != conf_tag_prefix + 'test-in-progress':
                continue
            found = True
            related = get_related_targets(e)
            for r in related:
                if r['Event']['info'] in target_query_strings:
                    continue
                qs = get_target_query_string(m, r['Event']['id'])
                target_query_strings[r['Event']['info']] = qs
    return found


def write_payload(m, payload_id, test_case):
    status, samples = m.download_samples(False, payload_id)
    if not status:
        return status
    share_paths = get_all_target_share_paths(test_case)
    total_sample_count = len(samples)
    for vm_path in share_paths:
        sample_counter = 0
        for sample in samples:
            sample_counter += 1
            filepath = vm_path + '/' + sample[1]
            with open(filepath, 'wb') as out:
                try:
                    out.write(sample[2].read())
                    logger.debug('wrote: ' + filepath)
                    sample[2].seek(0)  # otherwise next target will get a 0 byte file
                    if sample_counter == total_sample_count:
                        get_start_bat(m, payload_id, vm_path)
                except OSError:
                    logger.error('fail writing ' + filepath)
                    continue
                if sample_counter == 1:  # tag only the first sample
                    tag(m, payload_id, conf_tag_prefix + 'test-in-progress')
                    logger.debug('tagged ' + str(payload_id) + ' with ' + conf_tag_prefix + 'test-in-progress')
                    hostname = vm_path.replace(conf_target_path_prefix, '')
                    newtag = conf_tag_prefix + '{"target":"' + hostname + '","testcase-id":'
                    newtag += str(test_case['Event']['id']) + ',"filename":"' + sample[1] + '"}'
                    m.new_tag(newtag, '#000000', True)
                    tag(m, payload_id, newtag)
    return status


def get_payload_tags(test_case):
    t = []
    if 'Tag' not in str(test_case):
        return t
    if 'Tag' in test_case['Event']:
        for et in test_case["Event"]["Tag"]:
            if et['name'].startswith(conf_tag_prefix + 'payload'):
                t.append(et['name'])
    return t


def find_tag(m, eid, tag):
    r = m.search(eventid=eid)
    if 'Tag' not in str(r):
        return False
    if 'Tag' in r['response'][0]['Event']:
        for t in r['response'][0]['Event']['Tag']:
            if t['name'].startswith(tag):
                return True
    return False


def get_all_tags(m, eid):
    r = m.search(eventid=eid)
    if 'Tag' not in str(r):
        return []
    if 'Tag' in r['response'][0]['Event']:
        return r['response'][0]['Event']['Tag']
    return []


def dump(r):
    print(json.dumps(r, indent=2))


def wait_for_targets(m, payload_id, test_case):
    timeout_sec = conf_vm_wait_sec
    all_vm = get_all_target_host_names(test_case)
    while len(all_vm) > 0:
        for vm in all_vm:
            tags = get_all_tags(m, payload_id)  # payload may have old results
            tags_str = str(tags)
            if 'result_' in tags_str and vm in tags_str:
                if vm in all_vm:
                    all_vm.remove(vm)
                if len(all_vm) == 0:
                    break
        time.sleep(conf_poll_sleep_interval_sec)
        timeout_sec -= conf_poll_sleep_interval_sec
        if timeout_sec <= 0:
            logger.error('abort due to timeout')
            exit()
    untag(m, payload_id, conf_tag_prefix + 'test-in-progress')
    logger.info('All VM(s) done for payload-' + str(payload_id))


def tag(m, eid, tagname):
    try:
        r = m.get_event(eid)
        m.tag(r['Event']['uuid'], tagname)
        logger.debug('tag event ' + str(eid) + ' with ' + str(tagname))
    except:
        logger.debug(traceback.format_exc())
    return True


def untag(m, eid, tagname):
    r = m.search(eventid=eid)
    if 'uuid' not in str(r):
        logger.error(str(r))
        return False
    uuid = r['response'][0]['Event']['uuid']
    for t in r['response'][0]['Event']['Tag']:
        if t['name'] == tagname:
            logger.debug('untagged ' + tagname + ' from ' + uuid)
            m.untag(uuid, t['id'])
            return True


def delete_tag(m, eventid, tagname):
    r = m.search(eventid=eventid)
    if 'Tag' not in str(r):
        logger.error(str(r))
        return
    for t in r['response'][0]['Event']['Tag']:
        if t['name'] == tagname:
            logger.info('found tagid ' + t['id'])
            session = m._PyMISP__prepare_session()
            url = urljoin(m.root_url, 'tags/delete/{}'.format(t['id']))
            session.post(url)
    return


def get_target_query_string(m, target_id):
    r = m.search(eventid=target_id)
    if 'Attribute' not in str(r):
        return ''
    for a in r['response'][0]['Event']['Attribute']:
        if a['comment'].startswith('graylog'):
            return a['value']
    return ''


def create_n_tag(m, eventid, tagname, tagcolor):
    m.new_tag(tagname, tagcolor, True)
    tag(m, eventid, tagname)


def get_start_bat(m, payload_id, target_path):
    r = m.search(eventid=payload_id)
    if 'Attribute' not in str(r):
        logger.error(str(r))
        return

    for a in r['response'][0]['Event']['Attribute']:
        if a['comment'].lower() != 'start.bat':
            continue
        with open(target_path + '/start.bat', 'w') as out:
            try:
                out.write(a['value'])
                logger.info('wrote: ' + target_path + '/start.bat')
            except:
                logger.error('fail writing start.bat for payload ' + payload_id)
                return
    return


def query_graylog(m, query, filename=''):
    session = m._PyMISP__prepare_session() # I know this is bad thing...
    url = query
    if len(filename) == 0:
        url = url.replace('FILENAME%20AND%20', '')
    else:
        url = url.replace('FILENAME', quote(filename))
    response = session.get(url)
    r = json.loads(response.text)
    return int(r['total_results'])


def get_reboot_wait_query(m, target_id):
    q = ''
    r = m.search(eventid=target_id)
    if 'id' not in str(r):
        return q
    for e in r['response']:
        for a in e['Event']['Attribute']:
            if 'reboot' in a['comment']:
                q = a['value']
                break
    return q


def rollback_targets(m, test_case):
    target_paths = {}
    wait_vm = []
    wait_sec = conf_vm_wait_sec
    if 'RelatedEvent' not in str(test_case):
        return
    if len(test_case['Event']['RelatedEvent']) == 0:
        return
    logger.info('starting target roll-back...')
    for rt in test_case['Event']['RelatedEvent']:
        if rt['Event']['info'].startswith(conf_target_path_prefix):
            target_paths[rt['Event']['info']] = get_reboot_wait_query(m, rt['Event']['id'])
            if len(target_paths[rt['Event']['info']]) > 0:
                copyfile(conf_target_path_prefix + 'shutdown.bat', rt['Event']['info'] + '/start.bat')
                wait_vm.append(rt['Event']['info'])
    logger.info('waiting for target reboot...')
    while len(wait_vm) > 0:
        for k, v in target_paths.items():
            try:
                rc = query_graylog(m, v)
            except BaseException as e:
                logger.error('graylog query failed: ' + str(e))
                error_tag = conf_tag_prefix + ' roll-back error with graylog result poll', '#aa0000'
                create_n_tag(m, test_case['Event']['id'], error_tag)
                return
            if rc > 0:
                if k in wait_vm:
                    wait_vm.remove(k)
                    logger.debug(str(len(wait_vm)) + ' left...')
        wait_sec -= conf_poll_sleep_interval_sec
        if wait_sec <= 0:
            break
        time.sleep(conf_poll_sleep_interval_sec)
    return
