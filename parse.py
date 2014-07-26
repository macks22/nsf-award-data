import os
import sys
import zipfile

from bs4 import BeautifulSoup



class Awards(object):

    def __init__(self, dirpath=None):
        self.zipdir = dirpath if dirpath is not None else os.getcwd()
        self.zipfiles = [f for f in os.listdir(self.zipdir) if
                f.endswith('.zip')]

    def __getitem__(self, year):
        filename = '{}.zip'.format(year)
        if filename not in self.zipfiles:
            raise KeyError('{} not present in {}'.format(
                filename, self.zipdir))

        zipfile_path = os.path.join(self.zipdir, filename)
        with zipfile.ZipFile(zipfile_path, 'r') as archive:
            for filepath in archive.filelist:
                yield BeautifulSoup(archive.read(filepath), 'xml')

    def __iter__(self):
        for filename in self.zipfiles:
            zipfile_path = os.path.join(self.zipdir, filename)
            with zipfile.ZipFile(zipfile_path, 'r') as archive:
                for filepath in archive.filelist:
                    yield BeautifulSoup(archive.read(filepath), 'xml')

    def years(self):
        return [int(year.strip('.zip')) for year in self.zipfiles]

    def iterawards(self):
        return self.__iter__()


def parse_year(awards, year):
    for soup in awards[year]:
        award_id = soup.find('AwardID').text
        award_title = soup.find('AwardTitle').text
        abstract = soup.find('AbstractNarration').text  # may be empty
        instrument = ','.join(
            [tag.find('Value').text for tag in soup('AwardInstrument')])

        # all dates are in format: dd/mm/yyyy
        effective = soup.find('AwardEffectiveDate').text
        expires = soup.find('AwardExpiresDate').text
        first_amended = soup.find('MinAmdLetterDate').text
        last_amended = soup.find('MaxAmdLetterDate').text

        amount = int(soup.find('AwardAmount').text)
        arra_amount_str = soup.find('ARRAAmount').text
        arra_amount = 0 if not arra_amount_str else int(arra_amount)

        # organization stuff
        # TODO: if anyone ever figures out what org code is for, parse it here
        dirs = []
        divs = []
        orgs = soup('Organization')
        for org in orgs:
            dir_list = org('Directorate')
            div_list = org('Division')
            dir_names = [tag.find('LongName').text for tag in dir_list]
            div_names = [tag.find('LongName').text for tag in div_list]

        pgms = [{'code': pgm.find('Code').text,
            'name': pgm.find('Text').text} for pgm in soup('ProgramElement')]
        related_pgms = [{'code': pgm.find('Code').text,
            'name': pgm.find('Text').text} for pgm in soup('ProgramReference')]

        # institution

