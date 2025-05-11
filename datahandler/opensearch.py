from config import DB_URL
import requests
import sys

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

