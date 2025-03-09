# Get Started 

    docker-compose up --build 
    
# To remove / restart

    docker-compose down -v

then, navigate to the [WebUI](http://localhost:3000/) and choose a model like [deepseek-r1:1.5b](https://ollama.com/library/deepseek-r1)

![img](./image.png)

then, you can create a knowledge base and upload documents to it:

![img](./image2.png)

# Pages for all the services

ports are defined in the environment file
    
# [WebUI](http://localhost:3000/)
    
# [Opensearch panel](http://localhost:5601/)

# [Ollama API](http://localhost:11434/)
        
# [Opensearch API](http://localhost:9200/)
    
# Next steps 

Find a good way to do fuzzy search on text 
Add tagging and library codes to documents 
Display passages that the search term was found in

# Open WebUI + OpenSearch is broken\
so we have to do full security

to generate the security files:

## Generate a private key for the root CA
    openssl genpkey -algorithm RSA -out root-ca-key.pem -aes256

## Generate a root certificate
    openssl req -x509 -new -nodes -key root-ca-key.pem -sha256 -days 3650 -out root-ca.pem -subj "/C=DE/ST=Test/L=Test/O=Test/OU=SSL/CN=root-ca"

## Generate a private key for the OpenSearch node
    openssl genpkey -algorithm RSA -out node1-key.pem -aes256

## Generate a certificate signing request (CSR) for the OpenSearch node
    openssl req -new -key node1-key.pem -out node1.csr -subj "/C=DE/ST=Test/L=Test/O=Test/OU=SSL/CN=node1.example.com"

## Generate the node certificate signed by the root CA
    openssl x509 -req -in node1.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -out node1.pem -days 365 -sha256

## Generate a private key for the admin user
    openssl genpkey -algorithm RSA -out admin-key.pem -aes256

## Generate a certificate signing request (CSR) for the admin user
    openssl req -new -key admin-key.pem -out admin.csr -subj "/C=DE/ST=Test/L=Test/O=Test/OU=SSL/CN=admin"

## Generate the admin certificate signed by the root CA
    openssl x509 -req -in admin.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -out admin.pem -days 365 -sha256