from flask import request, jsonify, render_template, redirect, make_response

import json
import xml.etree.ElementTree as ET
import re
import mwparserfromhell
import html2text
import bz2
from html import escape
import requests
import os
import sys
import time
from opensearch import get_opensearch, create_opensearch
from knowledge import list_knowledge, create_knowledge, upload_file, get_all_files
from auth import auth_header

from config import *
def wiki_index(search_term='*'):
    url = DB_URL + '/wikipedia/_search'
    data = {
        "query": {
            "match": {
                "title": search_term
            }
        }
    }
    try:
        response = requests.get(url, json=data)
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def wiki_routes(app):
    
    
    @app.route('/wiki', methods=['GET'])
    def get_wiki():
        # Get query parameters for pagination
        page = int(request.args.get('page', 1))  # Default to page 1
        size = int(request.args.get('size', 99))  # Default to 99 results per page
        search_term = request.args.get('search', '')

        response = wiki_search(search_term, page, size)

        # Extract results and pagination info
        results = response.json().get('hits', {}).get('hits', [])
        has_more = len(results) == size

        # Render the results page
        return render_template('results.html', search=search_term, results=results, page=page, has_more=has_more)

    @app.route('/wiki/<string:title>', methods=['GET'])
    def get_wiki_article(title):
        response = wiki_search(title, size=1)

        results = response.json().get('hits', {}).get('hits', [])
        if not results:
            return jsonify({"error": "Article not found"}), 404

        article = results[0]
        return redirect('/view/' + article['_id'])

    @app.route('/view/<int:id>', methods=['GET'])
    def view_wiki(id):
        # get this article and the next to calculate the length
        d = DB_URL + '/wikipedia/_doc/' + str(id)
        response = requests.get(d)
        if response.status_code != 200:
            print(response.json(), file=sys.stderr)
            return jsonify({"error": "Failed to fetch data from OpenSearch"}), 500
        response = response.json()
        seek = response['_source']['seek'] 
        title = response['_source']['title']
        # remove newlines and leading/ttrailing whitespace from title for cleaner display
        title = title.replace('\n', ' ').strip() 
        id = response['_id']
        
        text = get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], seek, id, title)

        if text is None:
            print('Failed to get wikitext for article: ' + str(id), file=sys.stderr)
            return jsonify({"error": "No text found for this article " + str(title)}), 404
        text = format_wikitext(text)

        if request.args.get('markdown', 'false').lower() == 'true':
            # return as text file
            # Create a text/plain response with the markdown content
            markdown_text = html_to_markdown(text, title)  # Convert HTML to Markdown
            response = make_response(markdown_text)
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.md"'
            # Return the response to download the markdown file
            return response

        return render_template('article.html', article=text)


    @app.route('/sync_wiki', methods=['GET'])
    def sync_wiki_route():
        return jsonify(sync_wiki())

def wiki_search(search_term = '', page = 1, size = 99):
    
    # Calculate the 'from' parameter
    from_param = size * (page - 1)
    
    # Perform the search
    url = DB_URL + '/wikipedia/_search'

    if search_term == '':
        query = {
            "from": from_param,
            "size": size,
            "query": {
                "match_all": {}
            }
        }
    else:
        query = {
            "from": from_param,
            "size": size,
            "query": {
                "match": {
                    "title": search_term
                }
            }
        }

    # Send the request to OpenSearch
    response = requests.get(url, json=query)
    if response.status_code != 200:
        print(response.json(), file=sys.stderr)
        return response

    # Return the paginated results
    return response

def get_wikitext(dump_filename, offset, page_id=None, title=None, namespace_id=None, block_size=256*1024, r = 0):
    """Extract and clean wikitext from a multistream dump file."""
    unzipper = bz2.BZ2Decompressor()

    # Read the compressed stream, decompress the data
    uncompressed_data = b""
    with open(dump_filename, "rb") as infile:
        infile.seek(int(offset))
        iter = 0
        maxi = 100

        while True:
            iter += 1
            if iter > maxi:
                print('Failed to get wikitext for article: ' + str(page_id) + ' - ' + str(title), file=sys.stderr)
                return None
            compressed_data = infile.read(block_size)
            if not compressed_data:  # End of file
                break
            uncompressed_data += unzipper.decompress(compressed_data)
            if unzipper.eof:  # End of the compressed stream
                break

    # Decode and parse the XML
    uncompressed_text = uncompressed_data.decode("utf-8")
    xml_data = "<root>" + uncompressed_text + "</root>"
    root = ET.fromstring(xml_data)
    for page in root.findall("page"):
        pTitle = page.find("title").text.replace('\n', ' ').strip()
        if title is not None and str(title).strip() != str(pTitle):
            continue
        if namespace_id is not None and namespace_id != int(page.find("ns").text):
            continue
        if page_id is not None and int(page_id) != int(page.find("id").text):
            continue

        # Extract wikitext
        revision = page.find("revision")
        wikitext = revision.find("text").text

        # Handle redirects
        redirect_match = re.match(r"#REDIRECT \[\[(.*?)\]\]", wikitext, re.IGNORECASE)
        if redirect_match and r < 6:
            redirect_title = redirect_match.group(1)
            # Handle fetching the redirected article (not implemented here)
            # search for the redirected article
            response = wiki_search(redirect_title, size=1)
            results = response.json().get('hits', {}).get('hits', [])
            if results:
                article = results[0]
                return get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], article['_source']['seek'], article['_id'], article['_source']['title'], r = (r + 1))
            else:
                print(f"Redirected article not found: {redirect_title}", file=sys.stderr)
                return None            
        return wikitext
    
    # If no matching page is found
    print(f"No matching page found for title: {title}, page_id: {page_id}, namespace_id: {namespace_id}", file=sys.stderr)
    return None


def format_wikitext(wikitext):
    """
    Convert wikitext to HTML using mwparserfromhell.
    """
    # Parse the wikitext
    wikicode = mwparserfromhell.parse(wikitext)

    # Convert the parsed wikitext to HTML
    html_output = ""
    for node in wikicode.nodes:
        node_type = node.__class__.__name__

        if node_type == "Text":
            html_output += escape(str(node))
        elif node_type == "Template":
            # ignore templates for now
            continue
            # html_output += f"<span class='template'>{escape(str(node))}</span>"
        elif node_type == "Wikilink":
            target = escape(str(node.title))
            text = escape(str(node.text)) if node.text else target

            if '|' in text:
                text = text.split('|')[-1]
            
            if 'thumb' in text.split('|')[0]:
                # handle links [[]] in the 
                for link in re.findall(r'\[\[(.*?)\]\]', text):
                    # if there are any links inside the link text, we need to handle them
                    text = text.replace(link, f"<a class='wikilink' href='/wiki/{link}'>{link}</a>")

                html_output += f"<a class='img' href='/wiki/{target}'>🖼️</a> {text}"

            else:
                html_output += f"<a class='wikilink' href='/wiki/{target}'>{text}</a>"
        elif node_type == "ExternalLink":
            url = escape(str(node.url))
            text = escape(str(node.title)) if node.title else url
            html_output += f"<a class='external' href='{url}'>{text}</a>"
        elif node_type == "Heading":
            level = node.level
            heading_text = escape(str(node.title.strip_code()))
            html_output += f"<h{level}>{heading_text}</h{level}>"
        elif node_type == "Tag":
            if node.tag == "ref":
                # Parse the content inside the <ref> tag
                ref_content = str(node.contents.strip_code())
                citation_html = ""

                # Check if the content is a citation template
                if ref_content.startswith("{{cite"):
                    # Extract citation fields
                    fields = {}
                    for part in ref_content.strip("{}").split("|"):
                        if "=" in part:
                            key, value = part.split("=", 1)
                            fields[key.strip()] = value.strip()

                    # Build the citation HTML
                    url = fields.get("url", "")
                    title = fields.get("title", "Untitled")
                    author = f"{fields.get('first', '')} {fields.get('last', '')}".strip()
                    date = fields.get("date", "")
                    website = fields.get("website", "")

                    citation_html = f"<cite>"
                    if url:
                        citation_html += f"<a class='cite' href='{escape(url)}'>{escape(title)}</a>"
                    else:
                        citation_html += escape(title)
                    if author:
                        citation_html += f" by {escape(author)}"
                    if date:
                        citation_html += f", {escape(date)}"
                    if website:
                        citation_html += f" ({escape(website)})"
                    citation_html += f"</cite>"
                else:
                    # If not a citation template, output raw content
                    citation_html = escape(ref_content)

                # Wrap the citation in a reference span
                html_output += f" <sub class='reference'>{citation_html}</sub>"
            else:
                html_output += escape(str(node))
        elif node_type == "Bold":
            bold_text = escape(str(node.strip_code()))
            html_output += f"<b>{bold_text}</b>"
        elif node_type == "Italic":
            html_output += f"<i>{escape(str(node))}</i>"
        elif node_type == "File":
            file_name = escape(str(node.title))
            finaltext = file_name.split('|')[-1]
            # handle links [[]] in the 
            for link in re.findall(r'\[\[(.*?)\]\]', finaltext):
                # if there are any links inside the link text, we need to handle them
                finaltext = finaltext.replace(link, f"<a class='wikilink' href='/wiki/{link}'>{link}</a>")
            html_output += f"<ins>{finaltext}</ins>"
        else:
            html_output += escape(str(node))

    if html_output == "":
        return "No content found"
    return html_output

def html_to_markdown(html, title):
    """
    Convert HTML to Markdown using html2text.
    """
    markdown_converter = html2text.HTML2Text()
    markdown_converter.body_width = 0  # Prevent line wrapping in the output
    markdown_converter.ignore_links = True  # Keep links in the Markdown
    markdown_output = markdown_converter.handle(html)
    # add title to the top
    markdown_output = f"# {title}\n\n" + markdown_output

    return markdown_output

def sync_wiki(reindex=False):
    # If we dont have wikipedia, grab it
    if not os.path.exists(WIKI_DIR):
        os.makedirs(WIKI_DIR)
    if not os.path.exists(WIKI_DIR + WIKI_URL.split('/')[-1]):

        os.system('wget ' + WIKI_URL + ' -P ' + WIKI_DIR)
    if not os.path.exists(WIKI_DIR + INDEX.split('/')[-1]):
        # Get the index
        os.system('wget ' + INDEX + ' -P ' + WIKI_DIR)
    # check if an index exists in opensearch
    if get_opensearch('wikipedia') is None:
        create_opensearch()
        reindex = True
    elif reindex:
        # delete the index and recreate it
        print(requests.delete(DB_URL + '/wikipedia'), file=sys.stderr)
        print(create_opensearch(), file=sys.stderr)
    
    while get_opensearch('wikipedia') is None:
        print('Waiting for wikipedia index')
        time.sleep(5)

    if reindex:
        # upload the index into opensearch
        with bz2.open(WIKI_DIR + INDEX.split('/')[-1], 'rt') as f:
            chunk = []
            i = 0
            c = 0
            length = len(f.readlines())
            f.seek(0)
            print('Uploading ' + str(length // 1000) + ' chunks')
            for line in f:
                
                try:
                    l = line.split(':')
                    seek = int(l[0])
                    id = int(l[1])

                    # anything 2 onwards is the title, mash it back together
                    title = ':'.join(l[2:])
                except:
                    print('Failed to parse line ' + str(i) + '\n' + line, file=sys.stderr)
                    continue
                    
                # Add the create action and document to the chunk
                chunk.append(json.dumps({"create": {"_id": id}}))
                chunk.append(json.dumps({"title": title, "seek": seek}))
                
                if len(chunk) > 1000 * 2:
                    print('Uploading chunk ' + str(c + 1) + ' of ' + str(length // 1000))
                    bulk_data = '\n'.join(chunk) + '\n'
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.post(DB_URL + '/wikipedia/_bulk', data=bulk_data, headers=headers)
                    if response.status_code != 200:
                        print(response.json(), file=sys.stderr)
                        raise Exception('Failed to upload chunk: ' + str(response))
                    chunk = []
                    c += 1

                i += 1

        # Upload the last chunk
        bulk_data = '\n'.join(chunk) + '\n'
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(DB_URL + '/wikipedia/_bulk', data=bulk_data, headers=headers)
        if response.status_code != 200:
            print(response.json(), file=sys.stderr)
            raise Exception('Failed to upload chunk: ' + str(response))
        
        requests.post(DB_URL + '/_refresh')
    
        print('Finished uploading')
    
    # add files to knowledge
    # create a knowledge if it doesnt exist
    id = None
    name = 'Wikipedia'
    knowledge_list = list_knowledge()
    if knowledge_list is None:
        knowledge_list = list_knowledge()

    for knowledge in knowledge_list:
        if knowledge['name'] == name:
            id = knowledge['id']

    if id is None:
        knowledge = create_knowledge(name, '')
        id = knowledge['id']

    fileList = get_all_files()
    print('Adding files to knowledge base: ' + name, file=sys.stderr)
    page = 0
    done = False
    while not done:
        # get the next page of wikipedia articles
        page += 1
        
        results = wiki_search(search_term='', page=page, size=99).json().get('hits', {}).get('hits', [])

        tries = 3
        while len(results) == 0 and tries > 0:
            results = wiki_search(search_term='', page=page, size=99).json().get('hits', {}).get('hits', [])
            tries -= 1


        for hit in results:
            seek = hit['_source']['seek']
            hid = hit['_id']
            title = hit['_source']['title']
            title = title.replace('\n', ' ').strip() 

            # save the file to the temp file
            filename = '/tmp/' + title.replace('/', '_').replace(':', '_') + '.md'  # ensure filename is valid
            
            # check if the file is already in the knowledge base by title
            url = BASE_URL + 'knowledge/' + id
            exists = False
            try:
                # check if the file already exists in the knowledge base by title
                response = requests.get(url, headers=auth_header())
                if response.status_code == 200:
                    knowledge_data = response.json()
                    # Check if a file with the same title already exists in the knowledge base
                    for file in knowledge_data.get('files', []):
                        if file['filename'] == title.replace('/', '_').replace(':', '_') + '.md':
                            exists = True
                            break
            except Exception as err:
                print(f"Error checking knowledge base for existing file: {err}", file=sys.stderr)
                continue

            if exists:
                print(f"Skipping file as it already exists in the knowledge base: {title}", file=sys.stderr)
                continue
                
            else:
                # clear the files in temp
                for temp_file in os.listdir('/tmp/'):
                    temp_file_path = os.path.join('/tmp/', temp_file)
                    try:
                        if os.path.isfile(temp_file_path):
                            os.remove(temp_file_path)
                    except Exception as e:
                        print(f"Error deleting temp file: {e}", file=sys.stderr)
                with open(filename, 'w') as f:
                    text = get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], seek, hid, title)
                    if text is None:
                        print('Failed to get wikitext for article: ' + str(hid) + ' - ' + str(title), file=sys.stderr)
                        continue
                    text = html_to_markdown(format_wikitext(text), title)
                    # if this article sucks or is a redirect, skip it
                    if text is None:
                        continue
                    elif 'REDIRECT' in text:
                        continue
                    elif len(text) < 100:
                        continue
                    f.write(text)
                # upload the file
                res = upload_file(filename, fileList)
                if res is None:
                    print('Failed to upload file for article: ' + str(hid) + ' - ' + str(title), file=sys.stderr)
                    continue
            
                else:
                    data = {
                        'file_id': res['id']
                    }
                    url = BASE_URL + 'knowledge/' + id + '/file/add'
                    try:
                        response = requests.post(url, headers=auth_header(), json=data)
                        if response.status_code != 200:
                            print('Failed to add file to knowledge base for article: ' + str(hid) + ' - ' + str(title), file=sys.stderr)
                    except ValueError as ve:
                        # duplicate file in the knowledge base, this can happen if the same article is uploaded multiple times
                        continue
                    except Exception as err:
                        print(err, file=sys.stderr)
        
        requests.post(DB_URL + '/_refresh')
    
    return 'Finished syncing wikipedia'
