
"""
This module will run a kubectl command to check the creation of the secret that exposes the wallet information
to connect to an AutonomousDB created with OSOK operator in an OKE cluster. Once the secret is detected it will
write the wallet files to a specified directory
"""


import subprocess
import time
import json
import base64
import os


def check_secret(secret_name,namespace):
    """
    check if secret for autonomousDB is created
    if secret for autonomousDB is available it indicates that
    autonomous DB is ready for use

    secret_name: = secret in values.yaml wallet.walletName:
    """

    if namespace == '':
        kubectl_command = 'kubectl get secret'
    else:
        kubectl_command = f'kubectl -n {namespace} get secret'

    while True:
        secrets = subprocess.getoutput(kubectl_command)
        secret_list = secrets.split(' ')
        filterered_secret_list = list(filter(None, secret_list))
        newest_list =[]
        for secret in filterered_secret_list:
            word = " ".join(secret.split())
            temp_list = word.split(' ')
            for word in temp_list:
                newest_list.append(word)

        print("*********************************")
        print("Check for readiness of the AutonomousDB instance")
        print(secrets)
        print("*********************************")

        if secret_name in newest_list:
            break
        time.sleep(5)

    print("*********************************")
    print("Autonomous Database instance ready")
    print("*********************************")

def create_wallet_files(secret_name,path,namespace):
    """
    creates wallet files from secret
    secret_name: name defined for secret in values.yaml wallet.walletName:
    Kubernetes secrets are base64 encoded so this script will decode the
    secret content before writing to files
    """

    path_exist = os.path.exists(path)
    if not path_exist:
        os.makedirs(path)
        print(f'The new directory {path} is created!')

    data = "{.data}"

    if namespace == '':
        secrets = subprocess.getoutput ("kubectl get secret {}  -o  \"jsonpath={}\" ".format(secret_name, data))
    else:
        secrets = subprocess.getoutput ("kubectl -n {} get secret  {}  -o  \"jsonpath={}\" ".format(namespace,secret_name, data))

    secrets_convert = json.loads(secrets)
    for key, value  in secrets_convert.items():
        value = base64.b64decode(value)
        file_name = key
        with open(path + file_name, 'wb') as file:
            file.write(value)
        file.close()

def main():
    """
    namespace: namespace where AutonmousDB resource is created
    secret_name: define in values.yaml wallet.walletName
    path: path to write wallet files
    """

    namespace =('test300') # leave blank if default namespace or if running from inside Kubernetes cluster
    secret_name = ('autodbwallet')
    path = ("./wallet/")
    check_secret(secret_name, namespace)
    create_wallet_files(secret_name, path, namespace)

    """ 
    if script is run in Kubernetes pod change variables to
    read from environment variables and pass variables to container
    as env varaibles in Kubernetes manifest definitions
    Example:
    namespace =  os.getenv('namespace')
    path = os.getenv('path')
    secret_name = ('secret_name')
    """

if __name__ == "__main__":
    main()
