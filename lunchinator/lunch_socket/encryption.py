from lunchinator.utilities import getGPG

def decrypt(crypt, **kwargs):     
    if 0==len(crypt):
        return ""
    gpg = getGPG()
    r = gpg.decrypt(crypt, **kwargs)
    if str(r)=="":
        raise Exception(r.stderr)
    #is's not nice to strip, but gpg's decrypt adds a newline at the end
    return str(r).strip(), dict((k, getattr(r, k)) for k in ("username", "key_id", "signature_id", "fingerprint", "trust_level", "trust_text"))

def encrypt(plain, recipients, **kwargs):       
    if 0==len(plain):
        return ""      
    gpg = getGPG()
    r = gpg.encrypt(plain, recipients, **kwargs)
    if str(r)=="":
        raise Exception(r.stderr)
    return str(r)

def sign(v, **kwargs): 
    if 0==len(v):
        return ""      
    gpg = getGPG()
    r = gpg.sign(v, **kwargs)
    if str(r)=="":
        raise Exception(r.stderr)
    return str(r)

def verify(v, **kwargs):
    if 0==len(v):
        return ""      
    gpg = getGPG()
    verified = gpg.verify(v, **kwargs)
    if not verified:
        raise Exception("Verification of message failed")
    return verified.key_id