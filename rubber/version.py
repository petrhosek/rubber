import sys
import os
moddir = os.path.dirname(__file__)

# Read version from file
version_file = os.path.join(moddir, 'RELEASE-VERSION')
if not os.path.exists(version_file):
    version = 'UNKNOWN'
    sys.stderr.write('WARNING: Version information missing.\n\n')
else:
    version = str(open(os.path.join(moddir, 'RELEASE-VERSION'),
                       'r'
                      ).readlines()[0]
                 )
