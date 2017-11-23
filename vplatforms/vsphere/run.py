from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

def fetch_vm_list():
    #fetch from get request
    #username & password from credentials
    # load config of virt_opt
    config = load_config()

    service_instance = connect.SmartConnectNoSSL(host=host,
                                                 user=user,
                                                 pwd=password,
                                                 port=)

    #
    config['OVF folder']['path']

    return templates
    #vCenter login should be required for each action & tied to the session
    """
    Simple command-line program for listing the virtual machines on a system.
    """
    import atexit



    import tools.cli as cli

    def print_vm_info(virtual_machine):
        """
        Print information for a particular virtual machine or recurse into a
        folder with depth protection
        """
        summary = virtual_machine.summary
        print("Name       : ", summary.config.name)
        print("Template   : ", summary.config.template)
        print("Path       : ", summary.config.vmPathName)
        print("Guest      : ", summary.config.guestFullName)
        print("Instance UUID : ", summary.config.instanceUuid)
        print("Bios UUID     : ", summary.config.uuid)
        annotation = summary.config.annotation
        if annotation:
            print("Annotation : ", annotation)
        print("State      : ", summary.runtime.powerState)
        if summary.guest is not None:
            ip_address = summary.guest.ipAddress
            tools_version = summary.guest.toolsStatus
            if tools_version is not None:
                print("VMware-tools: ", tools_version)
            else:
                print("Vmware-tools: None")
            if ip_address:
                print("IP         : ", ip_address)
            else:
                print("IP         : None")
        if summary.runtime.question is not None:
            print("Question  : ", summary.runtime.question.text)
        print("")

    args = cli.get_args()

    try:
        if args.disable_ssl_verification:

        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        container = content.rootFolder  # starting point to look into
        viewType = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively
        containerView = content.viewManager.CreateContainerView(
            container, viewType, recursive)

        children = containerView.view
        for child in children:
            print_vm_info(child)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


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