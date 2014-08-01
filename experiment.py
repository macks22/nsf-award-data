from __future__ import division

import sys
import string
import cPickle as pickle

import nameparser
from jellyfish import jaro_winkler

from db import parse

class Person(object):

    ID = 0

    def __init__(self, name, email='', directorate='', division='',
                 programs=None):
        parsed_name = nameparser.HumanName(name)
        self.fname = parsed_name.first.encode('utf-8')
        self.lname = parsed_name.last.encode('utf-8')
        self.mname = parsed_name.middle.strip('.').encode('utf-8')
        self.title = parsed_name.title.strip('.').encode('utf-8')
        self.suffix = parsed_name.suffix.strip('.').encode('utf-8')
        self.nickname = parsed_name.nickname.encode('utf-8')

        self.email = email
        self.directorate = directorate.upper().strip(string.punctuation)
        self.division = division.upper().strip(string.punctuation)
        self.programs = set(p.upper().strip(string.punctuation) for p in
                programs) if programs is None else set(programs)

        self.id = Person.ID
        Person.ID += 1

    def num_shared_programs(self, other):
        return len(self.programs & other.programs)

    def num_shared_divisions(self, other):
        return len(self.divisions & other.divisions)

    def match(self, other):
        attrs = {'fname': 0, 'lname': 0, 'mname': 0}
        similarity = 0
        for k, v in attrs.items():
            attrs[k] = max(len(getattr(self, k)), len(getattr(other, k)))

        total = sum(attrs.values())
        weights = {k: v/total for (k,v) in attrs.items()}

        #print 'attrs: {}'.format(attrs)
        #print 'total: {}'.format(total)
        #print 'weights: {}'.format(weights)

        similarities = []
        for k, v in weights.items():
            similarities.append(
                weights[k] * jaro_winkler(getattr(self, k), getattr(other, k))
            )

        #print similarities
        return sum(similarities)

    @property
    def full_name(self):
        pieces = []
        if self.title:
            pieces.append(self.title)
        pieces.append(self.fname)
        if self.nickname:
            pieces.append('({})'.format(self.nickname))
        if self.mname:
            pieces.append(self.mname)
        pieces.append(self.lname)
        if self.suffix:
            pieces.append(self.suffix)
        return ' '.join(pieces)


class People(object):
    """Retrieve people from award soup."""

    def __init__(self, soup):
        direc = soup.find('Directorate').find('LongName').text
        div = soup.find('Division').find('LongName').text
        pgms = [pgm.find('Code').text.strip() for pgm in soup('ProgramElement')]

        # investigators
        self.people = []
        for inv_tag in soup('Investigator'):
            email = inv_tag.find('EmailAddress').text.strip()
            email = email if email else None
            name = '{} {}'.format(
                inv_tag.find('FirstName').text.encode('utf-8'),
                inv_tag.find('LastName').text.encode('utf-8'))
            person = Person(name, email, div, direc, pgms[:])
            self.people.append(person)

        # program officers
        for po_tag in soup('ProgramOfficer'):
            name = po_tag.text.strip('\n').encode('utf-8')
            person = Person(name, None, div, direc, pgms[:])
            self.people.append(person)


def parse_award(soup):
    people = People(soup)
    return people.people


if __name__ == "__main__":
    try:
        zipdir = sys.argv[2]
    except IndexError:
        zipdir = 'raw'

    awards = parse.Awards(zipdir)
    years = awards.years()

    people = []
    for year in years:
        for soup in awards[year]:
            print 'people parsed from {} awards: {}'.format(year, len(people))
            people += parse_award(soup)

    with open('people.pickle', 'w') as f:
        pickle.dump(people, f)
