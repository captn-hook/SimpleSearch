#!/bin/bash

# Ensure a file argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <file>"
  exit 1
fi

# Define additional form fields
query="Summarize this file."
model="llama3.2:3b"
form="{
  \"properties\": {
    \"status\": {
      \"type\": \"string\"
    },
    \"response\": {
      \"type\": \"string\"
    }
  },
  \"required\": [
    \"status\",
    \"response\"
  ]
  \"title\": \"File Upload\",
  \"type\": \"object\"
}"

# Use curl to upload the file with additional form fields
curl -F "file=@$1" \
     http://localhost:5000/home