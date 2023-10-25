# qChecker

- Add the filename of the source document in check_text.md (under `filename:`) or in response to a prompt.
- Add the quotations to be checked in check_text.md (pasted into the body) or have in your clipboard.

Prints a match % and colored diff per quotation.

## Example

- update PDF_DIRECTORY
- download this PDF and save to your PDF_DIRECTORY: https://arxiv.org/pdf/2310.14724.pdf
- note the existing filename in check_text.md and the existing quotations-to-be-checked. The first three quotations-to-be-checked were devised to test multiple page spans, column spans, and single page spans. The remaining were in the response from Claude in this tweet: https://twitter.com/danielsgriffin/status/1717312889625686367

## Note 

- Only tested on MacOS.
- See a small post on my website: [qChecker - a script to check for quotes in a source document](https://danielsgriffin.com/pposts/2023/10/25/qchecker-a-script-to-check-for-quotes-in-a-source-document.html)
