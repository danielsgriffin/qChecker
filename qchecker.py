import os
import fitz  # PyMuPDF
import pyperclip
import sys
from fuzzywuzzy import fuzz
import difflib
from termcolor import colored
import yaml
import string


# Constants
PDF_DIRECTORY = "/Users/dsg/Documents/pdfs/"  # Update this path as needed
HIGHLIGHT_COLOR = (1, 1, 0)  # Yellow


def get_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text


def fuzzy_find(phrase, text):
    """Find an approximate location of a phrase in text."""
    words = text.split()

    # Strip leading and trailing quotation marks from the phrase
    if phrase.startswith('"') and phrase.endswith('"'):
        phrase = phrase[1:-1]
    phrase_words = phrase.split()

    best_match = 0
    best_idx = -1
    found_phrase = ""

    # The following loop scans the text to find the best matching position for the phrase.
    # It does this by comparing the phrase with every possible substring of the text that has the same number of words as the phrase.
    # The comparison is done using the fuzz.ratio function, which calculates the Levenshtein distance between the two strings.
    # The Levenshtein distance is a measure of the minimum number of single-character edits (insertions, deletions or substitutions) required to change one string into the other.
    # If the match score for a substring is higher than the current best match score, the best match score and the best index are updated.
    # The best index is the position in the text where the best match starts.
    # The found phrase is also updated to be the substring that produced the best match.
    for i in range(len(words) - len(phrase_words) + 1):
        match = fuzz.ratio(
            " ".join(phrase_words), " ".join(words[i : i + len(phrase_words)])
        )
        if match > best_match:
            best_match = match
            best_idx = i
            found_phrase = " ".join(words[i : i + len(phrase_words)]).strip()

    # Make properly greedy -- clunky, TODO: add to functions and add tests
    missing_start = []
    for word in phrase_words:
        if word.lower() != found_phrase.split()[0].lower():
            missing_start.append(word)
        else:
            break
        
    missing_start_string = " ".join(missing_start)
    
    if missing_start_string:
        if missing_start_string.lower() == " ".join(words[best_idx-len(missing_start):best_idx]).lower():
            found_phrase = " ".join(words[best_idx-len(missing_start):best_idx]) + " " + found_phrase
        elif " ".join(words[best_idx-len(missing_start):best_idx]).lower() in missing_start_string.lower():
            missing_start_start_idx = best_idx-len(missing_start)-1
            try_start = " ".join(words[missing_start_start_idx:best_idx])
            print(try_start)
            if try_start.replace("- ", "").lower() == missing_start_string.lower():
                found_phrase = " ".join(words[best_idx-len(missing_start)-1:best_idx]) + " " + found_phrase
    
    missing_end = []
    for word in phrase_words[::-1]:
        if word.lower() != found_phrase.split()[-1].lower():
            missing_end.append(word)
        else:
            break

    missing_end_string = " ".join(missing_end)
    missing_end_start_idx = best_idx + len(found_phrase.split())
    missing_end_end_idx = best_idx + len(found_phrase.split()) + len(missing_end)
    bonus = len(
        [x for x in words[missing_end_start_idx:missing_end_end_idx] if x.endswith("-")])
    missing_end_end_idx += bonus
    if missing_end_string:
        found_missing_end = " ".join(words[missing_end_start_idx:missing_end_end_idx])
        if (found_missing_end in missing_end_string) or (found_missing_end.replace("- ", "") in missing_end_string):
            found_phrase = found_phrase + " " + found_missing_end

    def refuzz(phrase, found_phrase):
        """Strips leading and tailing quotation marks from the phrase if they are not in the
        found_phrase, attempts to repair all line-ending hyphenation problems, and then
        recalculates the fuzz.ratio."""
        # Strip leading and tailing quotation marks from the phrase if they are not in the found_phrase
        if phrase[0] == '"' and found_phrase[0] != '"':
            phrase = phrase[1:]
        if phrase[-1] == '"' and found_phrase[-1] != '"':
            phrase = phrase[:-1]

        # Function to handle hyphen-ended substrings
        # Note: CLUNKY!
        def handle_hyphen_ended_substring(phrase, found_phrase, hyphen_ended_substring):
            # print("Debug: Entering handle_hyphen_ended_substring function")
            # print(f"Debug: hyphen_ended_substring = {hyphen_ended_substring}")
            # Split the found_phrase using the hyphen_ended_substring
            split_phrase = found_phrase.split(hyphen_ended_substring)
            # print(f"Debug: split_phrase = {split_phrase}")
            
            # Get the substring after the hyphen_ended_substring
            after_hyphen_ended_substring = split_phrase[1]
            # print(f"Debug: after_hyphen_ended_substring (before split) = {after_hyphen_ended_substring}")
            
            # Split the after_hyphen_ended_substring by space and get the first element
            after_hyphen_ended_substring_list = after_hyphen_ended_substring.strip().split(" ")
            # print(f"Debug: after_hyphen_ended_substring_list (after split) = {after_hyphen_ended_substring_list}")
            after_hyphen_ended_substring = after_hyphen_ended_substring_list[0]
            # print(f"Debug: after_hyphen_ended_substring = {after_hyphen_ended_substring}")
            if hyphen_ended_substring + after_hyphen_ended_substring in phrase:
            #    print("Debug: Replacing hyphen-ended substring in found_phrase")
               found_phrase = found_phrase.replace(
                   f"{hyphen_ended_substring} {after_hyphen_ended_substring}", hyphen_ended_substring + after_hyphen_ended_substring)
            elif hyphen_ended_substring.rstrip("-") + after_hyphen_ended_substring in phrase:
                # print("Debug: Replacing hyphen-ended substring without hyphen in found_phrase")
                found_phrase = found_phrase.replace(f"{hyphen_ended_substring} {after_hyphen_ended_substring}",
                                        hyphen_ended_substring.rstrip("-") + after_hyphen_ended_substring)
            # print(f"Debug: Exiting handle_hyphen_ended_substring function with found_phrase = {found_phrase}")
            return found_phrase

        repaired_phrase = found_phrase
        # Check if hyphen exists in phrase
        for substring in found_phrase.split():
            if substring.endswith("-"):
                repaired_phrase = handle_hyphen_ended_substring(
                    phrase, repaired_phrase, substring)
    
        # Recalculate the fuzz.ratio
        match = fuzz.ratio(phrase, repaired_phrase)
        return match, repaired_phrase, phrase

    best_match, repaired_phrase, phrase = refuzz(phrase, found_phrase)

    def contextualize_found_phrase(text, found_phrase, context_length=5):
        
        """Find the found phrase in the text and then grab a few words from either end, return the expanded version with leading and trailing ellipses."""
        text = " ".join(text.split())
        start_idx = text.find(found_phrase)
        end_idx = start_idx + len(found_phrase)

        # Grab 50 chars from either end of the found phrase
        start_context = max(0, start_idx - 50)
        end_context = min(len(text), end_idx + 50 + 1)

        # Add the appropriate words to the found_phrase
        start_phrase = " ".join(text[start_context:start_idx].split()[-5:])
        end_phrase = " ".join(text[end_idx:end_context].split()[:5])

        # Return the expanded phrase with leading and trailing ellipses
        return '... ' + start_phrase, end_phrase + "..."

    start_phrase, end_phrase = contextualize_found_phrase(text, found_phrase)

    return (
        phrase,
        repaired_phrase,
        start_phrase, end_phrase,
        best_idx,
        best_idx + len(phrase_words) if best_idx != -1 else -1,
        best_match,
    )


def print_diff(phrase, found_phrase, start_phrase, end_phrase):
    """Prints a color text diff to show the differences between the phrase and found_phrase."""
    diff = difflib.ndiff(
        found_phrase.split(),
        phrase.split())
    diff_text = ""
    for i in diff:
        if i[0] == " ":
            diff_text += i[2:] + " "
        elif i[0] == "-":
            diff_text += colored(i[2:], "red") + " "
        elif i[0] == "+":
            diff_text += colored(i[2:], "green") + " "
    
    print(colored(start_phrase, "cyan") + " " +
          diff_text + " " + colored(end_phrase, "cyan"))


def print_diff(phrase, found_phrase, start_phrase, end_phrase):
    """Prints a color text diff with character-level highlighting."""
    diff = difflib.ndiff(found_phrase, phrase)
    diff_text = ""
    for i in diff:
        if i[0] == " ":
            diff_text += i[2]
        elif i[0] == "-":
            diff_text += colored(i[2], "red")
        elif i[0] == "+":
            diff_text += colored(i[2], "green")

    print(colored(start_phrase, "cyan") + " " +
          diff_text + " " + colored(end_phrase, "cyan"))
    

def main():
    
    # Try to get filename and contents from check_text.md
    try:
        with open('check_text.md', 'r') as file:
            file_contents = file.read()
            assert len(file_contents) > 2
        print("Using contents from check_text.md...")
    except (FileNotFoundError, AssertionError):
        print("check_text.md not found or empty. Pasting from clipboard...")
        check_content = pyperclip.paste()
    else:
        try:
            file_contents_dict = yaml.safe_load(file_contents.split("\n---")[0])
            if 'filename' in file_contents_dict:
                filename = file_contents_dict['filename']
                print("Using PDF filename from check_text.md...")
        except yaml.YAMLError as e:
            print(e)
            filename = input("Enter the filename of the PDF: ")
            # filename = "2310.14724.pdf" # optional hard-coding
            check_content = file_contents
        else:
            check_content = file_contents.split("\n---")[1]
    search_strings = [s.strip()
                      for s in check_content.split("\n") if s.strip()]
    
    pdf_path = os.path.join(PDF_DIRECTORY, filename)
    if not os.path.exists(pdf_path):
        print(f"File does not exist: {pdf_path}")
        sys.exit(1)

    # Process the PDF
    text = get_text_from_pdf(pdf_path)

    print("\nSearching for phrases...")
    print("If matches are found a colored diff will be printed:")
    print("   - ", colored("only in original", "red"))
    print("   - ", colored("only in search phrase", "green"))
    print("   - ", colored("prepended/appended context", "cyan"))
    print("Note: End-of-line hyphenation, if matched, is automatically repaired.")
    matches = []
    for i, phrase in enumerate(search_strings, 1):
        print("--------------------------------------------------")
        phrase, found_phrase, start_phrase, end_phrase, start, end, match_quality = fuzzy_find(
            phrase, text)
        matches.append((found_phrase, phrase, start, end, match_quality))
        if match_quality > 80:
            print(
                f"Phrase {i} - Match quality: {colored(str(match_quality) + '%', 'green')}"
            )
            print_diff(phrase, found_phrase, start_phrase, end_phrase)
        else:
            print(
                f"⚠️ Phrase {i} NOT found in document!\nMatch quality: {colored(str(match_quality) + '%', 'red')}"
            )
            print(colored(f"{phrase}", "red"))

if __name__ == "__main__":
    main()
