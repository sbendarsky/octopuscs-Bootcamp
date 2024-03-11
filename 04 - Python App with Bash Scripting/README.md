# Introduction
Firstly, used the previous cluster (from the previous mission - which includes: metallb, nginx ingress controller, and harbor) * You can view the configurations, and the installation of the cluster and the prerequisites in previous documents.

And then I started with creating a mongodb statetfulset deployment, so I could create the app and connect via pymongo library.

### namespace.yaml
```
apiVersion: v1
kind: Namespace    # Specifies the Kubernetes resource type as Namespace
metadata:
  name: survey-app   # Name of the namespace, in this case, "survey-app"
```

### mongo-pv.yaml:
```
apiVersion: v1
kind: PersistentVolume      # Specifies the Kubernetes resource type as PersistentVolume
metadata:
  name: mongodb-pv 	     # Name of the PersistentVolume, in this case, "mongodb-pv"
spec:
  capacity:
    storage: 1Gi            # Specifies the storage capacity of the PersistentVolume
  accessModes:
    - ReadWriteOnce         # Defines the access mode for the PersistentVolume
  storageClassName: gp2     # Specifies the storage class for dynamic provisioning
  hostPath:
    path: /dev/db           # Specifies the host path for the PersistentVolume
```
### mongo-secret.yaml:
```
apiVersion: v1
kind: Secret                # Specifies the Kubernetes resource type as Secret
metadata:
  name: mongo-secret        # Name of the Secret, in this case, "mongo-secret"
  namespace: survey-app     # Specifies the namespace where the Secret resides
type: Opaque                # Specifies the type of Secret as Opaque, which means arbitrary data
data:
  username: YWRtaW4=        # Base64 encoded value of "admin" for the username field
  password: YWRtaW4=        # Base64 encoded value of "admin" for the password field
```
### mongo-pvc.yaml:
```
apiVersion: "v1"
kind: "PersistentVolumeClaim"  # Specifies the Kubernetes resource type as PersistentVolumeClaim
metadata:
  name: "mongodb-pvc"           # Name of the PersistentVolumeClaim, in this case, "mongodb-pvc"
  namespace: "survey-app"       # Specifies the namespace where the PersistentVolumeClaim resides
  labels:                       # Labels attached to the PersistentVolumeClaim
    app: "mongo-db"             # Label indicating
spec:
  accessModes:                  # Specifies the access mode for the PersistentVolumeClaim
    - ReadWriteOnce             # Allows read/write access by a single node
  resources:        # Specifies the desired resources
    requests:
      storage: 1Gi              # Requests 1 gigabyte of storage
  storageClassName: gp2        # Specifies the storage class for dynamic provisioning
```
mongo-svc.yaml:
```
apiVersion: "v1"
kind: "Service"             # Specifies the Kubernetes resource type as Service
metadata:
  name: "mongo-db"          # Name of the Service, in this case, "mongo-db"
  namespace: "survey-app"   # Specifies the namespace where the Service resides
  labels:                   # Labels attached to the Service
    app: "mongo-db"         # Label indicating the application associated with the Service
spec:
  externalTrafficPolicy: "Local"  # Specifies the traffic policy for external traffic
  ports:
    -
      name: "mongodb"       # Name of the port, in this case, "mongodb"
      port: 27017           # Port number for MongoDB
      nodePort: 30332       # Specifies the node port for the Service
  type: "LoadBalancer"      # Specifies the type of Service as LoadBalancer
  selector:                 # Selects the set of Pods targeted by this Service
    app: "mongo-db"         # Matches Pods with the label "app: mongo-db"
```
### mongo-Statefulset.yaml:
```
apiVersion: apps/v1
kind: StatefulSet                      # Specifies the Kubernetes resource type as StatefulSet
metadata:
  name: mongo-db                       # Name of the StatefulSet, in this case, "mongo-db"
  namespace: survey-app                # Specifies the namespace where the StatefulSet resides
spec:
  serviceName: mongo-db               # Specifies the service name associated with this StatefulSet
  replicas: 1                         # Number of replicas for the StatefulSet
  selector:
    matchLabels:
      app: mongo-db                    # Labels used to match Pods managed by this StatefulSet
  template:
    metadata:
      labels:
        app: mongo-db                  # Labels applied to Pods created from this StatefulSet
    spec:
      containers:
        - name: mongo-db               # Name of the container
          image: mongo:4.4.6           # Docker image used for the container
          imagePullPolicy: Always      # Specifies the image pull policy
          env:
            - name: MONGO_INITDB_ROOT_USERNAME    # Environment variable for MongoDB root username
              valueFrom:
                secretKeyRef:
                  name: mongo-secret     # Name of the Secret containing the username
                  key: username         # Key within the Secret for the username
            - name: MONGO_INITDB_ROOT_PASSWORD    # Environment variable for MongoDB root password
              valueFrom:
                secretKeyRef:
                  name: mongo-secret     # Name of the Secret containing the password
                  key: password         # Key within the Secret for the password
          ports:
            - containerPort: 27017      # Port the container exposes for MongoDB
              name: mongodb             # Name of the port
          volumeMounts:
            - name: mongodb-persistent-storage   # Name of the volume
              mountPath: /data/db       # Mount path for the persistent volume
      volumes:
        - name: mongodb-persistent-storage    # Name of the persistent volume
          persistentVolumeClaim:
            claimName: mongodb-pvc    # Name of the PersistentVolumeClaim used by the persistent volume
```
To apply all of the files:
```
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/mongo-secret.yaml
kubectl apply -f k8s/mongo-pv.yaml
kubectl apply -f k8s/mongo-pvc.yaml
kubectl apply -f k8s/mongo-svc.yaml
kubectl apply -f k8s/mongo-StatefulSet.yaml
```
After applying all of the kuberenetes yamls, we successfully deployed our mongodb, and now we can start creating the app: 
* 
in this current state of code, I already appealed it to the deployment file, where it will fetch the mongodb creds through the env (and inside the deployment through the secret)

### app.py:
```
from flask import Flask, render_template, redirect, url_for, request
from pymongo import MongoClient
import os


# Initialize Flask app and specify template folder
app = Flask(__name__, template_folder='templates')


# Fetching MongoDB credentials from environment variables
mongo_username = os.environ.get('MONGO_INITDB_ROOT_USERNAME')
mongo_password = os.environ.get('MONGO_INITDB_ROOT_PASSWORD')
mongo_host = os.environ.get('MONGO_HOST')
mongo_port = os.environ.get('MONGO_PORT')


# Constructing MongoDB URI if all environment variables are present
if all([mongo_username, mongo_password, mongo_host, mongo_port]):
    mongo_uri = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/'
    app.config["MONGO_URI"] = mongo_uri
else:
    # Including MongoDB URI in the ValueError message
    mongo_uri_msg = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/'
    raise ValueError(f"MongoDB environment variables are not properly set. MongoDB URI: {mongo_uri_msg}")


# Initialize MongoDB client
mongo = MongoClient(app.config["MONGO_URI"])


# Check if the voting_db database exists, if not, create it
if "voting_db" not in mongo.list_database_names():
    db = mongo["voting_db"]
    # Create collections for votes and user votes
    db.create_collection("votes")
    db.create_collection("user_votes")
else:
    db = mongo["voting_db"]


# Initialize the voting collection if it doesn't exist
if "candidates" not in db.list_collection_names():
    db.create_collection("candidates")
    # Insert initial data for biden and trump
    db.candidates.insert_many([
        {'name': 'biden', 'votes': 0},
        {'name': 'trump', 'votes': 0}
    ])


# Home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        biden_choice = request.form.get('biden')
        trump_choice = request.form.get('trump')
       
        # Update database with user's choices
        db.votes.insert_one({'name': name, 'biden_choice': biden_choice, 'trump_choice': trump_choice})
        db.user_votes.insert_one({'name': name, 'biden_choice': biden_choice, 'trump_choice': trump_choice})
       
        # Increment vote counts for selected candidates
        if biden_choice == "1":
            db.candidates.update_one({'name': 'biden'}, {'$inc': {'votes': 1}})
        elif trump_choice == "1":
            db.candidates.update_one({'name': 'trump'}, {'$inc': {'votes': 1}})
       
        # Redirect to dashboard
        return redirect(url_for('dashboard'))
    return render_template('home.html')


# Dashboard page
@app.route('/dashboard')
def dashboard():
    # Get all votes from database
    votes = list(db.user_votes.find())
    candidates = list(db.candidates.find())
    return render_template('dashboard.html', votes=votes, candidates=candidates)


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```
After creating the app we can now start with the Dockerfile to create the image:
* Because I have Harbor already deployed, I choose to push the image to the same project as the last article to avoid uploading the cert file into each node.

### Dockerfile
```
# Use the official Python image as a parent image
FROM python:3.9-slim


# Set the working directory in the container
WORKDIR /app


# Copy the current directory contents into the container at /app
COPY . /app


# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Expose the port Flask will run on
EXPOSE 5000


# Run app.py when the container launches
CMD ["python", "app.py"]
```
and now just build and push the image into Harbor registry:
```
docker build -t survey-app .
docker tag survey-app:latest registry-stav.tamnun.lab/hotcold/survey-app:latest
docker login registry-stav.tamnun.lab
docker push registry-stav.tamnun.lab/hotcold/survey-app:latest
```
After uploading the image we can start now with creating the deployment files for the kubernetes. 
### survey-service.yaml:
apiVersion: v1
kind: Service
metadata:
  name: survey-app-service          # Name of the Service, in this case, "survey-app-service"
  namespace: survey-app             # Specifies the namespace where the Service resides
spec:
  selector:
    app: survey-app                 # Selects Pods with the label "app: survey-app"
  ports:
  - protocol: TCP                  # Specifies the protocol used for the port (TCP)
    port: 80                        # Port exposed on the Service
    targetPort: 5000                # Port to which traffic will be forwarded to in the Pods
  type: ClusterIP                   # Specifies the type of Service as ClusterIP

### ingress.yaml:
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: survey-app-ingress                # Name of the Ingress resource
  namespace: survey-app                  # Specifies the namespace where the Ingress resides
  annotations:
    kubernetes.io/ingress.class: "nginx" # Annotation specifying the Ingress class
spec:
  rules:
  - host: survey-stav.tamnun.lab         # Hostname for accessing the application
    http:
      paths:
      - path: /                           # Path for accessing the application
        pathType: Prefix                  # Specifies the type of path matching
        backend:
          service:
            name: survey-app-service      # Name of the backend Service
            port:
              number: 80                  # Port number exposed by the backend Service
```
### survey-deployment.yaml:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: survey-app-deployment            # Name of the Deployment resource
  namespace: survey-app                  # Specifies the namespace where the Deployment resides
spec:
  replicas: 1                            # Number of desired replicas for the Deployment
  selector:
    matchLabels:
      app: survey-app                    # Labels used to match Pods controlled by this Deployment
  template:
    metadata:
      labels:
        app: survey-app                  # Labels applied to Pods created by this Deployment
    spec:
      containers:
      - name: survey-app-container       # Name of the container
        image: registry-stav.tamnun.lab/hotcold/survey-app:latest  # Docker image for the container
        ports:
        - containerPort: 5000            # Port exposed by the container
        env:
        - name: MONGO_HOST               # Environment variable for MongoDB host
          value: "172.18.255.202"       # IP address of the MongoDB service
        - name: MONGO_PORT               # Environment variable for MongoDB port
          value: "27017"                 # Port MongoDB is listening on
        - name: MONGO_INITDB_ROOT_USERNAME  # Environment variable for MongoDB root username
          valueFrom:
            secretKeyRef:
              name: mongo-secret         # Name of the secret containing MongoDB username
              key: username             # Key within the secret containing MongoDB username
        - name: MONGO_INITDB_ROOT_PASSWORD  # Environment variable for MongoDB root password
          valueFrom:
            secretKeyRef:
              name: mongo-secret         # Name of the secret containing MongoDB password
              key: password             # Key within the secret containing MongoDB password
```
and now we can deploy the entirety of the kubernetes files and everything would be deployed:
```
kubectl apply -f k8s/survey-service.yaml
kubectl apply -f k8s/survey-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```
## Helm Chart
Great, Now lets start creating the helm-chart (a lot of yaml’s just mixes things up, better to work with helm charts )
```
helm create survey
```
And now lets configure each file:
### ingress.yaml:
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Values.ingress.name }}
  namespace: {{ .Values.ingress.namespace }}
  annotations:
    kubernetes.io/ingress.class: "nginx" # Annotation specifying the Ingress class
spec:
  rules:
  - host: {{ .Values.ingress.host }}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ .Values.ingress.service.name }}
            port:
              number: {{ .Values.ingress.service.port }}
```
### mongo-pv.yaml:
```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ .Values.mongopv.name }}
spec:
  capacity:
    storage: {{ .Values.mongopv.storage }}
  accessModes:
    - {{ .Values.mongopv.accessMode }}
  storageClassName: {{ .Values.mongopv.storageClassName }}
  hostPath:
    path: {{ .Values.mongopv.hostPath }}
```
### mongo-pvc.yaml:
```
apiVersion: "v1"
kind: "PersistentVolumeClaim"
metadata:
  name: "{{ .Values.mongopvc.name }}"
  namespace: "{{ .Values.mongopvc.namespace }}"
  labels:
    app: "{{ .Values.mongopvc.labels.app }}"
spec:
  accessModes:
    - {{ .Values.mongopvc.accessMode }}
  resources:
    requests:
      storage: {{ .Values.mongopvc.resources.requests.storage }}
  storageClassName: {{ .Values.mongopvc.storageClassName }}
```
### mongo-secret.yaml:
```
apiVersion: v1
kind: Secret
metadata:
  name: {{ .Values.mongosecret.name }}
  namespace: {{ .Values.mongosecret.namespace }}
type: Opaque
data:
  username: {{ .Values.mongosecret.username | b64enc | quote }} # Base64 encoded value of "admin"
  password: {{ .Values.mongosecret.password | b64enc | quote }} # Base64 encoded value of "admin"
```
### mongo-statefulset.yaml:
```
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ .Values.mongostatefulset.name }}
  namespace: {{ .Values.mongostatefulset.namespace }}
spec:
  serviceName: {{ .Values.mongostatefulset.serviceName }}
  replicas: {{ .Values.mongostatefulset.replicas }}
  selector:
    matchLabels:
      app: {{ .Values.mongostatefulset.MatchLabels }}
  template:
    metadata:
      labels:
        app: {{ .Values.mongostatefulset.lables }}
    spec:
      containers:
        - name: {{ .Values.mongostatefulset.containerName }}
          image: {{ .Values.mongostatefulset.image }}
          imagePullPolicy: {{ .Values.mongostatefulset.imagePullPolicy }}
          env:
            - name: MONGO_INITDB_ROOT_USERNAME
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.mongosecret.name }}
                  key: username
            - name: MONGO_INITDB_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.mongosecret.name }}
                  key: password
          ports:
            - containerPort: {{ .Values.mongostatefulset.containerPort }}
              name: {{ .Values.mongostatefulset.PortName }}
          volumeMounts:
            - name: {{ .Values.mongostatefulset.VolumeName }}
              mountPath: {{ .Values.mongostatefulset.mountPath }}
      volumes:
        - name: {{ .Values.mongostatefulset.VolumeName }}
          persistentVolumeClaim:
            claimName: {{ .Values.mongostatefulset.pvcName }}
```
### mongo-svc.yaml:
```
apiVersion: "v1"
kind: "Service"
metadata:
  name: {{ .Values.mongosvc.name }}
  namespace: {{ .Values.mongosvc.namespace }}
  labels:
    app: {{ .Values.mongosvc.labelApp }}
spec:
  externalTrafficPolicy: {{ .Values.mongosvc.externalTrafficPolicy }}
  ports:
    - name: {{ .Values.mongosvc.ports.name }}
      port: {{ .Values.mongosvc.ports.port }}
      nodePort: {{ .Values.mongosvc.ports.nodePort }}
  type: {{ .Values.mongosvc.type }}
  selector:
    app: {{ .Values.mongosvc.selector.app }}
```
### namespace.yaml:
```
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.namespace }}
```
### survey-deployment.yaml:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.surveydeployment.name }}
  namespace: {{ .Values.surveydeployment.namespace }}
spec:
  replicas: {{ .Values.surveydeployment.replicas }}
  selector:
    matchLabels:
      app: survey-app
  template:
    metadata:
      labels:
        app: survey-app
    spec:
      containers:
        - name: {{ .Values.surveydeployment.containerName }}
          image: {{ .Values.surveydeployment.containerImage }}
          ports:
            - containerPort: {{ .Values.surveydeployment.containerPort }}
          env:
          - name: MONGO_HOST
            value: {{ .Values.mongosvc.name }}  # Name of the MongoDB service
          - name: MONGO_PORT
            value: "27017"  # Port MongoDB is listening on
          - name: MONGO_INITDB_ROOT_USERNAME
            valueFrom:
              secretKeyRef:
                name: mongo-secret  # Name of the secret containing MongoDB username
                key: username  # Key within the secret containing MongoDB username
          - name: MONGO_INITDB_ROOT_PASSWORD
            valueFrom:
              secretKeyRef:
                name: mongo-secret  # Name of the secret containing MongoDB password
                key: password  # Key within the secret containing MongoDB password
```
survey-service.yaml:
```
apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.surveyservice.name }}
  namespace: {{ .Values.surveyservice.namespace }}
spec:
  selector:
    app: {{ .Values.surveyservice.selectorApp }}
  ports:
  - protocol: {{ .Values.surveyservice.protocol }}
    port: {{ .Values.surveyservice.port }}
    targetPort: {{ .Values.surveyservice.targetPort }}
  type: {{ .Values.surveyservice.type }}
```
### values.yaml:
```
namespace: survey-app
ingress:
  name: survey-app-ingress
  namespace: survey-app
  host: survey-stav.tamnun.lab
  service:
    name: survey-app-service
    port: "80"


mongopv:
  name: mongodb-pv
  storage: 1Gi
  accessMode: ReadWriteOnce
  storageClassName: gp2
  hostPath: /dev/db


mongopvc:
  name: mongodb-pvc
  namespace: survey-app
  labels:
    app: mongo-db
  accessMode: ReadWriteOnce
  storageClassName: gp2
  resources:
    requests:
      storage: 1Gi


mongosecret:
  name: mongo-secret
  namespace: survey-app
  username: admin
  password: admin


mongosvc:
  name: mongo-db
  namespace: survey-app
  labelApp: mongo-db
  externalTrafficPolicy: Local
  ports:
    name: mongodb
    port: "27017"  # This should be a string
    nodePort: "30332"
  type: LoadBalancer
  selector:
    app: mongo-db




mongostatefulset:
  name: mongo-db
  namespace: survey-app
  serviceName: mongo-db
  replicas: ""
  MatchLabels: mongo-db
  lables: mongo-db
  containerName: mongo-db
  image: mongo:4.4.6
  imagePullPolicy: Always
  containerPort: "27017"
  PortName: mongodb
  VolumeName: mongodb-persistent-storage
  mountPath: /data/db
  pvcName: mongodb-pvc


surveyservice:
  name: survey-app-service
  namespace: survey-app
  selectorApp: survey-app
  protocol: TCP
  port: "80"
  targetPort: "5000"
  type: ClusterIP


surveydeployment:
  name: survey-app-deployment
  namespace: survey-app
  replicas: "1"
  containerName: survey-app-container
  containerImage: registry-stav.tamnun.lab/hotcold/survey-app:latest
  containerPort: "5000"
  port: "27017"
```
Now lets create a script that will log, and create the helm chart and there you can configure how many replicas you wish to deploy for the mongo db:
### script.sh
```
#!/bin/bash


LOG_FILE="logs.log"


function log_info() {
    local message=$1
    echo "[INFO] $(date +"%Y-%m-%d %T") - $message" >> "$LOG_FILE"
}


function log_error() {
    local message=$1
    echo "[ERROR] $(date +"%Y-%m-%d %T") - $message" >> "$LOG_FILE"
}


function install_helm() {
    log_info "Installing helm..."
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh >> "$LOG_FILE" 2>&1
    rm get_helm.sh
}


function deploy_helm_chart() {
    if check_if_helmchart_installed; then
        echo "ERROR: Helm chart already installed. Please uninstall it first."
        log_error "Helm chart already installed. Please uninstall it first."
    else
        log_info "Deploying helm chart..."
        helm install survey ./survey >> "$LOG_FILE" 2>&1
    fi
}


function check_if_helmchart_installed() {
    if helm list | grep -q survey; then
        return 0
    else
        return 1
    fi
}


function uninstall_helm_chart() {
    if check_if_helmchart_installed; then
        log_info "Uninstalling helm chart..."
        helm uninstall survey >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function upgrade_helm_chart() {
    if check_if_helmchart_installed; then
        log_info "Upgrading helm chart..."
        helm upgrade survey ./survey >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function help_message() {
    echo "Usage: script.sh [OPTION]"
    echo "Options:"
    echo "  -helm      : to install helm (if not already installed)"
    echo "  -info      : to display the helm chart information"
    echo "  -deploy    : to deploy the helm chart"
    echo "  -uninstall : to uninstall the helm chart"
    echo "  -upgrade   : to upgrade the helm chart"
    echo "  -help      : to display the help message"
    echo "  -r         : to change the amount of replicas of the mongodb statefulset"
}


function change_replicas() {
    if check_if_helmchart_installed; then
        kubectl scale statefulset mongo-db -n survey-app --replicas="$1" >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function info_helm_chart() {
    if check_if_helmchart_installed; then
        kubectl get all -n survey-app
        # pass to logs
        kubectl get all -n survey-app >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function main() {
    if [ $# -eq 0 ]; then
        help_message
        exit 1
    fi
    while getopts "h:i:d:u:U:h:r:" opt; do
        case $opt in
            h|helm) install_helm;;
            i|info) info_helm_chart;;
            d|deploy) deploy_helm_chart info_helm_chart;;
            u|uninstall) uninstall_helm_chart;;
            U|upgrade) upgrade_helm_chart info_helm_chart;;
            h|help) help_message;;
            r) change_replicas "$OPTARG" info_helm_chart;;
            *) echo "Invalid option: -$OPTARG" >&2; help_message; exit 1;;
        esac
    done
}


main "$@"
```