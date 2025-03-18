# Get Started 

firstly, you need to edit the volume option in the .env file to point to the directory where you want to store the data. Models and knowledge bases can be more than 10 gb so make sure you have enough space.

furthermore, on wsl2 you will need to set the memory in %UserProfile%\\.wslconfig like

    [wsl2]
    memory=16GB

## run with docker-compose, -d for detached mode, --build to rebuild the images

    docker-compose up

## after compose

in the admin settings, you can modify the document settings
also, you can add a tool like [ocrtool.py](./ocrtool.py) 
    
# To remove / restart

    docker-compose down --remove-orphans

then, navigate to the [WebUI](http://localhost:3000/) and choose a model like [phi4](https://ollama.com/library/phi4) or [llama3.2:3b](https://ollama.com/library/llama3.2:3b)

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