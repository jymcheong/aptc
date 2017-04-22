#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-

from aptc import *


def check_testcase(m, test_case):
    if conf_tag_prefix + 'test-case' not in str(test_case):
        logger.error("ID provided is not a test-case")
        return False
    targets = test_case['Event']['RelatedEvent']
    if len(targets) == 0:
        create_n_tag(m, test_case['Event']['id'], conf_tag_prefix + 'error no targets', '#aa0000')
        return False
    for t in targets:
        qs = get_target_query_string(m, t['Event']['id'])
        if len(qs) == 0:
            create_n_tag(m, test_case['Event']['id'], conf_tag_prefix + 'error no query string for ' + t['Event']['info'], '#aa0000')
            return False
        if not os.path.exists(t['Event']['info']):
            create_n_tag(m, test_case['Event']['id'], conf_tag_prefix + 'error target path ' + t['Event']['info'] + ' does not exists', '#aa0000')
            return False
    return True


def clean_up(m, testcase_id):
    untag(m, testcase_id, conf_tag_prefix + 'test-in-progress')
    tag(misp, testcase_id, conf_tag_prefix + 'test-completed')
    logger.info('testcase ' + str(testcase_id) + ' completed')
    exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get payloads from MISP')
    parser.add_argument("-id", "--id", required=True, help="test-case integer id", type=int)
    args = parser.parse_args()
    testcase_id = int(args.id)

    misp = init(misp_url, misp_key)
    r = misp.search(eventid=testcase_id)
    if 'id' not in str(r):
        logger.error('event not found')
        exit()

    test_case = r['response'][0]
    if not check_testcase(misp, test_case):
        clean_up(misp, testcase_id)

    payload_tags = get_payload_tags(test_case)
    r = misp.search(not_tags=[conf_tag_prefix + 'test-case'], tags=payload_tags)
    if 'id' not in str(r) or len(payload_tags) == 0:
        create_n_tag(misp, testcase_id, conf_tag_prefix + 'error No payload found', '#aa0000')
        clean_up(misp, testcase_id)

    untag(misp, testcase_id, conf_tag_prefix + 'test-start')
    untag(misp, testcase_id, conf_tag_prefix + 'test-completed')
    tag(misp, testcase_id, conf_tag_prefix + 'test-in-progress')
    for payload in r['response']:
        if write_payload(misp, payload['Event']['id'], test_case):
            logger.info('Launching getresults for test-case ' + str(testcase_id))
            os.system(conf_script_path_prefix + 'getresults.py -id ' + str(testcase_id))
            wait_for_targets(misp, payload['Event']['id'], test_case)
            rollback_targets(misp, test_case)
    clean_up(misp, testcase_id)
