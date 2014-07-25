Goal:

    Given the zip arhives containing the XMl data for all available years, parse
    the data and enter it into the database.

Tools:

    Python
        zipfile
        lxml
        bs4.BeautifulSoup
        SQLAlchemy

Dialogue:

import zipfile
f = zipfile.ZipFile('1980.zip')
from bs4 import BeautifulSoup
with open(f.filelist[0], 'r') as f:
    soup = BeautifulSoup(f, 'xml')

pe = soup.find('ProgramElement')
pe_code = pe.find('Code')
