import sys
import multiprocessing as mp

from parse import Awards
from num_cpus import available_cpu_count


def find_multiples(awards, year, tag):
    print 'Checking year: {}'.format(year)
    for soup in awards[year]:
        if len(soup(tag)) > 1:
            print '{}: {}'.format(year, soup.find('AwardID').text)
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        zipdir = sys.argv[1]
        tag = sys.argv[2]
    except IndexError:
        print '{} <zipdir> {}'.format(sys.argv[0], sys.argv[2])
        sys.exit(1)

    awards = Awards(zipdir)
    years = awards.years()
    print 'Checking {} years.'.format(len(years))
    cpus = available_cpu_count()
    pool = mp.Pool(processes=cpus)
    for year in years:
        pool.apply_async(find_multiples, args=(awards, year, tag))
    pool.close()
    pool.join()
