While it is not necessarily worthwhile to split the StreetAddress field into
multiple component subfields, it will likely be wortwhile to attempt to
normalize certain portions for disambiguation purposes.

Directions
----------

Convert all occurences to their abbreviations:

*   N = NORTH
*   E = EAST
*   W = WEST
*   S = SOUTH
*   NE = NORTHEAST
*   NW = NORTHWEST
*   SE = SOUTHEAST
*   SW = SOUTHWEST

Numbers
-------

Convert all alphabetic numbers to their integer forms:

*   ONE = 1
*   TWO = 2
*   THREE = 3
*   ...

PO BOX/DRAWER
-------------

There are a variety of formats:

1.  PO BOX
2.  P O BOX
3.  P.O.BOX
4.  P. O. BOX
5.  BOX

6.  P O DRAWER
7.  P. O. DRAWER
8.  P.O.DRAWER

Each except plain BOX should be converted to one of:

1.  P.O.Box
2.  P.O.Drawer

Others
------

Other common address abbreviations are addressed by converting via the data at:

http://www.semaphorecorp.com/cgi/abbrev.html
