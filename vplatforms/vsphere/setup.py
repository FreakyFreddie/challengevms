# install module dependencies etc.
def setup():
    import os
    import pip

    virt_opt_dir = os.path.abspath(os.path.dirname(__file__))

    # install requirements for module & submodules
    pip.main(['install', '-r', virt_opt_dir + '/lib/requirements.txt', '--extra-index-url', 'file://' + virt_opt_dir + '/lib'])
    pip.main(['install', '-r', virt_opt_dir + '/requirements.txt'])
