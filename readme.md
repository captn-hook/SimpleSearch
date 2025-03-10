# Get Started 

    docker-compose up --build 
    
# To remove / restart

    docker-compose down --remove-orphans

then, navigate to the [WebUI](http://localhost:3000/) and choose a model like [deepseek-r1:1.5b](https://ollama.com/library/deepseek-r1) or [llama3.2:3b](https://ollama.com/library/llama3.2:3b)

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