"""
Mixins for database tables to inherit from.
"""
import re
from sqlalchemy.ext.declarative import declarative_base, declared_attr


class BasicMixin(object):

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


def _unique(session, cls, hashfunc, queryfunc, constructor, arg, kw):
    """Provide the "guts" to the unique recipe. This function is given a
    Session to work with, and associates a dictionary with the Session() which
    keeps track of current "unique" keys.
    """
    cache = getattr(session, '_unique_cache', None)
    if cache is None:
        session._unique_cache = cache = {}

    key = (cls, hashfunc(*arg, **kw))
    if key in cache:
        return cache[key]
    else:
        with session.no_autoflush:
            q = session.query(cls)
            q = queryfunc(q, *arg, **kw)
            obj = q.first()
            if not obj:
                obj = constructor(*arg, **kw)
                session.add(obj)
        cache[key] = obj
        return obj


class UniqueMixin(BasicMixin):
    @classmethod
    def unique_hash(cls, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def unique_filter(cls, query, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *arg, **kw):
        return _unique(session, cls,
                       cls.unique_hash,
                       cls.unique_filter,
                       cls, arg, kw)
