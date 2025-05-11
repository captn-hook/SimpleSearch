import os

BASE_DIRECTORY = '/app/data/docs/'

WIKI_DIR = '/app/data/wiki/'

WIKI_URL = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2'
INDEX = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2'

BASE_URL = os.getenv('OPENWEBUI_URL', 'http://open-webui:8080') + '/api/v1/'

DB_URL = os.getenv('OPENSEARCH_URI', 'http://opensearch-node1:9200')