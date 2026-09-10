The S-014 export (partner_export_2026-08.csv) is formatted differently than for other stores, it formats amounts over a thousand with a non-breaking space as a thousands separator. parse_amount's regex only matches a contiguous run of digits followed by a single optional decimal separator, so on hitting the non-breaking space it stops early and returns just the leading digit, this turns 1 321,49 into 1 instead of 1321.49.
The README notes that store S-014's data arrives through a separate exporter with different formatting, and a parse.py's comment describing the amount shapes it expects to handle. This pointed at parse_amount as the likely source. Checking every S-014 amount against those documented shapes showed the parser breaks specifically on amounts over 1,000.

The failing command: 
python -c "from pipeline.parse import parse_amount; from decimal import Decimal; assert parse_amount('1\xa0321,49') == Decimal("1321.49")"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AssertionError

This belongs in the instruction document: the comment in parse.py explicitly enumerates the amount shapes it expects and never accounted for thousands separators. 
There is also a problem in the structure of the code as this should have logged an error (same problem with treating any unparseable input as zero).

This took me just under 2 hours.