
def check_deps():
    from qgis.utils import iface
    import pathlib
    import subprocess

    from PyQt5.QtWidgets import QMessageBox
    plugin_dir = pathlib.Path(__file__).parent.parent

    try:
        import pip
    except ImportError:
        reply = QMessageBox.question(iface.mainWindow(), 'Module install',
                                     'Foresr Agro Plugin need to install the missing module ' + 'pip' + '. Continue?',
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            exec(
                open(str(pathlib.Path(plugin_dir, 'scripts', 'get_pip.py'))).read()
            )
        else:
            return 1

    with open(str(plugin_dir / 'scripts/requirements.txt'), "r") as requirements:
        for dep in requirements:
                dep, import_tag = dep.strip().split()
                try:
                    mod = __import__(import_tag)
                    print("Module " + dep + " is already installed! ", mod)
                except ImportError as e:
                    print("Module {} is not available, installing...".format(dep))

                    reply = QMessageBox.question(iface.mainWindow(), 'Module install',
                                                 'Foresr Agro Plugin need to install the missing module ' + dep + '. Continue?',
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        result = subprocess.run(["python3", '-m', 'pip', 'install', dep])

                        if result.returncode == 0:
                            print("Module {} was succesfull installed!".format(dep))
                        else:
                            print("Module {} was failed!".format(dep))
                    else:
                        return 1
    return 0
