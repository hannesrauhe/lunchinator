#!/usr/bin/python
from __future__ import with_statement
import os, platform
from distutils.core import setup
from distutils.command import install

DEVSTATUS = None

def _get_version(version_info, branch = ""):
    " Returns a PEP 386-compliant version number from version_info. "
    assert len(version_info) == 5
    assert version_info[3] in ('alpha', 'beta', 'rc', 'final')

    parts = 2 if version_info[2] == 0 else 3
    main = '.'.join(map(str, version_info[:parts]))
    if branch:
        main += "-" + branch

    if os.getenv("dist"):
        sub = '.' + os.getenv("dist")
    else:
        sub = ''

    if version_info[3] == 'alpha' and version_info[4] == 0:
        sub += '.dev'
    elif version_info[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub += mapping[version_info[3]] + str(version_info[4])

    return str(main + sub)

def compute_version():
    global DEVSTATUS
    if os.path.exists("version"):
        with open("version", "rb") as inFile:
            version = inFile.next().strip()
    else:
        raise IOError("version file does not exist")

    v_split = version.split('.')
    branch = None
    if len(v_split) == 3:
        status = 'final'
        DEVSTATUS = '5 - Production/Stable'
    elif len(v_split) == 4:
        status = 'alpha'
        DEVSTATUS = '3 - Alpha'
        branch = v_split[3]
    else:
        raise AttributeError("Illegal version format")
    version_info = (int(v_split[0]), int(v_split[1]), int(v_split[2]), status, 0)

    return _get_version(version_info, branch), version_info
    
version, version_info = compute_version()


long_description = \
'''A tool to call your colleagues for lunch.

The lunchinator is a chat tool that can be used to send messages to everyone in the lunch group at once.
Messages are delivered directly (not relayed via server): no internet connection is needed, hence the tool is especially suited for corporate networks.

You may report bugs on the http://github.com/hannesrauhe/lunchinator/issues
'''

data_files = [('share/lunchinator/sounds', ['sounds/sonar.wav']),
              ('share/lunchinator/images', ['images/webcam.jpg',
                                            'images/mini_breakfast.png',
                                            'images/lunchinator.png',
                                            'images/lunchinatorred.png',
                                            'images/lunchinatorgreen.png',
                                            'images/me.png'
                                            'images/warning.png'
                                            'images/error.png']),
              ('share/lunchinator', ['lunchinator_pub_0x17F57DC2.asc', 'version']),
              ('share/icons/hicolor/scalable/apps', ['images/lunchinator.svg']),
              ('share/applications', ['lunchinator.desktop'])]
# ensure icons are installed only on ubuntu
if os.getenv("__isubuntu") or (not os.getenv("__notubuntu") and platform.dist()[0] == "Ubuntu"):
    data_files.append(('share/icons/ubuntu-mono-dark/status/24', ['images/white/lunchinator.svg', 'images/lunchinatorred.svg', 'images/lunchinatorgreen.svg']))
    data_files.append(('share/icons/ubuntu-mono-light/status/24', ['images/black/lunchinator.svg', 'images/lunchinatorred.svg', 'images/lunchinatorgreen.svg']))
data_files.extend([("share/lunchinator/" + dp, [os.path.join(dp, fn) for fn in fns if not fn.endswith('.pyc')]) for dp, _, fns in os.walk('plugins')])
data_files.extend([("share/lunchinator/" + dp, [os.path.join(dp, fn) for fn in fns]) for dp, _, fns in os.walk('bin')])

# take ownership of the following directories, this is for RPM generation
total_ownership = set(['share/lunchinator'])
partial_ownership = set(['local/share/icons', 'icons/hicolor', 'lib/python.\..', 'lib64/python.\..', 'local/share/applications'])

class my_install(install.install):
    def get_outputs(self):
        import re
        outputs = install.install.get_outputs(self)
        # take ownership of directories, too
        
        dirs = set()
        
        root_len = 0
        if self.root:
            root_len = len(self.root)
        
        for aFile in outputs:
            found = False
            for pattern in total_ownership:
                match = re.search('/' + pattern + '/', aFile)
                if match:
                    dirs.add(aFile[:match.end()])
                    # file can only match one pattern
                    found = True
                    break
                    
            if not found:
                for pattern in partial_ownership:
                    match = re.search('/' + pattern + '/', aFile)
                    if match:
                        # strip prefix
                        aFile = aFile[root_len:]
                        
                        while len(aFile) > match.end() - root_len:
                            aFile = os.path.dirname(aFile)
                            dirs.add(" " * root_len + "%%dir %s" % (aFile))
                        
                        # file can only match one pattern
                        break
                
        outputs.extend(sorted(dirs))
        return outputs

name = "lunchinator"
branch = os.getenv("__lunchinator_branch")
if branch and branch!="master":
    name +="-"+branch

setup(
    name =          name,
    version =       version,
    url =           'http://www.lunchinator.de',
    #download_url =  'http://path/tp/Lunchinator-%s.tar.gz' % version,
    description =   'The Lunchinator',
    long_description = long_description,
    author =        'Hannes Rauhe, Cornelius Ratsch',
    author_email =  'info@lunchinator.de',
    maintainer =     os.getenv('DEBFULLNAME'),
    maintainer_email = os.getenv('DEBEMAIL'),
    license =       'GPLv3',
    packages =      ['lunchinator', 'lunchinator.cli', 'lunchinator.peer_actions'],
    scripts =       ['bin/lunchinator'],
    data_files =    data_files,
    cmdclass =      {'install': my_install},
    classifiers =   ['Development Status :: %s' % DEVSTATUS,
                     'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                     'Operating System :: OS Independent',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 2',
                     'Programming Language :: Python :: 2.6',
                     'Programming Language :: Python :: 2.7',
                     'Topic :: Office/Business :: Scheduling',
                     'Topic :: Utilities',
                     'Topic :: Communications :: Chat',
                    ],
    )

