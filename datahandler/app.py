from flask import Flask, jsonify, send_file, redirect, request, render_template, make_response
import requests
from requests.auth import HTTPBasicAuth # for opensearch if we enable security
from urllib.parse import unquote as URLDecoder
import os
import sys
import bz2
import time
import json
import xml.etree.ElementTree as ET
import re
import mwparserfromhell
import html2text
from html import escape

from openai import AsyncOpenAI
from outlines import models
from outlines.models.openai import OpenAIConfig

client = AsyncOpenAI(
    base_url="http://ollama:11434/v1/chat/completions",
    api_key='',
)
config = OpenAIConfig("llama3.2:35b")
model = models.openai(client, config)

print("Starting up data handler with model: " + str(model))

BASE_DIRECTORY = '/app/data/docs/'

WIKI_DIR = '/app/data/wiki/'

WIKI_URL = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2'
INDEX = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2'

BASE_URL = os.getenv('OPENWEBUI_URL', 'http://open-webui:8080') + '/api/v1/'

DB_URL = os.getenv('OPENSEARCH_URI', 'http://opensearch-node1:9200')

global current_token
current_token = None


def auth_header():
    return {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }

HEADERS = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

def signup():
    url = BASE_URL + 'auths/signup'

    data ={
    "name": os.getenv('DEFAULT_USERNAME'),
    "email": os.getenv('DEFAULT_USERNAME'),
    "password": os.getenv('DEFAULT_PASSWORD')
    }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        return login()
    except Exception as err:
        print(err, file=sys.stderr)
        return None

def login():
    url = BASE_URL + 'auths/signin'
    
    data = {
        'email': os.getenv('DEFAULT_USERNAME'),
        'password': os.getenv('DEFAULT_PASSWORD')
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        global current_token
        current_token = response.json()["token"]
        return response.json()

    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def get_opensearch(indexname = '_cluster/health'):
    url = DB_URL + '/' + indexname

    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"OpenSearch response: {response.json()}", file=sys.stderr)  # Log the response for debugging
            return response.json()
        else:
            print(response.json(), file=sys.stderr)
            return None
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def get_api():
    url = BASE_URL + 'auths/api_key'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None  
    
def session():
    url = BASE_URL + 'auths/'

    try:
        response = requests.get(url, headers=HEADERS)
        if response.json()["detail"] == "Not authenticated":
            return None
        
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def auth():
    # if we have a valid token, return it
    global current_token
    if current_token is not None and get_api() is not None:
        return {"token": current_token}
    
    # get session -> if not exist -> login -> if not exist -> signup
    session_data = session()
    if session_data is None:
        login_data = login()
        if login_data is None:
            signup_data = signup()
            return signup_data
        else:
            return login_data
    else:
        return session_data
    
app = Flask(__name__)

@app.route('/login', methods=['GET'])
def token():
    return jsonify(auth())

@app.route('/')
def explorer():
    return open('index.html').read()

@app.route('/dir/<path:path>', methods=['GET'])
def get_dir(path):
    return open('index.html').read()

@app.route('/file/<path:path>', methods=['GET'])
def get_file(path):
    return open('display.html').read()

@app.route('/sync/', methods=['GET'])
def sync_root():
    files = []
    directories = [BASE_DIRECTORY]

    while directories:
        current_directory = directories.pop()
        for entry in os.listdir(current_directory):
            full_path = os.path.join(current_directory, entry)
            if os.path.isdir(full_path):
                directories.append(full_path)
            else:
                files.append(full_path)
    print(files, file=sys.stderr)
    knowledgeid = sync('Default', files)
    return redirect('/knowledge/' + knowledgeid)

@app.route('/sync/dir/<path:path>', methods=['GET'])
def sync_dir(path):
    files = []
    for file in os.listdir(BASE_DIRECTORY + path):
        if os.path.isdir(os.path.join(BASE_DIRECTORY + path, file)):
            continue
        files.append(os.path.join(BASE_DIRECTORY + path, file))
    knowledgeid = sync(path.split('/')[-1], files)
    return redirect('/knowledge/' + knowledgeid)


@app.route('/get/<path:path>', methods=['GET'])
def get_file_content(path):
    try:
        path = URLDecoder(path)
        return send_file(BASE_DIRECTORY + path)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/list_files/<path:path>', methods=['GET'])
def list_files_dynamic(path):
    return list_files(path)

@app.route('/list_files', methods=['GET'])
def list_files_root():
    return list_files('')

@app.route('/list_knowledge', methods=['GET'])
def list_knowledge_dynamic():
    knowledge = list_knowledge()
    if knowledge is None:
        knowledge = list_knowledge()
    if knowledge is None:
        return jsonify([]), 404
    return jsonify(knowledge)

@app.route('/knowledge/<string:id>', methods=['GET'])
def get_knowledge(id):
    url = BASE_URL + 'knowledge/' + id

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    

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

def list_files(path):
    directory = BASE_DIRECTORY + path
    try:
        files = []
        dirs = []
        for file in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, file)):
                dirs.append(file)
            else:
                files.append(file)
        return jsonify({"files": files, "dirs": dirs}), 200
    except FileNotFoundError:
        return jsonify({"error": "Directory not found"}), 404
    
def list_knowledge():
    url = BASE_URL + 'knowledge/list'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def create_knowledge(name, description):
    url = BASE_URL + 'knowledge/create'

    data = {
        "name": name,
        "description": description
        }
    
    try:
        response = requests.post(url, headers=auth_header(), json=data)
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def get_all_files():
    url = BASE_URL + 'files/'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def upload_file(file, fileList=None, rename=None):
    url = BASE_URL + 'files/'
    global current_token
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }
    name = file.split('/')[-1]
    if rename is not None:
        name = rename

    file_metadata = {
        'name': name,
        'description': ''
    }
    
    files = { 
        'file': (file, open(file, 'rb')),
    }
    fileD = None
    # check if file exists
    try:
        if fileList is None: # filelist is passed in to make batch processing faster
            fileList = get_all_files()
        for f in fileList:
            if f['filename'] == file_metadata['name']:
                fileD = f
                break        
    except Exception as err:
        print(err, file=sys.stderr)

    if fileD is not None:
        # decide if we want to update it
        # for now, return the existing file
        return fileD
    else: # create file 
        try:
            response = requests.post(url, headers=headers, files=files)
            return response.json()
        except Exception as err:
            print(err, file=sys.stderr)
            return None
        
def add_files_to_knowledge(knowledge_id, files):
    url = BASE_URL + 'knowledge/' + knowledge_id + '/file/add'

    for file in files:
        res = upload_file(file, get_all_files())
        if res is not None:
            if res.get('id') is not None:
                data = { 
                    'file_id': res['id']
                }
                try:
                    response = requests.post(url, headers=auth_header(), json=data)
                except Exception as err:
                    print(err, file=sys.stderr)
                    return None
            else:
                print('Failed to upload, response: ' + str(res), file=sys.stderr)
    return requests.get(BASE_URL + 'knowledge/' + knowledge_id, headers=auth_header()).json()

def sync(name, files):
    id = None
    knowledge_list = list_knowledge()
    if knowledge_list is None:
        knowledge_list = list_knowledge()

    for knowledge in knowledge_list:
        if knowledge['name'] == name:
            id = knowledge['id']
            add_files_to_knowledge(id, files)
            return id

    if id is None:
        knowledge = create_knowledge(name, '')
        id = knowledge['id']

    add_files_to_knowledge(id, files)
    return id

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
    
def create_opensearch(indexname = 'wikipedia'):
    url = DB_URL + '/' + indexname
    data = {
        "mappings": {
            "properties": {
                "title": { # third the article title.
                    "type": "text"
                },
                "seek": { # first field of this index is the number of bytes to seek into the compressed archive 
                    "type": "integer"
                }
            }
        }
    }                
    
    try:
        # requests.put('http://opensearch-node:9200/wikipedia')
        response = requests.put(url, json=data)
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None


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

if __name__ == '__main__':
    
    time.sleep(10) # docker depend-on isnt waiting for the api to be ready
    print('Trying to authenticate')
    print(auth())
    while get_api() is None:
        print('Trying to authenticate')
        print(auth())
        time.sleep(5)
    time.sleep(1)

    # make sure opensearch is ready
    while get_opensearch() is None:
        print('Waiting for OpenSearch')
        time.sleep(5)

    # run start up sync
    if os.getenv('SYNC_ON_STARTUP', 'false').lower() == 'true':
        print('Syncing wiki')
       # print(sync_wiki())
        print('Syncing root')
        files = []
        if not os.path.exists(BASE_DIRECTORY):
            print(f"Base directory '{BASE_DIRECTORY}' does not exist. Creating it.", file=sys.stderr)
            os.makedirs(BASE_DIRECTORY)
        if not os.path.exists(WIKI_DIR):
            print(f"Wiki directory '{WIKI_DIR}' does not exist. Creating it.", file=sys.stderr)
            os.makedirs(WIKI_DIR)
        
        directories = [BASE_DIRECTORY]

        while directories:
            current_directory = directories.pop()
            for entry in os.listdir(current_directory):
                full_path = os.path.join(current_directory, entry)
                if os.path.isdir(full_path):
                    directories.append(full_path)
                else:
                    files.append(full_path)
        print(files, file=sys.stderr)
        sync('Default', files)

    app.run(host='0.0.0.0', port=os.getenv('FLASK_PORT', 5000))