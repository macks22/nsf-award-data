## Overview

Initially, an attempt was made at parsing all names using custom code, however,
it appears someone has already gone through all the trouble:

[python-nameparser](https://pypi.python.org/pypi/nameparser)

The notes below were produced during the initial effort.

## Program Officer

Names may either be empty or non-empty.

### Empty

1.  'name not available'
2.  '' # empty string

### Non-empty

1.  1 first name, 1 last name
    *   David Nelson
    *   Camelita Sellars-Wright
    *   Tanja Pietra\xdf
    *   Suk-Wah Tam-Chang
2.  Foreign Name with English in parentheses
    *   Pei-Chiung (Anne) Huang
3.  First name, middle initial, last name
    *   John D. Gannon
4.  First name, middle initial, last name, suffix
    *   Lawrence L. Lohr, Jr.
    *   Frank P. Scioli Jr.
5.  First initial, middle name, last name
    *   H. Lawrence Clark
6.  What?
    *   Kristen M. Biggar, N-BioS
7.  First name, two middle initials, last name
    *   Sherrie M.B. Green
8.  First name, middle initial, de Lname
    *   Adriaan M. de Graaf
9.  First name only
    *   Maria
10. First name, middle name, last name, suffix
    *   Charles Alexander Garris, Jr.
11. First name, middle name, last name
    *   Yick Grace Hsuan
12. Three initials, last name (maybe treat all initials as first name?)
    *   W. Y. B. Chang

## Investigator

### FirstName Field

0.  first name only
    *   Aaron
1.  2 first names
    *   Ann Marie
    *   Andranik Andrew
2.  misc. placeholder
    *   - (last name 'Robby')
3.  middle initial, first name
    *   A Joshua
    *   A. Giles
4.  two middle initials, first name
    *   A.L. Narasimha
    *   A.A. (Louis)
5.  initial only
    *   A.

### LastName Field

0.  last name only
    *   Ames
1.  2 last names
    *   Calabrese Barton
    *   Wagoner Johnson
2.  Roman Numeral Suffix
    *   Creekmore III
3.  last name with space
    *   La Rosa
