import os
moddir = os.path.dirname(__file__)

# Read version from file
version = str(open(os.path.join(moddir, 'RELEASE-VERSION'),
                   'r'
                  ).readlines()[0]
             )
