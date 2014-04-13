#!/usr/bin/python
from __future__ import with_statement
import os, subprocess
from distutils.core import setup
from distutils.command import install

def _get_version(version_info):
    " Returns a PEP 386-compliant version number from version_info. "
    " Taken from python-markdown project. "
    assert len(version_info) == 5
    assert version_info[3] in ('alpha', 'beta', 'rc', 'final')

    parts = 2 if version_info[2] == 0 else 3
    main = '.'.join(map(str, version_info[:parts]))

    sub = ''
    if version_info[3] == 'alpha' and version_info[4] == 0:
        # TODO: maybe append some sort of git info here??
        sub = '.dev'
    elif version_info[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = mapping[version_info[3]] + str(version_info[4])

    dist = ""
    if os.getenv("dist"):
        dist = "." + os.getenv("dist")
    return str(main + sub + dist)

def compute_version():
    if os.path.exists("version"):
        with open("version", "rb") as inFile:
            commit_count = inFile.next().strip()
    else:
        try:
            call = ["git","--no-pager","rev-list", "HEAD", "--count"]
            fh = subprocess.PIPE    
            p = subprocess.Popen(call,stdout=fh, stderr=fh)
            pOut, _ = p.communicate()
            retCode = p.returncode
            
            if retCode:
                # something went wrong
                return None, None
        
            commit_count = pOut.strip()
        except:
            return None, None

    version_info = (0, 1, commit_count, 'final', 0)
    return _get_version(version_info), version_info
    
version, version_info = compute_version()

# Get development Status for classifiers
dev_status_map = {
    'alpha': '3 - Alpha',
    'beta' : '4 - Beta',
    'rc'   : '4 - Beta',
    'final': '5 - Production/Stable'
}
if version_info[3] == 'alpha' and version_info[4] == 0:
    DEVSTATUS = '2 - Pre-Alpha'
else:
    DEVSTATUS = dev_status_map[version_info[3]]

long_description = \
'''This is the Lunchinator. It does lunch stuff.

Support
=======

You may report bugs on the `bug tracker`_.

.. _`bug tracker`: http://github.com/hannesrauhe/lunchinator/issues
'''

data_files = [('share/lunchinator/sounds', ['sounds/sonar.wav']),
              ('share/lunchinator/images', ['images/webcam.jpg',
                                            'images/mini_breakfast.png',
                                            'images/lunchinator.png',
                                            'images/lunchinatorred.png']),
              ('share/lunchinator', ['lunchinator_pub_0x17F57DC2.asc', 'version']),
              ('share/icons/hicolor/scalable/apps', ['images/lunchinator.svg']),
              ('share/applications', ['installer/lunchinator.desktop'])]
if os.getenv('dist'):
    data_files.append(('share/icons/ubuntu-mono-dark/status/24', ['images/white/lunchinator.svg', 'images/lunchinatorred.svg']))
    data_files.append(('share/icons/ubuntu-mono-light/status/24', ['images/black/lunchinator.svg', 'images/lunchinatorred.svg']))
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

setup(
    name =          'Lunchinator',
    version =       version,
    url =           'http://www.lunchinator.de',
    #download_url =  'http://path/tp/Lunchinator-%s.tar.gz' % version,
    description =   'The Lunchinator.',
    long_description = long_description,
    author =        'Hannes Rauhe, Cornelius Ratsch',
    author_email =  'info@lunchinator.de',
    maintainer =     os.getenv('DEBFULLNAME'),
    maintainer_email = os.getenv('DEBEMAIL'),
    license =       'BSD License',
    packages =      ['lunchinator', 'lunchinator.cli'],
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

