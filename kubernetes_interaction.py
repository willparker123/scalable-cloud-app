import json
from kubernetes import client, config, utils
import os

class Kubernetes_Interaction(object):
    """
    Interact with the Kubernetes cluster
    """
    def __init__(self, token, port=16443, node_ip="192.168.1.0", verify_ssl=False):
        if node_ip is not None:
            k8s_config = client.Configuration()
            k8s_config.host = f"https://{node_ip}:{port}"
        elif os.environ.get('KUBE_API_ADDRESS'):
            k8s_config = client.Configuration()
            k8s_config.host = os.environ['KUBE_API_ADDRESS']
        else:
            k8s_config = config.load_incluster_config()
        k8s_config.verify_ssl = verify_ssl
        k8s_config.api_key = {"authorization": "Bearer " + token}
        self.k8s_config = k8s_config
        self.apiClient = client.ApiClient(config)
        
    def list_all_pods(self):
        apiInstance = client.CoreV1Api(self.apiClient)
        pods = apiInstance.list_pod_for_all_namespaces(watch = False)

        podsList = []
        for item in pods.items:
            podsList.append(item.metadata.name)

        return json.dumps(podsList)
    
    def apply_resource(self, file):
        try:
            utils.create_from_yaml(self.apiClient, file, verbose=True)
        except Exception as ex:
            print(ex)