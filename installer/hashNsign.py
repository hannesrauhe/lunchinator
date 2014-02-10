import logging,sys,os,hashlib,shutil

path = os.path.abspath(sys.argv[0])
while os.path.dirname(path) != path:
    if os.path.exists(os.path.join(path, 'lunchinator', '__init__.py')):
        sys.path.insert(0, path)
        break
    path = os.path.dirname(path)
    
from lunchinator.lunch_settings import lunch_settings
from gnupg.gnupg import GPG

logging.root.setLevel(logging.INFO)

if len(sys.argv)>1 and os.path.isfile(sys.argv[1]):
    fileToSign = open(sys.argv[1],"rb")
else:
    print sys.argv
    logging.error("No file given or file does not exist")
    sys.exit(-1)

md = hashlib.md5()
md.update(fileToSign.read())
fileToSign.close()
fileHash = md.hexdigest()
logging.info("Hash is %s"%fileHash)

commitCount = lunch_settings.get_singleton_instance().get_commit_count()

#create signed version.asc

stringToSign = "Commit Count: %s\nInstaller Hash: %s\nURL: %s/%s"%(commitCount,fileHash,commitCount,os.path.basename(fileToSign.name))

gbinary = os.path.join(lunch_settings.get_singleton_instance().get_lunchdir(),"gnupg","gpg.exe")
ghome = os.path.join(lunch_settings.get_singleton_instance().get_main_config_dir(),"gnupg")
sec_key = os.path.join(ghome,"lunchinator_pub_sec_0x17F57DC2.asc")
if not os.path.isfile(gbinary):
    logging.error("GPG not found, cannot sign")
    sys.exit(-1)
if not os.path.isfile(sec_key):
    logging.error("Secret Key not found, cannot sign")
    sys.exit(-1)
    
gpg = GPG(gbinary,ghome)

gpg.import_keys(open(sec_key,"r").read())
signedString = gpg.sign(stringToSign)
v = gpg.verify(str(signedString))
if not v:
    logging.error("Verification of Signature failed")
    sys.exit(-1)

print stringToSign
    
version_file = open(os.path.join(os.path.dirname(sys.argv[1]),"latest_version.asc"),"w")
version_file.write(str(signedString))
version_file.close()

#moving files around

if not os.path.isdir(os.path.join(os.path.dirname(sys.argv[1]),str(commitCount))):
    os.mkdir(os.path.join(os.path.dirname(sys.argv[1]),str(commitCount)))

shutil.copyfile(os.path.join(os.path.dirname(sys.argv[1]),"latest_version.asc"), os.path.join(os.path.dirname(sys.argv[1]),commitCount,"version.asc"))
shutil.copyfile(sys.argv[1], os.path.join(os.path.dirname(sys.argv[1]),commitCount,os.path.basename(sys.argv[1])))