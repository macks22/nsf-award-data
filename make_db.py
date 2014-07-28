import re
import sys

import nameparser
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column, String, Text, Integer, Enum,
    DATETIME, CHAR, FLOAT,
    ForeignKey, CheckConstraint
)


Base = declarative_base()


class MixinHelper(object):

    @declared_attr
    def __tablename__(cls):
        """Convert "CamelCase" class names to "camel_case" table names."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @declared_attr
    def __repr__(cls):
        attributes = ['{}="{}"'.format(attr, getattr(self, attr))
                      for attr in dir(cls) if isinstance(attr, Column)]
        return '<{} ({})>'.format(cls.__name__, ', '.join(attributes))


class Directorate(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(4), unique=True)
    name = Column(String(80), nullable=False)
    phone = Column(String(15), unique=True)
    divisions = relationship(
        'Division', backref='directorate',
        cascade='all, delete-orphan', passive_deletes=True)


class Division(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(4), unique=True)
    name = Column(String(80), nullable=False)
    phone = Column(String(15), unique=True)
    dir_id = Column(Integer, ForeignKey('directorate.id', ondelete='CASCADE'))
    programs = relationship(
        'Program', backref='division',
        cascade='all, delete-orphan', passive_deletes=True)


class Program(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(4), unique=True)
    name = Column(String(80))
    div_id = Column(CHAR(4), ForeignKey('division.id', ondelete='CASCADE'))
    related_programs = association_proxy(
        '_related_programs', 'secondary_program')


class RelatedPrograms(MixinHelper, Base):
    pgm1_id = Column(
        Integer,
        ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)
    pgm2_id = Column(
        Integer,
        ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)

    main_program = relationship(
        'Program', foreign_keys='RelatedPrograms.pgm1_id',
        uselist=False, single_parent=True,
        backref=backref('_related_programs', cascade='all, delete-orphan',
                        passive_deletes=True)
    )

    secondary_program = relationship(
        'Program', foreign_keys='RelatedPrograms.pgm2_id',
        uselist=False, single_parent=True)

    __table_args__ = (
        CheckConstraint(pgm1_id != pgm2_id),
    )

    def __init__(self, pgm1_id, pgm2_id):
        self.pgm1_id = pgm1_id
        self.pgm2_id = pgm2_id


class Award(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    abstract = Column(Text)
    effective = Column(DATETIME)
    expires = Column(DATETIME)
    first_amended = Column(DATETIME)
    last_amended = Column(DATETIME)
    amount = Column(Integer)
    arra_amount = Column(Integer)
    instrument = Column(String(100))

    publications = relationship(
        'Publication', backref=backref('award', uselist=False))
    institutions = association_proxy('affiliations', 'institution')
    people = association_proxy('affiliations', 'person')
    funding_programs = association_proxy('_funding_programs', 'program')


class Funding(MixinHelper, Base):
    pgm_id = Column(
        Integer,
        ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer,
        ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)

    program = relationship('Program', uselist=False, single_parent=True)
    award = relationship(
        'Award', uselist=False, single_parent=True,
        backref=backref('_funding_programs',
                        cascade='all, delete-orphan',
                        passive_deletes=True)
    )

    def __init__(self, pgm_id, award_id):
        self.pgm_id = pgm_id
        self.award_id = award_id


class Publication(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    abstract = Column(Text)
    journal = Column(String(255))
    volume = Column(String(10))
    pages = Column(String(30))
    year = Column(Integer)
    uri = Column(String(255))
    award_id = Column(Integer, ForeignKey('award.id', ondelete='SET NULL'))


class State(MixinHelper, Base):
    abbr = Column(CHAR(2), primary_key=True)
    name = Column(String(14), nullable=False, unique=True)


class Country(MixinHelper, Base):
    alpha2 = Column(CHAR(2), primary_key=True)
    name = Column(String(100), nullable=False)


class Address(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    street = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    state = Column(CHAR(2), ForeignKey('state.abbr'), nullable=False)
    country = Column(CHAR(2), ForeignKey('country.alpha2'), nullable=False)
    zipcode = Column(String(10), nullable=False)
    lat = Column(FLOAT)
    lon = Column(FLOAT)


class Institution(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True)
    address_id = Column(Integer, ForeignKey('address.id', ondelete='SET NULL'))
    address = relationship('Address', uselist=False)

    people = association_proxy('_people', 'person')


class Person(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    fname = Column(String(50), nullable=False)
    lname = Column(String(50), nullable=False)
    mname = Column(String(50))
    nickname = Column(String(20))
    title = Column(String(10))
    suffix = Column(String(10))
    email = Column(String(100), unique=True)

    publications = association_proxy('_publications', 'publication')
    institutions = association_proxy('affiliations', 'institution')

    @classmethod
    def from_fullname(self, name, email=None):
        parsed_name = nameparser.HumanName(name)
        return cls(
            fname=parsed_name.first,
            lname=parsed_name.last,
            mname=parsed_name.middle if parsed_name.middle else None,
            title=parsed_name.title if parsed_name.title else None,
            suffix=parsed_name.suffix if parsed_name.suffix else None,
            nickname=parsed_name.nickname if parsed_name.nickname else None,
            email=email
        )

    @property
    def full_name(self):
        pieces = []
        if self.title is not None:
            pieces.append(self.title)
        pieces.append(self.fname)
        if self.nickname is not None:
            pieces.append('({})'.format(self.nickname))
        if self.mname is not None:
            pieces.append(self.mname)
        pieces.append(self.lname)
        if self.suffix is not None:
            pieces.append(self.suffix)
        return ' '.join(pieces)


class Author(MixinHelper, Base):
    person_id = Column(
        Integer,
        ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    pub_id = Column(
        Integer,
        ForeignKey('publication.id', ondelete='CASCADE'),
        primary_key=True)

    person = relationship(
        'Person', uselist=False, single_parent=True,
        backref=backref('_publications', cascade='all, delete-orphan',
                        passive_deletes=True)
    )

    publication = relationship(
        'Publication', uselist=False, single_parent=True)

    def __init__(self, person_id, pub_id):
        self.person_id = person_id
        self.pub_id = pub_id


class Role(MixinHelper, Base):
    person_id = Column(
        Integer,
        ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer,
        ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)
    role = Column(Enum('pi', 'copi', 'fpi', 'po'))
    start = Column(DATETIME)
    end = Column(DATETIME)

    award = relationship('Award', uselist=False, single_parent=True)
    person = relationship(
        'Person', uselist=False, single_parent=True,
        backref=backref('awards', cascade='all, delete-orphan',
                        passive_deletes=True)
    )


class Affiliation(MixinHelper, Base):
    person_id = Column(
        Integer,
        ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey('institution.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer,
        ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)

    person = relationship(
        'Person', backref=backref('affiliations', cascade='all, delete-orphan',
                                  passive_deletes=True)
    )

    institution = relationship(
        'Institution', backref=backref('affiliations',
                                       cascade='all, delete-orphan',
                                       passive_deletes=True)
    )

    award = relationship(
        'Award', backref=backref('affiliations', cascade='all, delete-orphan',
                                 passive_deletes=True)
    )

    def __init__(self, person_id, institution_id, award_id):
        self.person_id = person_id
        self.institution_id = institution_id
        self.award_id = award_id


def main():
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///nsf-award-data.db')
    Base.metadata.create_all(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
