import logging, sys, os, hashlib, shutil

try:
    import lunchinator
except:
    path = os.path.abspath(sys.argv[0])
    while os.path.dirname(path) != path:
        if os.path.exists(os.path.join(path, 'lunchinator', '__init__.py')):
            sys.path.insert(0, path)
            break
        path = os.path.dirname(path)
    
from lunchinator.lunch_settings import lunch_settings
from lunchinator.utilities import getGPG

logging.root.setLevel(logging.INFO)

if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
    fileToSign = open(sys.argv[1], "rb")
else:
    print sys.argv
    logging.error("No file given or file does not exist")
    sys.exit(-1)

md = hashlib.md5()
md.update(fileToSign.read())
fileToSign.close()
fileHash = md.hexdigest()
logging.info("Hash is %s" % fileHash)

commitCount = lunch_settings.get_singleton_instance().get_commit_count()

# create signed version.asc

stringToSign = "Commit Count: %s\nInstaller Hash: %s\nURL: %s/%s" % (commitCount, fileHash, commitCount, os.path.basename(fileToSign.name))

gpg, keyid = getGPG(secret=True)
if not gpg or not keyid:
    sys.exit(-1)

signedString = gpg.sign(stringToSign, keyid=keyid)
print stringToSign
    
version_file = open(os.path.join(os.path.dirname(sys.argv[1]), "latest_version.asc"), "w")
version_file.write(str(signedString))
version_file.close()

version_file = open(os.path.join(os.path.dirname(sys.argv[1]), "index.html"), "w")
version_file.write('Download lunchinator: <a href="%s/%s">Version %s</a>' % (commitCount, os.path.basename(fileToSign.name), commitCount))
version_file.close()

# moving files around

installer_dir = os.path.join(os.path.dirname(sys.argv[1]), str(commitCount))
if not os.path.isdir(installer_dir):
    os.mkdir(installer_dir)

shutil.copyfile(os.path.join(os.path.dirname(sys.argv[1]), "latest_version.asc"), os.path.join(os.path.dirname(sys.argv[1]), commitCount, "version.asc"))
shutil.copyfile(sys.argv[1], os.path.join(os.path.dirname(sys.argv[1]), commitCount, os.path.basename(sys.argv[1])))
