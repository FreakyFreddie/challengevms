from flask import Blueprint, render_template, request
from CTFd.utils import admins_only, is_admin
import os
import shutil
import yaml
import pip
import importlib
import json

def load(app):
    #create plugin blueprint with template folder (https://github.com/CTFd/CTFd-Docker/blob/master/templates/containers.html)
    challengeVMs = Blueprint('challengeVMs', __name__, template_folder='templates')
    vplatforms = importlib.import_module('.vplatforms', package='CTFd.plugins.challengevms')
    print(" * Initialized challengevms virtualization platforms module, %s" % vplatforms)

    # generate list of supported virtualization platforms based on folders in virt_platforms directory
    supported_platforms_dir=os.path.abspath(os.path.join(os.path.dirname(__file__),"vplatforms"))
    settings_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "settings.ini"))

    # virt_opt_dir = os.path.abspath(os.path.join(os.path.dirname(supported_platforms_dir), virt_opt))

    if os.path.exists(settings_file) == True:
        exit()
        # load config from the start
        # baseconfig + subconfigs
        # import modules

    #Set up route to management interface
    @challengeVMs.route('/admin/challengeVMs/manage', methods=['GET','POST'])
    @admins_only

    #function triggered by surfing to the route as admin
    def manage():
        # get supported_virt_options root directories (detect modules)
        supported_virt_options = []
        blacklist = {'__pycache__'}

        for (dirpath, dirnames, filenames) in os.walk(supported_platforms_dir):
            supported_virt_options.extend(dirnames)
            break

        #remove blacklist from supported virt_options
        # You cannot iterate over a list and mutate it at the same time, instead iterate over a slice
        for supported_virt_option in supported_virt_options[:]:
            if supported_virt_option in blacklist:
                supported_virt_options.remove(supported_virt_option)

        #if settings file does not exist, render initial configuration, else render management UI
        if os.path.exists(settings_file)==False:
            if request.method == 'POST':
                #check if virt opt is set
                try:
                    request.form.get("virt_opt")
                except NameError:
                    exit()

                # if virt_opt is a supported_virt_opt, return appropriate options
                for supported_virt_opt in supported_virt_options:
                    if request.form.get("virt_opt") == supported_virt_opt:
                        return load_virt_config_options(request.form.get("virt_opt"))

            else:
                #render the initial config template, showing a select with the options
                return render_template('init_config.html',virt_opts=supported_virt_options)
        else:
            #add error handling for bad config

            # try load config
            #(base dictionary)
            #(virt_opt_1)
            #(virt_opt_2)

            return render_template('manage.html')

    def load_virt_config_options(virt_opt):
        virt_opt_module = "." + virt_opt

        module = importlib.import_module(virt_opt_module, package='CTFd.plugins.challengevms.vplatforms')

        module.vspheretest()

        return 'test'
        # load config
        #virt_platform = importlib.import_module(virt_opt_module, package='CTFd.plugins.challengevms')

        # return dictionary converted to json
        #return json.dumps(virt_platform.config)

        # configure()
        # validate settings
        # write to settings file
    #catch request

    #in virt_opt/configure
    def install_virt_opt_requirements(virt_opt):
        pip.main(['install', '-r requirements.txt --extra-index-url <file:///abs_path/to/sdk/lib/>', package]);

    class challengeVMs_config:
        def __init__(self, config_file):
            self.config_file = name
            self.tricks = []  # creates a new empty list for each dog

        def add_trick(self, trick):
            self.tricks.append(trick)

    #config page (DNS, subnets, template datastore...)


    #upload new VM template
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

    app.register_blueprint(challengeVMs)