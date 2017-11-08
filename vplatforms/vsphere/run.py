import configparser
import os

def fetch_template_list():
    # load config of virt_opt
    config = load_config()

    #
    config['OVF folder']['path']

    return templates

def load_config():
    config = configparser.ConfigParser()
    config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.ini')))

    return config

    #def uploadVM():
        #

    #deploy an existing VM template
    #def deployVM(template, DNS):
        #check DNS availability
        #clone from template
        #register at DNS
        #add to database

    #def resetVM(id):


    #def destroyVM():