import os
from flask import Blueprint, render_template, request, abort, redirect, url_for
from CTFd.utils import admins_only, is_admin
from CTFd.models import db

import atexit
import ssl
import json

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from .models import *
from .blacklist import vm_blacklist

def load(app):
    print("test")
    #create tables
    app.db.create_all()
    print("test")

    # create plugin blueprint with template folder
    vspherevms = Blueprint('vspherevms', __name__, template_folder='templates')

    print("test")
    #valid configuration settions with their type
    valid_settings ={
        'Username': ['text', ''],
        'Password': ['password', ''],
        'Host': ['text', ''],
        'Port': ['number', '443']
    }

    print("test")
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
            vms = []

            #if connection failed, return error
            try:
                vms = fetch_vm_list_online_offline()
            except (IOError, vim.fault.InvalidLogin):
                errors.append("SmartConnect to vCenter failed.")

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

    def connect_to_vsphere():
        vspherevmsconfigusername = vSphereVMsConfig.query.filter_by(option="Username").first()
        vspherevmsconfigpassword = vSphereVMsConfig.query.filter_by(option="Password").first()
        vspherevmsconfighost = vSphereVMsConfig.query.filter_by(option="Host").first()
        vspherevmsconfigport = vSphereVMsConfig.query.filter_by(option="Port").first()

        username = vspherevmsconfigusername.value
        password = vspherevmsconfigpassword.value
        host = vspherevmsconfighost.value
        port = vspherevmsconfigport.value

        print("Attempting connection to vCenter...")

        context = ssl._create_unverified_context()
        service_instance = connect.SmartConnect(host=host,
                                                user=username,
                                                pwd=password,
                                                port=int(port),
                                                sslContext=context)

        atexit.register(connect.Disconnect, service_instance)

        return service_instance

    def fetch_vm_list(service_instance):
        content = service_instance.RetrieveContent()

        # search recursively from root folder and return all found VirtualMachine objects
        containerView = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True)

        virtual_machines = containerView.view
        containerView.Destroy()

        return virtual_machines


    # function to update VM on/off status
    # less data to lower network load
    def fetch_vm_list_online_offline():
        virtual_machines = fetch_vm_list(connect_to_vsphere())

        vms = []

        for virtual_machine in virtual_machines:
            summary = virtual_machine.summary

            name = summary.config.name
            template = summary.config.template
            blacklisted = False

            # if vm is template, exclude
            if template:
                continue

            # if vm is blacklisted, skip this iteration
            for blacklisted_vm in vm_blacklist:
                if name == blacklisted_vm['Name']:
                    blacklisted = True
            if blacklisted:
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

    @vspherevms.route('/admin/vspherevms/manage/update', methods=['POST'])
    @admins_only
    def update():
        return json.dumps(fetch_vm_list_online_offline())
    # Check if not in blacklist (after connecting to ...)

    @vspherevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/poweron', methods=['POST'])
    @admins_only
    def poweron_vm(vm_uuid):
        return powerstate_operation(vm_uuid, "powerOn")

    def fetch_vm_by_uuid(vm_uuid, service_instance):
        try:
            vm = service_instance.content.searchIndex.FindByUuid(None, vm_uuid,
                                                   True,
                                                   True)
            return vm
        except:
            raise # "Unable to locate VirtualMachine."


    # returns when tasklist is finished
    def WaitForTasks(tasks, service_instance):
        pc = service_instance.content.propertyCollector

        taskList = [str(task) for task in tasks]

        # Create filter
        objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                    for task in tasks]
        propSpec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                              pathSet=[], all=True)
        filterSpec = vmodl.query.PropertyCollector.FilterSpec()
        filterSpec.objectSet = objSpecs
        filterSpec.propSet = [propSpec]
        filter = pc.CreateFilter(filterSpec, True)

        try:
            version, state = None, None

            # Loop looking for updates till the state moves to a completed state.
            while len(taskList):
                update = pc.WaitForUpdates(version)
                for filterSet in update.filterSet:
                    for objSet in filterSet.objectSet:
                        task = objSet.obj
                        for change in objSet.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in taskList:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                taskList.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if filter:
                filter.Destroy()


    def powerstate_operation(vm_uuid, operation):
        service_instance = connect_to_vsphere()
        vm = fetch_vm_by_uuid(vm_uuid, service_instance)

        for blacklisted_vm in vm_blacklist:
            if vm.summary.config.name == blacklisted_vm['Name']:
                return "Operation failed."


        # only call powerOn on vm that is off and matches uuid
        if(vm.summary.runtime.powerState == "poweredOff"):
            # only call powerOn on vm that is off and matches uuid
            if (operation == "powerOn"):
                try:
                    tasks = []
                    tasks.append(vm.PowerOnVM())

                    # Wait for power on to complete
                    WaitForTasks(tasks, service_instance)
                    return "Success!"

                except vmodl.MethodFault as e:
                    return "Caught vmodl fault : " + e.msg
                except Exception as e:
                    return "Caught Exception : " + str(e)


        elif(vm.summary.runtime.powerState == "poweredOn"):
            if (operation == "Suspend"):
                try:
                    tasks = []
                    tasks.append(vm.SuspendVM())

                    # Wait for power on to complete
                    WaitForTasks(tasks, service_instance)
                    return "Success!"

                except vmodl.MethodFault as e:
                    return "Caught vmodl fault : " + e.msg
                except Exception as e:
                    return "Caught Exception : " + str(e)

            elif (operation == "Shutdown"):
                try:
                    tasks = []
                    tasks.append(vm.ShutdownGuest())

                    # Wait for power on to complete
                    WaitForTasks(tasks, service_instance)
                    return "Success!"

                except vmodl.MethodFault as e:
                    return "Caught vmodl fault : " + e.msg
                except Exception as e:
                    return "Caught Exception : " + str(e)

            elif (operation == "Reboot"):
                try:
                    tasks = []
                    tasks.append(vm.RebootGuest())

                    # Wait for power on to complete
                    WaitForTasks(tasks, service_instance)
                    return "Success!"

                except vmodl.MethodFault as e:
                    return "Caught vmodl fault : " + e.msg
                except Exception as e:
                    return "Caught Exception : " + str(e)

        elif(vm.summary.runtime.powerState == "suspended"):
            if (operation == "Resume"):
                try:
                    tasks = []
                    tasks.append(vm.PowerOnVM())

                    # Wait for power on to complete
                    WaitForTasks(tasks, service_instance)
                    return "Success!"

                except vmodl.MethodFault as e:
                    return "Caught vmodl fault : " + e.msg
                except Exception as e:
                    return "Caught Exception : " + str(e)

        else:
            return "requirements not met."

    @vspherevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/shutdown', methods=['POST'])
    @admins_only
    def suspend_vm(vm_uuid):
        return powerstate_operation(vm_uuid, "Suspend")

    @vspherevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/shutdown', methods=['POST'])
    @admins_only
    def shutdown_vm(vm_uuid):
        return powerstate_operation(vm_uuid, "Shutdown")

    @vspherevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/restart', methods=['POST'])
    @admins_only
    def restart_vm(vm_uuid):
        return powerstate_operation(vm_uuid, "Reboot")

    @vspherevms.route('/admin/challengeVMs/manage/VM/<string:vm_uuid>/resume', methods=['POST'])
    @admins_only
    def resume_vm(vm_uuid):
        return powerstate_operation(vm_uuid, "Resume")


