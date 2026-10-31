"""Require executed, passing, non-skipped cases in a pytest JUnit report."""

import argparse
import xml.etree.ElementTree as ET


def require_passing_cases(filename):
    """Return the case count, rejecting empty, skipped, failed, or errored runs."""
    root = ET.parse(filename).getroot()
    cases = list(root.iter('testcase'))
    if not cases:
        raise ValueError('The report contains no executed test cases.')
    for suite in root.iter('testsuite'):
        if any(int(suite.get(name, '0')) for name in ('skipped', 'failures', 'errors')):
            raise ValueError('The report contains skipped, failed, or errored tests.')
    for case in cases:
        if any(case.find(name) is not None for name in ('skipped', 'failure', 'error')):
            raise ValueError('Every test case must pass without skipping.')
    return len(cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filename', help='pytest JUnit XML report')
    count = require_passing_cases(parser.parse_args().filename)
    print(f'Verified {count} executed, passing tests with no skips.')
