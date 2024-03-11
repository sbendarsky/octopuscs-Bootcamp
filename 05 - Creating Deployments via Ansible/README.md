# Introduction
Creating a playbook called setup.yml to create the environment
```
- hosts: devops
  become: yes
  tasks:
    - name: Install dnf dependencies
      ansible.builtin.dnf:
        name: "{{ item }}"
        state: present
      loop:
        - curl
        - gnupg2
        - dnf-plugins-core


    - name: Add Docker's official GPG key
      ansible.builtin.shell: curl -fsSL https://download.docker.com/linux/fedora/gpg | sudo gpg --import -


    - name: Add Docker repository
      ansible.builtin.shell: sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo


    - name: Install Docker
      ansible.builtin.dnf:
        name: "{{ item }}"
        state: present
      loop:
        - docker-ce
        - docker-ce-cli
        - containerd.io
        - docker-buildx-plugin
        - docker-compose-plugin


    - name: Create a docker group
      ansible.builtin.group:
        name: docker
        state: present


    - name: adding existing user 'ansible' to group docker
      user:
        name: ansible
        groups: docker
        append: yes


    - name: make sure /etc/docker/daemon.json exists
      ansible.builtin.file:
        path: /etc/docker/daemon.json
        state: touch


    - name: Adding a docker registry to /etc/docker/daemon.json
      ansible.builtin.lineinfile:
        path: /etc/docker/daemon.json
        line: '{ "insecure-registries": ["docker-stav.octopus.lab"] }'
        state: present


    - name: Reload Docker
      ansible.builtin.service:
        name: docker
        state: reloaded


    - name: Enable containerd service
      ansible.builtin.systemd:
        name: containerd
        state: started
        enabled: yes


    - name: Start and enable Docker service
      ansible.builtin.systemd:
        name: docker
        state: started
        enabled: yes


    - name: Check Docker version
      ansible.builtin.command: docker --version
      register: docker_version
      changed_when: false


    - name: Display Docker version
      ansible.builtin.debug:
        var: docker_version.stdout_lines


    - name: Install Kind for AMD64 / x86_64
      ansible.builtin.shell: |
        [ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
      args:
        executable: /bin/bash
      when: ansible_architecture == "x86_64"


    - name: Install Kind for ARM64
      ansible.builtin.shell: |
        [ $(uname -m) = aarch64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-arm64
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
      args:
        executable: /bin/bash
      when: ansible_architecture == "aarch64"


    - name: Get latest kubectl version
      ansible.builtin.uri:
        url: https://dl.k8s.io/release/stable.txt
        return_content: yes
      register: version


    - name: Download the latest kubectl release
      ansible.builtin.get_url:
        url: https://dl.k8s.io/release/{{ version.content }}/bin/linux/arm/kubectl
        dest: /usr/local/bin/kubectl
        mode: '0755'


    - name: Verify kubectl is installed
      ansible.builtin.command: kubectl version --client
      register: kubectl_version
      changed_when: false


    - name: Display kubectl version
      ansible.builtin.debug:
        var: kubectl_version.stdout_lines


    - name: Install helm if not exists
      unarchive:
        src: https://get.helm.sh/helm-v3.11.0-linux-amd64.tar.gz
        dest: /usr/local/bin
        extra_opts: "--strip-components=1"
        owner: root
        group: root
        mode: 0755
        remote_src: true
      args:
        creates: /usr/local/bin/helm


    - name: Create kind cluster configurations
      ansible.builtin.copy:
        content: |
          kind: Cluster
          apiVersion: kind.x-k8s.io/v1alpha4
          name: kind-cluster
          nodes:
          - role: control-plane
            image: kindest/node:v1.25.3@sha256:f52781bc0d7a19fb6c405c2af83abfeb311f130707a0e219175677e366cc45d1
          - role: worker
            image: kindest/node:v1.25.3@sha256:f52781bc0d7a19fb6c405c2af83abfeb311f130707a0e219175677e366cc45d1
          - role: worker
            image: kindest/node:v1.25.3@sha256:f52781bc0d7a19fb6c405c2af83abfeb311f130707a0e219175677e366cc45d1
        dest: /home/ansible/kind-config.yaml


    - name: Create a local Kubernetes cluster
      ansible.builtin.command: kind create cluster --config /home/ansible/kind-config.yaml
     
    - name: Add ansible user to docker group
      ansible.builtin.user:
        name: ansible
        groups: docker
        append: yes
      become: yes


    - name: Export kubeconfig run as user ansible
      ansible.builtin.command: kind export kubeconfig --name kind-cluster
      args:
        chdir: /home/ansible
      become: no
      become_user: ansible


    - name: Install MetalLB
      ansible.builtin.command: kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.7/config/manifests/metallb-native.yaml


    - name: Wait for MetalLB pods to be ready
      ansible.builtin.command: kubectl wait --for=condition=ready pod --all -n metallb-system --timeout=300s


    - name: Inspect Docker network
      ansible.builtin.command: docker network inspect -f '{{ '{{.IPAM.Config}}' | to_json }}' kind
      register: docker_network
      changed_when: false
      check_mode: no


    - name: Parse Docker network inspect output
      ansible.builtin.set_fact:
        x_value: "{{ docker_network.stdout | regex_search('172\\.(\\d+)\\.\\d+\\.\\d+/16', '\\1') | first }}"
      changed_when: false


    - name: Create IP range
      ansible.builtin.set_fact:
        ip_range: "172.{{ x_value }}.255.200 - 172.{{ x_value }}.255.250"
      changed_when: false


    - name: Install pip3
      ansible.builtin.dnf:
        name: python3-pip
        state: present


    - name: Install required Python libraries
      ansible.builtin.pip:
        name: kubernetes
        state: present


    - name: Apply MetalLB IP configuration
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: metallb.io/v1beta1
          kind: IPAddressPool
          metadata:
            name: example
            namespace: metallb-system
          spec:
            addresses:
              - "{{ ip_range }}"
         
    - name: Apply L2Advertisement configuration
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: metallb.io/v1beta1
          kind: L2Advertisement
          metadata:
            name: empty
            namespace: metallb-system


    - name: Pull the helm
      ansible.builtin.command: helm pull oci://ghcr.io/nginxinc/charts/nginx-ingress --untar --version 1.1.3
      args:
        chdir: /home/ansible


    - name: Apply CRDs
      ansible.builtin.command: kubectl apply -f crds/
      args:
        chdir: /home/ansible/nginx-ingress


    - name: Install nginx-ingress
      ansible.builtin.command: helm install nginx-ingress oci://ghcr.io/nginxinc/charts/nginx-ingress --version 1.1.3
      args:
        chdir: /home/ansible/nginx-ingress
```
Creating a jfrog Artifactory:
```
- hosts: devops
  tasks:
    - name: Install openssl
      ansible.builtin.package:
        name: openssl
        state: present
      become: yes


    - name: Ensure /etc/ssl/private directory exists
      ansible.builtin.file:
        path: /etc/ssl/private
        state: directory
        mode: '0700'


    - name: Ensure /etc/ssl/csr directory exists
      ansible.builtin.file:
        path: /etc/ssl/csr
        state: directory
        mode: '0700'


    - name: Ensure /etc/ssl/crt directory exists
      ansible.builtin.file:
        path: /etc/ssl/crt
        state: directory
        mode: '0700'


    - name: Generate a private key for docker-stav.octopus.lab
      ansible.builtin.openssl_privatekey:
        path: /etc/ssl/private/docker-stav.octopus.lab.pem


    - name: Generate a Certificate Signing Request
      ansible.builtin.openssl_csr:
        path: /etc/ssl/csr/docker-stav.octopus.lab.csr
        privatekey_path: /etc/ssl/private/docker-stav.octopus.lab.pem
        common_name: docker-stav.octopus.lab


    - name: Generate a Self Signed OpenSSL certificate
      ansible.builtin.openssl_certificate:
        path: /etc/ssl/crt/docker-stav.octopus.lab.crt
        privatekey_path: /etc/ssl/private/docker-stav.octopus.lab.pem
        csr_path: /etc/ssl/csr/docker-stav.octopus.lab.csr
        provider: selfsigned


    - name: Generate a new private key
      ansible.builtin.openssl_privatekey:
        path: /etc/ssl/private/artifactory-stav.octopus.lab.pem


    - name: Generate a Certificate Signing Request
      ansible.builtin.openssl_csr:
        path: /etc/ssl/csr/artifactory-stav.octopus.lab.csr
        privatekey_path: /etc/ssl/private/artifactory-stav.octopus.lab.pem
        common_name: artifactory-stav.octopus.lab


    - name: Generate a Self Signed OpenSSL certificate
      ansible.builtin.openssl_certificate:
        path: /etc/ssl/crt/artifactory-stav.octopus.lab.crt
        privatekey_path: /etc/ssl/private/artifactory-stav.octopus.lab.pem
        csr_path: /etc/ssl/csr/artifactory-stav.octopus.lab.csr
        provider: selfsigned


    - name: Create a namespace for JFrog Artifactory
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: v1
          kind: Namespace
          metadata:
            name: jfrog


    - name: Create a namespace for JFrog Artifactory
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: v1
          kind: Namespace
          metadata:
            name: jfrog


    - name: Create a deployment for JFrog Artifactory
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: artifactory
            namespace: jfrog
          spec:
            replicas: 1
            selector:
              matchLabels:
                app: artifactory
            template:
              metadata:
                labels:
                  app: artifactory
              spec:
                containers:
                - name: artifactory
                  image: releases-docker.jfrog.io/jfrog/artifactory-pro:7.77.6
                  ports:
                  - containerPort: 8081
                    name: comms
                  - containerPort: 8082
                    name: ui


    - name: Create a service for JFrog Artifactory
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: v1
          kind: Service
          metadata:
            name: artifactory-service
            namespace: jfrog
          spec:
            selector:
              app: artifactory
            ports:
            - name: http
              protocol: TCP
              port: 80
              targetPort: 8082
            - name: docker
              protocol: TCP
              port: 8081
              targetPort: 8081


    - name: Fetch the certificate from the remote host
      ansible.builtin.fetch:
        src: /etc/ssl/crt/docker-stav.octopus.lab.crt
        dest: /tmp/docker-stav.octopus.lab.crt
        flat: yes


    - name: Fetch the private key from the remote host
      ansible.builtin.fetch:
        src: /etc/ssl/private/docker-stav.octopus.lab.pem
        dest: /tmp/docker-stav.octopus.lab.pem
        flat: yes


    - name: Create a secret for TLS
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: v1
          kind: Secret
          metadata:
            name: artifactory-tls
            namespace: jfrog
          type: kubernetes.io/tls
          data:
            tls.crt: "{{ lookup('file', '/tmp/docker-stav.octopus.lab.crt') | b64encode }}"
            tls.key: "{{ lookup('file', '/tmp/docker-stav.octopus.lab.pem') | b64encode }}"


    - name: Create an ingress for JFrog Artifactory
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: networking.k8s.io/v1
          kind: Ingress
          metadata:
            name: artifactory-ingress
            namespace: jfrog
            annotations:
              kubernetes.io/ingress.class: "nginx"
          spec:
            tls:
            - hosts:
              - artifactory-stav.octopus.lab
              - docker-stav.octopus.lab
              secretName: artifactory-tls
            rules:
            - host: artifactory-stav.octopus.lab
              http:
                paths:
                - pathType: Prefix
                  path: "/"
                  backend:
                    service:
                      name: artifactory-service
                      port:
                        number: 80


    - name: Create a ingress for Jfrog comms
      ansible.builtin.k8s:
        kubeconfig: /home/ansible/.kube/config
        state: present
        definition:
          apiVersion: networking.k8s.io/v1
          kind: Ingress
          metadata:
            name: artifactory-ingress-comms
            namespace: jfrog
            annotations:
              kubernetes.io/ingress.class: "nginx"
              ingress.kubernetes.io/force-ssl-redirect: "true"
              ingress.kubernetes.io/proxy-body-size: "0"
              ingress.kubernetes.io/proxy-read-timeout: "600"
              ingress.kubernetes.io/proxy-send-timeout: "600"
              nginx.org/client-max-body-size: "0"
              nginx.ingress.kubernetes.io/configuration-snippet: |
                proxy_set_header    X-JFrog-Override-Base-Url http://docker-stav.octopus.lab;
              nginx.ingress.kubernetes.io/proxy-body-size: "0"
          spec:
            tls:
            - hosts:
              - artifactory-stav.octopus.lab
              - docker-stav.octopus.lab
              secretName: artifactory-tls
            rules:
            - host: docker-stav.octopus.lab
              http:
                paths:
                - pathType: Prefix
                  path: "/"
                  backend:
                    service:
                      name: artifactory-service
                      port:
                        number: 8081


    - name: Extract ingress IP
      ansible.builtin.command: "kubectl get ingress -n jfrog artifactory-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
      register: ingress_ip


    - name: Apply to hosts file
      ansible.builtin.lineinfile:
        path: /etc/hosts
        line: "{{ ingress_ip.stdout }} artifactory-stav.octopus.lab"
        state: present


    - name: Apply coms to hosts file
      ansible.builtin.lineinfile:
        path: /etc/hosts
        line: "{{ ingress_ip.stdout }} docker-stav.octopus.lab"
        state: present


    - name: Copy to crt to Docker control plane
      ansible.builtin.shell: |
        docker cp /etc/ssl/crt/docker-stav.octopus.lab.crt kind-cluster-control-plane:/etc/ssl/certs
        docker exec kind-cluster-control-plane update-ca-certificates
        docker exec kind-cluster-control-plane systemctl restart containerd
      become: yes


    - name: Copy to crt to Docker worker
      ansible.builtin.shell: |
        docker cp /etc/ssl/crt/docker-stav.octopus.lab.crt kind-cluster-worker:/etc/ssl/certs
        docker exec kind-cluster-worker update-ca-certificates
        docker exec kind-cluster-worker systemctl restart containerd
      become: yes


    - name: Copy to crt to Docker worker2
      ansible.builtin.shell: |
        docker cp /etc/ssl/crt/docker-stav.octopus.lab.crt kind-cluster-worker2:/etc/ssl/certs
        docker exec kind-cluster-worker2 update-ca-certificates
        docker exec kind-cluster-worker2 systemctl restart containerd
      become: yes


    - name: Allow it through SE Linux with became
      ansible.builtin.seboolean:
        name: httpd_can_network_connect
        state: yes
        persistent: yes
      become: yes


    - name: Allow ports through firewall
      ansible.builtin.firewalld:
        port: "{{ item }}"
        permanent: yes
        state: enabled
        immediate: yes
      loop:
        - 80/tcp
        - 8081/tcp
        - 8082/tcp
      become: yes
```
entering the gui via: artifactory-stav.octopus.lab
default username and password - admin:password
and your license, and then create a docker repository named - docker-local.

* Create a flask.yml file (The flask application playbook):

### flask.yaml:
```
- hosts: devops
  tasks:
    - name: Create Flask application directory
      ansible.builtin.file:
        path: /home/ansible/flask
        state: directory
        mode: '0755'


    - name: Create a basic Flask application with one API endpoint (/api/message) thats return simple JSON response
      ansible.builtin.copy:
        content: |
          from flask import Flask, jsonify
          app = Flask(__name__)


          @app.route('/api/message', methods=['GET'])
          def message():
              return jsonify({'message': 'Hello, World!'})


          if __name__ == '__main__':
              app.run(host='0.0.0.0', port=5000)
        dest: /home/ansible/flask/app.py


    - name: Create a Dockerfile for the Flask application
      ansible.builtin.copy:
        content: |
          FROM python:3.8-slim
          WORKDIR /app
          COPY . /app
          RUN pip install --no-cache-dir flask
          EXPOSE 5000
          CMD ["python", "app.py"]
        dest: /home/ansible/flask/Dockerfile


    - name: Create a Docker image for the Flask application
      ansible.builtin.docker_image:
        name: flask-app
        tag: latest
        source: build
        build:
          path: /home/ansible/flask


    - name: login and push image
      ansible.builtin.shell: |
        docker login docker-stav.octopus.lab -u admin -p Password1
        docker tag flask-app docker-stav.octopus.lab/docker-local/flask-app:latest
        docker push docker-stav.octopus.lab/docker-local/flask-app:latest
```
* afterwards create a k8s.yml (The kubernetes deployment of the application)
```
- hosts: devops
  become: yes
  tasks:
    - name: Create a namespace for application
      ansible.builtin.k8s:
        definition:
          apiVersion: v1
          kind: Namespace
          metadata:
            name: flask-app


    - name: create a secret for the docker registry
      ansible.builtin.shell:
        cmd: |
          kubectl create secret docker-registry regcred \
          --docker-server=docker-stav.octopus.lab \
          --docker-username=admin \
          --docker-password=Password1 \
          --docker-email=your-email@example.com \
          -n flask-app


    - name: Create deployment and pull from docker-stav.octopus.lab/docker-local/flask-app:latest (use imagepullsecret)
      ansible.builtin.k8s:
        definition:
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: flask-app
            namespace: flask-app
          spec:
            replicas: 1
            selector:
              matchLabels:
                app: flask-app
            template:
              metadata:
                labels:
                  app: flask-app
              spec:
                containers:
                  - name: flask-app
                    image: docker-stav.octopus.lab/docker-local/flask-app:latest
                    ports:
                      - containerPort: 5000
                imagePullSecrets:
                  - name: regcred


    - name: Create a service for the Flask application
      ansible.builtin.k8s:
        definition:
          apiVersion: v1
          kind: Service
          metadata:
            name: flask-app
            namespace: flask-app
          spec:
            selector:
              app: flask-app
            ports:
              - protocol: TCP
                port: 80
                targetPort: 5000
            type: ClusterIP


    - name: Create ingress for the Flask application
      ansible.builtin.k8s:
        definition:
          apiVersion: networking.k8s.io/v1
          kind: Ingress
          metadata:
            name: flask-app
            namespace: flask-app
            annotations:
              kubernetes.io/ingress.class: "nginx"
          spec:
            rules:
              - host: flask-app.octopus.lab
                http:
                  paths:
                    - path: /
                      pathType: Prefix
                      backend:
                        service:
                          name: flask-app
                          port:
                            number: 80


    - name: Extract IP of the flask ingress
      ansible.builtin.command: "kubectl get ingress -n flask-app flask-app -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
      register: ingress


    - name: add to /etc/hosts
      ansible.builtin.lineinfile:
        path: /etc/hosts
        line: "{{ ingress.stdout }} flask-app.octopus.lab"
        state: present


    - name: Allow it through SE Linux with became
      ansible.builtin.seboolean:
        name: httpd_can_network_connect
        state: yes
        persistent: yes
      become: yes


    - name: Allow ports through firewall
      ansible.builtin.firewalld:
        port: "{{ item }}"
        permanent: yes
        state: enabled
        immediate: yes
      loop:
        - 80/tcp
        - 5000/tcp
```
and then you can access the app through the flask-app.octopus.lab

7. Lets create the rule running the command: 
```
$ ansible-galaxy init jfrog_flask_automate
```
Move the plays onto the tasks folder and configure the main.yml to this:
```
- name: Setup
  include_tasks: setup.yml


- name: Jfrog
  include_tasks: jfrog.yml
  register: jfrog_output


- name: Prompt user for input
  pause:
    prompt: "Please go to stav-artifactory.octopus.lab and create a docker-repository with your jfrog license. Afterwards, press 1 to continue."
  register: user_input


- name: Continue if user pressed 1
  debug:
    msg: "Continuing with the playbook..."
  when: user_input.user_input | int == 1


- name: Flask
  include_tasks: flask.yml


- name: Kubernetes
  include_tasks: kubernetes.yml
```