# Introduction
In the world of project management, having your own code repository brings security and ease of use. MkDocs simplifies documentation creation, while Nginx Reverse Proxy ensures secure access. In this guide, we'll show you how to deploy gogs git server with mkdocs and nginx reverse proxy locally, streamlining collaboration and documentation processes. Let's get started.

---
|Nginx Reverse Proxy                | What is MkDocs                        |What is Gogs                         |
|----------------|-------------------------------|-----------------------------|
|Nginx reverse proxy is a server software that sits in front of web servers, intercepting requests from clients and forwarding them to the appropriate backend servers.|MkDocs is a user-friendly static site generator tailored for crafting documentation websites. It simplifies the creation of professional-looking documentation using Markdown|Gogs, short for Go Git Service, is a lightweight, self-hosted Git service written in Go. It’s designed for easy repository management, code collaboration, and issue tracking.|
--- 
### Prerequisites
* RHEL machine with sudo privileges
* Basic familiarity with terminal commands

### Deploying Gogs
* Starting off with updating and upgrading our machine
```
$ sudo dnf update && sudo dnf upgrade
``` 
* Install required prerequisites
```
# Install Git
$ sudo dnf install git
# Downloading Go
$ wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz
# Removing any previous go installation 
$ rm -rf /usr/local/go && tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz
# Add to path variable
$ export PATH=$PATH:/usr/local/go/bin
``` 
* Gogs Installation
```
$ sudo adduser -r -m -s /sbin/nologin -c 'Gogs' git # Creating User

$ wget https://dl.gogs.io/0.13.0/gogs_0.13.0_linux_amd64.tar.gz

$ sudo tar xf gogs_0.13.0_linux_amd64.tar.gz -C /home/git

$ sudo chown -R git: /home/git/gogs

$ sudo cp /home/git/gogs/scripts/systemd/gogs.service /etc/systemd/system



$ sudo systemctl daemon-reload
$ sudo systemctl start gogs
$ sudo systemctl enable gogs
```

* Configuring through the GUI

After starting the Gogs service, access the GUI installation via localhost:3000. Choose the SQLite database type as our database

![GogsGUI](../resources/Gogs%20Git%20Server%20and%20Nginx/GogsGUI.png)<br>

Afterwards, for our domain, we’ll switch to our own domain. I choose         “gogs-stav” and change our application URL to your desired URL

![GogsGUI](../resources/Gogs%20Git%20Server%20and%20Nginx/GogsDomain.png)

Finally, create an admin account by clicking on “Admin Account Settings” and then click “Install Gogs”. After that, create a repository called “mkdocs”

![GogsGUI](../resources/Gogs%20Git%20Server%20and%20Nginx/GogsInstall.png)
![GogsGUI](../resources/Gogs%20Git%20Server%20and%20Nginx/GogsRepo.png)

### Deploying MkDocs
* Downloading MkDocs is simple. First, download pip, then use it to install MkDocs
```
sudo dnf install python3-pip
sudo pip3 install mkdocs

Deploying the MkDocs server

mkdocs new my-project
cd my-project
mkdocs serve
```

![cmd](../resources/Gogs%20Git%20Server%20and%20Nginx/GitPush.png)
And now we can access MkDocs via localhost:8000

![web](../resources/Gogs%20Git%20Server%20and%20Nginx/MkDocs.png)

### Pushing To MkDocs To Gogs

Next, we’ll push our MkDocs project to our Gogs Git server. Navigate to our MkDocs directory, initialize, add, and commit the files to our Gogs Git serve
```
git init

git add . 

git commit -m “first commit” 

git remote add origin http://gogs-stav.ort.tamnun.inc:3000/stav/mkdocs.git

git push -u origin master
```

### Configure Nginx
Finally, We need to connect everything to complete this project. Firstly, Download nginx server, add it to the firewall and verify everything is running correctly
```
sudo dnf install nginx
sudo systemctl enable nginx
sudo system start nginx
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload

setsebool -P httpd_can_network_connect 1 # The command enables SELinux to permit Nginx HTTP Server network connections
```

Now, let’s edit the /etc/hosts file on our machine. This file matches fully qualified domain names (FQDNs) with the server’s IP hosting a specific domain. Essentially, whenever you enter your localhost address (127.0.0.1), your machine will be able to resolve it to the Gogs or MkDocs server

```
vi /etc/hosts

# add the following

127.0.0.1 gogs-stav.ort.tamnun.inc
```

To streamline access to your websites, ensure you enter the correct URLs with ports: use :3000 for Gogs and :8000 for MkDocs. To optimize your setup further, integrate these servers with Nginx by modifying the Nginx configuration file. Prioritize safety by backing up the file before any alterations. After editing, execute a syntax check with sudo nginx -t and then restart the Nginx server using sudo systemctl restart nginx. Ensure that your configuration encompasses server blocks for each server listening on port 80. Each block should include server_name and proxy_pass directives to appropriately route incoming requests

![nginx](../resources/Gogs%20Git%20Server%20and%20Nginx/NginxConf.png)

### Congratulations

Congratulations! You’ve successfully completed the setup, configuration, and integration of Gogs Git Server, MkDocs, and Nginx on your local environment


