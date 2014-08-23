from lunchinator import log_error, log_exception, get_settings
from lunchinator.utilities import getBinary, getPlatform, PLATFORM_WINDOWS
import zlib, sqlite3, os, locale, sys
from gnupg import GPG
    
from gnupg import GPG
gbinary = getBinary("gpg", "bin")
if not gbinary:
    log_error("GPG not found")
    sys._exit(1)

ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")

if not locale.getpreferredencoding():
    os.putenv("LANG", "en_US.UTF-8")

if not locale.getpreferredencoding():
    os.putenv("LANG", "en_US.UTF-8")

try:
    gpg = None
    if getPlatform() == PLATFORM_WINDOWS:
        gpg = GPG("\""+gbinary+"\"",ghome)
    else:
        gpg = GPG(gbinary,ghome)
    if not gpg.encoding:
        gpg.encoding = 'utf-8'
except Exception, e:
    log_exception("GPG not working: "+str(e))
    sys.exit(1)
    
db_file = os.path.join(get_settings().get_main_config_dir(),"lunchinator.sq3")
tries = 10
public_key = "0x17F57DC2"

cnx = sqlite3.connect(db_file) 
cursor = cnx.cursor()
p,e,c,ce,ec,s,sc,es,esc,cnt = (0,)*10
cursor.execute("select mtype || \" \" || message from statistics_messages where mtype='HELO_INFO' order by rtime desc limit %d"%tries)
tries = 0
for (rec,) in cursor:
    plain_text = rec.encode("utf8")
    
    enc_data = str(gpg.encrypt(plain_text, public_key, always_trust=True))
    enc_data_comp = zlib.compress(enc_data)
    
    comp_data = zlib.compress(plain_text)
    comp_data_enc = str(gpg.encrypt(comp_data, public_key, always_trust=True))
    
    sign_data = str(gpg.sign(plain_text))
    sign_data_comp = zlib.compress(sign_data)
        
    sign_enc_data = str(gpg.encrypt(plain_text, public_key, sign=public_key, always_trust=True))
    sign_enc_data_comp = zlib.compress(sign_enc_data)
    
    p+=len(plain_text)
    e+=len(enc_data)
    c+=len(comp_data)
    ce+=len(comp_data_enc)
    ec+=len(enc_data_comp)
    s+=len(sign_data)
    sc+=len(sign_data_comp)
    es+=len(sign_enc_data)
    esc+=len(sign_enc_data_comp)
    if len(enc_data_comp)<len(enc_data):
        cnt+=1
    tries+=1
#     print "Plain text:", len(plain_text)
#     print "Compressed", len(comp_data)
#     print "compress, encrypt:", len(comp_data_enc)
#     print "Encrypted:", len(enc_data)
#     print "encrypt, compress:", len(enc_data_comp)
#     print

tries = float(tries)

print "Average for %d messages:"%tries
print "Plain text:", float(p)/tries
print "Compressed", float(c)/tries
print "compress, encrypt:", float(ce)/tries
print "Signed:", float(s)/tries
print "Encrypted:", float(e)/tries
print "Encrypted, signed:", float(es)/tries
print "encrypt, compress:", float(ec)/tries
print "Encrypted, signed, compressed:", float(esc)/tries