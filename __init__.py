from flask import Blueprint, render_template, request, abort
from CTFd.utils import admins_only, is_admin
import os
import shutil
import yaml
import pip
import importlib
import json
import configparser

def load(app):
    # create plugin blueprint with template folder (https://github.com/CTFd/CTFd-Docker/blob/master/templates/containers.html)
    challengeVMs = Blueprint('challengeVMs', __name__, template_folder='templates')
    vplatforms = importlib.import_module('.vplatforms', package='CTFd.plugins.challengevms')
    print(" * Initialized challengevms virtualization platforms module, %s" % vplatforms)

    # generate list of supported virtualization platforms based on folders in virt_platforms directory
    supported_platforms_dir=os.path.abspath(os.path.join(os.path.dirname(__file__),"vplatforms"))
    settings_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "settings.ini"))

    # Set up route to management interface
    @challengeVMs.route('/admin/challengeVMs/manage', methods=['GET','POST'])
    @admins_only

    # function triggered by surfing to the route as admin
    def manage():
        # get supported_virt_options root directories (detect modules)
        supported_virt_options = []
        blacklist = {'__pycache__'}

        for (dirpath, dirnames, filenames) in os.walk(supported_platforms_dir):
            supported_virt_options.extend(dirnames)
            break

        # remove blacklist from supported virt_options
        # You cannot iterate over a list and mutate it at the same time, instead iterate over a slice
        for supported_virt_option in supported_virt_options[:]:
            if supported_virt_option in blacklist:
                supported_virt_options.remove(supported_virt_option)

        # if settings file does not exist, render initial settings config
        # else render initial virtualization platform config or management UI
        if os.path.exists(settings_file)==True:
            # check if virt_opt is set and valid in settings.ini
            settings = configparser.ConfigParser()
            settings.read(settings_file)

            # if the section.option exists and it's value is valid
            if ('virtualization platform' in settings.sections()) and ('name' in settings.options('virtualization platform')) and (settings.get('virtualization platform', 'name') in supported_virt_options):
                # Launch virtualization platform module

                return render_template('manage.html')

            else:
                # render template to configure virt_opt & process configuration requests
                if request.method == 'POST':
                    # check if virt opt is set
                    try:
                        request.form.get("virt_opt")
                    except NameError:
                        abort(404)

                    if (request.form.get("virt_opt") in supported_virt_options) and (len(request.form) == 2):
                        # if virt_opt is a supported_virt_opt, return appropriate options
                        for supported_virt_opt in supported_virt_options:
                            if request.form.get("virt_opt") == supported_virt_opt:
                                config = load_virt_config_options(request.form.get("virt_opt"))
                                return convert_config_json_list(config)

                        return render_template('init_config.html', virt_opts=supported_virt_options)

                    elif (request.form.get("virt_opt") in supported_virt_options) and (len(request.form) > 2):
                        config = configparser.ConfigParser()
                        config.read(supported_platforms_dir + '/' + request.form.get("virt_opt") + '/config.ini')

                        for key in request.form:
                            if (key != 'nonce' and key != 'virt_opt'):
                                configopt = key.split('.')
                                sec = configopt[0]
                                opt = configopt[1]

                                # if sections.option exists, change its value
                                if sec in config.sections():
                                    if opt in config.options(sec):
                                        config.set(sec, opt, request.form.get(key))

                        with open(supported_platforms_dir + '/' + request.form.get("virt_opt") + '/config.ini',
                                  'w') as configfile:
                            config.write(configfile)
                            configfile.close()

                        # setup the virt_opt module
                        setup_virt_opt(request.form.get("virt_opt"))

                        # Write config option to settings file
                        settings = configparser.ConfigParser()
                        settings.read(settings_file)

                        if 'virtualization platform' not in settings.sections():
                            settings.add_section('virtualization platform')

                        settings.set('virtualization platform', 'name', request.form.get("virt_opt"))

                        with open(settings_file, 'w') as settingsfile:
                            settings.write(settingsfile)
                            settingsfile.close()

                        # Launch virtualization platform module


                        return render_template('manage.html')

                    else:
                        return render_template('init_config.html', virt_opts=supported_virt_options)

                else:
                    return render_template('init_config.html', virt_opts=supported_virt_options)
        else:
            # render the initial settings template, where user can configure the plugins general settings
            valid_settings = [
                {'DNS settings': [{'option1': 'value1'}, {'option2': 'value2'}]},
                {'section 2': [{'option1': 'value1'}, {'option2': 'value2'}]}
            ]

            # if page sends post, set the settings
            if request.method == 'POST':
                settings = configparser.ConfigParser()

                # validate the settings & write to file
                for key in request.form:
                    if (key != 'nonce'):
                        configopt = key.split('.')
                        sec = configopt[0]
                        opt = configopt[1]

                        # if sections.option exists, change its value
                        for section in valid_settings:
                            for k, v in section.items():
                                if k not in settings.sections():
                                    settings.add_section(k)
                                if k == sec:
                                    for option in v:
                                        for akey, avalue in option.items():
                                            if akey == opt:
                                                settings.set(sec, opt, request.form.get(key))

                with open(settings_file, 'w') as settingsfile:
                    settings.write(settingsfile)
                    settingsfile.close()

                return render_template('init_config.html', virt_opts=supported_virt_options)

            return render_template('init_settings.html', valid_settings=valid_settings)

    def load_virt_config_options(virt_opt):
        config = configparser.ConfigParser()
        config.read(supported_platforms_dir + '/' + virt_opt + '/config.ini')

        return config

    def load_virt_opt_package(virt_opt):
        # prepare relative import
        virt_opt_rel = "." + virt_opt

        # import module
        return importlib.import_module(virt_opt_rel, package='CTFd.plugins.challengevms.vplatforms')

    def convert_config_json_list(config):
        config_array=[]
        option_array=[]

        #append config options to array
        for section in config.sections():
            config_array.append(section)

            for option in config.options(section):
                option_array.append([option, config[section][option]])

            config_array.append(option_array)
            option_array=[]

        return json.dumps(config_array)

    def setup_virt_opt(virt_opt):
        package = load_virt_opt_package(virt_opt)

        # import setup script function
        importlib.import_module('.setup', package='CTFd.plugins.challengevms.vplatforms.' + virt_opt)

        # run setup script
        package.setup.setup()



    #config page (DNS, subnets, template datastore...)
    #DNS SETTINGS
    #IP
    #SUBNET

    #add_record
    #remove_record

    app.register_blueprint(challengeVMs)