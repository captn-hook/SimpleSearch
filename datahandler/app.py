from flask import Flask, jsonify, send_file, redirect, request, render_template
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

BASE_DIRECTORY = '/app/data/docs/'

WIKI_DIR = '/app/data/wiki/'

WIKI_URL = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2'
INDEX = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2'

BASE_URL = os.getenv('OPENWEBUI_URL', 'http://open-webui:8080') + '/api/v1/'

DB_URL = os.getenv('OPENSEARCH_URI', 'http://opensearch-node:9200')

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
    print('Signing up as default user', file=sys.stderr)
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
    print('Logging in as default user', file=sys.stderr)
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
    
def get_opensearch(indexname = None):
    url = DB_URL
    if indexname is not None:
        url += '/' + indexname

    try:
        response = requests.get(url)
        if response.status_code == 200:
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
    
    text = get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], response.json()['_source']['seek'], id)

    text = format_wikitext(text)

    return render_template('article.html', article=text)

@app.route('/sync_wiki', methods=['GET'])
def sync_wiki_route():
    return jsonify(sync_wiki(True))

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
        return jsonify({"error": "Failed to fetch data from OpenSearch"}), response.status_code

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
            data = {
                'file_id': res['id']
            }
            try:
                response = requests.post(url, headers=auth_header(), json=data)
            except Exception as err:
                print(err, file=sys.stderr)
                return None
    return requests.get(BASE_URL + 'knowledge/' + knowledge_id, headers=auth_header()).json()

def sync(name, files):
    id = None
    knowledge_list = list_knowledge()
    if knowledge_list is None:
        knowledge_list = list_knowledge()

    for knowledge in knowledge_list:
        if knowledge['name'] == name:
            id = knowledge['id']
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
    print(url, file=sys.stderr)
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


def get_wikitext(dump_filename, offset, page_id=None, title=None, namespace_id=None, verbose=True, block_size=256*1024):
    """Extract and clean wikitext from a multistream dump file."""
    unzipper = bz2.BZ2Decompressor()

    # Read the compressed stream, decompress the data
    uncompressed_data = b""
    with open(dump_filename, "rb") as infile:
        infile.seek(int(offset))

        while True:
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
        if title is not None and title != page.find("title").text:
            continue
        if namespace_id is not None and namespace_id != int(page.find("ns").text):
            continue
        if page_id is not None and page_id != int(page.find("id").text):
            continue

        # Extract wikitext
        revision = page.find("revision")
        wikitext = revision.find("text").text

        # Handle redirects
        redirect_match = re.match(r"#REDIRECT \[\[(.*?)\]\]", wikitext, re.IGNORECASE)
        if redirect_match:
            redirect_title = redirect_match.group(1)
            # Handle fetching the redirected article (not implemented here)
            if verbose:
                print(f"Redirected to: {redirect_title}")
            # search for the redirected article
            response = wiki_search(redirect_title, size=1)
            results = response.json().get('hits', {}).get('hits', [])
            if results:
                article = results[0]
                return get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], article['_source']['seek'], article['_id'])
            else:
                return None            

        return wikitext
    
    # If no matching page is found
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
            html_output += f"<a href='/wiki/{target}'>{text}</a>"
        elif node_type == "ExternalLink":
            url = escape(str(node.url))
            text = escape(str(node.title)) if node.title else url
            html_output += f"<a href='{url}'>{text}</a>"
        elif node_type == "Heading":
            level = node.level
            heading_text = escape(str(node.title.strip_code()))
            html_output += f"<h{level}>{heading_text}</h{level}>"
        elif node_type == "Tag":
            if node.tag == "ref":
                html_output += f"<span class='reference'>{escape(str(node))}</span>"
            else:
                html_output += escape(str(node))
        elif node_type == "Bold":
            bold_text = escape(str(node.strip_code()))
            html_output += f"<b>{bold_text}</b>"
        elif node_type == "Italic":
            html_output += f"<i>{escape(str(node))}</i>"
        elif node_type == "File":
            file_name = escape(str(node.title))
            html_output += f"<a href='/wiki/File:{file_name}'>{file_name}</a>"
        else:
            html_output += escape(str(node))

    return html_output

def html_to_markdown(html):
    """
    Convert HTML to Markdown using html2text.
    """
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False  # Keep links in the Markdown
    markdown_output = markdown_converter.handle(html)
    return markdown_output

def sync_wiki(reindex=False):
    # If we dont have wikipedia, grab it
    if not os.path.exists(WIKI_DIR):
        print('Wiki does not exist', file=sys.stderr)
        os.makedirs(WIKI_DIR)
    if not os.path.exists(WIKI_DIR + WIKI_URL.split('/')[-1]):
        print('Downloading wikipedia', file=sys.stderr)
        os.system('wget ' + WIKI_URL + ' -P ' + WIKI_DIR)
        print('Downloaded wikipedia', file=sys.stderr)
    if not os.path.exists(WIKI_DIR + INDEX.split('/')[-1]):
        # Get the index
        print('Downloading wikipedia INDEX', file=sys.stderr)
        os.system('wget ' + INDEX + ' -P ' + WIKI_DIR)
        print('Downloaded wikipedia index', file=sys.stderr)
    # check if an index exists in opensearch
    if get_opensearch('wikipedia') is None:
        print('Creating wikipedia index', file=sys.stderr)
        print(create_opensearch(), file=sys.stderr)
        reindex = True
    elif reindex:
        # delete the index and recreate it
        print('Deleting wikipedia index', file=sys.stderr)
        print(requests.delete(DB_URL + '/wikipedia'), file=sys.stderr)
        print('Creating wikipedia index', file=sys.stderr)
        print(create_opensearch(), file=sys.stderr)

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
            return

    if id is None:
        knowledge = create_knowledge(name, '')
        id = knowledge['id']

    fileList = get_all_files()

    for hit in wiki_index()['hits']['hits']:
        # save the file to the temp file
        with open('/tmp/file.md', 'w') as f:
            text = get_wikitext(WIKI_DIR + WIKI_URL.split('/')[-1], hit['_source']['seek'], hit['_id'])
            text = html_to_markdown(format_wikitext(text))
            # if this article sucks or is a redirect, skip it
            if text is None:
                continue
            elif 'REDIRECT' in text:
                continue
            elif len(text) < 100:
                continue

            print(text, file=sys.stderr)
            f.write(text)
        # upload the file
        res = upload_file('/tmp/file.md', fileList)
        if res is not None:
            data = {
                'file_id': res['id']
            }
            try:
                response = requests.post(BASE_URL + 'knowledge/wikipedia/file/add', headers=auth_header(), json=data)
            except Exception as err:
                print(err, file=sys.stderr)
                return None
    
    requests.post(DB_URL + '/_refresh')
    # for now just read and return index
    return wiki_index()

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
        print(sync_wiki())
        print('Syncing root')
        sync_root()

    app.run(host='0.0.0.0', port=os.getenv('FLASK_PORT', 5000))