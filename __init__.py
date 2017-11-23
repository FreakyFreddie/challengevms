import os
from flask import Blueprint, render_template, request, abort, redirect, url_for
from CTFd.utils import admins_only, is_admin
from CTFd.models import db

import atexit
import ssl

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from .models import *
from .blacklist import vm_blacklist

def load(app):
    #create tables
    app.db.create_all()

    # create plugin blueprint with template folder
    vspherevms = Blueprint('vspherevms', __name__, template_folder='templates')

    #valid configuration settions with their type
    valid_settings ={
        'Username': ['text', ''],
        'Password': ['password', ''],
        'Host': ['text', ''],
        'Port': ['number', '443']
    }

    # Set up route to configuration interface
    @vspherevms.route('/admin/vspherevms/configure', methods=['GET', 'POST'])
    @admins_only
    def configure():
        if request.method == 'POST':
            settings = {}
            errors = []

            for key, val in valid_settings:
                if key in request.form:
                    settings[key]=[val[0], request.form[key]]
                else:
                    errors.append("%s is not a valid setting" % key)

            # error handling
            if len(errors) > 0:
                return render_template('init_settings.html', errors=errors, settings=settings)
            else:
                #write all key-value pairs to database & redirect to manage
                for key,val in settings:
                    vspherevmsconfigopt = vSphereVMsConfig.query.filter_by(option=key).first()

                    # if key does not exist in database, add entry, else update
                    if vspherevmsconfig == None:
                        vspherevmsconfig = vSphereVMsConfig(key,val[1])
                        db.session.add(vspherevmsconfig)
                        db.session.commit()
                        db.session.flush()
                    else:
                        vspherevmsconfig.value = val
                        db.session.commit()
                        db.session.flush()

                return redirect(url_for('.manage'), code=302)

        else:
            # generate dictionary with already filled in config options + empty options
            settings = config_opts_db()

            return render_template('init_settings.html', settings=settings)

    # generate dictionary with already filled in config options + empty options
    def config_opts_db():
        settings = {}

        for key, val in valid_settings:
            vspherevmsconfigopt = vSphereVMsConfig.query.filter_by(option=key).first()

            if vspherevmsconfigopt == None:
                settings[key] = [val[0], val[1]]
            else:
                settings[key] = [val[0], vspherevmsconfigopt.value]

        return settings

    # Set up route to management interface
    @vspherevms.route('/admin/vspherevms/manage', methods=['GET'])
    @admins_only
    def manage():
        if not is_configured():
            return redirect(url_for('.configure'), code=302)
        else:
            errors = []
            #if connection failed, return error

            try:
                vms = fetch_vm_list_online_offline()
            except:
                errors.append("VM list could not be fetched. Is the configuration valid?")

            if len(errors) > 0:
                return render_template('manage.html', errors=errors, virtual_machines=vms)

            return render_template('manage.html', virtual_machines=vms)

    # plugin is not configured when one key has no value
    def is_configured():
        configured = True

        for key, val in valid_settings:
            vspherevmsconfigopt = vSphereVMsConfig.query.filter_by(option=key).first()
            if vspherevmsconfigopt == None:
                configured = False

        return configured

    def fetch_vm_list():
        vspherevmsconfigusername = vSphereVMsConfig.query.filter_by(option="Username").first()
        vspherevmsconfigpassword = vSphereVMsConfig.query.filter_by(option="Password").first()
        vspherevmsconfighost = vSphereVMsConfig.query.filter_by(option="Host").first()
        vspherevmsconfigport = vSphereVMsConfig.query.filter_by(option="Port").first()

        username = vspherevmsconfigusername.value
        password = vspherevmsconfigpassword.value
        host = vspherevmsconfighost.value
        port = vspherevmsconfigport.value

        print("Attempting connection to vCenter...")

        try:
            context = ssl._create_unverified_context()
            service_instance = connect.SmartConnect(host=host,
                                                         user=username,
                                                         pwd=password,
                                                         port=int(port),
                                                         sslContext=context)

            atexit.register(connect.Disconnect, service_instance)
        except (IOError, vim.fault.InvalidLogin):
            print("SmartConnect to vCenter failed.")

        content = service_instance.RetrieveContent()

        container = content.rootFolder  # starting point to look into
        viewType = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively

        containerView = content.viewManager.CreateContainerView(
            container, viewType, recursive)

        virtual_machines = containerView.view

        return virtual_machines


    # function to update VM on/off status
    # less data to lower network load
    def fetch_vm_list_online_offline():
        virtual_machines = fetch_vm_list()

        vms = []

        for virtual_machine in virtual_machines:
            summary = virtual_machine.summary

            name = summary.config.name
            template = summary.config.template

            # if vm is template, exclude
            if template:
                continue

            for blacklisted_vm in vm_blacklist:
                if name == blacklisted_vm['Name']:
                    continue

            instance_uuid = summary.config.instanceUuid
            state = summary.runtime.powerState

            if summary.guest is not None:
                if summary.guest.ipAddress:
                    ipaddress = summary.guest.ipAddress
                else:
                    ipaddress = "Unknown"

                if summary.guest.toolsRunningStatus is not None:
                    vmwaretools = summary.guest.toolsRunningStatus
                else:
                    vmwaretools = "guestToolsNotRunning"
            else:
                ipaddress = "Unknown"
                vmwaretools = "guestToolsNotRunning"

            # append VM to array
            vms.append({
                "Name": name,
                "UUID": instance_uuid,
                "State": state, #powereedOff, poweredOn, ??StandBy, ??unknown, suspended
                "Ipaddress": ipaddress,
                "Vmwaretools": vmwaretools
            })

        return vms


    # revert vm to latest snapshot (see snapshot_operations)
    @challengevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/revert', methods=['POST'])
    @admins_only
    def revert_vm(vm_uuid):
        #Check if not in blacklist

    @challengevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/start', methods=['POST'])
    @admins_only
    def start_vm(vm_uuid):
        # Check if not in blacklist


    @challengevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/restart', methods=['POST'])
    @admins_only
    def restart_vm(vm_uuid):
        if not si:
            raise SystemExit("Unable to connect to host with supplied info.")
        vm = si.content.searchIndex.FindByUuid(None, args.uuid, True, True)
        if not vm:
            raise SystemExit("Unable to locate VirtualMachine.")

        print("Found: {0}".format(vm.name))
        print("The current powerState is: {0}".format(vm.runtime.powerState))
        # This does not guarantee a reboot.
        # It issues a command to the guest
        # operating system asking it to perform a reboot.
        # Returns immediately and does not wait for the guest
        # operating system to complete the operation.
        vm.RebootGuest()
        print("A request to reboot the guest has been sent.")


        # Check if not in blacklist
        VM = SI.content.searchIndex.FindByUuid(None, ARGS.uuid,
                                               True,
                                               True)
        if VM is None:
            raise SystemExit("Unable to locate VirtualMachine.")

        print("Found: {0}".format(VM.name))
        print("The current powerState is: {0}".format(VM.runtime.powerState))
        TASK = VM.ResetVM_Task()
        tasks.wait_for_tasks(SI, [TASK])
        print("its done.")

    @challengevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/shutdown', methods=['POST'])
    @admins_only
    def shutdown_vm(vm_uuid):
        # Check if not in blacklist

    VM = SI.content.searchIndex.FindByUuid(None, uuid,
                                               True,
                                               False)
    if VM is None:
        raise SystemExit(
            "Unable to locate VirtualMachine. Arguments given: "
            "vm - {0} , uuid - {1} , name - {2} , ip - {3}"
                .format(ARGS.vm, ARGS.uuid, ARGS.name, ARGS.ip)
        )

    print("Found: {0}".format(VM.name))
    print("The current powerState is: {0}".format(VM.runtime.powerState))
    if format(VM.runtime.powerState) == "poweredOn":
        print("Attempting to power off {0}".format(VM.name))
        TASK = VM.PowerOffVM_Task()
        tasks.wait_for_tasks(SI, [TASK])
        print("{0}".format(TASK.info.state))

    print("Destroying VM from vSphere.")
    TASK = VM.Destroy_Task()
    tasks.wait_for_tasks(SI, [TASK])
    print("Done.")


import ssl
si = None

    print("Trying to connect to VCENTER SERVER . . .")

    context = None
    if inputs['ignore_ssl'] and hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()

    si = connect.Connect(inputs['vcenter_ip'], 443,
                         inputs['vcenter_user'], inputs[
                             'vcenter_password'],
                         sslContext=context)

    atexit.register(Disconnect, si)

    print("Connected to VCENTER SERVER !")




