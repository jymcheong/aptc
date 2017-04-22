#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-

from aptc import *
import asyncio


# borrowed from http://www.giantflyingsaucer.com/blog/?p=5557
@asyncio.coroutine
def start_polling(m, testcase_id, payload_id, target_name, filename):
    # todo support per payload query that is more specific than target level query
    query = target_query_strings[conf_target_path_prefix + target_name]
    t = 0
    alert_found = False
    newtag = ''
    logger.debug('query graylog with: ' + query)
    while t < conf_graylog_poll_timeout_sec:
        try:
            rc = query_graylog(m, query, filename)
        except BaseException as e:
            logger.error('graylog query failed: ' + str(e))
            create_n_tag(m, testcase_id, conf_tag_prefix + 'error with graylog result poll', '#aa0000')
            break
        if rc > 0:
            alert_found = True
            newtag = conf_tag_prefix + 'result_hit-testcase-' + str(testcase_id) + '-' + target_name
            m.new_tag(newtag, '#00aa00', True)
            break
        t += conf_poll_sleep_interval_sec
        yield from asyncio.sleep(conf_poll_sleep_interval_sec)

    if not alert_found:
        newtag = conf_tag_prefix + 'result_miss-testcase-' + str(testcase_id) + '-' + target_name
        m.new_tag(newtag, '#aa0000', True)
    logger.debug(newtag)
    tag(m, payload_id, newtag)
    newtag = conf_tag_prefix + '{"target":"' + target_name + '","testcase-id":'
    newtag += str(testcase_id) + ',"filename":"' + filename + '"}'
    delete_tag(m, payload_id, newtag)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get results for given testcase-id')
    parser.add_argument("-id", "--id", required=True, help="test-case integer id")
    args = parser.parse_args()
    testcase_id = args.id
    misp = init(misp_url, misp_key)
    if not get_all_query_strings(misp, testcase_id):
        logger.info('exit after get_all_query_strings')
        exit()
    tasks = []
    r = misp.search(not_tags=[conf_tag_prefix + 'test-case'], tags=[conf_tag_prefix + 'test-in-progress'])
    # assuming called by getpayloads.py, it should always return payloads
    for p in r['response']:
        for t in p['Event']['Tag']:
            if not t['name'].startswith(conf_tag_prefix + '{"target'):
                continue
            o = json.loads(t['name'].replace(conf_tag_prefix, ''))
            if str(o['testcase-id']) != str(testcase_id):
                continue
            tasks.append(start_polling(misp, o['testcase-id'], p['Event']['id'], o['target'], o['filename']))
    if len(tasks) > 0:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()
