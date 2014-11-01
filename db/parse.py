import os
import sys

import nameparser

import db
from awards import AwardExplorer


def parse_year(award_explorer, year):
    """Parse all XML award records for a given year, creating DB records."""
    session = db.Session()
    for award in award_explorer[year]:
        parse_award(award, session)
    session.commit()


def parse_award(award, session):
    """Parse a single XML file and create all relevant records in DB.

    :type  soup: `bs4.BeautifulSoup`
    :param soup: Soup instance wrapping the XML file to parse.
    :type  session: `sqlalchemy.Session`
    :param session: The active session object for the DB.

    """
    new_award = db.Award.as_unique(session,
        # general info
        code=award.id,
        title=award.title,
        abstract=award.abstract if award.abstract else None,
        instrument=','.join(award.instruments),

        # all dates are in format: dd/mm/yyyy
        effective=award.effective,
        expires=award.expires,
        first_amended=award.first_amended,
        last_amended=award.last_amended,

        # money
        amount=award.amount,
        arra_amount=award.arra_amount
    )
    session.add(new_award)
    session.flush()

    # organization stuff

    # TODO: if anyone ever figures out what org code is for, parse it here

    # NOTE: it would be necessary to parse directorate/division separately
    # for each <Organization> tag, but the data was scanned and there were
    # no instances of multiple <Organization>, <Directorate>, or <Division>
    # tags found.

    directorate = db.Directorate.as_unique(session, award.directorate)
    division = db.Division.as_unique(session, award.division)
    directorate.divisions.append(division)
    session.add(directorate)

    # TODO: look up code and phone number for div/dir

    related_pgms = []
    for pgmref in award.pgm_refs:
        ref = db.Program.as_unique(session, pgmref['code'], pgmref['name'])
        related_pgms.append(ref)
        session.add(ref)
    session.flush()

    pgm_elements = []
    for pgm in award.pgm_elements:
        pgm = db.Program.as_unique(
            session, pgm['code'], pgm['name'], division.id)
        session.add(pgm)
        session.flush()

        # Each program reference is related to each program element
        for related_pgm in related_pgms:
            relation = db.RelatedPrograms.as_unique(
                session, pgm.id, related_pgm.id)
            session.add(relation)

        # the pgm elements actually fund the award
        session.add(db.Funding.as_unique(session, pgm, new_award))

    session.flush()

    # institutions
    institutions = []
    for inst in award.institutions:
        institution = db.get_or_create(
            session, db.Institution,
            name=inst['name'],
            phone=inst['phone']
        )
        institution.address = db.Address.as_unique(
            session,
            street=inst['street'],
            city=inst['city'],
            state=inst['state'],
            country=inst['country'],
            zipcode=inst['zipcode']
        )
        session.add(institution)
        institutions.append(institution)

    session.flush()

    # investigators
    people = []
    for person in award.people:
        new_person = db.Person.from_fullname(
            session,
            name=person['name'],
            email=person['email']
        )
        people.append(new_person)
        session.add(new_person)
        session.flush()

        # TODO: use actual ids after creating entries in DB
        session.add(
            db.Role.as_unique(
                session,
                award_id=new_award.id,
                person_id=new_person.id,
                role=person['role'],
                start=person['start'],
                end=person['end'])
        )

    session.flush()

    for person in people:
        for institution in institutions:
            session.add(
                db.Affiliation.as_unique(session, person, institution, award)
            )

    session.flush()
    return session


if __name__ == "__main__":
    try:
        awards = AwardExplorer(sys.argv[1])
    except IndexError:
        print '{} <zipdir>'.format(sys.argv[0])
        sys.exit(1)

    g = awards.iterawards()
    award = g.next()
    award2 = g.next()
    session = db.Session()

    try:
        parse_award(award, session)
    except:
        session.rollback()
        print 'ROLLBACK'
        raise

    try:
        parse_award(award2, session)
    except:
        session.rollback()
        print 'ROLLBACK'
        raise

    try:
        session.commit()
    except:
        session.rollback()
        print 'ROLLBACK'
