import re
import sys

import nameparser
import sqlalchemy as sa
import sqlalchemy.orm as saorm

from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import (
    Column, String, Text, Integer, Enum, Date,
    CHAR, FLOAT,
    ForeignKey, CheckConstraint, UniqueConstraint
)

from mixins import BasicMixin, UniqueMixin


engine = sa.create_engine('sqlite:///nsf-award-data.db', echo=True)
session_factory = saorm.sessionmaker(bind=engine)
Session = saorm.scoped_session(session_factory)
Base = declarative_base()


class Directorate(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    code = Column(CHAR(4), unique=True)
    phone = Column(String(15), unique=True)
    divisions = saorm.relationship(
        'Division', backref='directorate',
        cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, name, code=None, phone=None):
        self.name = name
        self.code = code
        self.phone = phone

    @classmethod
    def unique_hash(cls, name, *args, **kwargs):
        return name

    @classmethod
    def unique_filter(cls, query, name, *args, **kwargs):
        return query.filter(Directorate.name == name)


class Division(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    code = Column(CHAR(4), unique=True)
    phone = Column(String(15), unique=True)
    dir_id = Column(
        Integer, ForeignKey('directorate.id', ondelete='CASCADE'),
        nullable=False)
    programs = saorm.relationship(
        'Program', backref='division',
        cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, name, code=None, phone=None, dir_id=None):
        self.name = name
        self.code = code
        self.phone = phone
        self.dir_id = dir_id

    @classmethod
    def unique_hash(cls, name, *args, **kwargs):
        return name

    @classmethod
    def unique_filter(cls, query, name, *args, **kwargs):
        return query.filter(Division.name == name)


class Program(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(4), unique=True, nullable=False)
    name = Column(String(80))
    div_id = Column(CHAR(4), ForeignKey('division.id', ondelete='CASCADE'))

    related_programs = association_proxy(
        '_related_programs', 'secondary',
        creator=lambda code, name: RelatedPrograms(
            secondary=Program(code, name))
    )

    def __init__(self, code, name=None, div_id=None):
        self.code = code
        self.name = name
        self.div_id = div_id

    @classmethod
    def unique_hash(cls, code, *args, **kwargs):
        return code

    @classmethod
    def unique_filter(cls, query, code, *args, **kwargs):
        return query.filter(Program.code == code)


class RelatedPrograms(UniqueMixin, Base):
    pgm1_id = Column(
        Integer, ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)
    pgm2_id = Column(
        Integer, ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)

    primary = saorm.relationship(
        'Program', foreign_keys='RelatedPrograms.pgm1_id',
        uselist=False, single_parent=True,
        backref=saorm.backref(
            '_related_programs', cascade='all, delete-orphan',
            collection_class=attribute_mapped_collection('secondary'),
            passive_deletes=True)
    )

    secondary = saorm.relationship(
        'Program', foreign_keys='RelatedPrograms.pgm2_id',
        uselist=False, single_parent=True)

    __table_args__ = (
        CheckConstraint(pgm1_id != pgm2_id),
    )

    def __init__(self, pgm1_id, pgm2_id):
        self.pgm1_id = pgm1_id
        self.pgm2_id = pgm2_id

    @classmethod
    def unique_hash(cls, pgm1_id, pgm2_id):
        return (pgm1_id, pgm2_id)

    @classmethod
    def unique_filter(cls, query, pgm1_id, pgm2_id):
        return query.filter(
            RelatedPrograms.pgm1_id == pgm1_id and
            RelatedPrograms.pgm2_id == pgm2_id)


class Award(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(7), nullable=False, unique=True)
    title = Column(String(100))
    abstract = Column(Text)
    effective = Column(Date)
    expires = Column(Date)
    first_amended = Column(Date)
    last_amended = Column(Date)
    amount = Column(Integer)
    arra_amount = Column(Integer)
    instrument = Column(String(100))

    publications = saorm.relationship(
        'Publication', backref=saorm.backref('award', uselist=False))
    institutions = association_proxy('affiliations', 'institution')
    people = association_proxy(
        'affiliations', 'person',
        creator=lambda kwargs: Person.from_fullname(**kwargs))

    @classmethod
    def unique_hash(cls, code, *args, **kwargs):
        return code

    @classmethod
    def unique_filter(cls, query, code, *args, **kwargs):
        return query.filter(Award.code == code)


class Funding(UniqueMixin, Base):
    pgm_id = Column(
        Integer, ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer, ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)

    program = saorm.relationship('Program', uselist=False, single_parent=True)
    award = saorm.relationship(
        'Award', uselist=False, # single_parent=True,
        backref=saorm.backref(
            'funding_programs', cascade='all, delete-orphan',
            passive_deletes=True)
    )

    def __init__(self, program, award):
        self.program = program
        self.award = award

    @classmethod
    def unique_hash(cls, pgm_id, award_id):
        return (pgm_id, award_id)

    @classmethod
    def unique_filter(cls, query, pgm, award):
        return query.filter(Funding.pgm_id == pgm.id and
                            Funding.award_id == award.id)


class Publication(BasicMixin, Base):
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    abstract = Column(Text)
    journal = Column(String(255))
    volume = Column(String(10))
    pages = Column(String(30))
    year = Column(Integer)
    uri = Column(String(255))
    award_id = Column(Integer, ForeignKey('award.id', ondelete='SET NULL'))


class State(BasicMixin, Base):
    abbr = Column(CHAR(2), primary_key=True)
    name = Column(String(14), nullable=False, unique=True)


class Country(BasicMixin, Base):
    alpha2 = Column(CHAR(2), primary_key=True)
    name = Column(String(100), nullable=False)


class Address(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    street = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    state = Column(CHAR(2), ForeignKey('state.abbr'), nullable=False)
    country = Column(CHAR(2), ForeignKey('country.alpha2'), nullable=False)
    zipcode = Column(String(10), nullable=False)
    lat = Column(FLOAT)
    lon = Column(FLOAT)

    __table_args__ = (
        UniqueConstraint('street', 'city', 'state', 'country', 'zipcode',
                         name='_address_uc'),
    )

    @classmethod
    def unique_hash(cls, street, city, state, country, zipcode,
                    *args, **kwargs):
        return (street, city, state, country, zipcode)

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter_by(*args)


class Institution(UniqueMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True)
    address_id = Column(Integer, ForeignKey('address.id', ondelete='SET NULL'))
    address = saorm.relationship('Address', uselist=False)

    people = association_proxy('_people', 'person')

    @classmethod
    def unique_hash(cls, name, phone, *args, **kwargs):
        return phone

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter_by(*args)


class Person(UniqueMixin, Base):
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
    awards = association_proxy('roles', 'award')

    __table_args__ = (
        UniqueConstraint('fname', 'lname', 'mname', name='_person_name_uc'),
    )

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        return args

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter_by(*args)

    @classmethod
    def from_fullname(cls, session, name, email=None):
        parsed_name = nameparser.HumanName(name)
        return cls.as_unique(session,
            fname=parsed_name.first.strip('.'),
            lname=parsed_name.last.strip('.'),
            mname=parsed_name.middle.strip('.'),
            title=parsed_name.title.strip('.'),
            suffix=parsed_name.suffix.strip('.'),
            nickname=parsed_name.nickname.strip('.'),
            email=email
        )

    @hybrid_property
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


class Author(UniqueMixin, Base):
    person_id = Column(
        Integer, ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    pub_id = Column(
        Integer, ForeignKey('publication.id', ondelete='CASCADE'),
        primary_key=True)

    person = saorm.relationship(
        'Person', uselist=False, single_parent=True,
        backref=saorm.backref(
            '_publications', cascade='all,delete-orphan', passive_deletes=True)
    )

    publication = saorm.relationship(
        'Publication', uselist=False, single_parent=True)

    def __init__(self, person, pub):
        self.person_id = person.id
        self.pub_id = pub.id

    @classmethod
    def unique_hash(cls, person_id, award_id, *args, **kwargs):
        return (person_id, award_id)

    @classmethod
    def unique_filter(cls, query, person_id, award_id, *args, **kwargs):
        return query.filter(Role.person_id == person_id and
                            Role.award_id == award_id)


class Role(UniqueMixin, Base):
    person_id = Column(
        Integer, ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer, ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)
    role = Column(Enum('pi', 'copi', 'fpi', 'po'))
    start = Column(Date)
    end = Column(Date)

    award = saorm.relationship('Award', uselist=False, single_parent=True)
    person = saorm.relationship(
        'Person', uselist=False, single_parent=True,
        backref=saorm.backref(
            'roles', cascade='all, delete-orphan', passive_deletes=True)
    )

    def __init__(self, person, award, role, start, end):
        self.person = person
        self.award = award
        self.role = role
        self.start = start
        self.end = end

    @classmethod
    def unique_hash(cls, person, award, *args, **kwargs):
        return (person.id, award.id)

    @classmethod
    def unique_filter(cls, query, person, award, *args, **kwargs):
        return query.filter(Role.person_id == person.id and
                            Role.award_id == award.id)


class Affiliation(UniqueMixin, Base):
    person_id = Column(
        Integer, ForeignKey('person.id', ondelete='CASCADE'),
        primary_key=True)
    institution_id = Column(
        Integer, ForeignKey('institution.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer, ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)

    person = saorm.relationship(
        'Person',
        backref=saorm.backref(
            'affiliations', cascade='all, delete-orphan', passive_deletes=True)
    )

    institution = saorm.relationship(
        'Institution',
        backref=saorm.backref(
            'affiliations', cascade='all, delete-orphan', passive_deletes=True)
    )

    award = saorm.relationship(
        'Award',
        backref=saorm.backref(
            'affiliations', cascade='all, delete-orphan', passive_deletes=True)
    )

    def __init__(self, person, institution, award):
        self.person = person
        self.institution = institution
        self.award = award

    @classmethod
    def unique_hash(cls, person, institution, award, *args, **kwargs):
        return (person.id, institution.id, award.id)

    @classmethod
    def unique_filter(cls, query, person, institution, award,
                      *args, **kwargs):
        return query.filter(
            Affiliation.person_id == person.id and
            Affiliation.institution_id == institution.id and
            Affiliation.award_id == award.id
        )


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
