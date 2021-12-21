import bibtexparser, re, io, csv
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser


parser = BibTexParser()
parser.ignore_nonstandard_types = False

parser = BibTexParser()
parser.ignore_nonstandard_types = False

cite_re = re.compile(r'[(]([^)]*)[)]')
entry_re = re.compile(r'^([^,]*).*(\d{4})$')

def bibtex_to_csv(bibtex_file):
    bib_database = bibtexparser.load(bibtex_file, parser)
    ouput = io.StringIO()
    w = csv.writer(ouput, delimiter=',',
        quotechar='"', quoting=csv.QUOTE_MINIMAL)
    w.writerow(["type", 
        "author", "year", "title", "pages", 
        "publisher", "editor", "institution", "journal", 
        "issue", "volume", "isbn", "issn", "doi"])
    for entry in bib_database.entries:
        w.writerow([entry['ENTRYTYPE'], 
            entry.get('author'), entry.get('year'), entry.get('title'), entry.get("pages"),
            entry.get('publisher'), entry.get('editor'), entry.get('institution'), entry.get('journal'),
            entry.get('issue'), entry.get('volume'), entry.get('isbn'), entry.get('issn'), entry.get('doi')])
    return ouput.getvalue()

def bibtex_entries_by_authors(bib_database: BibDatabase):
    index = {}
    for entry in bib_database.entries:
        author = entry.get('author')
        if author is not None:
            authors = author.split(" and ")
            if len(authors) > 0:
                names = authors[0].split(" ")
                first_author = names[-1]
            else:
                continue
        else:
            continue
        if first_author not in index:
            index[first_author] = []
        index[first_author].append(entry)
    return index

def matching_entries_ids(potential_entries: str, first_author: str, year: str) -> list:
    matching = []
    for potential_entry in potential_entries:
        if potential_entry.get('year') == year:
            matching.append(potential_entry['ID'])
    return matching

def auto_cite(bibtex_file, text):
    citations = cite_re.findall(text)
    bib_database = bibtexparser.load(bibtex_file, parser)
    entries_by_authors = bibtex_entries_by_authors(bib_database)
    replacements = []
    for citation in citations:
        citation_parts = citation.split(";")
        matching_entries = []
        for citation_part in citation_parts:
            m = entry_re.match(citation_part)
            if m is not None:
                first_author, year = m.groups()
                first_author = first_author.removesuffix("et al.").strip()
                print("author", first_author)
                potential_entries = entries_by_authors.get(first_author)
            matching_entries += matching_entries_ids(potential_entries, first_author, year) if potential_entries else []
        if len(matching_entries) > 0:
            replacements.append((f'({citation})', f'\\cite{{{",".join(matching_entries)}}}'))
    for old, new in replacements:
        text = text.replace(old, new)
    return text