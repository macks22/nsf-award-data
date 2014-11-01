import os
import sys

import nameparser

import db
from awards import AwardExplorer


def parse_year(awards, year):
    """Parse all XML award records for a given year, creating DB records."""
    session = db.Session()
    for soup in awards[year]:
        parse_award(soup, session)
    session.commit()


def parse_award(soup, session):
    """Parse a single XML file and create all relevant records in DB.

    :type  soup: `bs4.BeautifulSoup`
    :param soup: Soup instance wrapping the XML file to parse.
    :type  session: `sqlalchemy.Session`
    :param session: The active session object for the DB.

    """
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
        role = ROLES[role_str.lower()]

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
        awards = AwardExplorer(sys.argv[1])
    except IndexError:
        print '{} <zipdir>'.format(sys.argv[0])
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
