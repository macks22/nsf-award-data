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

        # NOTE: it would be necessary to parse directorate/division separately
        # for each <Organization> tag, but the data was scanned and there were
        # no instances of multiple <Organization>, <Directorate>, or <Division>
        # tags found.

        dir_name = soup.find('Directorate').find('LongName').text
        div_name = soup.find('Division').find('LongName').text
        # TODO: look up code and phone number for div/dir

        #dir_names = [tag.find('LongName').text for tag in soup('Directorate')]
        #div_names = [tag.find('LongName').text for tag in soup('Division')]

        pgms = [{'code': pgm.find('Code').text,
            'name': pgm.find('Text').text} for pgm in soup('ProgramElement')]
        related_pgms = [{'code': pgm.find('Code').text,
            'name': pgm.find('Text').text} for pgm in soup('ProgramReference')]

        # institutions
        institutions = []
        inst_tags = soup.find('Institution')
        for inst_tag in inst_tags:
            address = {
                'street': inst_tag.find('StreetAddress').text,  # parse unit
                'city': inst_tag.find('CityName').text,  # lowercase
                'state': inst_tag.find('StateCode').text,  # uppercase
                'country': inst_tag.find('CountryName').text, # lookup alpha2
                'zipcode': inst_tag.find('ZipCode').text
            }
            institution = {
                'name': inst_tag.find('Name').text,
                'phone': inst_tag.find('PhoneNumber').text,
                'address': address
            }
            institutions.append(institution)

        # investigators
