#!/usr/bin/python
from __future__ import with_statement
import os, subprocess
from distutils.core import setup


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

    return str(main + sub)

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
              ('share/lunchinator', ['lunchinator_pub_0x17F57DC2.asc', 'installer/version']),
              ('share/icons/hicolor/scalable/apps', ['images/lunchinator.svg']),
              ('share/icons/ubuntu-mono-dark/status/24', ['images/white/lunchinator.svg', 'images/lunchinatorred.svg']),
              ('share/icons/ubuntu-mono-light/status/24', ['images/black/lunchinator.svg', 'images/lunchinatorred.svg']),
              ('share/applications', ['installer/lunchinator.desktop'])]
data_files.extend([("share/lunchinator/" + dp, [os.path.join(dp, fn) for fn in fns if not fn.endswith('.pyc')]) for dp, _, fns in os.walk('plugins')])
data_files.extend([("share/lunchinator/" + dp, [os.path.join(dp, fn) for fn in fns]) for dp, _, fns in os.walk('bin')])

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
    packages =      ['lunchinator', 'lunchinator.cli', 'lunchinator.yapsy', 'gnupg'],
    scripts =       ['bin/lunchinator'],
    data_files =    data_files,
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

