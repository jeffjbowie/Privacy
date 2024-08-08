import glob
import os
import pyzipper
import time
import uuid
import sys
import string 
import random

'''
INSTALL
-------
sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
gcloud init
gcloud auth application-default login
'''

from google.cloud import storage

def upload_blob(bucket_name, source_file_name, destination_blob_name):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name, if_generation_match=0)

    print(
        f"[U] {source_file_name} uploaded to GCS \"{bucket_name}\" ."
    )

def gen_random(N):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))

def archive_and_encrypt(path, SECRET_PASSWORD):

    identifier = str(uuid.uuid4())
    archive_name = f"{identifier}{int(time.time())}.zip"

    with pyzipper.AESZipFile(f"/tmp/{archive_name}",
                             'w',
                             compression=pyzipper.ZIP_LZMA,
                             encryption=pyzipper.WZ_AES) as zf:
        
        zf.setpassword(SECRET_PASSWORD)
        
        for _f in glob.glob(f"{path}**", recursive=True):
            # Only archive JPEG images.
            if _f.endswith('.jpg'):
                # Skip files less than 1MB.
                if not os.path.getsize(_f) < 102400:
                    try:
                        zf.write(_f, arcname=gen_random(random.randint(5,9)))
                        # Remove file after writing to archive.
                        os.remove(_f)
                    except Exception as e:
                        print(f"[E] {e}")
                        pass
    return archive_name

def decrypt(SECRET_PASSWORD, _f):
    try:
        with pyzipper.AESZipFile(_f) as zf:
            zf.setpassword(SECRET_PASSWORD)
            zf.extractall()
    except Exception as e:
        print(f"[E] {e}")
        
if __name__ == '__main__':

    SEARCH_PATH = "/mnt/4K_Recordings"
    SECRET_PASSWORD = b'You know, the keyspace in a password is the most impactful factor in preventing cracking!'
    GOOGLE_STORAGE_BUCKET = "surveillance"
    LOG_PATH = "/var/log/surveillance-backup/"
    
    if len(sys.argv) == 1:

        f = open(f"{LOG_PATH}{int(time.time())}-SurveillanceBackup.log", "w")

        _archive_name = archive_and_encrypt(SEARCH_PATH, SECRET_PASSWORD)
        f.writelines(f"[{time.ctime()}] Starting backup of files from {SEARCH_PATH} ...\n")

        try:
            upload_blob(GOOGLE_STORAGE_BUCKET, f"/tmp/{_archive_name}", _archive_name)
            # Remove archive after upload.
            os.remove(f"/tmp/{_archive_name}")
            f.writelines(f"[{time.ctime()}] Completed.\n")
        except Exception as e:
            f.writelines(f"[{time.ctime()}] [E]: {e} ...\n")
            print(f"[E] {e}")
        
        f.close()

    elif len(sys.argv) == 2:

        if os.path.exists(sys.argv[1]):
            print(f"[>] Extracting {sys.argv[1]}...")
            SECRET_PASSWORD = input("Password: ")
            decrypt(SECRET_PASSWORD.encode(), sys.argv[1])
        else:
            print(f"[!] Unable to locate {sys.argv[1]}.")
    else:
        print(f"Usage: {sys.argv[0]}, to decrypt & extract pass the path to an encrypted zip file.")
