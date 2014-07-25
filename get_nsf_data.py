"""
Download the NSF data directly from nsf.gov using the RESTful API.
Data is downloaded by year. It arrives in zipped XML files. These
files are written to disk in the current directory using the year
for naming::

    <year>.zip

"""
import os
import sys
import logging
import argparse
import requests


NSF_AWARDS_URL = 'http://www.nsf.gov/awardsearch/download'
REQUIRED_PARAMS = ('DownloadFileName', 'All')


def request_data(year, dirpath='./'):
    """Request data from NSF. Write to disk on response. Note that
    the response will come back as a zipped XML file with all award
    data for the requested year.

    :param str year: The year to request data for.
    :param str dirpath: The directory to write the zip file to.
    :raises :class:requests.exceptions.HTTPError: If an HTTP error
        occurs as a result of the request.

    """
    params = {'DownloadFileName': year, 'All': 'true'}
    logging.info('requesting award data for year: {}'.format(year))
    r = requests.post(NSF_AWARDS_URL, params)

    # will raise HTTP error if one occured
    r.raise_for_status()

    # write results to zip file in designated directory
    fname = '{}.zip'.format(year)
    outfile = os.path.join(os.path.abspath(dirpath), fname)
    with open(outfile, 'wb') as f:
        f.write(r.content)
        logging.info('data for {} written to {}'.format(year, outfile))

def request_all(*args):
    """Request data for all years."""
    start = '1960'
    end = '2014'  # TODO: get based on current date
    for year in range(int(start), int(end) + 1):
        request_data(str(year), *args)


def setup_parser():
    parser = argparse.ArgumentParser(
        description='Get raw zipped XML NSF award data from nsf.gov.')

    parser.add_argument(
        'years', action='store', nargs='*',
        help='pass one or more years to restrict requests to those years')
    parser.add_argument(
        '-o', '--outfile', action='store', default='./',
        help='write to a particular file, rather than the curdir')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='print verbose output to console')

    return parser


def main():
    parser = setup_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s\t%(asctime)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
    if args.years:
        for year in args.years:
            request_data(year, args.outfile)
    else:
        request_all(args.outfile)

    return 1


if __name__ == "__main__":
    sys.exit(main())
