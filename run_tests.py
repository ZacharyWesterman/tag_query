#!/usr/bin/env python3

import argparse

import tests

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Run tests for the project.')

	parser.add_argument(
		'--tests', '-t', dest='test_list', nargs='+',
		help='List of tests to run. If not specified, all tests will be run.',
		default=[]
	)
	args = parser.parse_args()

	# Run the tests
	tests.run_tests([i.replace('-', '_') for i in args.test_list])
