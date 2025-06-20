#######################################################################
on Ubuntu system - Miniconda
#######################################################################
1) First, download and install Miniconda
   cd ~/Downloads
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

2) Configure conda for best practices
   # Set strict channel priority
   conda config --set channel_priority strict

   # Add conda-forge as a channel (recommended)
   conda config --add channels conda-forge

   # Disable auto activation of base environment (recommended)
   conda config --set auto_activate_base false

#######################################################################
Create and activate environment on behalf environment.yml
#######################################################################
*) cd /home/werner/development/stecher_tennis

   conda env create -f environment.yml

   or
   conda create -n stecher_tennis python=3.12   
   
*) Activate the environment
   ##############################
   conda activate stecher_tennis
   ##############################
   
   # To verify everything worked correctly, you can run:
   conda env list    # Shows all environments, with * next to the active one
   python --version  # Should show Python 3.12
   flask --version   # Should show Flask is installed

*) Best Practices for Environment Management and create "environment.yml" for reproducibility
   name: stecher_tennis
   channels:
     - conda-forge
     - defaults
   dependencies:
     - python=3.12
     # Add your specific packages here     
     - flask
     - flask-cors  # Useful for API development
     - python-dotenv  # For environment variable management
     - werkzeug  # WSGI web application library
     - click  # Command line interface creation kit
     - itsdangerous  # Security signing
     - jinja2  # Template engine
     - pip  # For any packages not available in conda

*) Use this file to create/update environment
   conda env create -f environment.yml

   # or update existing environment:
   conda env update -f environment.yml --prune

*) Keep track of exact package version
   # Export current environment
   conda env export > environment.yml
   # For better cross-platform compatibility:
   conda env export --from-history > environment.yml

#######################################################################
Common useful commands
#######################################################################
    conda --version
    conda info
    
    # List all environments
    conda env list

   # Deactivate current environment
   conda deactivate

   # Remove environment if needed
   conda env remove -n stecher_tennis

---> use conda install instead of pip when possible <---

#######################################################################
## git 
#######################################################################
git status
git add .
git commit -m "Initial commit"
git push -u origin main
git push

#######################################################################
date time testing
#######################################################################
All calls to get the current time now go through the get_current_time() function.
This function checks for a TEST_DATE environment variable (formatted as YYYY-MM-DD-HH-MM-SS)
to allow testing with a simulated date.
If it isn’t set or is invalid, it falls back to datetime.now().

1) export TEST_DATE=2025-03-13-21-13-23
2) conda activate stecher_tennis
   (source ./bin/activate)
3) python3 app.py --host=0.0.0.0 --port=5000

