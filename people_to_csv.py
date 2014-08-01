from csv import DictWriter
import cPickle as pickle


pfields = ['id', 'title', 'nickname', 'fname', 'mname', 'lname', 'suffix']
pgmfields = ['person_id', 'program']
divfields = ['person_id', 'division']

pfile = open('people.csv', 'w')
pwriter = DictWriter(pfile, fieldnames=pfields, extrasaction='ignore')

pgmfile = open('people-in-programs.csv', 'w')
pgmwriter = DictWriter(pgmfile, fieldnames=pgmfields, extrasaction='ignore')

divfile = open('people-in-divisions.csv', 'w')
divwriter = DictWriter(divfile, fieldnames=divfields, extrasaction='ignore')

writers = [pwriter, pgmwriter, divwriter]
for writer in writers:
    writer.writeheader()


def gen_person(people):
    for person in people:
        person.__dict__['person_id'] = person.id
        yield person.__dict__

def people_to_csv(people):
    for person in gen_person(people):
        pwriter.writerow(person)
        divwriter.writerow(person)
        for pgm in person['programs']:
            pgmwriter.writerow({'person_id': person['id'], 'program': pgm})


if __name__ == "__main__":
    with open('people.pickle', 'r') as f:
        people = pickle.load(f)
        people_to_csv(people)
