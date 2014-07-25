## Overview

The National Science Foundation (NSF) hosts a wealth of data regarding their
awards, both those currently being funded as well as those that were funded in
the past. This award data contains information regarding funding trends,
research collaborations, organizational cooperation, and more. In an effort to
make this information more readily obtainable, I am going to download all of the
raw data (XML) and parse it into a relational data format which is easier to
analyze.

## Disambiguation

After initially populating the database, I'll need to perform disambiguation of
the records. There are a variety of fields which will involve redundancy. I will
seek to thoroughly document my methodology. I have yet to decide whether or not
to retain disambiguation history. Purdue University maintains a pre-processed
copy of this data as well, and the method they used was to enter every person as
having a unique ID, then disambiguate by tying those unique IDs to unique
canonical IDs. This method retains history but may complicate queries. Perhaps a
better approach would be to transition the stored people entries to using the
canonical IDs as their PKs and retain in another database the disambiguation
records.

## Address Storage: Consistency/Convenience Tradeoffs

When storing addresses, there is always a tradeoff between querying convenience
and data consistency. When addresses are used for purposes of shipping and/or
identification, consistency is a more important consideration. However, when
addresses are primarily maintained for analytical purposes or disambiguation
reasons, then convenience is more important. Therefore the approach taken will
be to store certain codes (state, country) in separate tables, with display
names as attributes, use the codes as keys, and then put FKs on the attributes
of the address table. There needs to be a reasonable balance between planning
for internationalization and simplicity. In this case, NSF data mostly
references US locations,  so this general schema should suffice:

    *********************************
    Field              Type
    *********************************
    address_id (PK)    int
    unit               string
    building           string
    street             string
    city               string
    state              string
    country            string
    address_code       string
    *********************************

It will be useful to have additional tables for codes/abbreviations, as
described above:

1. state (abbrev, name)
2. country (code, name)

A note on #1: since a region may not be a state, there are a few possible
approaches which could be taken:

1. Do not constrain region at all, and don't use a state table
2. Do not constrain region at all, and use a state table only when abbreviations
   are found
3. Do not constrain region at all, and use a general region-mapping table to map
   region abbreviations to region names; use this for translation
4. Attempt to capture all region abbreviations in a region table, and constrain
   the region attribute using that
5. Add another attribute for state, constrain that one, and allow either to be
   NULL (but not both at the same time? Is that possible?)

## Enrichment

One of the more ambitious goals with this database will be an effort to enrich
the data we have by mining additional papers, abstracts, publications, etc for
each investigator. It will also be useful to make an attempt to map their
affiliation progressions. For instance, for a particular researcher, we can
currently tell what their affiliations are as a group, and we can infer what the
current one is, but we do not have the time interval over which they were
actually affiliated with an organization. This could probably be scraped from
personal pages, institutional faculty listings, etc.

### Geospatial Analysis

It will likely be interesting at some point to map a trend of NSF funding based
on geospatial locality, so adding two lat/lon fields to the address table
might also be useful. The decimal values used below allow for ~1mm accuracy at
the equator. Initially at least it will be useful to allow these to be NULL by
default, since the raw NSF data does not have lat/lon coords.

    *********************************
    Field              Type
    *********************************
    lat             decimal(10,8)
    lon             decimal(11,8)
    *********************************

The addresses of institutions can be used to get lat/lon coords using a library
like [pygeocoder](http://code.xster.net/pygeocoder/wiki/Home).
