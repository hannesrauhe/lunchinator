from lunchinator import log_error, log_exception, get_settings
from lunchinator.utilities import getBinary, getPlatform, PLATFORM_WINDOWS
import zlib, sqlite3, os, locale
from gnupg import GPG

def encrypt_RSA(pubkey, message):    
    from gnupg import GPG
    gbinary = getBinary("gpg", "bin")
    if not gbinary:
        log_error("GPG not found")
        return None, None
    
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
        return None
    
    c = gpg.encrypt(message, pubkey, always_trust=True)
    return str(c)

db_file = os.path.join(get_settings().get_main_config_dir(),"lunchinator.sq3")
tries = 10
public_key = "0x17F57DC2"

cnx = sqlite3.connect(db_file) 
cursor = cnx.cursor()
p,e,c,ce,ec,cnt = 0,0,0,0,0,0
cursor.execute("select mtype || \" \" || message from statistics_messages where mtype='HELO_INFO' order by rtime desc limit %d"%tries)
tries = 0
for (rec,) in cursor:
    plain_text = rec.encode("utf8")
    enc_data = encrypt_RSA(public_key, plain_text)
    enc_data_comp = zlib.compress(enc_data)
    
    comp_data = zlib.compress(plain_text)
    comp_data_enc = encrypt_RSA(public_key, comp_data)
    
    p+=len(plain_text)
    e+=len(enc_data)
    c+=len(comp_data)
    ce+=len(comp_data_enc)
    ec+=len(enc_data_comp)
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
print "Encrypted:", float(e)/tries
print "encrypt, compress:", float(ec)/tries
print "compression was better on encrpyted data", cnt