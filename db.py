import re
import sys

import nameparser
import sqlalchemy as sa
import sqlalchemy.orm as saorm
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import (
    Column, String, Text, Integer, Enum, Date,
    CHAR, FLOAT,
    ForeignKey, CheckConstraint
)


engine = sa.create_engine('sqlite:///nsf-award-data.db')
session_factory = saorm.sessionmaker(bind=engine)
Session = saorm.scoped_session(session_factory)
Base = declarative_base()


class MixinHelper(object):

    @declared_attr
    def __tablename__(cls):
        """Convert "CamelCase" class names to "camel_case" table names."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def __repr__(self):
        def reprs():
            for col in self.__table__.c:
                yield col.name, repr(getattr(self, col.name))

        def format(seq):
            for key, value in seq:
                yield '{}="{}"'.format(key, value)

        args = '({})'.format(', '.join(format(reprs())))
        classy = type(self).__name__
        return classy + args


class Directorate(MixinHelper, Base):
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


class Division(MixinHelper, Base):
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


class Program(MixinHelper, Base):
    id = Column(Integer, primary_key=True)
    code = Column(CHAR(4), unique=True, nullable=False)
    name = Column(String(80))
    div_id = Column(CHAR(4), ForeignKey('division.id', ondelete='CASCADE'))

    def __init__(self, code, name=None, div_id=None):
        self.code = code
        self.name = name
        self.div_id = div_id


class RelatedPrograms(MixinHelper, Base):
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
            'related_programs', cascade='all, delete-orphan',
            passive_deletes=True)
    )

    secondary = saorm.relationship(
        'Program', foreign_keys='RelatedPrograms.pgm2_id',
        uselist=False, single_parent=True)

    __table_args__ = (
        CheckConstraint(pgm1_id != pgm2_id),
    )

    def __init__(self, primary_id, secondary_id):
        self.pgm1_id = primary_id
        self.pgm2_id = secondary_id


class Award(MixinHelper, Base):
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


class Funding(MixinHelper, Base):
    pgm_id = Column(
        Integer, ForeignKey('program.id', ondelete='CASCADE'),
        primary_key=True)
    award_id = Column(
        Integer, ForeignKey('award.id', ondelete='CASCADE'),
        primary_key=True)

    program = saorm.relationship('Program', uselist=False, single_parent=True)
    award = saorm.relationship(
        'Award', uselist=False, single_parent=True,
        backref=saorm.backref(
            'funding_programs', cascade='all, delete-orphan',
            passive_deletes=True)
    )

    def __init__(self, program, award):
        self.program = program
        self.award = award



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
    address = saorm.relationship('Address', uselist=False)

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
    awards = association_proxy('roles', 'award')

    @classmethod
    def from_fullname(cls, name, email=None):
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


class Author(MixinHelper, Base):
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

    def __init__(self, person_id, pub_id):
        self.person_id = person_id
        self.pub_id = pub_id


class Role(MixinHelper, Base):
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


class Affiliation(MixinHelper, Base):
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

    def __init__(self, person_id, institution_id, award_id):
        self.person_id = person_id
        self.institution_id = institution_id
        self.award_id = award_id


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
