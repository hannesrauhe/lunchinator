#!/usr/bin/python
from __future__ import with_statement
import subprocess
from distutils.core import setup

def get_version():
    call = ["git","--no-pager","rev-list", "HEAD", "--count"]
    fh = subprocess.PIPE    
    p = subprocess.Popen(call,stdout=fh, stderr=fh)
    pOut, _ = p.communicate()
    retCode = p.returncode
    
    if retCode:
        # something went wrong
        return None, None
    
    commit_count = int(pOut.strip())
    return commit_count, (0, 1, commit_count, 'final', 0)
    
version, version_info = get_version()

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

setup(
    name =          'Lunchinator',
    version =       version,
    url =           'http://www.lunchinator.de',
    #download_url =  'http://path/tp/Lunchinator-%s.tar.gz' % version,
    description =   'The Lunchinator.',
    long_description = long_description,
    author =        'Hannes Rauhe, Cornelius Ratsch',
    author_email =  'info [at] lunchinator.de',
    maintainer =    'Hannes Rauhe',
    maintainer_email = 'hannes [at] scitivity.net',
    license =       'BSD License',
    packages =      ['lunchinator', 'lunchinator.cli', 'lunchinator.yapsy'],
    scripts =       ['bin/lunchinator'],
    data_files =    [('sounds', ['sounds/sonar.wav']),
                     ('images', ['images/webcam.jpg',
                                 'images/mini_breakfast.png',
                                 'images/lunch.png',
                                 'images/lunchred.png'])],
    classifiers =   ['Development Status :: %s' % DEVSTATUS,
                     'License :: OSI Approved :: BSD License',
                     'Operating System :: OS Independent',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 2',
                     'Programming Language :: Python :: 2.6',
                     'Programming Language :: Python :: 2.7',
                     'Topic :: Office/Business :: Scheduling',
                     'Topic :: Utilities',
                     'Topic :: Communications :: Chat',
                    ],
      requires =    ['gnupg']
    )
