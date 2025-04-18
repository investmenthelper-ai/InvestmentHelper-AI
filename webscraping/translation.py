from openai import OpenAI
from bs4 import BeautifulSoup, NavigableString
import pandas as pd
import re


client = OpenAI(api_key='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')

def read_html_from_excel(file_path):
    """
    Read HTML content from Excel file, handling both direct Excel reading
    and text-based fallback if needed
    """
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        html_content = df.iloc[0, 0]
        return html_content
    except Exception as excel_error:
        print(f"Warning: Could not read as regular Excel file: {str(excel_error)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '<html' in content.lower() or '<body' in content.lower():
                    return content
                else:
                    df = pd.read_excel(file_path, engine='openpyxl', dtype=str)
                    return df.iloc[0, 0]
        except Exception as e:
            raise Exception(f"Could not read file content: {str(e)}")

def is_translatable_content(text):
    text = text.strip()
    if not text:
        return False
    number_pattern = r'^[\d\s,.%$€£¥+-/=()<>[\]{}|#@!&_\'"]$'
    if re.match(number_pattern, text):
        return False
    date_pattern = r'^[\d\s\-./:|]*$'
    if re.match(date_pattern, text):
        return False
    if not re.search(r'[a-zA-Z]', text):
        return False
    if len(text) < 2:
        return False
    return True

def query_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.12
        )

        print(response)
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error querying OpenAI: {str(e)}")

def translate_html_content(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        excluded_tags = {'script', 'style', 'noscript', 'code', 'pre', 'time', 'meta'}

        def should_translate(element):
            if not isinstance(element, NavigableString):
                return False
            if element.parent.name in excluded_tags:
                return False
            if element.parent.has_attr('translate') and element.parent['translate'].lower() == 'no':
                return False
            return is_translatable_content(element.strip())

        stats = {
            'total_elements': 0,
            'translated': 0,
            'skipped_numbers': 0,
            'skipped_empty': 0,
            'failed': 0
        }

        for element in soup.find_all(string=True):
            stats['total_elements'] += 1
            text = element.strip()

            if not text:
                stats['skipped_empty'] += 1
                continue

            if not is_translatable_content(text):
                stats['skipped_numbers'] += 1
                continue

            if should_translate(element):
                try:
                    prompt = f"""If the following text contains human-readable content, translate it into English and provide only the translation.
If not, output nothing without any explanations or additional details.

Text: {text}"""

                    translated_text = query_openai(prompt)
                    element.replace_with(translated_text)
                    stats['translated'] += 1
                except Exception as e:
                    print(f"Warning: Translation failed for '{text[:50]}...': {str(e)}")
                    stats['failed'] += 1
                    continue

        print("\nTranslation Statistics:")
        print(f"Total elements processed: {stats['total_elements']}")
        print(f"Successfully translated: {stats['translated']}")
        print(f"Skipped numbers/symbols: {stats['skipped_numbers']}")
        print(f"Skipped empty elements: {stats['skipped_empty']}")
        print(f"Failed translations: {stats['failed']}")

        return str(soup)
    except Exception as e:
        raise Exception(f"Error translating HTML: {str(e)}")

def save_html_to_file(html_content, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        raise Exception(f"Error saving file: {str(e)}")

def process_excel_html(input_file, output_file):
    try:
        print(f"Reading HTML from Excel file: {input_file}")
        html_content = read_html_from_excel(input_file)

        if not html_content:
            raise ValueError("No HTML content found in the Excel file")

        print("Validating HTML content...")
        if '<html' not in html_content.lower() and '<body' not in html_content.lower():
            print("Warning: Content might not be proper HTML. Attempting to process anyway...")

        print("Translating content...")
        translated_html = translate_html_content(html_content)

        print(f"Saving translated content to: {output_file}")
        save_html_to_file(translated_html, output_file)

        print("Processing completed successfully!")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False