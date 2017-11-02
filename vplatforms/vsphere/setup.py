def setup():
    # in virt_opt/configure
    import pip
    def install_virt_opt_requirements(virt_opt):
        pip.main(['install', '-r requirements.txt --extra-index-url <file:///abs_path/to/sdk/lib/>', package]);