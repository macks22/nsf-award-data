import os
import sys
import pickle
import zipfile
from difflib import SequenceMatcher

import nameparser
from bs4 import BeautifulSoup


with open('address-abbrevs.pickle', 'r') as f:
    SUBS = pickle.load(f)

with open('country-codes.pickle', 'r') as f:
    COUNTRIES = pickle.load(f)


class Awards(object):

    def __init__(self, dirpath=None):
        self.zipdir = dirpath if dirpath is not None else os.getcwd()
        self.zipfiles = [f for f in os.listdir(self.zipdir) if
                f.endswith('.zip')]

    def __getitem__(self, year):
        filename = '{}.zip'.format(year)
        if filename not in self.zipfiles:
            raise KeyError('{} not present in {}'.format(
                filename, self.zipdir))

        zipfile_path = os.path.join(self.zipdir, filename)
        with zipfile.ZipFile(zipfile_path, 'r') as archive:
            for filepath in archive.filelist:
                yield BeautifulSoup(archive.read(filepath), 'xml')

    def __iter__(self):
        for filename in self.zipfiles:
            zipfile_path = os.path.join(self.zipdir, filename)
            with zipfile.ZipFile(zipfile_path, 'r') as archive:
                for filepath in archive.filelist:
                    yield BeautifulSoup(archive.read(filepath), 'xml')

    def years(self):
        return [int(year.strip('.zip')) for year in self.zipfiles]

    def iterawards(self):
        return self.__iter__()


def parse_name(name):
    parsed_name = nameparser.HumanName(name)
    mname = parsed_name.middle if parsed_name.middle else None
    title = parsed_name.title if parsed_name.title else None
    suffix = parsed_name.suffix if parsed_name.suffix else None
    nickname = parsed_name.nickname if parsed_name.nickname else None
    person = {
        'fname': parsed_name.first,
        'lname': parsed_name.last,
        'mname': mname,
        'title': title,
        'suffix': suffix,
        'nickname': nickname
    }
    return person


def clean_street(street_address):
    caps = street_address.upper()
    stripped = caps.strip('.').strip()
    for key in SUBS:
        stripped = stripped.replace(key, SUBS[key])
    return stripped


def closest_country_code(country):
    caps = country.upper()
    top = (0, '')
    for name in COUNTRIES:
        similarity = SequenceMatcher(None, caps, name).ratio()
        if similarity > top[0]:
            top = (similarity, name)
    return COUNTRIES[top[1]]


def parse_year(awards, year):
    for soup in awards[year]:
        parse_award(soup)


def parse_award(soup):
    arra_amount_str = soup.find('ARRAAmount').text
    award = {

        # general info
        'code': soup.find('AwardID').text,
        'title': soup.find('AwardTitle').text,
        'abstract': soup.find('AbstractNarration').text,  # may be empty
        'instrument': ','.join(
            [tag.find('Value').text for tag in soup('AwardInstrument')]),

        # all dates are in format: dd/mm/yyyy
        'effective': soup.find('AwardEffectiveDate').text,
        'expires': soup.find('AwardExpiresDate').text,
        'first_amended': soup.find('MinAmdLetterDate').text,
        'last_amended': soup.find('MaxAmdLetterDate').text,

        # money
        'amount': int(soup.find('AwardAmount').text),
        'arra_amount': 0 if not arra_amount_str else int(arra_amount)
    }

    # organization stuff

    # TODO: if anyone ever figures out what org code is for, parse it here

    # NOTE: it would be necessary to parse directorate/division separately
    # for each <Organization> tag, but the data was scanned and there were
    # no instances of multiple <Organization>, <Directorate>, or <Division>
    # tags found.

    dir_name = soup.find('Directorate').find('LongName').text
    div_name = soup.find('Division').find('LongName').text
    # TODO: look up code and phone number for div/dir

    #dir_names = [tag.find('LongName').text for tag in soup('Directorate')]
    #div_names = [tag.find('LongName').text for tag in soup('Division')]

    pgms = [{'code': pgm.find('Code').text,
        'name': pgm.find('Text').text} for pgm in soup('ProgramElement')]
    related_pgms = [{'code': pgm.find('Code').text,
        'name': pgm.find('Text').text} for pgm in soup('ProgramReference')]

    # institutions
    institutions = []
    inst_tags = soup('Institution')
    for inst_tag in inst_tags:
        address = {
            'street': clean_street(inst_tag.find('StreetAddress').text),
            'city': inst_tag.find('CityName').text.upper(),
            'state': inst_tag.find('StateCode').text.upper(),
            'country': closest_country_code(inst_tag.find('CountryName').text),
            'zipcode': inst_tag.find('ZipCode').text
        }
        institution = {
            'name': inst_tag.find('Name').text,
            'phone': inst_tag.find('PhoneNumber').text,
            'address': address
        }
        institutions.append(institution)

    # investigators
    people = []
    roles = []
    inv_tags = soup('Investigator')
    for inv_tag in inv_tags:
        name = '{} {}'.format(
            inv_tag.find('FirstName').text,
            inv_tag.find('LastName').text
        )
        person = parse_name(name)
        person.update({
            'email': inv_tag.find('EmailAddress').text
        })
        people.append(person)

        start_date = inv_tag.find('StartDate').text.strip()
        start = start_date if start_date else award['effective']
        end_date = inv_tag.find('EndDate').text.strip()
        end = end_date if end_date else award['expires']

        # TODO: deal with inexact matches
        role_str = inv_tag.find('RoleCode').text.strip()
        if role_str == 'Principal Investigator':
            role = 'pi'
        elif role_str == 'Co-Principal Investigator':
            role = 'copi'
        elif role_str == 'Former Principal Investigator':
            role = 'fpi'

        # TODO: use actual ids after creating entries in DB
        role = {
            'person_id': person,
            'award_id': award,
            'role': role,
            'start': start,
            'end': end
        }
        roles.append(role)

    # program officers
    po_tags = soup('ProgramOfficer')
    for po_tag in po_tags:
        name = po_tag.text.strip('\n')
        person = parse_name(name)
        people.append(person)

        # TODO: use actual ids after creating entries in DB
        role = {
            'person_id': person,
            'award_id': award,
            'role': 'po',
            'start': award['effective'],
            'end': award['expires']
        }
        roles.append(role)


if __name__ == "__main__":
    try:
        awards = Awards(sys.argv[1])
    except IndexError:
        print '{} <zipdir'.format(sys.argv[0])
        sys.exit(1)

    g = awards.iterawards()
    soup = g.next()

    arra_amount_str = soup.find('ARRAAmount').text
    award = {

        # general info
        'code': soup.find('AwardID').text,
        'title': soup.find('AwardTitle').text,
        'abstract': soup.find('AbstractNarration').text,  # may be empty
        'instrument': ','.join(
            [tag.find('Value').text for tag in soup('AwardInstrument')]),

        # all dates are in format: dd/mm/yyyy
        'effective': soup.find('AwardEffectiveDate').text,
        'expires': soup.find('AwardExpirationDate').text,
        'first_amended': soup.find('MinAmdLetterDate').text,
        'last_amended': soup.find('MaxAmdLetterDate').text,

        # money
        'amount': int(soup.find('AwardAmount').text),
        'arra_amount': 0 if not arra_amount_str else int(arra_amount)
    }

    # organization stuff

    # TODO: if anyone ever figures out what org code is for, parse it here

    # NOTE: it would be necessary to parse directorate/division separately
    # for each <Organization> tag, but the data was scanned and there were
    # no instances of multiple <Organization>, <Directorate>, or <Division>
    # tags found.

    dir_name = soup.find('Directorate').find('LongName').text
    div_name = soup.find('Division').find('LongName').text
    # TODO: look up code and phone number for div/dir

    #dir_names = [tag.find('LongName').text for tag in soup('Directorate')]
    #div_names = [tag.find('LongName').text for tag in soup('Division')]

    pgms = [{'code': pgm.find('Code').text,
        'name': pgm.find('Text').text} for pgm in soup('ProgramElement')]
    related_pgms = [{'code': pgm.find('Code').text,
        'name': pgm.find('Text').text} for pgm in soup('ProgramReference')]

    # institutions
    institutions = []
    inst_tags = soup('Institution')
    for inst_tag in inst_tags:
        address = {
            'street': clean_street(inst_tag.find('StreetAddress').text),
            'city': inst_tag.find('CityName').text.upper(),
            'state': inst_tag.find('StateCode').text.upper(),
            'country': closest_country_code(inst_tag.find('CountryName').text),
            'zipcode': inst_tag.find('ZipCode').text
        }
        institution = {
            'name': inst_tag.find('Name').text,
            'phone': inst_tag.find('PhoneNumber').text,
            'address': address
        }
        institutions.append(institution)

    # investigators
    people = []
    roles = []
    inv_tags = soup('Investigator')
    for inv_tag in inv_tags:
        name = '{} {}'.format(
            inv_tag.find('FirstName').text,
            inv_tag.find('LastName').text
        )
        person = parse_name(name)
        person.update({
            'email': inv_tag.find('EmailAddress').text
        })
        people.append(person)

        start_date = inv_tag.find('StartDate').text.strip()
        start = start_date if start_date else award['effective']
        end_date = inv_tag.find('EndDate').text.strip()
        end = end_date if end_date else award['expires']

        # TODO: deal with inexact matches
        role_str = inv_tag.find('RoleCode').text.strip()
        if role_str == 'Principal Investigator':
            role = 'pi'
        elif role_str == 'Co-Principal Investigator':
            role = 'copi'
        elif role_str == 'Former Principal Investigator':
            role = 'fpi'

        # TODO: use actual ids after creating entries in DB
        role = {
            'person_id': person,
            'award_id': award,
            'role': role,
            'start': start,
            'end': end
        }
        roles.append(role)

    # program officers
    po_tags = soup('ProgramOfficer')
    for po_tag in po_tags:
        name = po_tag.text.strip('\n')
        person = parse_name(name)
        people.append(person)

        # TODO: use actual ids after creating entries in DB
        role = {
            'person_id': person,
            'award_id': award,
            'role': 'po',
            'start': award['effective'],
            'end': award['expires']
        }
        roles.append(role)
