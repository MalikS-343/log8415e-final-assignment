#!/bin/bash

python3 create_pem_key.py

eval "$(ssh-agent -s)"

chmod 400 final_assignment.pem
ssh-add final_assignment.pem

python3 main.py
