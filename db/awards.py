import os
import zipfile
import datetime
import cPickle as pickle
from difflib import SequenceMatcher

import ujson as json
import nameparser

from bs4 import BeautifulSoup as Soup


with open('../data/address-abbrevs.pickle', 'r') as f:
    SUBS = pickle.load(f)

with open('../data/country-codes.pickle', 'r') as f:
    COUNTRIES = pickle.load(f)

ROLES = {
    'principal investigator': 'pi',
    'co-principal investigator': 'copi',
    'former principal investigator': 'fpi',
    'former co-principal investigator': 'fcopi'
}


def parse_date(date):
    """Parse data from dd/mm/yyyy format to Python datetime object."""
    month, day, year = [int(part) for part in date.split('/')]
    return datetime.date(year, month, day)


def normalize_street(street_address):
    """Sub common street name elements for abbreviations and capitalize."""
    caps = street_address.upper()
    stripped = caps.strip('.').strip()
    for key in SUBS:
        stripped = stripped.replace(key, SUBS[key])
    return stripped


def closest_country_code(country):
    """Get the country code for the country name most similar to the given."""
    caps = country.upper()
    top = (0, '')
    for name in COUNTRIES:
        similarity = SequenceMatcher(None, caps, name).ratio()
        if similarity > top[0]:
            top = (similarity, name)
    return COUNTRIES[top[1]]


class AwardXML(object):
    """Wrapper for award XML soup, to make data extraction simple."""

    def __init__(self, soup):
        """Extract data from XML soup and discard soup."""
        find_text = lambda key: soup.find(key).text
        self.title = find_text('AwardTitle')
        self.id = find_text('AwardID')
        self.abstract = find_text('AbstractNarration').strip()
        self.instruments = [tag.find('Value').text
                            for tag in soup('AwardInstrument')]

        # all dates are in format: dd/mm/yyyy
        def find_date(key):
            text = find_text(key)
            return parse_date(text) if text else None

        self.effective = find_date('AwardEffectiveDate')
        self.expires = find_date('AwardExpirationDate')
        self.first_amended = find_date('MinAmdLetterDate')
        self.last_amended = find_date('MaxAmdLetterDate')

        # money
        self.amount = int(find_text('AwardAmount'))
        self.arra_amount = find_text('ARRAAmount').strip()
        self.arra_amount = int(self.arra_amount) if self.arra_amount else 0

        # organizational data
        tag = soup.find('Directorate')
        self.directorate = tag.find('LongName').text.upper() if tag else u''
        tag = soup.find('Division')
        self.division = tag.find('LongName').text.upper() if tag else u''

        # TODO: look up code and phone number for div/dir
        self.pgm_elements = [{
            'code': pgm.find('Code').text,
            'name': pgm.find('Text').text}
            for pgm in soup('ProgramElement')]

        self.pgm_refs = [{
            'code': pgm.find('Code').text,
            'name': pgm.find('Text').text}
            for pgm in soup('ProgramReference')]

        # institutions
        self.institutions = [{
            'name': tag.find('Name').text,
            'phone': tag.find('PhoneNumber').text,
            'street': normalize_street(tag.find('StreetAddress').text),
            'city': tag.find('CityName').text.upper(),
            'state': tag.find('StateCode').text.upper(),
            'country': closest_country_code(tag.find('CountryName').text),
            'zipcode': tag.find('ZipCode').text}
            for tag in soup('Institution')]

        # investigators
        self.people = []
        for tag in soup('Investigator'):
            get_text = lambda key: tag.find(key).text
            email = get_text('EmailAddress').strip()
            fullname = u'{} {}'.format(
                get_text('FirstName'), get_text('LastName'))

            start_date = get_text('StartDate').strip()
            start = parse_date(start_date) if start_date else self.effective
            end_date = get_text('EndDate').strip()
            end = parse_date(end_date) if end_date else self.expires

            # TODO: deal with inexact matches
            role_str = get_text('RoleCode').strip()
            role = ROLES[role_str.lower()]
            self.people.append({
                'email': email if email else None,
                'name': fullname,
                'role': role,
                'start': start,
                'end': end
            })

        # program officers
        for tag in soup('ProgramOfficer'):
            self.people.append({
                'name': tag.text.strip('\n'),
                'role': 'po',
                'start': self.effective,
                'end': self.expires,
                'email': None
            })

    def write_json(fpath):
        with open(fpath, 'w') as f:
            json.dump(self, fpath)


class NoAwardsFound(Exception):
    """Raise when no awards are found at a given path."""
    def __init__(self, path):
        self.msg = "no awards found at path: {}".format(path)
    def __repr__(self):
        return self.msg
    def __str__(self):
        return self.msg


class AwardExplorer(object):
    """Wrapper class that iterates over XML award data, yielding XML Soup."""

    def __init__(self, dirpath=None):
        """Set up the file paths to the data using the given directory."""
        self.zipdir = dirpath if dirpath is not None else os.getcwd()
        self.zipfiles = [f for f in os.listdir(self.zipdir)
                         if f.endswith('.zip')]

        if not self.zipfiles:
            raise NoAwardsFound(self.zipdir)

    def _iterarchive(self, zipfile_path):
        with zipfile.ZipFile(zipfile_path, 'r') as archive:
            for filepath in archive.filelist:
                yield Soup(archive.read(filepath), 'xml')

    def __getitem__(self, year):
        filename = '{}.zip'.format(year)
        if filename not in self.zipfiles:
            raise KeyError('{} not present in {}'.format(
                filename, self.zipdir))

        zipfile_path = os.path.join(self.zipdir, filename)
        return (AwardXML(soup) for soup in self._iterarchive(zipfile_path))

    def __iter__(self):
        return self.iterawards()

    def years(self):
        return [int(year.strip('.zip')) for year in self.zipfiles]

    def itersoup(self):
        for filename in self.zipfiles:
            zipfile_path = os.path.join(self.zipdir, filename)
            return self._iterarchive(zipfile_path)

    def iterawards(self):
        return (AwardXML(soup) for soup in self.itersoup())


if __name__ == "__main__":
    expl = AwardExplorer('../raw')
    g = iter(expl)
    awd = next(g)
