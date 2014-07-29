import os
import sys
import pickle
import zipfile
import datetime
from difflib import SequenceMatcher

import nameparser
from bs4 import BeautifulSoup

import db


with open('data/address-abbrevs.pickle', 'r') as f:
    SUBS = pickle.load(f)

with open('data/country-codes.pickle', 'r') as f:
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


def normalize_street(street_address):
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


def parse_date(date):
    month, day, year = [int(part) for part in date.split('/')]
    return datetime.date(year, month, day)


def parse_year(awards, year):
    session = db.Session()
    for soup in awards[year]:
        parse_award(soup, session)
    session.commit()


def parse_award(soup, session):
    arra_amount_str = soup.find('ARRAAmount').text.strip()
    abstract = soup.find('AbstractNarration').text.strip()
    award = db.Award(
        # general info
        code=soup.find('AwardID').text,
        title=soup.find('AwardTitle').text,
        abstract=abstract if abstract else None,
        instrument=','.join(
            [tag.find('Value').text for tag in soup('AwardInstrument')]),

        # all dates are in format: dd/mm/yyyy
        effective=parse_date(soup.find('AwardEffectiveDate').text),
        expires=parse_date(soup.find('AwardExpirationDate').text),
        first_amended=parse_date(soup.find('MinAmdLetterDate').text),
        last_amended=parse_date(soup.find('MaxAmdLetterDate').text),

        # money
        amount=int(soup.find('AwardAmount').text),
        arra_amount=int(arra_amount_str) if arra_amount_str else 0
    )
    session.add(award)
    session.flush()

    # organization stuff

    # TODO: if anyone ever figures out what org code is for, parse it here

    # NOTE: it would be necessary to parse directorate/division separately
    # for each <Organization> tag, but the data was scanned and there were
    # no instances of multiple <Organization>, <Directorate>, or <Division>
    # tags found.

    directorate = db.Directorate(
        name=soup.find('Directorate').find('LongName').text)
    division = db.Division(
        name=soup.find('Division').find('LongName').text)
    directorate.divisions.append(division)
    # TODO: look up code and phone number for div/dir

    for pgm in soup('ProgramElement'):
        pgm = db.Program(pgm.find('Code').text, pgm.find('Text').text)
        division.programs.append(pgm)
        session.flush()

        for pgm_tag in soup('ProgramReference'):
            code = pgm_tag.find('Code').text
            name = pgm_tag.find('Text').text
            pgm.related_programs[code] = name

        session.add(db.Funding(pgm, award))

    session.add(directorate)
    session.flush()

    # institutions
    institutions = []
    for inst_tag in soup('Institution'):
        institution = db.Institution(
            name=inst_tag.find('Name').text,
            phone=inst_tag.find('PhoneNumber').text,
        )
        institution.address = db.Address(
            street=normalize_street(inst_tag.find('StreetAddress').text),
            city=inst_tag.find('CityName').text.upper(),
            state=inst_tag.find('StateCode').text.upper(),
            country=closest_country_code(inst_tag.find('CountryName').text),
            zipcode=inst_tag.find('ZipCode').text
        )
        session.add(institution)
        institutions.append(institution)

    session.flush()

    # investigators
    people = []
    for inv_tag in soup('Investigator'):
        email = inv_tag.find('EmailAddress').text.strip()
        person = db.Person.from_fullname(
            name='{} {}'.format(
                inv_tag.find('FirstName').text,
                inv_tag.find('LastName').text),
            email=email if email else None
        )
        session.add(person)
        people.append(person)

        start_date = inv_tag.find('StartDate').text.strip()
        start = parse_date(start_date) if start_date else award.effective
        end_date = inv_tag.find('EndDate').text.strip()
        end = parse_date(end_date) if end_date else award.expires

        # TODO: deal with inexact matches
        role_str = inv_tag.find('RoleCode').text.strip()
        if role_str == 'Principal Investigator':
            role = 'pi'
        elif role_str == 'Co-Principal Investigator':
            role = 'copi'
        elif role_str == 'Former Principal Investigator':
            role = 'fpi'

        # TODO: use actual ids after creating entries in DB
        person.roles.append(
            db.Role(award_id=award.id, role=role, start=start, end=end)
        )

    session.flush()

    # program officers
    for po_tag in soup('ProgramOfficer'):
        name = po_tag.text.strip('\n')
        person = db.Person.from_fullname(name)
        session.add(person)
        people.append(person)

        person.roles.append(
            db.Role(award_id=award.id, role='po', start=award.effective,
                    end=award.expires)
        )

    session.flush()

    for person in people:
        for institution in institutions:
            session.add(db.Affiliation(person.id, institution.id, award.id))

    session.flush()
    return session


if __name__ == "__main__":
    try:
        awards = Awards(sys.argv[1])
    except IndexError:
        print '{} <zipdir'.format(sys.argv[0])
        sys.exit(1)

    g = awards.iterawards()
    soup = g.next()
    session = db.Session()
    parse_award(soup, session)

    try:
        session.commit()
    except:
        session.rollback()
        print 'ROLLBACK'
