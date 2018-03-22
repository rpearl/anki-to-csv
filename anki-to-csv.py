import argparse
import csv
import json
import os
import sqlite3
import tempfile
import zipfile

from collections import defaultdict

parser = argparse.ArgumentParser(description='Convert an apkg to a csv and a list of media files')

parser.add_argument('file', help="file to parse")
parser.add_argument('outdir', help="output directory")

def progress(val, start, end, length):
    pct = (val - start) / (end - start)
    filled = int(pct * length)
    unfilled = length - filled
    return '█'*filled + '░'*unfilled + ' %d/%d (%.2f%%)' % (val, (end-start), pct*100)

def main():
    args = parser.parse_args()

    z = zipfile.ZipFile(args.file)

    media_dir = os.path.join(args.outdir, 'media')

    os.makedirs(media_dir, exist_ok=True)

    media = json.loads(z.read("media").decode("utf8"))
    i = 0
    for k, v in media.items():
        i += 1
        print('\rWriting media: '+progress(i, 0, len(media), 20), end='')
        path = os.path.join(media_dir, v)
        with open(path, 'wb') as f:
            f.write(z.read(k))

    print()

    with tempfile.NamedTemporaryFile() as f:
        f.write(z.read("collection.anki2"))

        conn = sqlite3.connect(f.name)
        c = conn.cursor()
        models = {}
        for row in c.execute('select models from col'):
            models.update(json.loads(row[0]))

        fieldnames = {}
        for mid, model in models.items():
            fieldnames[mid] = [f['name'] for f in model['flds']]

        data = defaultdict(list)

        c.execute('select mid, flds from notes')
        notes = c.fetchall()
        i = 0
        for note in notes:
            i += 1
            print('\rWriting notes: '+progress(i, 0, len(notes), 20), end='')
            mid, flds = note
            mid = str(mid)
            line = {}
            model = fieldnames[mid]
            fields = flds.split('\x1f')
            for name, field in zip(model, fields):
                line[name] = field
            data[mid].append(line)

        for mid, rows in data.items():
            csv_name = 'model%s.csv' % (mid,)
            csv_path = os.path.join(args.outdir, csv_name)
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, dialect='unix', fieldnames=fieldnames[mid])
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        print()

if __name__ == '__main__':
    main()

