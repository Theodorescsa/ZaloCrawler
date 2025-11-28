import csv

with open('contacts_selected.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    with open('contacts.vcf', 'w', encoding='utf-8') as vcf:
        for row in reader:
            name = row.get('name') or row['mobile']
            phone = row['mobile']
            vcf.write("BEGIN:VCARD\n")
            vcf.write("VERSION:3.0\n")
            vcf.write(f"N:{phone}-{name};;;\n")
            vcf.write(f"FN:{phone}-{name}\n")
            vcf.write(f"TEL;TYPE=CELL:{phone}\n")
            vcf.write("END:VCARD\n")
            vcf.write("\n")
