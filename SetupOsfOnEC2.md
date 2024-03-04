# aws-xray-evaluation

## Quick Start Guide

For setting up this project on your local environment, follow these steps:

### 1. Change to Project Directory

Setup for git:
```bash
git config --global user.name 'Your github account name' 
git config --global user.email 'Your email address'        
git config --global core.editor 'code --wait'
git config --global merge.tool 'code --wait "$MERGED"'
git config --global push.default simple
git config --list  # githuconfig confirmation 
```

You need generate and register your github token in your gitconfig.

link: https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

Navigate to the project root directory:
```bash
cd aws-xray-evaluation
git clone https://github.com/RCOSDP/RDM-osf.io.git
git clone https://github.com/RCOSDP/RDM-ember-osf-web.git
git clone https://github.com/RCOSDP/RDM-modular-file-renderer.git
git clone https://github.com/RCOSDP/RDM-waterbutler.git
```


### 2. Docker Build
setup docker and docker compose.

link: https://docs.docker.jp/v1.12/compose/install.html

link: https://docs.docker.com/engine/install/ubuntu/

Build Docker images for each module:
```bash
sudo docker build RDM-ember-osf-web -t rdm-osf-web:dev
sudo docker build RDM-modular-file-renderer -t rdm-mfr:dev
sudo docker build RDM-waterbutler -t rdm-wb:dev
sudo docker build fakecas -t rdm-fakecas:dev
sudo docker build RDM-osf.io -t rdm-osf:dev
```

### 3. Setup Loopback Interface


Configure your loopback interface on your machine:
```bash
sudo apt install net-tools
sudo ifconfig lo:0 192.168.168.167 netmask 255.255.255.255 up
```

### 4. Change to Module Directory

Navigate to the module directory:
```bash
cd aws-xray-evaluation/RDM-osf.io/
```

### 5. Copy Local Settings

Copy the local settings of the project:
```bash
cp ./website/settings/local-dist.py ./website/settings/local.py
cp ./api/base/settings/local-dist.py ./api/base/settings/local.py
cp ./admin/base/settings/local-dist.py ./admin/base/settings/local.py
cp ./tasks/local-dist.py ./tasks/local.py
```

### 6. Docker Compose Up Requirements

Ensure you have the required services running:
```bash
sudo docker-compose up requirements wb_requirements mfr_requirements
```

### 7. Start Core Component Services (Detached)

Spin up denpent services:
```bash
sudo docker-compose up -d elasticsearch elasticsearch6 postgres mongo rabbitmq
```

### 8. Assets Setup

Remove your existing node_modules and start the assets:
```bash
sudo rm -Rf ./node_modules
sudo rm -Rf ./website/static/vendor/bower_components
sudo rm -Rf ./admin/node_modules
sudo rm -Rf ./admin/static/vendor/bower_components
sudo docker-compose up assets admin_assets
```

### 9. More Services

Start additional services:
```bash
sudo docker-compose up -d unoconv mfr wb fakecas sharejs
```

### 10. Database Migration
When starting with an empty database you will need to run migrations and populate preprint providers. 
Perform database migrations:
```bash
sudo docker-compose run --rm web python3 manage.py migrate
```
See the [Running arbitrary commands](RDM-osf.io/README-docker-compose.md#running-arbitrary-commands) section below for instructions.

### 11. Run the Project

Finally start the OSF Web, API Server, and Preprints (Detached):
```bash
sudo docker-compose up -d wb_worker worker web api admin preprints ember_osf_web registries reviews
```

Once you follow these steps, you should have a local environment up and running for development.

## Configuration Guide

### 1. Let's Encrypt Setup
**Configure AWS Credentials**

Use the AWS CLI Docker image to configure your AWS credentials:

```bash
sudo docker run --rm -it -v "/root/.aws:/root/.aws" amazon/aws-cli configure
```
**Verify AWS Credentials**

Verify if your AWS credentials are working and have nominal access to Route 53:

```
sudo docker run --rm -it -v "/root/.aws:/root/.aws" amazon/aws-cli route53 list-hosted-zones
```
**Request a Let's Encrypt Wildcard Certificate**

Use the certbot/dns-route53 Docker image to request a wildcard certificate, forwarding your AWS credentials:
Nii has a Certificate Management Service link: https://certs.nii.ac.jp/ . You can contact to them if your service is created on NII infrastructure.
```
certbot certonly --dns-route53 --domain "your.com" --domain "*.your.com"
```

**Automate Certificate Renewal**

Create systemd timer to automate certificate renewal, then daemon-reload, enable, and start the timer.
Create /etc/systemd/system/certbot.service. For the docker command, remove --it for non-interactive execution by systemd, and pass /usr/bin to the container to allow execution of systemctl by --deploy-hook:
```
[Unit]
Description=Let's Encrypt certificate renewal

[Service]
Type=oneshot
ExecStart=certbot renew --dns-route53 --quiet --agree-tos --deploy-hook "cd /home/ubuntu/aws-xray-evaluation/RDM-osf.io && sudo docker-compose restart web admin wb fakecas ember_osf_web  preprints registries reviews"
```

Then create /etc/systemd/system/certbot.timer:
```
[Unit]
Description=Monthly renewal of Let's Encrypt certificates

[Timer]
OnCalendar=monthly
RandomizedDelaySec=12 hours
Persistent=true

[Install]
WantedBy=timers.target
```

### 2. User Management
**Create User**

Method 1:
Create a user via register link: https://EC2-url:5000/register/

Method 2:
Create a user directly through the RDM shell.
```bash
docker-compose run --rm web invoke shell
```
Create an OSF User with python code:
```python
user = OSFUser.create(username=<your_user@cos.io>,password=<password>,fullname=<full name>)
```
> **Note:** User's registration status is to be shifted to True by adding `user.is_registered = True` `user.have_email = True` and `user.date_confirmed = timezone.now()`. Due to the lack of an inherited mail server in local environment, the newly created account is unable to send confirmation emails making the account unconfirmed.

Save your user with `user.save()`
Commit the changes with `commit()`

**Admin User**

Please refer to [RDM-osf.io/admin/README.md](RDM-osf.io/admin/README.md) for instructions on how to make existing user super admin.
